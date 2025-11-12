import logging
from typing import List, Dict, Any


class TaxCalculator:
    """
    Calculates federal tax on combined income (married‐filing‐jointly
    brackets + SS rules), including standard deduction and early withdrawal penalties.
    """

    TAXABLE_RATES: Dict[str, float] = {
        "Stocks": 0.50,  # assuming 50% of gains are taxable
        "Bonds": 0.04,  # interest-like exposure
        "Penalty": 0.10,  # early-withdrawal fee
    }

    def __init__(
        self,
        base_brackets: Dict[str, Any],
        base_inflation: Dict[int, Dict[str, float]],
    ):
        self.base_inflation = base_inflation
        self.standard_deduction_by_year = self._inflate_deductions(
            base_brackets["Standard Deduction"]
        )
        self.ordinary_tax_brackets_by_year = self._inflate_brackets_by_year(
            base_brackets["Ordinary"]
        )
        self.capital_gains_tax_brackets_by_year = self._inflate_cap_gains_brackets(
            base_brackets["Capital Gains"]
        )
        self.social_security_brackets_by_year = self._inflate_social_security_brackets(
            base_brackets["Social Security Taxability"]
        )

    def _inflate_social_security_brackets(self, base_brackets):
        inflated = {}
        for year, inflation in self.base_inflation.items():
            modifier = inflation.get("modifier", 1.0)
            inflated[year] = [
                {**b, "min_provisional": int(round(b["min_provisional"] * modifier))}
                for b in base_brackets
            ]
        return inflated

    def _inflate_cap_gains_brackets(
        self, brackets_by_type: Dict[str, List[Dict[str, float]]]
    ) -> Dict[str, List[Dict[str, float]]]:
        inflated = {}
        for label, bracket_list in brackets_by_type.items():
            for year, inflation in self.base_inflation.items():
                modifier = inflation.get("modifier", 1.0)
                inflated_key = f"{label} {year}"
                inflated[inflated_key] = [
                    {**b, "min_salary": int(round(b["min_salary"] * modifier))}
                    for b in bracket_list
                ]
        return inflated

    def _inflate_deductions(self, deduction: int) -> Dict[str, int]:
        return {
            str(year): int(
                round(
                    deduction * self.base_inflation.get(year, {}).get("modifier", 1.0)
                )
            )
            for year in self.base_inflation
        }

    def _inflate_brackets_by_year(self, brackets_by_label):
        inflated = {}
        for label, bracket_list in brackets_by_label.items():
            try:
                base_year = int(label.split()[-1])
                base_label = " ".join(label.split()[:-1])
            except (ValueError, IndexError):
                logging.warning(f"Could not extract year from bracket label: {label}")
                continue

            for year, inflation in self.base_inflation.items():
                modifier = inflation.get("modifier", 1.0)
                inflated_key = f"{base_label} {year}"
                inflated[inflated_key] = [
                    {**b, "min_salary": int(round(b["min_salary"] * modifier))}
                    for b in bracket_list
                ]
        return inflated

    def _taxable_social_security(self, year: int, ss_benefits: int, agi: int) -> int:
        if ss_benefits <= 0:
            return 0

        brackets = self.social_security_brackets_by_year.get(year, [])
        if not brackets:
            logging.warning("Social Security taxability brackets not found")
            return 0

        provisional = agi + int(round(0.5 * ss_benefits))
        max_rate = max(bracket["rate"] for bracket in brackets)
        max_taxable = int(round(max_rate * ss_benefits))

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
        year: int,
        salary: int = 0,
        fixed_income_interest: int = 0,
        unemployment: int = 0,
        ss_benefits: int = 0,
        withdrawals: int = 0,
        gains: int = 0,
        roth: int = 0,
        penalty_basis: int = 0,
    ) -> Dict[str, int]:
        year_str = str(year)
        deduction = self.standard_deduction_by_year.get(year_str, 0)
        ordinary_brackets = self.ordinary_tax_brackets_by_year.get(
            f"Federal {year}", []
        )
        capital_gains_brackets = self.capital_gains_tax_brackets_by_year.get(
            f"long_term {year}", []
        )

        # Unemployment is taxable, but not part of provisional income for SS
        provisional_income = salary + withdrawals + roth + gains
        taxable_ss = self._taxable_social_security(
            year, ss_benefits, provisional_income
        )
        agi = (
            salary
            + unemployment
            + withdrawals
            + roth
            + gains
            + ss_benefits
            + fixed_income_interest
        )

        ordinary_income = max(
            0,
            salary
            + unemployment
            + withdrawals
            + roth
            + taxable_ss
            + fixed_income_interest
            - deduction,
        )
        ordinary_tax = self._calculate_ordinary_tax(ordinary_brackets, ordinary_income)
        gains_tax = self._calculate_capital_gains_tax(
            ordinary_income, gains, capital_gains_brackets
        )
        penalty_tax = int(round(self.TAXABLE_RATES["Penalty"] * penalty_basis))
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
        self, bracket_list: List[Dict[str, float]], income: int
    ) -> int:
        tax = 0
        for i, bracket in enumerate(bracket_list):
            next_bracket = bracket_list[i + 1] if i + 1 < len(bracket_list) else None
            if income > bracket["min_salary"]:
                upper = next_bracket["min_salary"] if next_bracket else float("inf")
                taxable_chunk = min(income, upper) - bracket["min_salary"]
                logging.debug(
                    f"Bracket {i}: {bracket['min_salary']}–{upper} at {bracket['tax_rate']}, "
                    f"taxable_chunk={taxable_chunk}"
                )
                tax += taxable_chunk * bracket["tax_rate"]
            else:
                logging.debug(
                    f"Income {income} not above bracket floor {bracket['min_salary']}"
                )

        return int(tax)

    def _calculate_capital_gains_tax(
        self, ordinary_income: int, gains: int, brackets: List[Dict[str, float]]
    ) -> int:
        if gains <= 0:
            return 0

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
