import numpy as np
from typing import List, Optional
from datetime import datetime

class AssetClass:
    """
    Defines an asset class with a name and return‐sampling behavior.
    """
    def __init__(self, name: str):
        self.name = name

    def sample_return(self, avg: float, std: float) -> float:
        """
        Draw a random return from a normal distribution.
        """
        return np.random.normal(avg, std)


class Holding:
    """
    A single slice in a Bucket.
      - asset_class: the AssetClass instance  
      - weight:     relative weight for split deposits  
      - amount:     current dollar amount in this slice  
    """
    def __init__(self,
                 asset_class: AssetClass,
                 weight: float,
                 amount: int = 0):
        self.asset_class = asset_class
        self.weight      = weight
        self.amount      = amount


class Bucket:
    def __init__(self, name: str, holdings: List[Holding]):
        self.name     = name
        self.holdings = holdings

    def deposit(self,
                amount: int,
                holding_name: Optional[str] = None) -> None:
        if holding_name:
            for h in self.holdings:
                if h.asset_class.name == holding_name:
                    h.amount += amount
                    return
            raise KeyError(f"Holding '{holding_name}' not found in '{self.name}'")

        total_weight = sum(h.weight for h in self.holdings)
        remainder    = amount
        for h in self.holdings[:-1]:
            share      = int(round(amount * (h.weight / total_weight)))
            h.amount  += share
            remainder -= share
        self.holdings[-1].amount += remainder

    def balance(self) -> int:
        return sum(h.amount for h in self.holdings)