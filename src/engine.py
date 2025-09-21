import logging
import pandas as pd

from pandas.tseries.offsets import MonthBegin
from typing import Dict, List, Tuple

# Internal Imports
from domain import Bucket
from policies import ThresholdRefillPolicy
from strategies import GainStrategy
from taxes import TaxCalculator
from transactions import Transaction


class ForecastEngine:
    def __init__(
        self,
        buckets: Dict[str, Bucket],
        transactions: List[Transaction],
        refill_policy: ThresholdRefillPolicy,
        gain_strategy: GainStrategy,
        inflation: Dict[int, Dict[str, float]],
        tax_calc: TaxCalculator,
        profile: Dict[str, int],
    ):
        self.buckets = buckets
        self.transactions = transactions
        self.refill_policy = refill_policy
        self.gain_strategy = gain_strategy
        self.inflation = inflation
        self.tax_calc = tax_calc
        self.profile = profile

    def run(self, ledger_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        records = []
        tax_records = []
        yearly_tax_log = {}

        for _, row in ledger_df.iterrows():
            forecast_date = pd.to_datetime(row["Date"])
            tx_month = (forecast_date - MonthBegin(1)).to_period("M")
            year = forecast_date.year

            # 1) Core transactions
            for tx in self.transactions:
                tx.apply(self.buckets, tx_month)

            # 2) Refill policy
            refill_txns = self.refill_policy.generate(self.buckets, tx_month)
            for tx in refill_txns:
                tx.apply(self.buckets, tx_month)

            # 3) Market returns
            self.gain_strategy.apply(self.buckets, forecast_date)

            # 4) Tax calculation & cash withdrawal

            # Gather monthly flows
            monthly_salary = sum(
                tx.get_salary(tx_month)
                for tx in self.transactions
                if callable(getattr(tx, "get_salary", None))
            )
            monthly_ss = sum(
                tx.get_social_security(tx_month)
                for tx in self.transactions
                if hasattr(tx, "get_social_security")
            )
            monthly_deferred = sum(
                tx.get_withdrawal(tx_month)
                for tx in (*self.transactions, *refill_txns)
                if tx.is_tax_deferred
            )
            monthly_taxable = sum(
                tx.get_taxable_gain(tx_month)
                for tx in (*self.transactions, *refill_txns)
                if tx.is_taxable
            )

            # 4a) Ordinary‐income tax (annualized → monthly slice)
            annual_ordinary_tax = self.tax_calc.calculate_tax(
                salary=monthly_salary * 12,
                ss_benefits=monthly_ss * 12,
                withdrawals=monthly_deferred,
                gains=0,
            )
            monthly_ordinary_tax = annual_ordinary_tax // 12

            # 4b) Capital‐gains tax (annualize gains, then slice)
            annual_gains_tax = self.tax_calc.calculate_tax(
                salary=0, ss_benefits=0, withdrawals=0, gains=monthly_taxable * 12
            )
            monthly_gains_tax = annual_gains_tax // 12

            # 4c) Combine and withdraw
            monthly_tax = monthly_ordinary_tax + monthly_gains_tax
            if monthly_tax > 0:
                paid = self.buckets["Cash"].withdraw(monthly_tax)
                logging.debug(
                    f"[Taxes:{tx_month}] paid ${paid:,} "
                    f"(ordinary ${monthly_ordinary_tax:,} + gains ${monthly_gains_tax:,})"
                )

            # 5) Yearly summary
            if year not in yearly_tax_log:
                yearly_tax_log[year] = {
                    "TaxDeferredWithdrawals": 0,
                    "TaxableGains": 0,
                    "Salary": 0,
                    "SocialSecurity": 0,
                    "TotalTax": 0,
                }
            ylog = yearly_tax_log[year]
            ylog["TaxDeferredWithdrawals"] += monthly_deferred
            ylog["TaxableGains"] += monthly_taxable
            ylog["Salary"] += monthly_salary
            ylog["SocialSecurity"] += monthly_ss
            ylog["TotalTax"] += monthly_tax

            # 7) Snapshot balances
            snapshot = {"Date": forecast_date}
            for name, bucket in self.buckets.items():
                snapshot[name] = bucket.balance()
            records.append(snapshot)

            # 8) Year‐end tax record
            if forecast_date.month == 12:
                tr = {"Year": year}
                tax_records.append(tr)

        return pd.DataFrame(records), pd.DataFrame(tax_records)
