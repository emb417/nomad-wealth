from typing import Dict
from domain import Bucket

class RefillPolicy:
    def __init__(
        self,
        thresholds: Dict[str, int],
        amounts:    Dict[str, int],
        sources:    Dict[str, str]
    ):
        self.thresholds = thresholds
        self.amounts    = amounts
        self.sources    = sources

    def apply(self, buckets: Dict[str, Bucket]) -> None:
        for name, bucket in buckets.items():
            bal    = bucket.balance()
            thresh = self.thresholds.get(name, 0)
            if bal < thresh:
                amt = self.amounts.get(name, 0)
                src = self.sources.get(name)
                if src and buckets[src].balance()   >= amt:
                    buckets[src].holdings[0].amount -= amt
                    bucket.holdings[0].amount       += amt
