from typing import List, Dict, Optional

# Internal Imports
from policies_engine import ThresholdRefillPolicy


class TaxCalculator:
    """
    Calculates federal tax on combined income (married‐filing‐jointly
    brackets + SS rules), including standard deduction and early withdrawal penalties.
    """

    def __init__(
        self,
        tax_brackets: Dict[str, Dict[str, List[Dict[str, float]]]],
    ):
        self.ordinary_tax_brackets = tax_brackets["ordinary"]
        self.capital_gains_tax_brackets = tax_brackets["capital_gains"]

    def _taxable_social_security(self, ss_benefits: int, other_income: int) -> int:
        if ss_benefits <= 0:
            return 0

        brackets = self.ordinary_tax_brackets.get("social_security_taxability", [])
        if not brackets:
            return 0  # fallback if config is missing

        base_rate = brackets[1]["rate"] if len(brackets) > 1 else 0.5
        provisional = other_income + int(base_rate * ss_benefits)

        max_rate = max(bracket["rate"] for bracket in brackets)
        max_taxable = int(max_rate * ss_benefits)

        taxable = 0
        remaining = provisional

        for i, bracket in enumerate(brackets):
            lower = bracket["min_provisional"]
            upper = (
                brackets[i + 1]["min_provisional"]
                if i + 1 < len(brackets)
                else float("inf")
            )

            if remaining <= lower:
                break

            chunk = min(remaining, upper) - lower
            taxable += chunk * bracket["rate"]

        return min(int(taxable), max_taxable)

    def calculate_tax(
        self,
        salary: int = 0,
        ss_benefits: int = 0,
        withdrawals: int = 0,
        gains: int = 0,
        age: Optional[int] = None,
        standard_deduction: int = 27700,
    ) -> Dict[str, int]:
        # Step 1: Ordinary income
        other_income = salary + withdrawals
        taxable_ss = self._taxable_social_security(ss_benefits, other_income)
        ordinary_income = max(0, other_income + taxable_ss - standard_deduction)

        ordinary_tax = 0
        for bracket_name, bracket_list in self.ordinary_tax_brackets.items():
            ordinary_tax += self._calculate_ordinary_tax(
                {bracket_name: bracket_list}, ordinary_income
            )

        # Step 2: Capital gains tax (long-term only)
        gains_tax = self._calculate_capital_gains_tax(ordinary_income, gains)

        # Step 3: Early withdrawal penalty
        penalty_tax = 0
        if age is not None and age < 59.5 and withdrawals > 0:
            penalty_tax = int(0.10 * withdrawals)

        total_tax = int(ordinary_tax + gains_tax + penalty_tax)

        return {
            "ordinary_tax": int(ordinary_tax),
            "capital_gains_tax": int(gains_tax),
            "penalty_tax": int(penalty_tax),
            "total_tax": total_tax,
        }

    def _calculate_ordinary_tax(
        self, brackets: Dict[str, List[Dict[str, float]]], income: int
    ) -> int:
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
        if gains <= 0:
            return 0

        brackets = self.capital_gains_tax_brackets["long_term"]
        tax = 0
        remaining_gains = gains

        for i, bracket in enumerate(brackets):
            lower = bracket["min_salary"]
            upper = (
                brackets[i + 1]["min_salary"] if i + 1 < len(brackets) else float("inf")
            )

            bracket_floor = max(lower, ordinary_income)
            if remaining_gains <= 0 or upper <= bracket_floor:
                continue

            taxable_chunk = min(remaining_gains, upper - bracket_floor)
            tax += taxable_chunk * bracket["tax_rate"]
            remaining_gains -= taxable_chunk

        return int(tax)
