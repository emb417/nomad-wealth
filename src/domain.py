import numpy as np
from typing import List, Optional, Tuple


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
        cost_basis: Optional[int] = None,
    ):
        self.asset_class = asset_class
        self.weight = weight
        self.amount = amount
        # default cost_basis to the current amount when not provided
        self.cost_basis = cost_basis if cost_basis is not None else amount

    def apply_return(self, avg: float, std: float) -> None:
        """
        Apply a sampled return to this holding.
        """
        rate = self.asset_class.sample_return(avg, std)
        growth = int(self.amount * rate)
        self.amount += growth
        # keep cost_basis unchanged on market returns


class Bucket:
    """
    A container of holdings. Supports weighted deposits and safe or
    negative-allowed withdrawals.

    Metadata flags
      - can_go_negative: allow withdraw to push holdings negative
      - allow_cash_fallback: when True, RefillTransaction.apply may attempt full withdrawal
        and let Cash cover the shortfall
    """

    def __init__(
        self,
        name: str,
        holdings: List[Holding],
        can_go_negative: bool = False,
        allow_cash_fallback: bool = False,
        bucket_type: str = "other",
    ):
        self.name = name
        self.holdings = holdings
        self.can_go_negative = can_go_negative
        self.allow_cash_fallback = allow_cash_fallback
        self.bucket_type = bucket_type

    def deposit(self, amount: int, holding_name: Optional[str] = None) -> None:
        if amount == 0:
            return

        if holding_name:
            for h in self.holdings:
                if h.asset_class.name == holding_name:
                    h.amount += amount
                    h.cost_basis += amount
                    return
            raise KeyError(
                f"Holding '{holding_name}' not found in bucket '{self.name}'"
            )

        total_weight = sum(h.weight for h in self.holdings)
        remainder = amount
        # distribute into holdings using weights; last holding gets residual to avoid rounding loss
        for h in self.holdings[:-1]:
            share = int(round(amount * (h.weight / total_weight)))
            h.amount += share
            h.cost_basis += share
            remainder -= share

        self.holdings[-1].amount += remainder
        self.holdings[-1].cost_basis += remainder

    def balance(self) -> int:
        return sum(h.amount for h in self.holdings)

    def available_for_withdraw(self) -> int:
        """
        Positive available amount for conservative withdrawals (never negative).
        """
        return max(0, self.balance())

    def _withdraw_from_holdings(self, amount: int) -> int:
        """
        Core helper: remove up to `amount` from holdings, reducing cost_basis proportionally.
        Returns actual withdrawn (non-negative).
        """
        if amount <= 0:
            return 0

        # Cap withdrawal to available when not allowing negatives
        available = self.balance()
        to_withdraw = amount if self.can_go_negative else min(amount, available)
        remaining = to_withdraw

        # If allowed negative, deduct from the first holding to keep simple semantics
        if self.can_go_negative and to_withdraw > available:
            primary = self.holdings[0]
            primary.amount -= to_withdraw
            # once negative, cost_basis semantics are undefined; set to zero
            primary.cost_basis = max(
                0, primary.cost_basis - min(primary.cost_basis, to_withdraw)
            )
            return to_withdraw

        # Otherwise deduct proportionally from holdings in order
        for h in self.holdings:
            if remaining <= 0:
                break
            deduct = min(h.amount, remaining)
            h.amount -= deduct
            # reduce cost_basis pro rata (if cost_basis exists)
            if h.cost_basis > 0:
                basis_deduct = (
                    int(round(deduct * (h.cost_basis / (h.amount + deduct))))
                    if (h.amount + deduct) > 0
                    else 0
                )
                h.cost_basis = max(0, h.cost_basis - basis_deduct)
            remaining -= deduct

        return to_withdraw

    def withdraw(self, amount: int) -> int:
        """
        Remove up to `amount` from this bucket.
        - If can_go_negative is True, will attempt to take exactly `amount` and may push holdings negative.
        - Otherwise will cap at current balance.
        Returns the actual withdrawn (== amount if can_go_negative or enough balance).
        """
        return self._withdraw_from_holdings(amount)

    def partial_withdraw(self, amount: int) -> int:
        """
        Withdraw up to `amount` but never go below zero.
        Returns how much was actually taken (<= amount).
        """
        # partial_withdraw should not reduce below zero even if can_go_negative True
        saved_flag = self.can_go_negative
        try:
            self.can_go_negative = False
            return self._withdraw_from_holdings(amount)
        finally:
            self.can_go_negative = saved_flag

    def withdraw_with_cash_fallback(
        self, amount: int, cash_bucket: "Bucket"
    ) -> Tuple[int, int]:
        """
        Attempt to withdraw `amount` from this bucket. If this bucket has
        allow_cash_fallback True and cash_bucket is provided, any shortfall
        will be pulled from cash_bucket (cash_bucket may be driven negative).
        Returns a tuple (from_source, from_cash) indicating amounts withdrawn.
        """
        if amount <= 0:
            return 0, 0

        # Try to withdraw up to available (or full amount if this bucket allows negative)
        if self.allow_cash_fallback:
            # attempt full withdraw (may drive source negative)
            from_src = self.withdraw(amount)
            shortfall = amount - from_src
            from_cash = 0
            if shortfall > 0 and cash_bucket is not None:
                # withdraw shortfall from cash (cash_bucket.withdraw may go negative or cap depending on its flag)
                from_cash = cash_bucket.withdraw(shortfall)
            return from_src, from_cash

        # conservative: only withdraw what source can supply without going negative
        from_src = self.partial_withdraw(amount)
        return from_src, 0

    def __repr__(self) -> str:
        return f"<Bucket {self.name}: ${self.balance():,}>"
