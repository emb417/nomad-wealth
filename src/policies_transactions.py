import pandas as pd

from abc import ABC, abstractmethod
from typing import Dict

# Internal Imports
from buckets import Bucket


class PolicyTransaction(ABC):
    is_tax_deferred: bool = False
    is_taxable: bool = False

    @abstractmethod
    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        pass

    def get_salary(self, tx_month: pd.Period) -> int:
        return 0

    def get_social_security(self, tx_month: pd.Period) -> int:
        return 0

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return 0

    def get_penalty_eligible_withdrawal(self, tx_month: pd.Period) -> int:
        return 0

    def get_realized_gain(self, tx_month: pd.Period) -> int:
        return 0

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return 0

    def get_taxfree_withdrawal(self, tx_month: pd.Period) -> int:
        return 0


class PropertyTransaction(PolicyTransaction):
    def __init__(
        self,
        property_config: Dict,
        inflation_modifiers: Dict[str, Dict[int, Dict[str, float]]],
    ):
        super().__init__()
        self.config = property_config
        self.inflation_modifiers = inflation_modifiers
        self.starting_principal = float(property_config.get("Remaining Principal", 0))
        self.remaining_principal = self.starting_principal
        self.property_owned = self.remaining_principal > 0
        self.source_bucket = "Cash"

    def _inflated(self, key: str, tx_month: pd.Period) -> float:
        base_year = min(
            self.inflation_modifiers.get(key, {}).keys(), default=tx_month.year
        )
        current_year = tx_month.start_time.year
        base_modifier = (
            self.inflation_modifiers.get(key, {})
            .get(base_year, {})
            .get("modifier", 1.0)
        )
        current_modifier = (
            self.inflation_modifiers.get(key, {})
            .get(current_year, {})
            .get("modifier", 1.0)
        )
        return current_modifier / base_modifier

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        property_bucket = buckets.get("Property")
        if property_bucket is None or property_bucket.balance() <= 0:
            return

        cash = buckets["Cash"]

        # Inflation multipliers
        tax_infl = self._inflated("Property Taxes", tx_month)
        insurance_infl = self._inflated("Home Insurance", tx_month)
        maintenance_infl = self._inflated("Home Maintenance", tx_month)

        # Maintenance
        home_value = float(self.config.get("Market Value", 0))
        maintenance_rate = float(self.config.get("Annual Maintenance", 0))
        maintenance_base = home_value * maintenance_rate / 12
        maintenance_payment = maintenance_base * maintenance_infl
        cash.withdraw(int(round(maintenance_payment)), "Property Maintenance", tx_month)

        # Mortgage logic
        apr = float(self.config.get("Mortgage APR", 0))
        monthly_p_and_i = float(self.config.get("Monthly Principal and Interest", 0))
        monthly_interest = self.remaining_principal * (apr / 12)
        principal_payment = monthly_p_and_i - monthly_interest

        # Escrow components (inflated)
        tax_base = float(self.config.get("Monthly Taxes", 0))
        insurance_base = float(self.config.get("Monthly Insurance", 0))
        tax_payment = tax_base * tax_infl
        insurance_payment = insurance_base * insurance_infl
        escrow_payment = tax_payment + insurance_payment

        if self.remaining_principal > 0:
            if self.remaining_principal <= principal_payment:
                final_p_and_i = self.remaining_principal + monthly_interest
                final_total = final_p_and_i + escrow_payment
                cash.withdraw(int(round(final_total)), "Property Mortgage", tx_month)
                self.remaining_principal = 0
            else:
                total_payment = monthly_p_and_i + escrow_payment
                cash.withdraw(int(round(total_payment)), "Property Mortgage", tx_month)
                self.remaining_principal = max(
                    0, self.remaining_principal - principal_payment
                )

        # Escrow logic after payoff
        if self.remaining_principal == 0:
            cash.withdraw(int(round(tax_payment)), "Property Tax", tx_month)
            cash.withdraw(int(round(insurance_payment)), "Property Insurance", tx_month)


