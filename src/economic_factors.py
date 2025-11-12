import numpy as np
import pandas as pd

from typing import Dict, List

# Internal Imports
from buckets import Bucket
from policies_transactions import MarketGainTransaction


class InflationGenerator:
    def __init__(self, years: List[int], avg: float, std: float, seed: int = 42):
        self.years = years
        self.avg = avg
        self.std = std
        self.seed = seed

    def generate(self) -> Dict[int, Dict[str, float]]:
        rng = np.random.default_rng(self.seed)
        modifier = 1.0
        out = {}
        for y in self.years:
            rate = max(0.0, rng.normal(self.avg, self.std))
            modifier *= 1 + rate
            out[y] = {"rate": rate, "modifier": modifier}
        return out


class MarketGains:
    """
    Applies market gains to each Bucket’s holdings by:
      1) looking up that asset’s low/high inflation thresholds
      2) comparing the year’s inflation rate to pick Low/Average/High
      3) sampling gain from gain_table[asset][scenario]
      4) applying fixed income for bond holdings using same monthly_returns
    """

    def __init__(
        self,
        gain_table: Dict[str, Dict[str, Dict[str, float]]],
        inflation_thresholds: Dict[str, Dict[str, float]],
        inflation: Dict[int, Dict[str, float]],
    ):
        self.gain_table = gain_table
        self.thresholds = inflation_thresholds
        self.inflation = inflation

    def apply(
        self, buckets: Dict[str, Bucket], forecast_date: pd.Timestamp
    ) -> List[MarketGainTransaction]:
        transactions = []
        year = forecast_date.year
        inflation_rate = self.inflation[year]["rate"]

        # Determine scenario per asset class
        scenarios = {}
        for cls_name, thresholds in self.thresholds.items():
            low = thresholds.get("low", 0.0)
            high = thresholds.get("high", 0.0)
            if inflation_rate < low:
                scenarios[cls_name] = "Low"
            elif inflation_rate > high:
                scenarios[cls_name] = "High"
            else:
                scenarios[cls_name] = "Average"

        # Sample monthly return per asset class
        monthly_returns = {
            cls_name: np.random.normal(
                self.gain_table[cls_name][scenarios.get(cls_name, "Average")]["avg"],
                self.gain_table[cls_name][scenarios.get(cls_name, "Average")]["std"],
            )
            for cls_name in self.gain_table
        }

        # Emit transactions based on holdings and sampled returns
        for bucket_name, bucket in buckets.items():
            bucket_type = getattr(bucket, "bucket_type", None)
            for h in bucket.holdings:
                cls_name = h.asset_class.name
                rate = monthly_returns.get(cls_name, 0)

                if cls_name == "Bonds":
                    rate = min(max(rate, 0.001), 0.004)

                delta = int(round(h.amount * rate))
                if delta == 0:
                    continue

                if cls_name == "Bonds" and bucket_type == "taxable":
                    flow_type = "deposit"
                else:
                    flow_type = "gain" if delta > 0 else "loss"

                transactions.append(
                    MarketGainTransaction(
                        bucket_name=bucket_name,
                        asset_class=cls_name,
                        amount=delta,
                        flow_type=flow_type,
                    )
                )

        return transactions
