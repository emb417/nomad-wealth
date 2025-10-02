import logging
import pandas as pd

from typing import Dict, List, Optional

# Internal Imports
from domain import Bucket
from transactions import Transaction


class RefillTransaction(Transaction):
    """
    Conservative refill transaction:
      - inherits Transaction for interface consistency
      - delegates money movement to Bucket helpers (withdraw_with_cash_fallback / partial_withdraw)
      - records tax flags only (tax accounting done elsewhere)
      - estimates taxable gains for withdrawals from taxable buckets when cost-basis info is absent
    """

    def __init__(
        self,
        source: str,
        target: str,
        amount: int,
        is_tax_deferred: bool = False,
        is_taxable: bool = False,
    ):
        super().__init__()
        self.source = source
        self.target = target
        self.amount = int(amount)
        self.is_tax_deferred = bool(is_tax_deferred)
        self.is_taxable = bool(is_taxable)

        # runtime-applied amounts and estimated gains (set by apply)
        self._applied_amount: int = 0
        self._taxable_gain: int = 0

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        src = buckets.get(self.source)
        tgt = buckets.get(self.target)
        # reset runtime fields
        self._applied_amount = 0
        self._taxable_gain = 0

        if src is None or tgt is None or self.amount <= 0:
            return

        cash = buckets.get("Cash")

        # If source allows fallback, try combined withdraw then deposit once
        if getattr(src, "allow_cash_fallback", False) and cash is not None:
            from_src, from_cash = src.withdraw_with_cash_fallback(self.amount, cash)
            applied = int((from_src or 0) + (from_cash or 0))
            if applied > 0:
                tgt.deposit(applied)
            logging.debug(
                f"[RefillApply] {tx_month} {self.source}->{self.target} planned={self.amount} "
                f"from_src={from_src} from_cash={from_cash}"
            )
            self._applied_amount = applied

            # estimate taxable gain portion for amounts withdrawn from a taxable source
            bt = getattr(src, "bucket_type", None)
            if bt == "taxable" and self.is_taxable:
                # conservative heuristic: estimate 50% of proceeds are taxable gains
                self._taxable_gain = int(round(self._applied_amount * 0.5))
            return

        # Conservative: only take what the source can supply without going negative
        withdrawn = src.partial_withdraw(self.amount)
        applied = int(withdrawn or 0)
        if applied > 0:
            tgt.deposit(applied)
            logging.debug(
                f"[RefillApply] {tx_month} {self.source}->{self.target} withdrew={applied}"
            )
        self._applied_amount = applied

        # estimate taxable gain portion for amounts withdrawn from a taxable source
        bt = getattr(src, "bucket_type", None)
        if bt == "taxable" and self.is_taxable and self._applied_amount > 0:
            # conservative heuristic: estimate 50% of proceeds are taxable gains
            self._taxable_gain = int(round(self._applied_amount * 0.5))

    # Report tax-relevant amounts to the engine's tax accumulation
    def get_withdrawal(self, tx_month: pd.Period) -> int:
        # Report as tax-deferred withdrawal only when transaction is marked so
        return self._applied_amount if getattr(self, "is_tax_deferred", False) else 0

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        # Return the estimated taxable gain (0 if not applicable)
        return int(self._taxable_gain or 0)


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
    ):
        # Minimal validation
        self.thresholds = thresholds or {}
        self.sources = source_by_target or {}
        self.amounts = amounts or {}
        self.taxable_eligibility = taxable_eligibility
        self.liquidation_threshold = liquidation_threshold

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
        if cash and cash.balance() < self.liquidation_threshold:
            prop = buckets.get("Property")
            if prop and prop.balance() > 0:
                amt = prop.balance()
                txns.append(
                    RefillTransaction(
                        source="Property",
                        target="Taxable",
                        amount=amt,
                        is_tax_deferred=False,
                        is_taxable=True,
                    )
                )
                logging.debug(
                    f"[Emergency Liquidation] {tx_month} — "
                    f"Liquidated ${amt:,} from Property → Taxable"
                )
        return txns
