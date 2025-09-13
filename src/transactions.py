import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict
from domain import Bucket

class Transaction(ABC):
    @abstractmethod
    def apply(self, date: pd.Timestamp, buckets: Dict[str, Bucket]) -> None:
        """Apply this transaction on the given date to the buckets."""
        pass


class FixedTransaction(Transaction):
    def __init__(self, df: pd.DataFrame):
        # df columns: Date, Type, Amount, [AssetClass], Description
        self.df = df.copy()
        self.df["Date"] = pd.to_datetime(self.df["Date"])

    def apply(self, date, buckets):
        mask = self.df["Date"].dt.to_period("M") == date.to_period("M")
        for _, row in self.df[mask].iterrows():
            amt = int(row["Amount"])
            bucket = buckets[row["Type"]]
            desc   = row.get("Description", "").strip()

            # Target a specific holding if AssetClass is provided
            asset_class = row.get("AssetClass")
            if asset_class and pd.notna(asset_class):
                for h in bucket.holdings:
                    if h.asset_class.name == asset_class:
                        h.amount += amt
                        break
            else:
                # Default: apply to first holding (e.g., cash)
                bucket.holdings[0].amount += amt


class RecurringTransaction(Transaction):
    def __init__(self, df: pd.DataFrame, profile: Dict):
        # df cols: Start Date, End Date, Type, Amount, [AssetClass], Description
        self.df = df.copy()
        self.profile = profile

        # Normalize dates
        self.df["Start Date"] = pd.to_datetime(self.df["Start Date"])
        # Open-ended if End Date blank
        self.df["End Date"] = pd.to_datetime(
            self.df["End Date"].fillna(pd.Timestamp.max)
        )

    def apply(self, date: pd.Timestamp, buckets: Dict[str, Bucket]) -> None:
        period = date.to_period("M")

        # 1) Loop all defined recurring rows
        for _, row in self.df.iterrows():
            start = row["Start Date"].to_period("M")
            end   = row["End Date"].to_period("M")
            if start <= period <= end:
                bucket = buckets[row["Type"]]
                amt    = int(row["Amount"])
                asset_cls = row.get("AssetClass")
                desc   = row.get("Description", "").strip()

                # Target a specific holding if provided
                if asset_cls and pd.notna(asset_cls):
                    for h in bucket.holdings:
                        if h.asset_class.name == asset_cls:
                            h.amount += amt
                            break
                else:
                    bucket.holdings[0].amount += amt

        # 2) Built-in Social Security (if in profile)
        ss_date = pd.to_datetime(self.profile["Social Security Date"])
        if date >= ss_date:
            ss_amt = int(
                self.profile["Social Security Amount"]
                * self.profile["Social Security Percentage"]
            )
            buckets["Cash"].holdings[0].amount += ss_amt
