# external_transactions.py

import logging
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Optional

from buckets import Bucket


class RuleTransaction(ABC):
    is_tax_deferred: bool = False
    is_taxable: bool = False

    @abstractmethod
    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        pass


class FixedTransaction(RuleTransaction):
    def __init__(
        self, df: pd.DataFrame, taxable_eligibility: Optional[pd.Period] = None
    ):
        self.df = df.copy()
        self.df["Month"] = pd.to_datetime(self.df["Month"])
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
        hits = self.df[self.df["Month"].dt.to_period("M") == tx_month]
        for _, row in hits.iterrows():
            bucket_name = str(row.get("Bucket", "Cash")).strip()
            if bucket_name not in buckets:
                logging.warning(f"{tx_month} — Bucket '{bucket_name}' not found")
                continue

            amount = int(row["Amount"])
            bucket = buckets[bucket_name]

            if amount >= 0:
                bucket.deposit(amount, row["Description"], tx_month)
            else:
                needed = -amount
                if (
                    self.taxable_eligibility is not None
                    and getattr(bucket, "bucket_type", None)
                    in {"tax_free", "tax_deferred"}
                    and tx_month < self.taxable_eligibility
                ):
                    buckets["Cash"].withdraw(needed, row["Description"], tx_month)
                    logging.debug(
                        f"[Pre-eligibility] {tx_month} — Routed withdrawal ${needed:,} from {bucket_name} to Cash"
                    )
                    continue

                withdrawn = bucket.withdraw(needed, row["Description"], tx_month)
                shortfall = needed - withdrawn
                if shortfall > 0:
                    buckets["Cash"].withdraw(shortfall, row["Description"], tx_month)
                    logging.debug(
                        f"[Fallback] {tx_month} — ${shortfall:,} pulled from Cash for '{bucket_name}'"
                    )


class RecurringTransaction(RuleTransaction):
    def __init__(
        self,
        df: pd.DataFrame,
        taxable_eligibility: Optional[pd.Period] = None,
        description_inflation_modifiers: Optional[
            Dict[str, Dict[int, Dict[str, float]]]
        ] = None,
    ):
        self.df = df.copy()
        self.df["Start Month"] = pd.to_datetime(self.df["Start Month"]).dt.to_period(
            "M"
        )
        self.df["End Month"] = pd.to_datetime(
            self.df["End Month"], errors="coerce"
        ).dt.to_period("M")
        self.taxable_eligibility = (
            taxable_eligibility
            if isinstance(taxable_eligibility, pd.Period)
            else (
                pd.to_datetime(taxable_eligibility).to_period("M")
                if taxable_eligibility is not None
                else None
            )
        )
        self.description_inflation_modifiers = description_inflation_modifiers or {}

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        for _, row in self.df.iterrows():
            start = row["Start Month"]
            end = row["End Month"] if pd.notna(row["End Month"]) else None
            if not (start <= tx_month and (end is None or tx_month <= end)):
                continue

            bucket_name = str(row.get("Bucket", "Cash")).strip()
            if bucket_name not in buckets:
                logging.warning(f"{tx_month} — Bucket '{bucket_name}' not found")
                continue

            base_year = row["Start Month"].year
            current_year = tx_month.start_time.year
            amount = float(row["Amount"])
            desc = row["Description"]
            inflation_dict = self.description_inflation_modifiers.get(desc, {})

            try:
                base_modifier = inflation_dict.get(base_year, {}).get("modifier", 1.0)
                current_modifier = inflation_dict.get(current_year, {}).get(
                    "modifier", 1.0
                )
                inflation_multiplier = current_modifier / base_modifier
                amount *= inflation_multiplier
            except Exception as e:
                logging.warning(
                    f"{tx_month} — Inflation adjustment failed for '{desc}': {e}"
                )

            amount = int(round(amount))
            bucket = buckets[bucket_name]

            if amount >= 0:
                bucket.deposit(amount, row["Description"], tx_month)
            else:
                needed = -amount
                if (
                    self.taxable_eligibility is not None
                    and getattr(bucket, "bucket_type", None)
                    in {"tax_free", "tax_deferred"}
                    and tx_month < self.taxable_eligibility
                ):
                    buckets["Cash"].withdraw(needed, row["Description"], tx_month)
                    logging.debug(
                        f"[Pre-eligibility] {tx_month} — Routed recurring withdrawal ${needed:,} from {bucket_name} to Cash"
                    )
                    continue

                withdrawn = bucket.withdraw(needed, row["Description"], tx_month)
                shortfall = needed - withdrawn
                if shortfall > 0:
                    buckets["Cash"].withdraw(shortfall, row["Description"], tx_month)
                    logging.debug(
                        f"[Fallback] {tx_month} — ${shortfall:,} pulled from Cash for '{bucket_name}'"
                    )