class RefillTransaction(PolicyTransaction):
    """
    Internal refill transaction:
      - uses Bucket.transfer for clean internal movement
      - records tax flags only (tax accounting done elsewhere)
      - estimates taxable gains for withdrawals from taxable buckets
    """

    def __init__(
        self,
        source: str,
        target: str,
        amount: int,
        is_tax_deferred: bool = False,
        is_taxable: bool = False,
        is_penalty_applicable: bool = False,
    ):
        super().__init__()
        self.source = source
        self.target = target
        self.amount = int(amount)
        self.is_tax_deferred = bool(is_tax_deferred)
        self.is_taxable = bool(is_taxable)
        self.is_penalty_applicable = bool(is_penalty_applicable)
        # runtime-applied amounts and estimated gains (set by apply)
        self._applied_amount: int = 0
        self._taxable_gain: int = 0
        self._realized_gain: int = 0
        self._taxfree_amount: int = 0

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        src = buckets.get(self.source)
        tgt = buckets.get(self.target)
        self._applied_amount = 0
        self._taxable_gain = 0
        self._realized_gain = 0
        self._taxfree_amount = 0

        if src is None or tgt is None or self.amount <= 0:
            return

        # Use internal transfer for refill
        applied = src.transfer(self.amount, tgt, tx_month)
        self._applied_amount = applied

        # Estimate taxable gain if applicable
        if (
            getattr(src, "bucket_type", None) == "taxable"
            and self.is_taxable
            and applied > 0
        ):
            self._taxable_gain = int(round(applied * 0.5))
            self._realized_gain = int(round(applied))

        if getattr(src, "bucket_type", None) == "tax_free" and applied > 0:
            self._taxfree_amount = int(round(applied))

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return self._applied_amount if self.is_tax_deferred else 0

    def get_realized_gain(self, tx_month: pd.Period) -> int:
        return self._realized_gain

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return self._taxable_gain

    def get_penalty_eligible_withdrawal(self, tx_month: pd.Period) -> int:
        return (
            self._applied_amount
            if self.is_tax_deferred and self.is_penalty_applicable
            else 0
        )

    def get_taxfree_withdrawal(self, tx_month: pd.Period) -> int:
        return self._taxfree_amount


class RentTransaction(PolicyTransaction):
    def __init__(
        self,
        monthly_amount: int,
        annual_infl: Dict[int, Dict[str, float]],
        description_key: str = "Rent",
    ):
        super().__init__()
        self.monthly_amount = int(monthly_amount)
        self.source_bucket = "Cash"
        self.condition_bucket = "Property"
        self.annual_infl = annual_infl
        self.description_key = description_key
        self.nominal_monthly_amount = int(monthly_amount)

    def _inflated_amount_for_month(self, tx_month: pd.Period) -> int:
        if not self.annual_infl:
            return self.nominal_monthly_amount

        base_year = min(self.annual_infl.keys())
        # if we have a recorded start year for the transaction, you could store it; otherwise use the first available year
        start_year = base_year
        current_year = tx_month.start_time.year
        base_modifier = self.annual_infl.get(start_year, {}).get("modifier", 1.0)
        current_modifier = self.annual_infl.get(current_year, {}).get("modifier", 1.0)
        try:
            inflation_multiplier = current_modifier / base_modifier
        except Exception:
            inflation_multiplier = 1.0
        return int(round(self.nominal_monthly_amount * inflation_multiplier))

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        cond = buckets.get(self.condition_bucket)
        if cond is None or cond.balance() > 0:
            return

        src = buckets.get(self.source_bucket)
        if src is None:
            return

        amt = self._inflated_amount_for_month(tx_month)
        src.withdraw(amt, "Rent", tx_month)


