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
        self,
        df: pd.DataFrame,
        taxable_eligibility: Optional[pd.Period] = None,
        description_inflation_modifiers: Optional[
            Dict[str, Dict[int, Dict[str, float]]]
        ] = None,
        simulation_start_year: Optional[int] = None,
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
        self.description_inflation_modifiers = description_inflation_modifiers or {}
        self.simulation_start_year = (
            simulation_start_year or pd.DatetimeIndex(self.df["Month"]).year.min()
        )

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        hits = self.df[pd.PeriodIndex(self.df["Month"], freq="M") == tx_month]
        for _, row in hits.iterrows():
            bucket_name = str(row.get("Bucket", "Cash")).strip()
            if bucket_name not in buckets:
                logging.warning(f"{tx_month} — Bucket '{bucket_name}' not found")
                continue

            tx_type = row.get("Type", "default")
            inflation_dict = self.description_inflation_modifiers.get(tx_type, {})
            base_year = self.simulation_start_year
            current_year = tx_month.start_time.year

            try:
                base_modifier = inflation_dict.get(base_year, {}).get("modifier", 1.0)
                current_modifier = inflation_dict.get(current_year, {}).get(
                    "modifier", 1.0
                )
                inflation_multiplier = current_modifier / base_modifier
                amount = float(row["Amount"]) * inflation_multiplier
            except Exception as e:
                logging.warning(
                    f"{tx_month} — Inflation adjustment failed for '{tx_type}': {e}"
                )
                amount = float(row["Amount"])

            amount = int(round(amount))
            bucket = buckets[bucket_name]

            if amount == 0:
                continue

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
        simulation_start_year: Optional[int] = None,
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
        self.simulation_start_year = (
            simulation_start_year or pd.DatetimeIndex(self.df["Month"]).year.min()
        )

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

            base_year = self.simulation_start_year
            current_year = tx_month.start_time.year
            amount = float(row["Amount"])
            tx_type = row.get("Type", "default")
            inflation_dict = self.description_inflation_modifiers.get(tx_type, {})

            try:
                base_modifier = inflation_dict.get(base_year, {}).get("modifier", 1.0)
                current_modifier = inflation_dict.get(current_year, {}).get(
                    "modifier", 1.0
                )
                inflation_multiplier = current_modifier / base_modifier
                amount *= inflation_multiplier
            except Exception as e:
                logging.warning(
                    f"{tx_month} — Inflation adjustment failed for '{tx_type}': {e}"
                )

            amount = int(round(amount))
            bucket = buckets[bucket_name]
            if amount == 0:
                continue

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
