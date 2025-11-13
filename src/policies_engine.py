import logging
import pandas as pd
from typing import Dict, List

# Internal Imports
from buckets import Bucket
from policies_transactions import RefillTransaction


class ThresholdRefillPolicy:
    """
    Refill policy using buckets.json metadata attached to Bucket instances.
    Inline eligibility gating is performed using taxable_eligibility (a pd.Period or Timestamp),
    and SEPP gating is enforced for all tax_deferred bucket types during the SEPP period.
    """

    def __init__(
        self,
        refill_thresholds: Dict[str, int],
        source_by_target: Dict[str, List[str]],
        refill_amounts: Dict[str, int],
        liquidation_sources: List[str],
        liquidation_targets: Dict[str, int],
        liquidation_threshold: int,
        taxable_eligibility: pd.Period,
        sepp_start_month: str,
        sepp_end_month: str,
    ):
        self.refill_thresholds = refill_thresholds
        self.sources = source_by_target
        self.refill_amounts = refill_amounts
        self.taxable_eligibility = taxable_eligibility
        self.liquidation_threshold = liquidation_threshold
        self.liquidation_sources = liquidation_sources
        self.liquidation_targets = liquidation_targets
        self.sepp_start_month = pd.Period(sepp_start_month, freq="M")
        self.sepp_end_month = pd.Period(sepp_end_month, freq="M")

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

                bt = getattr(src_bucket, "bucket_type", None)

                # Age-gate tax-advantaged bucket types
                if self.taxable_eligibility is not None and bt in {
                    "tax_free",
                    "tax_deferred",
                }:
                    if tx_month < self.taxable_eligibility:
                        logging.debug(
                            f"[RefillPolicy] {tx_month} — source '{source}' age-gated (bucket_type={bt})"
                        )
                        continue

                # SEPP-gate all tax_deferred buckets during SEPP period
                if (
                    bt == "tax_deferred"
                    and self.sepp_start_month <= tx_month <= self.sepp_end_month
                ):
                    logging.debug(
                        f"[RefillPolicy] {tx_month} — source '{source}' blocked due to SEPP period ({self.sepp_start_month} to {self.sepp_end_month})"
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

                is_def = bt == "tax_deferred"
                is_tax = bt in {"taxable", "property"}
                is_free = bt == "tax_free"

                txns.append(
                    RefillTransaction(
                        source=source,
                        target=target,
                        amount=int(transfer),
                        is_tax_deferred=is_def,
                        is_taxable=is_tax,
                        is_tax_free=is_free,
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

        for bucket_name in self.liquidation_sources:
            if bucket_name == "Cash":
                continue

            src = buckets.get(bucket_name)
            if not src or src.balance() <= 0:
                continue

            bt = getattr(src, "bucket_type", None)

            # SEPP-gate all tax_deferred buckets during SEPP period
            if (
                bt == "tax_deferred"
                and self.sepp_start_month <= tx_month <= self.sepp_end_month
            ):
                logging.debug(
                    f"[LiquidationPolicy] {tx_month} — source '{bucket_name}' blocked due to SEPP period ({self.sepp_start_month} to {self.sepp_end_month})"
                )
                continue

            full_balance = src.balance()
            take = full_balance if bt == "property" else min(full_balance, shortfall)
            if take <= 0:
                continue

            is_def = bt == "tax_deferred"
            is_tax = bt in {"taxable", "property"}
            is_free = bt == "tax_free"
            is_penalty_applicable = (
                self.taxable_eligibility is not None
                and tx_month < self.taxable_eligibility
                and bt in {"tax_deferred", "tax_free"}
            )

            # Determine target routing
            if bt == "property":
                targets = self.liquidation_targets
            else:
                targets = {"Cash": 1.0}

            # Distribute 'take' across targets
            for tgt_name, pct in targets.items():
                if pct <= 0:
                    continue
                tgt_bucket = buckets.get(tgt_name)
                if not tgt_bucket:
                    continue

                tgt_amount = int(round(take * pct))
                if tgt_amount <= 0:
                    continue

                txns.append(
                    RefillTransaction(
                        source=bucket_name,
                        target=tgt_name,
                        amount=tgt_amount,
                        is_tax_deferred=is_def,
                        is_taxable=is_tax,
                        is_tax_free=is_free,
                        is_penalty_applicable=is_penalty_applicable,
                        num_of_targets=len(targets),
                    )
                )

            shortfall -= take
            if shortfall <= 0:
                break

        return txns
