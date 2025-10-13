import numpy as np
import pandas as pd

from typing import Dict, List

# Internal Imports
from domain import Bucket


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

    def apply(self, buckets: Dict[str, Bucket], forecast_date: pd.Timestamp) -> None:
        year = forecast_date.year
        rate = self.inflation[year]["rate"]
        tx_month = pd.Period(forecast_date, freq="M")

        for bucket in buckets.values():
            for h in bucket.holdings:
                cls_name = h.asset_class.name

                # pull per-asset low/high thresholds (fallback to 0,0)
                th = self.thresholds.get(cls_name, {"low": 0.0, "high": 0.0})
                low, high = th["low"], th["high"]

                # pick scenario
                if rate < low:
                    scenario = "Low"
                elif rate > high:
                    scenario = "High"
                else:
                    scenario = "Average"

                # sample gain
                params = self.gain_table[cls_name][scenario]
                gain = np.random.normal(params["avg"], params["std"])
                delta = int(round(h.amount * gain))

                # apply gain
                if delta > 0:
                    bucket.deposit(
                        amount=delta,
                        source="Market Gains",
                        tx_month=tx_month,
                        flow_type="gain",
                    )
                elif delta < 0:
                    bucket.deposit(
                        amount=abs(delta),
                        source="Market Losses",
                        tx_month=tx_month,
                        flow_type="loss",
                    )
