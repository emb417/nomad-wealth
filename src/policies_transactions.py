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
    """
    A conditional monthly expense (e.g. rent) that withdraws directly from Cash,
    but only when Property has zero balance.
    """

    def __init__(
        self,
        monthly_amount: int,
    ):
        super().__init__()
        self.monthly_amount = int(monthly_amount)
        self.source_bucket = "Cash"
        self.condition_bucket = "Property"

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        # only pay rent if property is gone
        cond = buckets.get(self.condition_bucket)
        if cond is None or cond.balance() > 0:
            return

        src = buckets.get(self.source_bucket)
        if src is None:
            return

        src.withdraw(self.monthly_amount, "Rental", tx_month)


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
        self, start_date: str, monthly_amount: int, pct_cash: float, cash_bucket: str
    ):
        self.start_month = pd.to_datetime(start_date).to_period("M")
        self.monthly_amount = monthly_amount
        self.cash_amt = int(round(monthly_amount * pct_cash))
        self.cash_bucket = cash_bucket

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        if tx_month >= self.start_month:
            buckets[self.cash_bucket].deposit(
                self.cash_amt, "Social Security", tx_month
            )

    def get_social_security(self, tx_month: pd.Period) -> int:
        return self.monthly_amount if tx_month >= self.start_month else 0