class RequiredMinimumDistributionTransaction(PolicyTransaction):
    DEFAULT_DIVISOR_TABLE = {
        70: 27.4,
        71: 26.5,
        72: 25.6,
        73: 24.7,
        74: 23.8,
        75: 22.9,
        76: 22.0,
        77: 21.2,
        78: 20.3,
        79: 19.5,
        80: 18.7,
        81: 17.9,
        82: 17.1,
        83: 16.3,
        84: 15.5,
        85: 14.8,
        86: 14.1,
        87: 13.4,
        88: 12.7,
        89: 12.0,
        90: 11.4,
        91: 10.8,
        92: 10.2,
        93: 9.6,
        94: 9.1,
        95: 8.6,
        96: 8.1,
        97: 7.6,
        98: 7.1,
        99: 6.7,
        100: 6.3,
    }

    def __init__(
        self,
        dob: str,
        targets: Dict[str, float],
        start_age: int = 72,
        rmd_month: int = 12,
        monthly_spread: bool = False,
        rounding: str = "monthly",
    ):
        super().__init__()
        self.dob = pd.to_datetime(dob)
        self.targets = targets
        self.start_age = int(start_age)
        self.rmd_month = int(rmd_month)
        self.monthly_spread = monthly_spread
        self.rounding = rounding
        self._cached_annual_rmd: Dict[int, int] = {}
        self._applied_amount: int = 0

    def _age_at_period(self, period: pd.Period) -> int:
        year_diff = period.start_time.year - self.dob.year
        had_birthday = (period.start_time.month, period.start_time.day) >= (
            self.dob.month,
            self.dob.day,
        )
        return year_diff if had_birthday else year_diff - 1

    def _compute_annual_rmd(self, year: int, buckets: Dict[str, Bucket]) -> int:
        if year in self._cached_annual_rmd:
            return self._cached_annual_rmd[year]

        prior_year = year - 1
        total_balance = sum(
            b.balance_at_period_end(prior_year)
            for b in buckets.values()
            if getattr(b, "bucket_type", None) == "tax_deferred"
        )

        age = self._age_at_period(pd.Period(f"{year}-12", freq="M"))
        divisor = self.DEFAULT_DIVISOR_TABLE.get(age, 25.6)
        rmd = int(round(total_balance / divisor)) if divisor > 0 else 0
        self._cached_annual_rmd[year] = rmd
        return rmd

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        year = tx_month.start_time.year
        month = tx_month.start_time.month
        age = self._age_at_period(tx_month)
        self._applied_amount = 0

        if age < self.start_age:
            return
        if not self.monthly_spread and month != self.rmd_month:
            return
        if self.monthly_spread and month < self.rmd_month:
            return

        annual_rmd = self._compute_annual_rmd(year, buckets)
        months_to_spread = max(1, 13 - self.rmd_month)
        amount = (
            annual_rmd
            if not self.monthly_spread
            else int(round(annual_rmd / months_to_spread))
        )

        # Aggregate all tax-deferred sources
        sources = [
            b
            for b in buckets.values()
            if getattr(b, "bucket_type", None) == "tax_deferred"
        ]

        # Distribute RMD across target buckets based on percentage
        for tgt_name, pct in self.targets.items():
            if pct <= 0:
                continue
            tgt_bucket = buckets.get(tgt_name)
            if not tgt_bucket:
                continue

            target_amount = int(round(amount * pct))
            remaining = target_amount

            for src_bucket in sources:
                if remaining <= 0:
                    break
                applied = src_bucket.transfer(remaining, tgt_bucket, tx_month)
                self._applied_amount += applied
                remaining -= applied

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return self._applied_amount

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return 0

    def get_penalty_eligible_withdrawal(self, tx_month: pd.Period) -> int:
        return 0


class RothConversionTransaction(PolicyTransaction):
    """
    Dynamically convert from Tax-Deferred → Roth bucket,
    maximizing conversions without exceeding a user-defined marginal tax rate.

    Each conversion is treated as a tax-deferred withdrawal (ordinary income).
    """

    is_tax_deferred = True

    def __init__(
        self,
        source_bucket: str,
        target_bucket: str,
    ):
        super().__init__()
        self.source_bucket = source_bucket
        self.target_bucket = target_bucket

    def apply(
        self, buckets: Dict[str, Bucket], tx_month: pd.Period, amount: int
    ) -> int:
        src = buckets.get(self.source_bucket)
        tgt = buckets.get(self.target_bucket)
        if src is None or tgt is None or src.balance() <= 0:
            return 0
        return src.transfer(amount, tgt, tx_month)

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return 0  # Roth conversions are penalty free withdrawals

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return 0  # Roth conversions are not capital gains

    def get_penalty_eligible_withdrawal(self, tx_month: pd.Period) -> int:
        return 0  # Roth conversions are exempt from early withdrawal penalties


