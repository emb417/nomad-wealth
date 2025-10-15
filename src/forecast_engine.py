import logging
import pandas as pd

from pandas.tseries.offsets import MonthBegin
from typing import Dict, List, Tuple

# Internal Imports
from buckets import Bucket
from economic_factors import MarketGains
from policies_engine import ThresholdRefillPolicy
from policies_transactions import PolicyTransaction
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
        self.profile = profile
        self.annual_tax_estimate = int(
            self.tax_calc.calculate_tax(
                salary=profile["Annual Gross Income"],
                ss_benefits=0,
                withdrawals=0,
                gains=0,
            )
        )
        self.monthly_tax_drip = int(self.annual_tax_estimate / 12)

    def run(self, ledger_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        records = []
        tax_records = []
        yearly_tax_log = {}

        for _, row in ledger_df.iterrows():
            forecast_date = pd.to_datetime(row["Date"])
            tx_month = (forecast_date - MonthBegin(1)).to_period("M")
            year = forecast_date.year

            # Rule-driven transactions
            for tx in self.rule_transactions:
                tx.apply(self.buckets, tx_month)

            # Policy-driven transactions (e.g. salary, social security, Roth conversions)
            for tx in self.policy_transactions:
                tx.apply(self.buckets, tx_month)

            # Refill policy
            refill_txns = self.refill_policy.generate_refills(self.buckets, tx_month)
            for tx in refill_txns:
                tx.apply(self.buckets, tx_month)

            # Market returns
            self.market_gains.apply(self.buckets, forecast_date)

            # Taxes: Monthly withdraw from Cash into Tax Collection
            self.buckets["Cash"].transfer(
                self.monthly_tax_drip, self.buckets["Tax Collection"], tx_month
            )

            # Liqudiate based on policy
            liq_txns = self.refill_policy.generate_liquidation(self.buckets, tx_month)
            for tx in liq_txns:
                tx.apply(self.buckets, tx_month)

            # Stats: Accumulate flows into yearly_tax_log
            monthly_salary = sum(
                tx.get_salary(tx_month)
                for tx in self.policy_transactions + refill_txns + liq_txns
            )
            monthly_ss = sum(
                tx.get_social_security(tx_month)
                for tx in self.policy_transactions + refill_txns + liq_txns
            )
            monthly_deferred = sum(
                tx.get_withdrawal(tx_month)
                for tx in self.policy_transactions + refill_txns + liq_txns
            )
            monthly_taxable = sum(
                tx.get_taxable_gain(tx_month)
                for tx in self.policy_transactions + refill_txns + liq_txns
            )
            monthly_penalty = sum(
                tx.get_penalty_tax(tx_month)
                for tx in self.policy_transactions + refill_txns + liq_txns
            )

            if year not in yearly_tax_log:
                yearly_tax_log[year] = {
                    "TaxDeferredWithdrawals": 0,
                    "TaxableGains": 0,
                    "Salary": 0,
                    "SocialSecurity": 0,
                    "PenaltyTax": 0,
                }
            ylog = yearly_tax_log[year]
            ylog["Salary"] += monthly_salary
            ylog["SocialSecurity"] += monthly_ss
            ylog["TaxDeferredWithdrawals"] += monthly_deferred
            ylog["TaxableGains"] += monthly_taxable
            ylog["PenaltyTax"] += monthly_penalty

            # Snapshot balances
            snapshot = {"Date": forecast_date}
            for name, bucket in self.buckets.items():
                snapshot[name] = bucket.balance()
            records.append(snapshot)

            # January: finalize prior‐year taxes
            if forecast_date.month == 1:
                prev_year = year - 1
                prev_log = yearly_tax_log.get(prev_year)
                if prev_log:
                    sal = prev_log["Salary"]
                    ss = prev_log["SocialSecurity"]
                    wdraw = prev_log["TaxDeferredWithdrawals"]
                    gain = prev_log["TaxableGains"]
                    pen = prev_log["PenaltyTax"]

                    # total tax
                    total_tax = self.tax_calc.calculate_tax(
                        salary=sal, ss_benefits=ss, withdrawals=wdraw, gains=gain
                    )
                    # ordinary = salary+SS+withdrawals only
                    ord_tax = self.tax_calc.calculate_tax(
                        salary=sal, ss_benefits=ss, withdrawals=wdraw, gains=0
                    )
                    capg_tax = total_tax - ord_tax

                    if pen:
                        logging.debug(
                            f"[Penalty] Adding ${pen:,} early‐withdrawal penalty for {prev_year}"
                        )
                        total_tax += pen

                    # pay full year’s bill
                    paid_from_tc = self.buckets["Tax Collection"].withdraw(
                        total_tax, "Taxes", tx_month
                    )
                    remaining = total_tax - paid_from_tc
                    paid_from_cash = self.buckets["Cash"].withdraw(
                        remaining, "Taxes", tx_month
                    )

                    logging.debug(
                        f"[Yearly Tax:{prev_year}] paid "
                        f"${paid_from_tc:,} from TaxCollection + "
                        f"${paid_from_cash:,} from Cash "
                        f"(ordinary ${ord_tax:,} + gains ${capg_tax:,})"
                    )

                    # Capture leftover in TaxCollection
                    leftover = self.buckets["Tax Collection"].balance()
                    next_est = max(total_tax - leftover, 0)
                    self.annual_tax_estimate = next_est
                    self.monthly_tax_drip = int(next_est / 12)
                    if next_est == 0 and leftover > 0:
                        self.buckets["Tax Collection"].transfer(
                            leftover, self.buckets["Cash"], tx_month
                        )
                        logging.debug(
                            f"[TaxCollection Cleanup] Moved ${leftover:,} "
                            "back to Cash (no tax due next year)"
                        )
                    tax_records.append(
                        {
                            "Year": prev_year,
                            "TaxDeferredWithdrawals": wdraw,
                            "TaxableGains": gain,
                            "Salary": sal,
                            "SocialSecurity": ss,
                            "OrdinaryTax": ord_tax,
                            "CapitalGainsTax": capg_tax,
                            "PenaltyTax": pen,
                            "TotalTax": total_tax,
                        }
                    )

        return pd.DataFrame(records), pd.DataFrame(tax_records)
