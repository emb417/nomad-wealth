import numpy as np
import pandas as pd
from typing import Dict, List
from domain import Bucket

class InflationGenerator:
    def __init__(self, years: List[int], avg: float, std: float, seed: int=42):
        self.years = years
        self.avg   = avg
        self.std   = std
        self.seed  = seed

    def generate(self) -> Dict[int, Dict[str, float]]:
        rng = np.random.default_rng(self.seed)
        modifier = 1.0
        out = {}
        for y in self.years:
            rate = max(0.0, rng.normal(self.avg, self.std))
            modifier *= (1 + rate)
            out[y] = {"rate": rate, "modifier": modifier}
        return out

class GainStrategy:
    """
    Applies market gains to each Bucket’s holdings.
    Chooses an inflation scenario per holding based on
    the year’s inflation rate vs. that asset_class’s thresholds.
    """

    def __init__(
        self,
        gain_table:     Dict[str, Dict[str, Dict[str, float]]],
        thresholds:     Dict[str, Dict[str, float]],
        inflation:      Dict[int, Dict[str, float]]
    ):
        self.gain_table = gain_table
        self.thresholds = thresholds
        self.inflation  = inflation

    def apply(self,
              buckets: Dict[str, Bucket],
              forecast_date: pd.Timestamp
    ) -> None:
        """
        For each bucket, for each holding, pick Low/Average/High
        scenario based on that holding’s asset_class thresholds
        and the inflation rate for forecast_date.year,
        then sample a gain and mutate h.amount.
        """
        year      = forecast_date.year
        infl_rate = self.inflation[year]["rate"]

        # mutate each Bucket in place
        for bucket in buckets.values():
            for h in bucket.holdings:
                cls_name = h.asset_class.name

                # determine scenario for this asset_class
                th       = self.thresholds.get(cls_name, {"low": 0.0, "high": 0.0})
                scenario = "Average"
                if infl_rate >  th["high"]:
                    scenario = "High"
                elif infl_rate < th["low"]:
                    scenario = "Low"

                # look up avg/std for this scenario
                params = self.gain_table[cls_name][scenario]
                gain   = np.random.normal(params["avg"], params["std"])

                # apply growth
                h.amount = int(round(h.amount * (1 + gain)))