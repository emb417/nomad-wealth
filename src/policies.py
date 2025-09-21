import logging
import pandas as pd

from typing import Dict, List, Optional

# Internal Imports
from domain import Bucket
from transactions import Transaction


class RefillTransaction(Transaction):
    def __init__(
        self,
        source: str,
        target: str,
        amount: int,
        is_tax_deferred: bool = False,
        is_taxable: bool = False,
    ):
        self.source = source
        self.target = target
        self.amount = amount
        self.is_tax_deferred = is_tax_deferred
        self.is_taxable = is_taxable

    def apply(self, buckets: Dict[str, Bucket], tx_month: pd.Period) -> None:
        buckets[self.source].withdraw(self.amount)
        buckets[self.target].deposit(self.amount)

    def get_withdrawal(self, tx_month: pd.Period) -> int:
        return self.amount if self.is_tax_deferred else 0

    def get_taxable_gain(self, tx_month: pd.Period) -> int:
        return self.amount if self.is_taxable else 0


class ThresholdRefillPolicy:
    def __init__(
        self,
        thresholds: Dict[str, int],
        source_by_target: Dict[str, List[str]],
        amounts: Dict[str, int],
        taxable_eligibility: Optional[pd.Period] = None,
    ):
        self.thresholds = thresholds
        self.sources = source_by_target
        self.amounts = amounts
        self.taxable_eligibility = taxable_eligibility

    def generate(
        self, buckets: Dict[str, Bucket], tx_month: pd.Period
    ) -> List[RefillTransaction]:
        txns: List[RefillTransaction] = []

        # Emergency: if Cash < 0, liquidate all Real-Estate into Cash
        cash_balance = buckets["Cash"].balance()
        if cash_balance < -100000:
            re = buckets.get("Real-Estate")
            if re and re.balance() > 0:
                amt = re.balance()
                txns.append(
                    RefillTransaction(
                        source="Real-Estate",
                        target="Taxable",
                        amount=amt,
                        is_tax_deferred=False,
                        is_taxable=True,
                    )
                )
                logging.info(
                    f"[Emergency Refill] {tx_month} — "
                    f"Liquidated ${amt:,} from Real-Estate → Cash"
                )

        for target, threshold in self.thresholds.items():
            # 1) Skip taxable until eligible
            if (
                target.lower() == "taxable"
                and self.taxable_eligibility
                and tx_month < self.taxable_eligibility
            ):
                continue

            # 2) Only trigger refill when below threshold
            tgt_bucket = buckets.get(target)
            if tgt_bucket is None or tgt_bucket.balance() >= threshold:
                continue

            # 3) Always try to move the full configured amount
            per_pass = self.amounts.get(target, 0)
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

                available = src_bucket.balance()
                # cap only by what's available and what's left of per_pass
                transfer = min(available, remaining)
                if transfer <= 0:
                    continue

                is_def = source.lower() == "tax-deferred"
                is_tax = source.lower() == "taxable"

                txns.append(
                    RefillTransaction(
                        source=source,
                        target=target,
                        amount=transfer,
                        is_tax_deferred=is_def,
                        is_taxable=is_tax,
                    )
                )
                remaining -= transfer
                if remaining <= 0:
                    break

        return txns