class SalaryTransaction(PolicyTransaction):
    def __init__(
        self,
        annual_gross: int,
        annual_bonus: int,
        bonus_date: str,
        salary_buckets: Dict[str, float],
        retirement_date: str,
    ):
        self.monthly_base = annual_gross // 12
        self.remainder = annual_gross - (self.monthly_base * 12)
        self.annual_bonus = annual_bonus
        self.bonus_period = pd.to_datetime(bonus_date).to_period("M")
        self.retirement_period = pd.to_datetime(retirement_date).to_period("M")
        self.bucket_pcts = salary_buckets

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        if tx_month > self.retirement_period:
            return

        total = self.monthly_base + (self.remainder if tx_month.month == 12 else 0)
        for bucket_name, pct in self.bucket_pcts.items():
            bucket = buckets.get(bucket_name)
            if bucket is None:
                continue

            amount = int(round(total * pct))
            bucket.deposit(amount, "Salary", tx_month)

        if tx_month == self.bonus_period:
            bucket = buckets.get(list(self.bucket_pcts.keys())[0])
            if bucket is None:
                return
            bucket.deposit(self.annual_bonus, "Salary Bonus", tx_month)

    def get_salary(self, tx_month: pd.Period) -> int:
        if tx_month > self.retirement_period:
            return 0

        total = sum(
            int(round(self.monthly_base * pct))
            for bucket_name, pct in self.bucket_pcts.items()
            if bucket_name.lower() != "tax-deferred"
        )

        if tx_month == self.bonus_period:
            total += self.annual_bonus

        return total


class SEPPTransaction(PolicyTransaction):
    """
    Transfer a fixed SEPP withdrawal amount from a tax-deferred source to a target bucket.

    The SEPP amount is calculated externally (e.g., in ForecastEngine) based on IRS RMD method.
    """

    is_tax_deferred = True
    is_taxable = False  # SEPP withdrawals are ordinary income but penalty-exempt

    def __init__(self, source_bucket: str, target_bucket: str):
        super().__init__()
        self.source_bucket = source_bucket
        self.target_bucket = target_bucket
        self._monthly_withdrawals: Dict[pd.Period, int] = {}

    def apply(
        self, buckets: Dict[str, Bucket], tx_month: pd.Period, amount: int
    ) -> int:
        src = buckets.get(self.source_bucket)
        tgt = buckets.get(self.target_bucket)
        if src is None or tgt is None or src.balance() <= 0:
            return 0
        applied = src.transfer(amount, tgt, tx_month)
        self._monthly_withdrawals[tx_month] = applied
        return applied

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return self._monthly_withdrawals.get(
            tx_month, 0
        )  # SEPP income considered tax-deferred withdrawal

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return 0  # SEPP withdrawals are not capital gains

    def get_penalty_eligible_withdrawal(self, tx_month: pd.Period) -> int:
        return 0  # SEPP withdrawals are exempt from early withdrawal penalties


class SocialSecurityTransaction(PolicyTransaction):
    def __init__(
        self,
        start_date: str,
        monthly_amount: int,
        pct_payout: float,
        target_bucket: str,
        annual_infl: Dict[int, Dict[str, float]],
    ):
        self.start_month = pd.to_datetime(start_date).to_period("M")
        self.nominal_monthly_amount = int(round(monthly_amount))
        self.pct_payout = pct_payout  # store for later use
        self.target_bucket = target_bucket
        self.annual_infl = annual_infl

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        amt = self.get_social_security(tx_month)
        if amt <= 0:
            return

        # deposit scaled amount to cash bucket
        deposit_amt = int(round(amt))
        buckets[self.target_bucket].deposit(deposit_amt, "Social Security", tx_month)

    def get_social_security(self, tx_month: pd.Period) -> int:
        if tx_month < self.start_month:
            return 0

        if not self.annual_infl:
            return int(round(self.nominal_monthly_amount * self.pct_payout))

        base_year = self.start_month.start_time.year
        current_year = tx_month.start_time.year

        base_modifier = self.annual_infl.get(base_year, {}).get("modifier", 1.0)
        current_modifier = self.annual_infl.get(current_year, {}).get("modifier", 1.0)
        inflation_multiplier = current_modifier / base_modifier

        inflated = self.nominal_monthly_amount * inflation_multiplier
        scaled = inflated * self.pct_payout
        return int(round(scaled))
