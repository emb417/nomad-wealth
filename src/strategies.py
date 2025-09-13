from typing import Dict, List
import numpy as np

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
    def __init__(self, gain_table, thresholds, inflation):
        self.gain_table = gain_table
        self.thresholds = thresholds
        self.inflation  = inflation

    def apply(self, bucket, date):
        year = date.year
        infl = self.inflation[year]["rate"]

        for h in bucket.holdings:
            cls_name = h.asset_class.name

            # Pick inflation scenario
            th = self.thresholds.get(cls_name, {"low":0,"high":0})
            scenario = "Average"
            if infl > th["high"]:
                scenario = "High"
            elif infl < th["low"]:
                scenario = "Low"

            # Sample gain from gain_table
            params = self.gain_table[cls_name][scenario]
            gain   = np.random.normal(params["avg"], params["std"])
            h.amount *= (1 + gain)
