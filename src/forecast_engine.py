import logging
import pandas as pd

from typing import Any, Dict, List, Tuple, Optional, Union

# Internal Imports
from buckets import Bucket
from economic_factors import MarketGains
from policies_engine import ThresholdRefillPolicy
from policies_transactions import (
    PolicyTransaction,
    RothConversionTransaction,
    SEPPTransaction,
)
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
        magi: Dict[Union[str, int], Union[str, int]],
        retirement_period: str,
        sepp_policies: Optional[Dict[str, Any]],
        roth_policies: Dict[str, Dict[str, Union[int, float, bool]]],
        irmaa_brackets: List[Dict[str, float]],
        marketplace_premiums: Dict[str, Dict[str, float]],
    ):
        self.buckets = buckets
        self.rule_transactions = rule_transactions
        self.policy_transactions = policy_transactions
        self.refill_policy = refill_policy
        self.market_gains = market_gains
        self.inflation = inflation
        self.tax_calc = tax_calc
        self.dob = pd.to_datetime(dob).to_period("M")
        self.magi = {int(year): int(value) for year, value in magi.items()}
        self.retirement_period = pd.to_datetime(retirement_period).to_period("M")
        self.sepp_policies = sepp_policies or {}
        self.roth_policies = roth_policies
        self.irmaa_brackets = irmaa_brackets
        self.marketplace_premiums = marketplace_premiums

        self.annual_tax_estimate = 0
        self.monthly_tax_drip = 0
        self.records: List[Dict[str, Any]] = []
        self.tax_records: List[Dict[str, Any]] = []
        self.yearly_tax_log: Dict[int, Dict[str, int]] = {}
        self.quarterly_tax_log: Dict[Tuple[int, int], Dict[str, int]] = {}

    def run(self, ledger_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        self._initialize_results()

        for _, row in ledger_df.iterrows():
            forecast_month = row["Month"]

            self._apply_sepp_withdrawal(forecast_month)
            self._apply_marketplace_premiums(forecast_month)
            self._apply_irmaa_premiums(forecast_month)
            self._apply_rule_transactions(self.buckets, forecast_month)
            self._apply_policy_transactions(self.buckets, forecast_month)
            self.market_gains.apply(self.buckets, forecast_month)

            refill_txns = self.refill_policy.generate_refills(
                self.buckets, forecast_month
            )
            self._apply_refill_transactions(refill_txns, self.buckets, forecast_month)

            self._withhold_monthly_taxes(self.buckets, forecast_month)

            liq_txns = self.refill_policy.generate_liquidation(
                self.buckets, forecast_month
            )
            self._apply_liquidation_transactions(liq_txns, self.buckets, forecast_month)

            all_policy_txns = self.policy_transactions + refill_txns + liq_txns

            self._update_results(
                forecast_month,
                self.buckets,
                all_policy_txns,
            )

        return pd.DataFrame(self.records), pd.DataFrame(self.tax_records)

    def _initialize_results(self):
        self.records = []
        self.tax_records = []
        self.yearly_tax_log = {}
        self.quarterly_tax_log = {}

    def _get_age_in_years(self, period: pd.Period) -> float:
        """
        Compute age in years at the start of a given period.
        Assumes self.dob is a pd.Period("M").
        """
        return (period - self.dob).n / 12

    def _get_prior_year_end_balance(self, tx_month: pd.Period, bucket_name: str) -> int:
        prior_year = tx_month.year - 1
        candidates = [r for r in self.records if r["Month"].year == prior_year]
        if not candidates:
            return 0
        latest_record = max(candidates, key=lambda r: r["Month"])
        return latest_record.get(bucket_name, 0)

    def _apply_sepp_withdrawal(self, tx_month: pd.Period):
        if not self.sepp_policies.get("Enabled", False):
            return

        start_month = pd.to_datetime(self.sepp_policies["Start Month"]).to_period("M")
        end_month = pd.to_datetime(self.sepp_policies["End Month"]).to_period("M")

        if not (start_month <= tx_month < end_month):
            return

        source_bucket = self.sepp_policies["Source"]
        target_bucket = self.sepp_policies["Target"]
        source_pct = self.sepp_policies.get("Source Percentage", 1.0)

        balance = self._get_prior_year_end_balance(tx_month, source_bucket)
        adjusted_balance = balance * source_pct
        age = self._get_age_in_years(tx_month)
        life_expectancy = self._get_uniform_life_expectancy(int(age))
        monthly_amount = int(adjusted_balance / life_expectancy / 12)

        logging.info(
            f"Applying SEPP withdrawal of ${monthly_amount} from {source_bucket} to {target_bucket} in {tx_month}."
        )
        sepp_txn = SEPPTransaction(source_bucket, target_bucket)
        sepp_txn.apply(self.buckets, tx_month, monthly_amount)
        self.policy_transactions.append(sepp_txn)

    def _get_uniform_life_expectancy(self, age: int) -> float:
        table = {
            50: 33.1,
            55: 29.6,
            60: 25.2,
            65: 21.0,
            70: 17.0,
            75: 13.4,
            80: 10.2,
            85: 7.6,
            90: 5.5,
        }
        return next((v for a, v in sorted(table.items()) if age <= a), 33.1)

    def _apply_marketplace_premiums(self, tx_month: pd.Period) -> None:
        age = self._get_age_in_years(tx_month)
        if self.retirement_period > tx_month or age >= 65:
            return

        household_type = (
            "silver_family"
            if tx_month < pd.Period("2032-12", freq="M")
            else "silver_couple"
        )
        benchmark_premium = self.marketplace_premiums[household_type]["monthly_premium"]

        record = self._get_minus_2_tax_record(tx_month)
        prior_magi = (
            record["Adjusted Gross Income (AGI)"] + record["Tax-Exempt Interest"]
        )
        capped_monthly = (prior_magi * 0.085) / 12
        monthly_premium = int(min(benchmark_premium, capped_monthly))

        self.buckets["Cash"].withdraw(monthly_premium, "Marketplace Premium", tx_month)
        logging.debug(
            f"[Marketplace] Deducted ${monthly_premium:.0f} in {tx_month} "
            f"for {household_type} (age {age}, MAGI ${prior_magi:.0f}, cap ${capped_monthly:.0f})"
        )

    def _apply_irmaa_premiums(self, tx_month: pd.Period) -> None:
        age = self._get_age_in_years(tx_month)
        if age < 65:
            return

        record = self._get_minus_2_tax_record(tx_month)
        prior_magi = (
            record["Adjusted Gross Income (AGI)"] + record["Tax-Exempt Interest"]
        )

        for bracket in self.irmaa_brackets:
            if prior_magi <= float(bracket["max_magi"]):
                monthly_cost = int(bracket["part_b"] + bracket["part_d"])
                bracket_info = (
                    f"MAGI ${prior_magi:.0f}, bracket ≤ ${bracket['max_magi']}"
                )
                break
        else:
            monthly_cost = int(
                self.irmaa_brackets[-1]["part_b"] + self.irmaa_brackets[-1]["part_d"]
            )
            bracket_info = f"MAGI ${prior_magi:.0f}, bracket > all thresholds"

        self.buckets["Cash"].withdraw(monthly_cost, "IRMAA", tx_month)
        logging.debug(
            f"[IRMAA] Deducted ${monthly_cost:.0f} in {tx_month} ({bracket_info})"
        )

    def _get_minus_2_tax_record(self, tx_month: pd.Period) -> Dict[str, int]:
        year = tx_month.year - 2

        if year in self.magi:
            return {
                "Adjusted Gross Income (AGI)": self.magi[year],
                "Tax-Exempt Interest": 0,
            }

        record = next((r for r in self.tax_records if r.get("Year") == year), None)
        if record:
            return {
                "Adjusted Gross Income (AGI)": int(
                    record.get("Adjusted Gross Income (AGI)", 0)
                ),
                "Tax-Exempt Interest": int(record.get("Tax-Exempt Interest", 0)),
            }

        # MAGI must always be available — raise if missing
        raise ValueError(f"MAGI not available for year {year}")

    def _apply_rule_transactions(self, buckets, tx_month):
        for tx in self.rule_transactions:
            tx.apply(buckets, tx_month)

    def _apply_policy_transactions(self, buckets, tx_month):
        for tx in self.policy_transactions:
            if not isinstance(tx, (RothConversionTransaction, SEPPTransaction)):
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
        forecast_month: pd.Period,
        buckets: Dict[str, Bucket],
        all_policy_txns: List[PolicyTransaction],
    ):
        year = forecast_month.year
        quarter = (forecast_month.month - 1) // 3 + 1
        qkey = (year, quarter)

        salary, ss, deferred, realized, taxable, penalty, taxfree = (
            self._accumulate_monthly_tax_inputs(forecast_month, all_policy_txns)
        )

        self._update_tax_logs(
            year,
            qkey,
            self.yearly_tax_log,
            self.quarterly_tax_log,
            salary,
            ss,
            deferred,
            realized,
            taxable,
            penalty,
            taxfree,
        )

        self._update_tax_estimate_if_needed(forecast_month, buckets)

        if forecast_month.month == 12:
            self._apply_year_end_reconciliation(
                forecast_month,
                self.yearly_tax_log,
                buckets,
                self.tax_records,
            )

        self._record_snapshot(forecast_month, buckets)

    def _accumulate_monthly_tax_inputs(self, tx_month, txs):
        salary = sum(tx.get_salary(tx_month) for tx in txs)
        ss = sum(tx.get_social_security(tx_month) for tx in txs)
        deferred = sum(tx.get_withdrawal(tx_month) for tx in txs)
        realized = sum(tx.get_realized_gain(tx_month) for tx in txs)
        taxable = sum(tx.get_taxable_gain(tx_month) for tx in txs)
        penalty = sum(tx.get_penalty_eligible_withdrawal(tx_month) for tx in txs)
        taxfree = sum(tx.get_taxfree_withdrawal(tx_month) for tx in txs)
        return salary, ss, deferred, realized, taxable, penalty, taxfree

    def _update_tax_logs(
        self,
        year,
        qkey,
        yearly_log,
        quarterly_log,
        salary,
        ss,
        deferred,
        realized,
        taxable,
        penalty,
        taxfree,
    ):
        ylog = yearly_log.setdefault(
            year,
            {
                "Tax-Deferred Withdrawals": 0,
                "Realized Gains": 0,
                "Taxable Gains": 0,
                "Penalty Tax": 0,
                "Roth Conversions": 0,
                "Social Security": 0,
                "Salary": 0,
                "Tax-Free Withdrawals": 0,
            },
        )
        ylog["Salary"] += salary
        ylog["Social Security"] += ss
        ylog["Tax-Deferred Withdrawals"] += deferred
        ylog["Realized Gains"] += realized
        ylog["Taxable Gains"] += taxable
        ylog["Penalty Tax"] += penalty
        ylog["Tax-Free Withdrawals"] += taxfree

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
            age = self._get_age_in_years(forecast_date)
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
        tx_month: Optional[pd.Period] = None,
    ) -> int:
        # Use MAGI directly if available for the current year
        if tx_month is not None and tx_month.year in self.magi:
            logging.info(
                f"tx_month.year: {tx_month.year}, self.magi[tx_month.year]: {self.magi[tx_month.year]},standard_deduction: {standard_deduction}"
            )
            ordinary_income = max(0, self.magi[tx_month.year] - standard_deduction)
        else:
            taxable_ss = self.tax_calc._taxable_social_security(
                ss_benefits, salary + withdrawals + gains
            )
            ordinary_income = max(
                0, salary + withdrawals + taxable_ss - standard_deduction
            )

        federal_brackets = self.tax_calc.ordinary_tax_brackets["Federal 2025"]

        for bracket in federal_brackets:
            if bracket["tax_rate"] > max_rate:
                next_threshold = bracket["min_salary"]
                break
        else:
            next_threshold = float("inf")

        headroom = max(0, next_threshold - ordinary_income)
        return int(headroom)

    def _apply_roth_conversion_if_eligible(
        self,
        forecast_month: pd.Period,
        ylog: dict,
    ) -> int:
        age = self._get_age_in_years(forecast_month)

        # Determine phase based on age and cutoff
        for phase, policy in self.roth_policies.items():
            if age < policy.get("Cutoff Age", float("inf")):
                phase_config = policy
                break
        else:
            phase_config = {}

        if not phase_config.get("Allow Conversion", True):
            logging.debug(
                f"[Roth] Skipping conversion in {forecast_month} — phase disallows conversion"
            )
            return 0

        max_rate = phase_config.get("Max Tax Rate", 0.0)

        headroom = self._estimate_roth_headroom(
            salary=ylog["Salary"],
            ss_benefits=ylog["Social Security"],
            withdrawals=ylog["Tax-Deferred Withdrawals"],
            gains=ylog["Taxable Gains"],
            max_rate=max_rate,
            tx_month=forecast_month,
        )

        max_amt = phase_config.get("Max Conversion Amount")
        if max_amt is not None:
            headroom = int(min(headroom, max_amt))

        if headroom <= 0:
            return 0

        roth_tx = RothConversionTransaction(
            source_bucket="Tax-Deferred",
            target_bucket="Tax-Free",
        )
        converted = roth_tx.apply(self.buckets, forecast_month, headroom)
        logging.debug(
            f"[Roth] Applied conversion of ${converted:,} in {forecast_month} with headroom ${headroom:,}"
        )
        return converted

    def _apply_year_end_reconciliation(
        self,
        forecast_month: pd.Period,
        yearly_tax_log: Dict[int, Dict[str, int]],
        buckets: Dict[str, Bucket],
        tax_records: List[Dict[str, Any]],
    ):
        year = forecast_month.year
        ylog = yearly_tax_log.get(year)
        if not ylog:
            raise RuntimeError(
                f"Missing yearly_tax_log entry for {year} before reconciliation"
            )

        age = self._get_age_in_years(forecast_month)

        # Apply Roth conversion using finalized year-end snapshot
        converted = self._apply_roth_conversion_if_eligible(
            forecast_month=forecast_month,
            ylog=ylog,
        )
        ylog["Roth Conversions"] = converted

        # Final tax calculation
        penalty_basis = ylog.get("Penalty Tax", 0)
        final_tax = self.tax_calc.calculate_tax(
            salary=ylog.get("Salary", 0),
            ss_benefits=ylog.get("Social Security", 0),
            withdrawals=ylog.get("Tax-Deferred Withdrawals", 0),
            gains=ylog.get("Taxable Gains", 0),
            roth=converted,
            age=age,
            penalty_basis=penalty_basis,
            standard_deduction=27700,
        )

        # Pay from Tax Collection, then Cash if needed
        if final_tax["total_tax"] > 0:
            paid_from_tc = buckets["Tax Collection"].withdraw(
                final_tax["total_tax"], "Taxes", forecast_month
            )
            if final_tax["total_tax"] > paid_from_tc:
                buckets["Cash"].withdraw(
                    final_tax["total_tax"] - paid_from_tc, "Taxes", forecast_month
                )

        # Handle leftover tax collection
        leftover = buckets["Tax Collection"].balance()
        self.annual_tax_estimate = max(final_tax["total_tax"] - leftover, 0)
        self.monthly_tax_drip = int(self.annual_tax_estimate / 12)
        if self.annual_tax_estimate == 0 and leftover > 0:
            buckets["Tax Collection"].transfer(
                leftover, buckets["Cash"], forecast_month
            )

        # Log tax record
        tax_records.append(
            {
                "Year": year,
                "Adjusted Gross Income (AGI)": final_tax.get("agi"),
                "Ordinary Income": final_tax.get("ordinary_income"),
                "Total Tax": final_tax["total_tax"],
                "Tax-Free Withdrawals": ylog.get("Tax-Free Withdrawals", 0),
                "Tax-Deferred Withdrawals": ylog.get("Tax-Deferred Withdrawals", 0),
                "Penalty Tax": final_tax["penalty_tax"],
                "Realized Gains": ylog.get("Realized Gains", 0),
                "Taxable Gains": ylog.get("Taxable Gains", 0),
                "Capital Gains Tax": final_tax["capital_gains_tax"],
                "Roth Conversions": converted,
                "Salary": ylog.get("Salary", 0),
                "Social Security": ylog.get("Social Security", 0),
                "Taxable Social Security": final_tax.get("taxable_ss"),
                "Ordinary Tax": final_tax["ordinary_tax"],
            }
        )

    def _record_snapshot(self, forecast_date, buckets):
        snapshot = {"Month": forecast_date}
        for name, bucket in buckets.items():
            snapshot[name] = bucket.balance()
        self.records.append(snapshot)
