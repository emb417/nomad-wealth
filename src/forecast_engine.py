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
        dob: str,
        policies: Dict[str, Dict[str, int]],
    ):
        self.buckets = buckets
        self.rule_transactions = rule_transactions
        self.policy_transactions = policy_transactions
        self.refill_policy = refill_policy
        self.market_gains = market_gains
        self.inflation = inflation
        self.tax_calc = tax_calc
        self.dob = dob
        self.roth_conversion = policies["roth_conversion"]
        self.roth_start_date = pd.to_datetime(self.roth_conversion["Start Date"])
        self.roth_max_rate = self.roth_conversion["Max Tax Rate"]

        # Tax tracking
        self.annual_tax_estimate = 0
        self.monthly_tax_drip = 0
        self.prior_tax_context = {
            "Salary": 0,
            "Social Security": 0,
            "Tax-Deferred Withdrawals": 0,
            "Taxable Gains": 0,
            "Roth Conversions": 0,
            "Estimated Tax": 0,
        }

        # Logs for tracking tax inputs and outputs
        self.yearly_tax_log: Dict[int, Dict[str, int]] = {}
        self.quarterly_tax_log: Dict[Tuple[int, int], Dict[str, int]] = {}

    def run(self, ledger_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        records, tax_records, yearly_tax_log, quarterly_tax_log = (
            self._initialize_results()
        )

        for _, row in ledger_df.iterrows():
            forecast_date = pd.to_datetime(row["Date"])
            tx_month = (forecast_date - MonthBegin(1)).to_period("M")

            self._apply_rule_transactions(self.buckets, tx_month)
            self._apply_policy_transactions(self.buckets, tx_month)

            refill_txns = self.refill_policy.generate_refills(self.buckets, tx_month)
            self._apply_refill_transactions(refill_txns, self.buckets, tx_month)

            self.market_gains.apply(self.buckets, forecast_date)
            self._withhold_monthly_taxes(self.buckets, tx_month)

            liq_txns = self.refill_policy.generate_liquidation(self.buckets, tx_month)
            self._apply_liquidation_transactions(liq_txns, self.buckets, tx_month)

            all_policy_txns = self.policy_transactions + refill_txns + liq_txns

            records, tax_records, yearly_tax_log, quarterly_tax_log = (
                self._update_results(
                    records,
                    tax_records,
                    yearly_tax_log,
                    quarterly_tax_log,
                    forecast_date,
                    tx_month,
                    self.buckets,
                    all_policy_txns,
                )
            )

        return pd.DataFrame(records), pd.DataFrame(tax_records)

    def _initialize_results(self):
        records = []
        tax_records = []
        yearly_tax_log = {}
        quarterly_tax_log = {}
        return records, tax_records, yearly_tax_log, quarterly_tax_log

    def _apply_rule_transactions(self, buckets, tx_month):
        for tx in self.rule_transactions:
            tx.apply(buckets, tx_month)

    def _apply_policy_transactions(self, buckets, tx_month):
        for tx in self.policy_transactions:
            if not isinstance(tx, RothConversionTransaction):
                tx.apply(buckets, tx_month)

    def _apply_refill_transactions(self, refill_txns, buckets, tx_month):
        for tx in refill_txns:
            tx.apply(buckets, tx_month)

    def _withhold_monthly_taxes(self, buckets, tx_month):
        buckets["Cash"].transfer(
            self.monthly_tax_drip, buckets["Tax Collection"], tx_month
        )

    def _apply_liquidation_transactions(self, liq_txns, buckets, tx_month):
        for tx in liq_txns:
            tx.apply(buckets, tx_month)

    def _update_results(
        self,
        records,
        tax_records,
        yearly_tax_log,
        quarterly_tax_log,
        forecast_date,
        tx_month,
        buckets,
        all_policy_txns,
    ):
        year = forecast_date.year
        quarter = (forecast_date.month - 1) // 3 + 1
        qkey = (year, quarter)

        salary, ss, deferred, taxable, penalty = self._accumulate_monthly_tax_inputs(
            tx_month, all_policy_txns
        )
        self._update_tax_logs(
            year,
            qkey,
            yearly_tax_log,
            quarterly_tax_log,
            salary,
            ss,
            deferred,
            taxable,
            penalty,
        )
        self._update_tax_estimate_if_needed(forecast_date, buckets)
        self._apply_yearly_tax_payment_if_needed(
            forecast_date, tx_month, yearly_tax_log, buckets, tax_records
        )
        self._record_snapshot(records, forecast_date, buckets)

        return records, tax_records, yearly_tax_log, quarterly_tax_log

    def _accumulate_monthly_tax_inputs(self, tx_month, txs):
        salary = sum(tx.get_salary(tx_month) for tx in txs)
        ss = sum(tx.get_social_security(tx_month) for tx in txs)
        deferred = sum(tx.get_withdrawal(tx_month) for tx in txs)
        taxable = sum(tx.get_taxable_gain(tx_month) for tx in txs)
        penalty = sum(tx.get_penalty_eligible_withdrawal(tx_month) for tx in txs)
        return salary, ss, deferred, taxable, penalty

    def _update_tax_logs(
        self,
        year,
        qkey,
        yearly_log,
        quarterly_log,
        salary,
        ss,
        deferred,
        taxable,
        penalty,
    ):
        ylog = yearly_log.setdefault(
            year,
            {
                "Tax-Deferred Withdrawals": 0,
                "Taxable Gains": 0,
                "Penalty Tax": 0,
                "Roth Conversions": 0,
                "Social Security": 0,
                "Salary": 0,
            },
        )
        ylog["Salary"] += salary
        ylog["Social Security"] += ss
        ylog["Tax-Deferred Withdrawals"] += deferred
        ylog["Taxable Gains"] += taxable
        ylog["Penalty Tax"] += penalty

        qlog = quarterly_log.setdefault(
            qkey,
            {
                "Tax-Deferred Withdrawals": 0,
                "Taxable Gains": 0,
                "Roth Conversions": 0,
                "Social Security": 0,
                "Salary": 0,
            },
        )
        qlog["Salary"] += salary
        qlog["Social Security"] += ss
        qlog["Tax-Deferred Withdrawals"] += deferred
        qlog["Taxable Gains"] += taxable

    def _update_tax_estimate_if_needed(self, forecast_date, buckets):
        if forecast_date.month in {3, 6, 9, 12}:
            year = forecast_date.year
            quarter = (forecast_date.month - 1) // 3 + 1
            ytd_raw = {
                "Salary": 0,
                "Social Security": 0,
                "Tax-Deferred Withdrawals": 0,
                "Taxable Gains": 0,
                "Roth Conversions": 0,
            }
            for q in range(1, quarter + 1):
                qlog = self.quarterly_tax_log.get((year, q), {})
                for k in ytd_raw:
                    ytd_raw[k] += qlog.get(k, 0)
            ytd = {
                "salary": ytd_raw["Salary"],
                "ss_benefits": ytd_raw["Social Security"],
                "withdrawals": ytd_raw["Tax-Deferred Withdrawals"],
                "gains": ytd_raw["Taxable Gains"],
                "roth": ytd_raw["Roth Conversions"],
            }
            age = (
                (forecast_date - pd.to_datetime(self.dob)).days / 365
                if self.dob
                else None
            )
            estimate = self.tax_calc.calculate_tax(
                **ytd, age=age, standard_deduction=27700
            )["total_tax"]
            paid = buckets["Tax Collection"].balance()
            self.monthly_tax_drip = int(
                max(estimate - paid, 0) / max(12 - forecast_date.month, 1)
            )

    def _estimate_roth_headroom(
        self,
        salary: int,
        ss_benefits: int,
        withdrawals: int,
        gains: int,
        max_rate: float,
        standard_deduction: int = 27700,
    ) -> int:
        BRACKET_YEAR = "Federal 2025"
        taxable_ss = self.tax_calc._taxable_social_security(
            ss_benefits, salary + withdrawals + gains
        )
        ordinary_income = max(0, salary + withdrawals + taxable_ss - standard_deduction)

        federal_brackets = self.tax_calc.ordinary_tax_brackets[BRACKET_YEAR]
        headroom = 0
        for i, bracket in enumerate(federal_brackets):
            rate = bracket["tax_rate"]
            if rate > max_rate:
                break
            upper = (
                federal_brackets[i + 1]["min_salary"]
                if i + 1 < len(federal_brackets)
                else float("inf")
            )
            if ordinary_income < upper:
                headroom = upper - ordinary_income

        return int(headroom)

    def _apply_roth_conversion_if_eligible(
        self,
        forecast_date: pd.Timestamp,
        ylog: dict,
    ) -> int:
        conversion_month = pd.Period(forecast_date - pd.DateOffset(months=1), freq="M")
        conversion_date = conversion_month.to_timestamp()

        if conversion_date < self.roth_start_date:
            logging.debug(
                f"[Roth] Skipping conversion in {conversion_month} — before start date {self.roth_start_date}"
            )
            return 0

        headroom = max(
            0,
            self._estimate_roth_headroom(
                salary=ylog["Salary"],
                ss_benefits=ylog["Social Security"],
                withdrawals=ylog["Tax-Deferred Withdrawals"],
                gains=ylog["Taxable Gains"],
                max_rate=self.roth_max_rate,
            ),
        )

        if headroom <= 0:
            return 0

        roth_tx = RothConversionTransaction(
            source_bucket="Tax-Deferred",
            target_bucket="Tax-Free",
        )
        converted = roth_tx.apply(self.buckets, conversion_month, headroom)
        logging.debug(
            f"[Roth] Applied conversion of ${converted:,} in {conversion_month} with headroom ${headroom:,}"
        )
        return converted

    def _apply_yearly_tax_payment_if_needed(
        self, forecast_date, tx_month, yearly_tax_log, buckets, tax_records
    ):
        if forecast_date.month != 1:
            return

        prev_year = forecast_date.year - 1
        ylog = yearly_tax_log.get(prev_year)
        if not ylog:
            return

        age = forecast_date.year - pd.to_datetime(self.dob).year

        # Apply Roth conversion if eligible
        converted = self._apply_roth_conversion_if_eligible(
            forecast_date=forecast_date,
            ylog=ylog,
        )
        ylog["Roth Conversions"] += converted

        # Final tax calculation
        penalty_basis = ylog.get("Penalty Tax", 0)
        final_tax = self.tax_calc.calculate_tax(
            salary=ylog["Salary"],
            ss_benefits=ylog["Social Security"],
            withdrawals=ylog["Tax-Deferred Withdrawals"],
            gains=ylog["Taxable Gains"],
            roth=ylog["Roth Conversions"],
            age=age,
            penalty_basis=penalty_basis,
            standard_deduction=27700,
        )

        if final_tax["total_tax"] > 0:
            paid_from_tc = buckets["Tax Collection"].withdraw(
                final_tax["total_tax"], "Taxes", tx_month
            )
            if final_tax["total_tax"] > paid_from_tc:
                buckets["Cash"].withdraw(
                    final_tax["total_tax"] - paid_from_tc, "Taxes", tx_month
                )

        leftover = buckets["Tax Collection"].balance()
        self.annual_tax_estimate = max(final_tax["total_tax"] - leftover, 0)
        self.monthly_tax_drip = int(self.annual_tax_estimate / 12)
        if self.annual_tax_estimate == 0 and leftover > 0:
            buckets["Tax Collection"].transfer(leftover, buckets["Cash"], tx_month)

        tax_records.append(
            {
                "Year": prev_year,
                "Adjusted Gross Income (AGI)": final_tax.get("agi"),
                "Ordinary Income": final_tax.get("ordinary_income"),
                "Total Tax": final_tax["total_tax"],
                "Tax-Deferred Withdrawals": ylog["Tax-Deferred Withdrawals"],
                "Penalty Tax": final_tax["penalty_tax"],
                "Taxable Gains": ylog["Taxable Gains"],
                "Capital Gains Tax": final_tax["capital_gains_tax"],
                "Roth Conversions": ylog["Roth Conversions"],
                "Salary": ylog["Salary"],
                "Social Security": ylog["Social Security"],
                "Taxable Social Security": final_tax.get("taxable_ss"),
                "Ordinary Tax": final_tax["ordinary_tax"],
            }
        )

    def _record_snapshot(self, records, forecast_date, buckets):
        snapshot = {"Date": forecast_date}
        for name, bucket in buckets.items():
            snapshot[name] = bucket.balance()
        records.append(snapshot)
