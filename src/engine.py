import pandas as pd
from pandas.tseries.offsets import MonthBegin
from typing import Dict, List

from domain import Bucket
from policies import RefillPolicy
from strategies import GainStrategy
from transactions import Transaction  # your base type

class ForecastEngine:
    def __init__(
        self,
        buckets:        Dict[str, Bucket],
        transactions:   List[Transaction],
        refill_policy:  RefillPolicy,
        gain_strategy:  GainStrategy,
        inflation:      Dict[int, Dict[str, float]]
    ):
        self.buckets        = buckets
        self.transactions   = transactions
        self.refill_policy  = refill_policy
        self.gain_strategy  = gain_strategy
        self.inflation      = inflation

    def run(self, ledger_df: pd.DataFrame) -> pd.DataFrame:
        """
        ledger_df: a DataFrame with one column "Date" (datetime64[ns]) for
                   each forecast step (historical+future).
        Returns a new DataFrame with Date + one column per bucket.
        """
        records = []

        for _, row in ledger_df.iterrows():
            # 1) Grab the date we’re forecasting
            forecast_date = pd.to_datetime(row["Date"])

            # 2) Determine which month’s transactions to apply
            #    e.g. for Oct 1, 2025 we look at Sep 2025 txns
            tx_month = (forecast_date - MonthBegin(1)).to_period("M")

            # 3) Apply every transaction against that prior month
            for tx in self.transactions:
                tx.apply(self.buckets, tx_month)

            # 4) Refill under-threshold buckets
            self.refill_policy.apply(self.buckets)

            # 5) Apply market gains for this forecast_date
            self.gain_strategy.apply(self.buckets, forecast_date)

            # 6) Snapshot: Date + each bucket’s total
            snapshot = {"Date": forecast_date}
            for name, bucket in self.buckets.items():
                snapshot[name] = bucket.balance
            records.append(snapshot)

        # 7) Return a tidy DataFrame
        return pd.DataFrame(records)