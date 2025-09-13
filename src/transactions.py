import pandas as pd
from pandas import Timestamp
from abc import ABC, abstractmethod
from typing import Dict, Optional
from domain import Bucket

class Transaction(ABC):
    @abstractmethod
    def apply(self, buckets: Dict[str, Bucket], date: pd.Timestamp ) -> None:
        """Apply this transaction on the given date to the buckets."""
        pass


class FixedTransaction:
    """
    One‐off cash flows applied to buckets based on the transaction date.
    When forecasting for month M, we look for any fixed transactions
    whose date falls in the prior month’s period.
    """

    def __init__(self, df: pd.DataFrame):
        # Expect columns: Date, Type, Amount, optional AssetClass, optional Description
        self.df = df.copy()
        self.df["Date"] = pd.to_datetime(self.df["Date"])

    def apply(self,
          buckets: Dict[str, Bucket],
          tx_month: pd.Period) -> None:
        """
        Apply all fixed transactions whose Date’s year-month matches tx_month.
        If an AssetClass is provided, target that specific holding;
        otherwise default to the first holding in the bucket.
        
        :param buckets: mapping of bucket name → Bucket instance
        :param tx_month: the period to look back on (forecast_date minus one month)
        """
        # Filter for transactions in the same YYYY-MM as tx_month
        month_period = tx_month.to_timestamp().to_period("M")
        hits = self.df[self.df["Date"].dt.to_period("M") == month_period]

        for _, row in hits.iterrows():
            bucket_name = row["Type"]
            bucket      = buckets[bucket_name]
            amt         = int(row["Amount"])
            asset_class = row.get("AssetClass")

            # Target a specific holding if AssetClass is provided
            if asset_class and pd.notna(asset_class):
                for h in bucket.holdings:
                    if h.asset_class.name == asset_class:
                        h.amount += amt
                        break
            else:
                # Default: apply to first holding (e.g., cash slice)
                bucket.holdings[0].amount += amt


class RecurringTransaction:
    """
    Monthly cash flows applied to buckets based on a start/end range.
    When forecasting for month M, we look for any recurring transactions
    whose window includes the prior month’s period.
    """

    def __init__(self, df: pd.DataFrame):
        # Expect columns: Start Date, End Date, Type, Amount, optional AssetClass, optional Description
        self.df = df.copy()
        self.df["Start Date"] = pd.to_datetime(self.df["Start Date"])
        self.df["End Date"]   = pd.to_datetime(self.df["End Date"], errors="coerce")

    def apply(self,
          buckets: Dict[str, Bucket],
          tx_month: pd.Period) -> None:
        """
        Apply one monthly transaction per rule if tx_month falls within its window.
        :param buckets: mapping of bucket name → Bucket instance
        :param tx_month: the period to look back on (forecast_date minus one month)
        """
        period = tx_month.to_timestamp().to_period("M")
        for _, row in self.df.iterrows():
            start = row["Start Date"].to_period("M")
            end   = row["End Date"].to_period("M") if not pd.isna(row["End Date"]) else None

            if start <= period and (end is None or period <= end):
                bucket = buckets[row["Type"]]
                amt    = int(row["Amount"])
                asset_cls: Optional[str] = row.get("AssetClass")

                # Target a specific holding if AssetClass is provided
                if asset_cls and pd.notna(asset_cls):
                    for h in bucket.holdings:
                        if h.asset_class.name == asset_cls:
                            h.amount += amt
                            break
                else:
                    # Default: apply to first holding slice
                    bucket.holdings[0].amount += amt
                    
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