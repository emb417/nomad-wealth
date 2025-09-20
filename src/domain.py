import numpy as np
from typing import List, Optional


class AssetClass:
    """
    Defines an asset class with a name and return-sampling behavior.
    """
    def __init__(self, name: str):
        self.name = name

    def sample_return(self, avg: float, std: float) -> float:
        return np.random.normal(avg, std)


class Holding:
    """
    A single slice in a Bucket.
      - asset_class: the AssetClass instance  
      - weight:     relative weight for split deposits  
      - amount:     current dollar amount in this slice  
      - cost_basis: optional cost basis for taxable gain tracking  
    """
    def __init__(
        self,
        asset_class: AssetClass,
        weight: float,
        amount: int = 0,
        cost_basis: Optional[int] = None
    ):
        self.asset_class = asset_class
        self.weight      = weight
        self.amount      = amount
        self.cost_basis  = cost_basis if cost_basis is not None else amount

    def apply_return(self, avg: float, std: float) -> None:
        """
        Apply a sampled return to this holding.
        """
        rate   = self.asset_class.sample_return(avg, std)
        growth = int(self.amount * rate)
        self.amount += growth


class Bucket:
    """
    A container of holdings. Supports weighted deposits and safe or
    negative‐allowed withdrawals.
    """
    def __init__(self, name: str, holdings: List[Holding], can_go_negative: bool = False):
        self.name            = name
        self.holdings        = holdings
        self.can_go_negative = can_go_negative

    def deposit(self, amount: int, holding_name: Optional[str] = None) -> None:
        if amount == 0:
            return

        if holding_name:
            for h in self.holdings:
                if h.asset_class.name == holding_name:
                    h.amount    += amount
                    h.cost_basis += amount
                    return
            raise KeyError(f"Holding '{holding_name}' not found in bucket '{self.name}'")

        total_weight = sum(h.weight for h in self.holdings)
        remainder    = amount
        for h in self.holdings[:-1]:
            share        = int(round(amount * (h.weight / total_weight)))
            h.amount    += share
            h.cost_basis += share
            remainder   -= share

        self.holdings[-1].amount     += remainder
        self.holdings[-1].cost_basis += remainder

    def withdraw(self, amount: int) -> int:
        """
        Remove up to `amount` from this bucket. If can_go_negative is True,
        will always take exactly `amount` (pushing the first holding—and thus
        bucket—into negative). Otherwise caps at current balance.
        Returns the actual withdrawn (which equals `amount` if can_go_negative).
        """
        if amount <= 0:
            return 0

        if self.can_go_negative:
            # force a full withdrawal, even beyond zero
            primary = self.holdings[0]
            primary.amount -= amount
            # cost_basis is not relevant once negative
            return amount

        # otherwise, safe cap at available
        available   = self.balance()
        to_withdraw = min(amount, available)
        remaining   = to_withdraw

        for h in self.holdings:
            if remaining <= 0:
                break
            deduct = min(h.amount, remaining)
            h.amount      -= deduct
            h.cost_basis   = max(0, h.cost_basis - deduct)
            remaining     -= deduct

        return to_withdraw

    def partial_withdraw(self, amount: int) -> int:
        """
        Withdraw up to `amount` but never go below zero.
        Returns how much was actually taken.
        """
        available   = self.balance()
        to_withdraw = min(available, amount)
        remaining   = to_withdraw

        for h in self.holdings:
            if remaining <= 0:
                break
            deduct = min(h.amount, remaining)
            h.amount  -= deduct
            remaining  -= deduct

        return to_withdraw

    def balance(self) -> int:
        return sum(h.amount for h in self.holdings)

    def __repr__(self) -> str:
        return f"<Bucket {self.name}: ${self.balance():,}>"
