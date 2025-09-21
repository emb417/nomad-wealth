from typing import List, Tuple
from policies import ThresholdRefillPolicy


class TaxCalculator:
    """
    Calculates federal tax on combined income (married‐filing‐jointly
    brackets + SS rules), withdraws from Cash (allowing negative),
    then lets RefillPolicy pull from other buckets (down to zero)
    so only Cash can stay negative.
    """

    def __init__(self, refill_policy: ThresholdRefillPolicy):
        # Married filing jointly 2025 brackets: (lower_bound, rate)
        self.brackets: List[Tuple[int, float]] = [
            (0, 0.10),
            (22000, 0.12),
            (89450, 0.22),
            (190750, 0.24),
            (364200, 0.32),
            (462500, 0.35),
            (751600, 0.37),
        ]
        self.refill_policy = refill_policy

    def _taxable_social_security(self, ss_benefits: int, other_income: int) -> int:
        provisional = other_income + int(0.5 * ss_benefits)
        if provisional <= 32000:
            return 0
        if provisional <= 44000:
            return int(0.5 * ss_benefits)
        return int(0.85 * ss_benefits)

    def calculate_tax(
        self,
        salary: int = 0,
        ss_benefits: int = 0,
        withdrawals: int = 0,
        gains: int = 0,
    ) -> int:
        # Step 1: Ordinary income
        other_income = salary + withdrawals
        taxable_ss = self._taxable_social_security(ss_benefits, other_income)
        ordinary_income = other_income + taxable_ss

        ordinary_tax = self._calculate_ordinary_tax(ordinary_income)

        # Step 2: Capital gains tax (long-term only)
        gains_tax = self._calculate_capital_gains_tax(ordinary_income, gains)

        return ordinary_tax + gains_tax

    def _calculate_ordinary_tax(self, income: int) -> int:
        """
        Applies 2025 ordinary income tax brackets for MFJ.
        """
        tax = 0
        for i, (lower, rate) in enumerate(self.brackets):
            upper = (
                self.brackets[i + 1][0] if i + 1 < len(self.brackets) else float("inf")
            )
            if income > lower:
                taxable_chunk = min(income, upper) - lower
                tax += taxable_chunk * rate
            else:
                break
        return int(tax)

    def _calculate_capital_gains_tax(self, ordinary_income: int, gains: int) -> int:
        """
        Applies 2025 long-term capital gains brackets for MFJ.
        Brackets are layered on top of ordinary income.
        """
        if gains <= 0:
            return 0

        brackets = [
            (0, 0.00),
            (89250, 0.15),
            (553850, 0.20),
        ]

        total_income = ordinary_income + gains
        tax = 0

        for i, (lower, rate) in enumerate(brackets):
            upper = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
            if total_income > lower:
                taxable = min(total_income, upper) - max(lower, ordinary_income)
                if taxable > 0:
                    tax += taxable * rate
            else:
                break

        return int(tax)
