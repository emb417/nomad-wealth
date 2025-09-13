import pandas as pd
from typing import Dict, List
from domain import Bucket
from policies import RefillPolicy
from strategies import GainStrategy
from transactions import Transaction

class ForecastEngine:
    def __init__(
        self,
        buckets:      Dict[str, Bucket],
        transactions: List[Transaction],
        refill_policy: RefillPolicy,
        gain_strategy: GainStrategy,
        inflation:     Dict[int, Dict[str, float]]
    ):
        self.buckets        = buckets
        self.transactions   = transactions
        self.refill_policy  = refill_policy
        self.gain_strategy  = gain_strategy
        self.inflation      = inflation

    def run(self, ledger_df: pd.DataFrame) -> pd.DataFrame:
        records = []
        for _, row in ledger_df.iterrows():
            date = pd.to_datetime(row.Date)
            # snapshot balances
            snap = {"Date": date}
            snap.update({n: b.balance for n, b in self.buckets.items()})
            records.append(snap)

            # mutate for next period
            for tx in self.transactions:
                tx.apply(date, self.buckets)
            self.refill_policy.apply(self.buckets)
            for bucket in self.buckets.values():
                self.gain_strategy.apply(bucket, date)

        return pd.DataFrame(records)
