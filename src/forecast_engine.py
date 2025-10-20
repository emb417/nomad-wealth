import logging
import pandas as pd

from pandas.tseries.offsets import MonthBegin
from typing import Dict, List, Tuple

# Internal Imports
from buckets import Bucket
from economic_factors import MarketGains
from policies_engine import ThresholdRefillPolicy
from policies_transactions import PolicyTransaction, RothConversionTransaction
from rules_transactions import RuleTransaction
from taxes import TaxCalculator


class ForecastEngine:
    def __init__(
        self,
        buckets: Dict[str, Bucket],
        rule_transactions: List[RuleTransaction],
        policy_transactions: List[PolicyTransaction],
        refill_policy: ThresholdRefillPolicy,
        market_gains: MarketGains,
        inflation: Dict[int, Dict[str, float]],
        tax_calc: TaxCalculator,
        profile: Dict[str, int],
    ):
        self.buckets = buckets
        self.rule_transactions = rule_transactions
        self.policy_transactions = policy_transactions
        self.refill_policy = refill_policy
        self.market_gains = market_gains
        self.inflation = inflation
        self.tax_calc = tax_calc
        self.annual_tax_estimate = 0
        self.monthly_tax_drip = 0
        self.dob = profile.get("Date of Birth")

    def run(self, ledger_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        records = []
        tax_records = []
        yearly_tax_log = {}
        quarterly_tax_log = {}

        for _, row in ledger_df.iterrows():
            forecast_date = pd.to_datetime(row["Date"])
            tx_month = (forecast_date - MonthBegin(1)).to_period("M")
            year = forecast_date.year
            quarter = (forecast_date.month - 1) // 3 + 1
            qkey = (year, quarter)

            # Rule-driven transactions
            for tx in self.rule_transactions:
                tx.apply(self.buckets, tx_month)

            # Policy-driven transactions
            for tx in self.policy_transactions:
                tx.apply(self.buckets, tx_month)

            # Refill policy
            refill_txns = self.refill_policy.generate_refills(self.buckets, tx_month)
            for tx in refill_txns:
                tx.apply(self.buckets, tx_month)

            # Market returns
            self.market_gains.apply(self.buckets, forecast_date)

            # Monthly tax withholding
            self.buckets["Cash"].transfer(
                self.monthly_tax_drip, self.buckets["Tax Collection"], tx_month
            )

            # Emergency liquidation
            liq_txns = self.refill_policy.generate_liquidation(self.buckets, tx_month)
            for tx in liq_txns:
                tx.apply(self.buckets, tx_month)

            # Monthly income and tax-relevant flows
            monthly_salary = sum(
                tx.get_salary(tx_month)
                for tx in self.policy_transactions + refill_txns + liq_txns
            )
            monthly_ss = sum(
                tx.get_social_security(tx_month)
                for tx in self.policy_transactions + refill_txns + liq_txns
            )
            monthly_roth_conversions = sum(
                tx.get_withdrawal(tx_month)
                for tx in self.policy_transactions
                if isinstance(tx, RothConversionTransaction)
            )
            monthly_deferred = (
                sum(
                    tx.get_withdrawal(tx_month)
                    for tx in self.policy_transactions + refill_txns + liq_txns
                )
                - monthly_roth_conversions
            )
            monthly_taxable = sum(
                tx.get_taxable_gain(tx_month)
                for tx in self.policy_transactions + refill_txns + liq_txns
            )
            monthly_penalty = sum(
                tx.get_penalty_eligible_withdrawal(tx_month)
                for tx in self.policy_transactions + refill_txns + liq_txns
            )

            # Accumulate yearly totals
            if year not in yearly_tax_log:
                yearly_tax_log[year] = {
                    "Tax-Deferred Withdrawals": 0,
                    "Taxable Gains": 0,
                    "Penalty Tax": 0,
                    "Roth Conversions": 0,
                    "Social Security": 0,
                    "Salary": 0,
                }
            ylog = yearly_tax_log[year]
            ylog["Tax-Deferred Withdrawals"] += monthly_deferred
            ylog["Taxable Gains"] += monthly_taxable
            ylog["Penalty Tax"] += monthly_penalty
            ylog["Roth Conversions"] += monthly_roth_conversions
            ylog["Social Security"] += monthly_ss
            ylog["Salary"] += monthly_salary

            # Accumulate quarterly totals
            if qkey not in quarterly_tax_log:
                quarterly_tax_log[qkey] = {
                    "Tax-Deferred Withdrawals": 0,
                    "Taxable Gains": 0,
                    "Roth Conversions": 0,
                    "Social Security": 0,
                    "Salary": 0,
                }
            qlog = quarterly_tax_log[qkey]
            qlog["Tax-Deferred Withdrawals"] += monthly_deferred
            qlog["Taxable Gains"] += monthly_taxable
            qlog["Roth Conversions"] += monthly_roth_conversions
            qlog["Social Security"] += monthly_ss
            qlog["Salary"] += monthly_salary

            # Snapshot balances
            snapshot = {"Date": forecast_date}
            for name, bucket in self.buckets.items():
                snapshot[name] = bucket.balance()
            records.append(snapshot)

            # Quarterly tax estimation
            if forecast_date.month in {3, 6, 9, 12}:
                ytd_log = {
                    "Tax-Deferred Withdrawals": 0,
                    "Taxable Gains": 0,
                    "Roth Conversions": 0,
                    "Social Security": 0,
                    "Salary": 0,
                }
                for q in range(1, quarter + 1):
                    qlog = quarterly_tax_log.get((year, q))
                    if qlog:
                        for k in ytd_log:
                            ytd_log[k] += qlog[k]

                tax_estimate = self.tax_calc.calculate_tax(
                    salary=ytd_log["Salary"],
                    ss_benefits=ytd_log["Social Security"],
                    withdrawals=ytd_log["Tax-Deferred Withdrawals"],
                    gains=ytd_log["Taxable Gains"],
                    roth=ytd_log["Roth Conversions"],
                    age=(
                        (forecast_date - pd.to_datetime(self.dob)).days / 365
                        if self.dob
                        else None
                    ),
                    standard_deduction=27700,
                )

                estimated_total = tax_estimate["total_tax"]
                paid_so_far = self.buckets["Tax Collection"].balance()
                remaining = max(estimated_total - paid_so_far, 0)
                months_remaining = 12 - forecast_date.month
                self.monthly_tax_drip = int(remaining / max(months_remaining, 1))

            # January: finalize prior‐year taxes
            if forecast_date.month == 1:
                prev_year = year - 1
                prev_log = yearly_tax_log.get(prev_year)
                if prev_log:
                    sal = prev_log["Salary"]
                    ss = prev_log["Social Security"]
                    wdraw = prev_log["Tax-Deferred Withdrawals"]
                    gain = prev_log["Taxable Gains"]
                    roth = prev_log.get("Roth Conversions", 0)

                    tax_breakdown = self.tax_calc.calculate_tax(
                        salary=sal,
                        ss_benefits=ss,
                        withdrawals=wdraw,
                        gains=gain,
                        roth=roth,
                        age=(
                            (year - pd.to_datetime(self.dob).year) if self.dob else None
                        ),
                        standard_deduction=27700,
                    )

                    agi = tax_breakdown.get("agi", sal + wdraw + gain)
                    taxable_ss = tax_breakdown.get("taxable_ss", ss)
                    ordinary_income = tax_breakdown.get(
                        "ordinary_income", sal + wdraw + taxable_ss
                    )
                    ord_tax = tax_breakdown["ordinary_tax"]
                    capg_tax = tax_breakdown["capital_gains_tax"]
                    pen_tax = tax_breakdown["penalty_tax"]
                    total_tax = tax_breakdown["total_tax"]

                    if pen_tax:
                        logging.debug(
                            f"[Penalty] ${pen_tax:,} early‐withdrawal penalty applied for {prev_year}"
                        )

                    paid_from_tc = self.buckets["Tax Collection"].withdraw(
                        total_tax, "Taxes", tx_month
                    )
                    remaining = total_tax - paid_from_tc
                    paid_from_cash = self.buckets["Cash"].withdraw(
                        remaining, "Taxes", tx_month
                    )

                    logging.debug(
                        f"[Yearly Tax:{prev_year}] paid "
                        f"${paid_from_tc:,} from Tax Collection + "
                        f"${paid_from_cash:,} from Cash "
                        f"(ordinary ${ord_tax:,} + gains ${capg_tax:,} + penalty ${pen_tax:,})"
                    )

                    leftover = self.buckets["Tax Collection"].balance()
                    next_est = max(total_tax - leftover, 0)
                    self.annual_tax_estimate = next_est
                    self.monthly_tax_drip = int(next_est / 12)
                    if next_est == 0 and leftover > 0:
                        self.buckets["Tax Collection"].transfer(
                            leftover, self.buckets["Cash"], tx_month
                        )
                        logging.debug(
                            f"[Tax Collection Cleanup] Moved ${leftover:,} "
                            "back to Cash (no tax due next year)"
                        )

                    tax_records.append(
                        {
                            "Year": prev_year,
                            "Adjusted Gross Income (AGI)": agi,
                            "Ordinary Income": ordinary_income,
                            "Total Tax": total_tax,
                            "Tax-Deferred Withdrawals": wdraw,
                            "Penalty Tax": pen_tax,
                            "Taxable Gains": gain,
                            "Capital Gains Tax": capg_tax,
                            "Roth Conversions": roth,
                            "Salary": sal,
                            "Social Security": ss,
                            "Taxable Social Security": taxable_ss,
                            "Ordinary Tax": ord_tax,
                        }
                    )

        return pd.DataFrame(records), pd.DataFrame(tax_records)
