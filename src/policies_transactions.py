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

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return 0


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

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        src = buckets.get(self.source)
        tgt = buckets.get(self.target)
        self._applied_amount = 0
        self._taxable_gain = 0

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

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return self._applied_amount if self.is_tax_deferred else 0

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return self._taxable_gain

    def get_penalty_eligible_withdrawal(self, tx_month: pd.Period) -> int:
        return (
            self._applied_amount
            if self.is_tax_deferred and self.is_penalty_applicable
            else 0
        )


class RentalTransaction(PolicyTransaction):
    def __init__(
        self,
        monthly_amount: int,
        annual_infl: Dict[int, Dict[str, float]],
        description_key: str = "Rental",
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
        src.withdraw(amt, "Rental", tx_month)


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
        start_age: int = 72,
        rmd_month: int = 12,
        monthly_spread: bool = False,
        rounding: str = "monthly",
    ):
        super().__init__()
        self.dob = pd.to_datetime(dob)
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
        b = buckets.get("Tax-Deferred")
        prior_balance = b.balance_at_period_end(prior_year) if b else 0
        age = self._age_at_period(pd.Period(f"{year}-12", freq="M"))
        divisor = RequiredMinimumDistributionTransaction.DEFAULT_DIVISOR_TABLE.get(
            age, 25.6
        )
        rmd = int(round(prior_balance / divisor)) if divisor > 0 else 0
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
        if self.monthly_spread:
            if self.rounding == "annual":
                base = annual_rmd // months_to_spread
                remainder = annual_rmd - base * months_to_spread
                month_index = month - self.rmd_month
                amount = base + (remainder if month_index == 0 else 0)
            else:
                amount = int(round(annual_rmd / months_to_spread))
        else:
            amount = annual_rmd

        src = buckets.get("Tax-Deferred")
        tgt = buckets.get("Taxable")
        if src and tgt and amount > 0:
            applied = src.transfer(amount, tgt, tx_month)
            self._applied_amount = applied

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return self._applied_amount

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return 0

    def get_penalty_eligible_withdrawal(self, tx_month: pd.Period) -> int:
        return 0


class RothConversionTransaction(PolicyTransaction):
    """
    Gradually convert from Tax-Deferred → Roth bucket,
    beginning at start_date, with a fixed monthly target.
    Stops when source is empty.

    Each month’s converted amount is treated as a tax-deferred
    withdrawal (ordinary income) and also as a taxable gain.
    """

    is_tax_deferred = True

    def __init__(
        self,
        start_date: str,
        monthly_target: int,
        source_bucket: str = "Tax-Deferred",
        target_bucket: str = "Tax-Free",
    ):
        self.start_period = pd.to_datetime(start_date).to_period("M")
        self.monthly_target = monthly_target
        self.source_bucket = source_bucket
        self.target_bucket = target_bucket
        self.amount: int = 0

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        self.amount = 0

        if tx_month < self.start_period:
            return

        src = buckets.get(self.source_bucket)
        tgt = buckets.get(self.target_bucket)
        if src is None or tgt is None:
            return

        available = src.balance()
        if available <= 0:
            return

        to_convert = min(available, self.monthly_target)
        if to_convert <= 0:
            return

        self.amount = src.transfer(to_convert, tgt, tx_month)

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return self.amount if getattr(self, "is_tax_deferred", False) else 0

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return self.amount if getattr(self, "is_taxable", False) else 0

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


class SocialSecurityTransaction(PolicyTransaction):
    def __init__(
        self,
        start_date: str,
        monthly_amount: int,
        pct_cash: float,
        cash_bucket: str,
        annual_infl: Dict[int, Dict[str, float]],
    ):
        self.start_month = pd.to_datetime(start_date).to_period("M")
        self.nominal_monthly_amount = int(round(monthly_amount))
        self.cash_amt = int(round(monthly_amount * pct_cash))
        self.cash_bucket = cash_bucket
        self.annual_infl = annual_infl

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        amt = self.get_social_security(tx_month)
        if amt <= 0:
            return

        # deposit scaled amount to cash bucket
        deposit_amt = int(round(amt))
        buckets[self.cash_bucket].deposit(deposit_amt, "Social Security", tx_month)

    def get_social_security(self, tx_month: pd.Period) -> int:
        if tx_month < self.start_month:
            return 0

        if not self.annual_infl:
            return self.nominal_monthly_amount

        base_year = self.start_month.start_time.year
        current_year = tx_month.start_time.year

        # choose base and current modifiers
        base_modifier = self.annual_infl.get(base_year, {}).get("modifier", 1.0)
        current_modifier = self.annual_infl.get(current_year, {}).get("modifier", 1.0)
        inflation_multiplier = current_modifier / base_modifier

        inflated = int(round(self.nominal_monthly_amount * inflation_multiplier))
        return inflated
