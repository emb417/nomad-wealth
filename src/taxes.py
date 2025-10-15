from typing import List, Dict

# Internal Imports
from policies_engine import ThresholdRefillPolicy


class TaxCalculator:
    """
    Calculates federal tax on combined income (married‐filing‐jointly
    brackets + SS rules), withdraws from Cash (allowing negative),
    then lets RefillPolicy pull from other buckets (down to zero)
    so only Cash can stay negative.
    """

    def __init__(
        self,
        refill_policy: ThresholdRefillPolicy,
        tax_brackets: Dict[str, Dict[str, List[Dict[str, float]]]],
    ):
        self.refill_policy = refill_policy
        self.ordinary_tax_brackets = tax_brackets["ordinary"]
        self.capital_gains_tax_brackets = tax_brackets["capital_gains"]

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

        ordinary_tax = 0
        for bracket_name, bracket_list in self.ordinary_tax_brackets.items():
            ordinary_tax += self._calculate_ordinary_tax(
                {bracket_name: bracket_list}, ordinary_income
            )

        # Step 2: Capital gains tax (long-term only)
        gains_tax = self._calculate_capital_gains_tax(ordinary_income, gains)

        return ordinary_tax + gains_tax

    def _calculate_ordinary_tax(
        self, brackets: Dict[str, List[Dict[str, float]]], income: int
    ) -> int:
        """
        Applies 2025 ordinary income tax brackets for MFJ.
        """
        tax = 0
        for _, bracket_list in brackets.items():
            for i, bracket in enumerate(bracket_list):
                next_bracket = (
                    bracket_list[i + 1] if i + 1 < len(bracket_list) else None
                )
                if income > bracket["min_salary"]:
                    taxable_chunk = (
                        min(
                            income,
                            (
                                next_bracket["min_salary"]
                                if next_bracket
                                else float("inf")
                            ),
                        )
                        - bracket["min_salary"]
                    )
                    tax += taxable_chunk * bracket["tax_rate"]
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

        brackets = self.capital_gains_tax_brackets["long_term"]

        total_income = ordinary_income + gains
        tax = 0

        taxable = 0
        for i, bracket in enumerate(brackets):
            lower = bracket["min_salary"]
            upper = (
                brackets[i + 1]["min_salary"] if i + 1 < len(brackets) else float("inf")
            )

            if total_income > lower:
                taxable = min(total_income, upper) - lower
                tax += taxable * bracket["tax_rate"]
            else:
                break

        return int(tax)
