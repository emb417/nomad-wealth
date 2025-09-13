from dataclasses import dataclass, field
from typing import List
import numpy as np

@dataclass
class AssetClass:
    name: str
    mean: float
    std: float

    def sample_return(self) -> float:
        """Draw one period’s return for this asset class."""
        return float(np.random.normal(self.mean, self.std))

@dataclass
class Holding:
    asset_class: AssetClass
    amount: int        # dollars as integer

    def apply_growth(self) -> None:
        """
        Sample a float return, apply to int amount,
        then round back to the nearest dollar.
        """
        r = self.asset_class.sample_return()
        new_amt = self.amount * (1 + r)
        self.amount = int(round(new_amt))

@dataclass
class Bucket:
    name: str
    holdings: List[Holding] = field(default_factory=list)

    @property
    def balance(self) -> float:
        return sum(h.amount for h in self.holdings)

    def apply_growth(self) -> None:
        """Apply growth to each holding in this bucket."""
        for h in self.holdings:
            h.apply_growth()
