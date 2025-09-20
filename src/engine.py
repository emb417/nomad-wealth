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

            # 1) Core transactions (fixed, recurring, salary, SS)
            for tx in self.transactions:
                tx.apply(self.buckets, tx_month)

            # 2) Refill policy (top up any bucket below its threshold)
            for refill_tx in self.refill_policy.generate(self.buckets, tx_month):
                refill_tx.apply(self.buckets, tx_month)

            # 3) Market returns (now applies to the *refilled* balances)
            self.gain_strategy.apply(self.buckets, forecast_date)

            # 4) Tax calculation & cash withdrawal
            #    (same as your existing tax section)
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
                for tx in self.transactions
                if getattr(tx, "is_tax_deferred", False)
            )
            monthly_taxable = sum(
                tx.get_taxable_gain(tx_month)
                for tx in self.transactions
                if getattr(tx, "is_taxable", False)
            )

            annual_tax = self.tax_calc.calculate_tax(
                salary=monthly_salary * 12,
                ss_benefits=monthly_ss * 12,
                withdrawals=monthly_deferred,
                gains=monthly_taxable,
            )
            monthly_tax = annual_tax // 12
            if monthly_tax > 0:
                self.buckets["Cash"].deposit(-monthly_tax)

            # update yearly summary…
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

            if self.buckets["Cash"].balance() < -100000:
                logging.warning(
                    f"[Yearly] {forecast_date} — Cash balance is low: ${self.buckets['Cash'].balance():,}"
                )
            # 5) Record end‐of‐month balances
            snapshot = {"Date": forecast_date}
            for name, bucket in self.buckets.items():
                snapshot[name] = bucket.balance()
            records.append(snapshot)

            # 6) Year‐end tax summary (same as before)…
            if forecast_date.month == 12:
                tr = {
                    "Year": year,
                    # … fill in your existing bracket/gains logic …
                }
                tax_records.append(tr)

        return pd.DataFrame(records), pd.DataFrame(tax_records)
