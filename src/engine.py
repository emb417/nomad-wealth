import logging
import pandas as pd

from pandas.tseries.offsets import MonthBegin
from typing import Dict, List, Tuple

# Internal Imports
from domain import Bucket
from policies import ThresholdRefillPolicy
from economic_factors import MarketGains
from taxes import TaxCalculator
from transactions import Transaction


class ForecastEngine:
    def __init__(
        self,
        buckets: Dict[str, Bucket],
        transactions: List[Transaction],
        refill_policy: ThresholdRefillPolicy,
        market_gains: MarketGains,
        inflation: Dict[int, Dict[str, float]],
        tax_calc: TaxCalculator,
        profile: Dict[str, int],
    ):
        self.buckets = buckets
        self.transactions = transactions
        self.refill_policy = refill_policy
        self.market_gains = market_gains
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
            self.market_gains.apply(self.buckets, forecast_date)

            # 4) Accumulate flows into yearly_tax_log
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

            if year not in yearly_tax_log:
                yearly_tax_log[year] = {
                    "TaxDeferredWithdrawals": 0,
                    "TaxableGains": 0,
                    "Salary": 0,
                    "SocialSecurity": 0,
                }
            ylog = yearly_tax_log[year]
            ylog["Salary"] += monthly_salary
            ylog["SocialSecurity"] += monthly_ss
            ylog["TaxDeferredWithdrawals"] += monthly_deferred
            ylog["TaxableGains"] += monthly_taxable

            # 5) Snapshot balances
            snapshot = {"Date": forecast_date}
            for name, bucket in self.buckets.items():
                snapshot[name] = bucket.balance()
            records.append(snapshot)

            # 6) January: finalize prior‐year taxes
            if forecast_date.month == 1:
                prev_year = year - 1
                prev_log = yearly_tax_log.get(prev_year)
                if prev_log:
                    sal = prev_log["Salary"]
                    ss = prev_log["SocialSecurity"]
                    wdraw = prev_log["TaxDeferredWithdrawals"]
                    gain = prev_log["TaxableGains"]

                    # total tax
                    total_tax = self.tax_calc.calculate_tax(
                        salary=sal, ss_benefits=ss, withdrawals=wdraw, gains=gain
                    )
                    # ordinary = salary+SS+withdrawals only
                    ord_tax = self.tax_calc.calculate_tax(
                        salary=sal, ss_benefits=ss, withdrawals=wdraw, gains=0
                    )
                    capg_tax = total_tax - ord_tax

                    # pay full year’s bill
                    paid = self.buckets["Cash"].withdraw(total_tax)
                    logging.debug(
                        f"[Yearly Tax:{prev_year}] paid ${paid:,} "
                        f"(ordinary ${ord_tax:,} + gains ${capg_tax:,})"
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
                            "TotalTax": total_tax,
                        }
                    )

        return pd.DataFrame(records), pd.DataFrame(tax_records)
