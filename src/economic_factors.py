import numpy as np
import pandas as pd

from typing import Dict, List

# Internal Imports
from buckets import Bucket


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

        # Precompute scenario per asset class
        scenarios = {}
        for cls_name in self.gain_table:
            th = self.thresholds.get(cls_name, {"low": 0.0, "high": 0.0})
            low, high = th["low"], th["high"]
            if rate < low:
                scenarios[cls_name] = "Low"
            elif rate > high:
                scenarios[cls_name] = "High"
            else:
                scenarios[cls_name] = "Average"

        # Sample one return per asset class
        monthly_returns = {
            cls_name: np.random.normal(
                self.gain_table[cls_name][scenarios[cls_name]]["avg"],
                self.gain_table[cls_name][scenarios[cls_name]]["std"],
            )
            for cls_name in self.gain_table
        }

        # Apply gains/losses using shared return per asset class
        for bucket in buckets.values():
            for h in bucket.holdings:
                cls_name = h.asset_class.name
                rate = monthly_returns.get(cls_name, 0)
                delta = int(round(h.amount * rate))

                if delta != 0:
                    label = "Market Gains" if delta > 0 else "Market Losses"
                    bucket.deposit(
                        amount=delta,
                        source=f"{label} {cls_name}",
                        tx_month=tx_month,
                        flow_type="gain" if delta > 0 else "loss",
                    )
