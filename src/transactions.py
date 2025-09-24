import logging
import pandas as pd

from abc import ABC, abstractmethod
from typing import Dict, Optional

# Internal Imports
from domain import Bucket


class Transaction(ABC):
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

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return 0


class FixedTransaction(Transaction):
    def __init__(
        self, df: pd.DataFrame, taxable_eligibility: Optional[pd.Period] = None
    ):
        self.df = df.copy()
        self.df["Date"] = pd.to_datetime(self.df["Date"])
        self.taxable_eligibility = (
            taxable_eligibility
            if isinstance(taxable_eligibility, pd.Period)
            else (
                pd.to_datetime(taxable_eligibility).to_period("M")
                if taxable_eligibility is not None
                else None
            )
        )

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        # find any rows that happen in this month
        hits = self.df[self.df["Date"].dt.to_period("M") == tx_month]
        for _, row in hits.iterrows():
            bucket_name = str(row.get("Bucket", "Cash")).strip()
            if bucket_name not in buckets:
                logging.warning(f"{tx_month} — Bucket '{bucket_name}' not found")
                continue

            amount = int(row["Amount"])
            bucket = buckets[bucket_name]

            if amount >= 0:
                # a true inflow
                bucket.deposit(amount)
            else:
                # an outflow: try to withdraw from the bucket
                needed = -amount

                # Pre-eligibility gating: if bucket is tax-advantaged and we're before eligibility,
                # route withdrawal to Cash instead of touching the tax-advantaged bucket.
                if (
                    self.taxable_eligibility is not None
                    and getattr(bucket, "bucket_type", None)
                    in {"tax_free", "tax_deferred"}
                    and tx_month < self.taxable_eligibility
                ):
                    buckets["Cash"].withdraw(needed)
                    logging.debug(
                        f"[Pre-eligibility] {tx_month} — Routed withdrawal ${needed:,} from {bucket_name} to Cash (bucket_type={bucket.bucket_type})"
                    )
                    continue

                withdrawn = bucket.withdraw(needed)
                shortfall = needed - withdrawn

                if shortfall > 0:
                    # route any shortfall back to Cash
                    buckets["Cash"].withdraw(shortfall)
                    logging.debug(
                        f"[Fallback] {tx_month} — ${shortfall:,} pulled from Cash for '{bucket_name}'"
                    )


class RecurringTransaction(Transaction):
    def __init__(
        self, df: pd.DataFrame, taxable_eligibility: Optional[pd.Period] = None
    ):
        self.df = df.copy()
        self.df["Start Date"] = pd.to_datetime(self.df["Start Date"])
        self.df["End Date"] = pd.to_datetime(self.df["End Date"], errors="coerce")
        self.taxable_eligibility = (
            taxable_eligibility
            if isinstance(taxable_eligibility, pd.Period)
            else (
                pd.to_datetime(taxable_eligibility).to_period("M")
                if taxable_eligibility is not None
                else None
            )
        )

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        for _, row in self.df.iterrows():
            start = row["Start Date"].to_period("M")
            end = row["End Date"].to_period("M") if pd.notna(row["End Date"]) else None
            if not (start <= tx_month and (end is None or tx_month <= end)):
                continue

            bucket_name = str(row.get("Bucket", "Cash")).strip()
            if bucket_name not in buckets:
                logging.warning(f"{tx_month} — Bucket '{bucket_name}' not found")
                continue

            amount = int(row["Amount"])
            bucket = buckets[bucket_name]

            if amount >= 0:
                bucket.deposit(amount)
            else:
                needed = -amount

                # Pre-eligibility gating: if bucket is tax-advantaged and we're before eligibility,
                # route withdrawal to Cash instead of touching the tax-advantaged bucket.
                if (
                    self.taxable_eligibility is not None
                    and getattr(bucket, "bucket_type", None)
                    in {"tax_free", "tax_deferred"}
                    and tx_month < self.taxable_eligibility
                ):
                    buckets["Cash"].withdraw(needed)
                    logging.debug(
                        f"[Pre-eligibility] {tx_month} — Routed recurring withdrawal ${needed:,} from {bucket_name} to Cash (bucket_type={bucket.bucket_type})"
                    )
                    continue

                withdrawn = bucket.withdraw(needed)
                shortfall = needed - withdrawn

                if shortfall > 0:
                    buckets["Cash"].withdraw(shortfall)
                    logging.debug(
                        f"[Fallback] {tx_month} — ${shortfall:,} pulled from Cash for '{bucket_name}'"
                    )


