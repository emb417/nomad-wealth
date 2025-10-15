import logging
import pandas as pd

from typing import Dict, List, Optional

# Internal Imports
from buckets import Bucket
from policies_transactions import RefillTransaction


class ThresholdRefillPolicy:
    """
    Refill policy using buckets.json metadata attached to Bucket instances.
    Inline eligibility gating is performed using taxable_eligibility (a pd.Period).
    """

    def __init__(
        self,
        thresholds: Dict[str, int],
        source_by_target: Dict[str, List[str]],
        amounts: Dict[str, int],
        taxable_eligibility: Optional[pd.Period] = None,
        liquidation_threshold: int = 0,
        liquidation_buckets: Optional[List[str]] = None,
    ):
        # Minimal validation
        self.thresholds = thresholds or {}
        self.sources = source_by_target or {}
        self.amounts = amounts or {}
        self.taxable_eligibility = taxable_eligibility
        self.liquidation_threshold = liquidation_threshold
        self.liquidation_buckets = liquidation_buckets or [
            "Taxable",
            "Fixed-Income",
            "Tax-Deferred",
            "Property",
        ]

    def generate_refills(
        self, buckets: Dict[str, Bucket], tx_month: pd.Period
    ) -> List[RefillTransaction]:
        txns: List[RefillTransaction] = []

        # normalize eligibility once per call (ensure Period with monthly freq)
        elig: Optional[pd.Period] = None
        if self.taxable_eligibility is not None:
            elig = (
                self.taxable_eligibility
                if isinstance(self.taxable_eligibility, pd.Period)
                else pd.to_datetime(self.taxable_eligibility).to_period("M")
            )

        # defensive: ensure tx_month is compared as a Period
        tx_month_period = (
            tx_month.to_period("M") if not isinstance(tx_month, pd.Period) else tx_month
        )

        for target, threshold in self.thresholds.items():
            tgt_bucket = buckets.get(target)
            if tgt_bucket is None:
                logging.warning(
                    f"[RefillPolicy] {tx_month_period} — target '{target}' missing, skipping"
                )
                continue

            if tgt_bucket.balance() >= threshold:
                continue

            per_pass = int(self.amounts.get(target, 0))
            if per_pass <= 0:
                logging.warning(
                    f"[RefillPolicy] {tx_month_period} — no refill amount for '{target}'"
                )
                continue

            remaining = per_pass
            for source in self.sources.get(target, []):
                src_bucket = buckets.get(source)
                if src_bucket is None:
                    continue

                # Age-gate tax-advantaged bucket types using canonical bucket_type
                if elig is not None and getattr(src_bucket, "bucket_type", None) in {
                    "tax_free",
                    "tax_deferred",
                }:
                    if tx_month_period < elig:
                        logging.debug(
                            f"[RefillPolicy] {tx_month_period} — source '{source}' age-gated (bucket_type={src_bucket.bucket_type})"
                        )
                        continue

                available = max(0, src_bucket.balance())
                allow_fallback = getattr(src_bucket, "allow_cash_fallback", False)

                # If fallback allowed, plan the full chunk; apply() will pull remainder from Cash
                if allow_fallback:
                    transfer = min(remaining, per_pass)
                else:
                    transfer = min(available, remaining)

                if transfer <= 0:
                    continue

                # Use bucket_type as canonical source for tax semantics
                bt = getattr(src_bucket, "bucket_type", None)
                is_def = bt == "tax_deferred"
                is_tax = bt == "taxable"

                txns.append(
                    RefillTransaction(
                        source=source,
                        target=target,
                        amount=int(transfer),
                        is_tax_deferred=is_def,
                        is_taxable=is_tax,
                    )
                )

                remaining -= transfer
                if remaining <= 0:
                    break

        return txns

    def generate_liquidation(
        self, buckets: Dict[str, Bucket], tx_month: pd.Period
    ) -> List[RefillTransaction]:
        txns: List[RefillTransaction] = []
        cash = buckets.get("Cash")
        if cash is None:
            return txns
        shortfall = self.liquidation_threshold - cash.balance()
        if shortfall <= 0:
            return txns

        for bucket_name in self.liquidation_buckets:
            if bucket_name == "Cash":
                continue

            src = buckets.get(bucket_name)
            if not src or src.balance() <= 0:
                continue

            if bucket_name == "Property":
                take = src.balance()
                normal_take = min(take, self.amounts.get("Cash", 0))
                taxable_take = take - normal_take
                logging.debug(
                    f"[Emergency Liquidation] {tx_month} — ${normal_take:,} Property Liquidated to Cash, ${taxable_take:,} to Taxable"
                )
                txns.append(
                    RefillTransaction(
                        source=bucket_name,
                        target="Cash",
                        amount=normal_take,
                        is_tax_deferred=False,
                        is_taxable=True,
                    )
                )
                txns.append(
                    RefillTransaction(
                        source=bucket_name,
                        target="Taxable",
                        amount=taxable_take,
                        is_tax_deferred=False,
                        is_taxable=True,
                    )
                )
            else:
                take = min(src.balance(), shortfall)

            bt = getattr(src, "bucket_type", None)
            if (
                bt == "tax_deferred"
                and self.taxable_eligibility
                and tx_month < self.taxable_eligibility
            ):
                penalty_rate = 0.10
            else:
                penalty_rate = 0.0
            is_def = bt == "tax_deferred"
            is_tax = bt == "taxable"
            txns.append(
                RefillTransaction(
                    source=bucket_name,
                    target="Cash",
                    amount=take,
                    is_tax_deferred=is_def,
                    is_taxable=is_tax,
                    penalty_rate=penalty_rate,
                )
            )
            shortfall -= take
            if shortfall <= 0:
                break
        return txns
