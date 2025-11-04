import logging
import pandas as pd

from typing import Dict, List, Optional

# Internal Imports
from buckets import Bucket
from policies_transactions import RefillTransaction


class ThresholdRefillPolicy:
    """
    Refill policy using buckets.json metadata attached to Bucket instances.
    Inline eligibility gating is performed using taxable_eligibility (a pd.Period or Timestamp).
    """

    def __init__(
        self,
        refill_thresholds: Dict[str, int],
        source_by_target: Dict[str, List[str]],
        refill_amounts: Dict[str, int],
        taxable_eligibility: Optional[pd.Period] = None,
        liquidation_threshold: int = 0,
        liquidation_buckets: Optional[List[str]] = None,
    ):
        self.refill_thresholds = refill_thresholds or {}
        self.sources = source_by_target or {}
        self.refill_amounts = refill_amounts or {}
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

        for target, threshold in self.refill_thresholds.items():
            tgt_bucket = buckets.get(target)
            if tgt_bucket is None:
                logging.warning(
                    f"[RefillPolicy] {tx_month} — target '{target}' missing, skipping"
                )
                continue

            if tgt_bucket.balance() >= threshold:
                continue

            per_pass = int(self.refill_amounts.get(target, 0))
            if per_pass <= 0:
                logging.warning(
                    f"[RefillPolicy] {tx_month} — no refill amount for '{target}'"
                )
                continue

            remaining = per_pass
            for source in self.sources.get(target, []):
                src_bucket = buckets.get(source)
                if src_bucket is None:
                    continue

                # Age-gate tax-advantaged bucket types
                if self.taxable_eligibility is not None and getattr(
                    src_bucket, "bucket_type", None
                ) in {"tax_free", "tax_deferred"}:
                    if tx_month < self.taxable_eligibility:
                        logging.debug(
                            f"[RefillPolicy] {tx_month} — source '{source}' age-gated (bucket_type={src_bucket.bucket_type})"
                        )
                        continue

                available = max(0, src_bucket.balance())
                allow_fallback = getattr(src_bucket, "allow_cash_fallback", False)

                transfer = (
                    min(remaining, per_pass)
                    if allow_fallback
                    else min(available, remaining)
                )
                if transfer <= 0:
                    continue

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
                normal_take = min(take, self.refill_amounts.get("Cash", 0))
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
            is_def = bt == "tax_deferred"
            is_tax = bt == "taxable"
            is_penalty_applicable = (
                is_def
                and self.taxable_eligibility is not None
                and tx_month < self.taxable_eligibility
            )
            txns.append(
                RefillTransaction(
                    source=bucket_name,
                    target="Cash",
                    amount=take,
                    is_tax_deferred=is_def,
                    is_taxable=is_tax,
                    is_penalty_applicable=is_penalty_applicable,
                )
            )

            shortfall -= take
            if shortfall <= 0:
                break

        return txns
