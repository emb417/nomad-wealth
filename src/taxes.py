import logging

from typing import List, Dict, Optional


class TaxCalculator:
    """
    Calculates federal tax on combined income (married‐filing‐jointly
    brackets + SS rules), including standard deduction and early withdrawal penalties.
    """

    def __init__(
        self,
        standard_deduction: int,
        ordinary_brackets: Dict[str, List[Dict[str, float]]],
        capital_gains_brackets: Dict[str, List[Dict[str, float]]],
        social_security_brackets: List[Dict[str, float]],
    ):
        self.standard_deduction = standard_deduction
        self.ordinary_tax_brackets = ordinary_brackets
        self.capital_gains_tax_brackets = capital_gains_brackets
        self.social_security_brackets = social_security_brackets

    def _taxable_social_security(self, ss_benefits: int, agi: int) -> int:
        if ss_benefits <= 0:
            return 0

        brackets = self.social_security_brackets
        if not brackets:
            logging.warning("Social Security taxability brackets not found")
            return 0  # fallback if config is missing

        # Step 1: Compute provisional income using AGI + ½ SS
        provisional = agi + int(round(0.5 * ss_benefits))

        # Step 2: Determine maximum taxable portion
        max_rate = max(bracket["rate"] for bracket in brackets)
        max_taxable = int(round(max_rate * ss_benefits))

        # Step 3: Layer provisional income through brackets
        taxable = 0
        for i, bracket in enumerate(brackets):
            lower = bracket["min_provisional"]
            upper = (
                brackets[i + 1]["min_provisional"]
                if i + 1 < len(brackets)
                else float("inf")
            )

            if provisional < lower:
                continue

            chunk = min(provisional, upper) - lower
            taxable += int(round(chunk * bracket["rate"]))

        return min(taxable, max_taxable)

    def calculate_tax(
        self,
        salary: int = 0,
        ss_benefits: int = 0,
        withdrawals: int = 0,
        gains: int = 0,
        roth: int = 0,
        penalty_basis: int = 0,
    ) -> Dict[str, int]:
        # Compute taxable Social Security
        provisional_income = salary + withdrawals + roth + gains
        taxable_ss = self._taxable_social_security(ss_benefits, provisional_income)

        # Compute AGI including all taxable income
        agi = salary + withdrawals + roth + gains + taxable_ss

        # Compute ordinary income after standard deduction
        ordinary_income = max(
            0, salary + withdrawals + roth + taxable_ss - self.standard_deduction
        )

        # Ordinary tax
        ordinary_tax = 0
        for bracket_name, bracket_list in self.ordinary_tax_brackets.items():
            if bracket_name != "social_security_taxability":
                ordinary_tax += self._calculate_ordinary_tax(
                    {bracket_name: bracket_list}, ordinary_income
                )

        # Capital gains tax
        gains_tax = self._calculate_capital_gains_tax(ordinary_income, gains)

        # Early withdrawal penalty (only on penalty-eligible withdrawals)
        penalty_tax = 0
        penalty_tax = int(round(0.10 * penalty_basis))

        total_tax = int(ordinary_tax + gains_tax + penalty_tax)

        return {
            "agi": agi,
            "capital_gains_tax": gains_tax,
            "ordinary_income": ordinary_income,
            "ordinary_tax": ordinary_tax,
            "penalty_tax": penalty_tax,
            "roth_conversions": roth,
            "taxable_ss": taxable_ss,
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
