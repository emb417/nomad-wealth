import pandas as pd
from pandas import Period
from abc import ABC, abstractmethod
from typing import Dict
from domain import Bucket

class Transaction(ABC):
    @abstractmethod
    def apply(self, buckets: Dict[str, Bucket], date: pd.Timestamp ) -> None:
        """Apply this transaction on the given date to the buckets."""
        pass


class FixedTransaction:
    """
    One‐off cash flows keyed by the CSV’s Date/Amount/Bucket columns.
    Always deposits the full amount into bucket.deposit(amount),
    letting the bucket’s own holding-policy split it internally.
    """

    def __init__(self, df: pd.DataFrame):
        # Expect columns: Date, Bucket, Amount, optional Description
        self.df = df.copy()
        self.df["Date"] = pd.to_datetime(self.df["Date"])

    def apply(self,
              buckets: Dict[str, Bucket],
              tx_month: Period) -> None:
        # Filter for any fixed transactions in this YYYY-MM
        hits = self.df[self.df["Date"].dt.to_period("M") == tx_month]

        for _, row in hits.iterrows():
            # 1) pick the bucket name from CSV
            raw_bucket = row.get("Bucket")
            bucket_key = (
                raw_bucket
                if pd.notna(raw_bucket) and str(raw_bucket).strip()
                else "Cash"
            )

            # 2) deposit into the bucket and let it split per its policy
            bucket = buckets[bucket_key]
            amt    = int(row["Amount"])
            bucket.deposit(amt)


class RecurringTransaction:
    """
    Monthly cash flows keyed by Start Date/End Date/Bucket/Amount.
    Fires each month if tx_month ∈ [Start, End].
    """

    def __init__(self, df: pd.DataFrame):
        # Expect columns: Start Date, End Date, Bucket, Amount
        self.df = df.copy()
        self.df["Start Date"] = pd.to_datetime(self.df["Start Date"])
        self.df["End Date"]   = pd.to_datetime(self.df["End Date"], errors="coerce")

    def apply(self,
              buckets: Dict[str, Bucket],
              tx_month: Period) -> None:
        period = tx_month

        for _, row in self.df.iterrows():
            start = row["Start Date"].to_period("M")
            end   = (
                row["End Date"].to_period("M")
                if pd.notna(row["End Date"])
                else None
            )

            if not (start <= period and (end is None or period <= end)):
                continue

            raw_bucket = row.get("Bucket")
            bucket_key = (
                raw_bucket
                if pd.notna(raw_bucket) and str(raw_bucket).strip()
                else "Cash"
            )

            bucket = buckets[bucket_key]
            amt    = int(row["Amount"])
            bucket.deposit(amt)
                    
class SocialSecurityTransaction:
    """
    Models monthly SS inflows beginning on `start_date`.
    Deposits only `pct_cash` × monthly_amount into the cash bucket.
    """

    def __init__(self,
                 start_date: str,
                 monthly_amount: int,
                 pct_cash: float,
                 cash_bucket: str):
        # Month to start SS deposits (inclusive)
        self.start_month = pd.to_datetime(start_date).to_period("M")
        # Precompute integer cash portion
        self.cash_amt    = int(round(monthly_amount * pct_cash))
        self.cash_bucket = cash_bucket

    def apply(self,
          buckets: Dict[str, Bucket],
          tx_month: pd.Period) -> None:
        """
        If tx_month ≥ start_month, add cash_amt to the first holding
        of the designated cash_bucket.
        """
        if tx_month.to_timestamp().to_period("M") < self.start_month:
            return

        bucket = buckets[self.cash_bucket]
        # Default to the first holding slice (e.g. money-market fund)
        bucket.holdings[0].amount += self.cash_amt