class RothConversionTransaction(Transaction):
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

        src = buckets[self.source_bucket]
        tgt = buckets[self.target_bucket]

        available = src.balance()
        if available <= 0:
            return

        to_convert = min(available, self.monthly_target)
        if to_convert <= 0:
            return

        self.amount = to_convert
        withdrawn = src.withdraw(to_convert)
        tgt.deposit(withdrawn)

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return self.amount if getattr(self, "is_tax_deferred", False) else 0

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return self.amount if getattr(self, "is_taxable", False) else 0


class SalaryTransaction(Transaction):
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
            bucket.deposit(amount)

        if tx_month == self.bonus_period:
            bucket = buckets.get(list(self.bucket_pcts.keys())[0])
            if bucket is None:
                return
            bucket.deposit(self.annual_bonus)

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


class SocialSecurityTransaction(Transaction):
    def __init__(
        self, start_date: str, monthly_amount: int, pct_cash: float, cash_bucket: str
    ):
        self.start_month = pd.to_datetime(start_date).to_period("M")
        self.monthly_amount = monthly_amount
        self.cash_amt = int(round(monthly_amount * pct_cash))
        self.cash_bucket = cash_bucket

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        if tx_month >= self.start_month:
            buckets[self.cash_bucket].deposit(self.cash_amt)

    def get_social_security(self, tx_month: pd.Period) -> int:
        return self.monthly_amount if tx_month >= self.start_month else 0


class TaxDeferredTransaction(Transaction):
    is_tax_deferred = True

    def __init__(
        self,
        annual_gross: int,
        annual_bonus: int,
        bonus_date: str,
        target_bucket: str,
        retirement_date: str,
    ):
        self.monthly_base = annual_gross // 12
        self.remainder = annual_gross - (self.monthly_base * 12)
        self.annual_bonus = annual_bonus
        self.bonus_period = pd.to_datetime(bonus_date).to_period("M")
        self.retirement_period = pd.to_datetime(retirement_date).to_period("M")
        self.bucket_name = target_bucket

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        if tx_month > self.retirement_period:
            return

        bucket = buckets[self.bucket_name]
        amount = self.monthly_base + (self.remainder if tx_month.month == 12 else 0)
        bucket.deposit(amount)

        if tx_month == self.bonus_period:
            bucket.deposit(self.annual_bonus)

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        if tx_month > self.retirement_period:
            return 0
        base = self.monthly_base + (self.remainder if tx_month.month == 12 else 0)
        return base + (self.annual_bonus if tx_month == self.bonus_period else 0)


class TaxableTransaction(Transaction):
    is_taxable = True

    def __init__(
        self,
        annual_gross: int,
        annual_bonus: int,
        bonus_date: str,
        target_bucket: str,
        retirement_date: str,
        gain_log: Dict[pd.Period, int],
    ):
        self.monthly_base = annual_gross // 12
        self.remainder = annual_gross - (self.monthly_base * 12)
        self.annual_bonus = annual_bonus
        self.bonus_period = pd.to_datetime(bonus_date).to_period("M")
        self.retirement_period = pd.to_datetime(retirement_date).to_period("M")
        self.bucket_name = target_bucket
        self.gain_log = gain_log

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        if tx_month > self.retirement_period:
            return

        bucket = buckets[self.bucket_name]
        amount = self.monthly_base + (self.remainder if tx_month.month == 12 else 0)
        bucket.deposit(amount)

        if tx_month == self.bonus_period:
            bucket.deposit(self.annual_bonus)

        # deposit any realized gain
        gain = self.gain_log.get(tx_month, 0)
        if gain > 0:
            bucket.deposit(gain)

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return self.gain_log.get(tx_month, 0)
