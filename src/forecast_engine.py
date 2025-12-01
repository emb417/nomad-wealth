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
        magi: Dict[str, int],
        retirement_period: str,
        sepp_policies: Optional[Dict[str, Any]],
        roth_policies: Dict[str, Dict[str, Union[int, float, bool]]],
        marketplace_premiums: Dict[str, Any],
        ytd_income: Dict[str, int],
        dep_dob: str,
        forecast_start_year: int | None = None,
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

        self.irmaa_brackets_by_year = tax_calc.irmaa_brackets_by_year
        self.base_premiums_by_year = tax_calc.base_premiums_by_year

        self.marketplace_premiums = marketplace_premiums
        self.dep_dob = pd.to_datetime(dep_dob).to_period("M")
        self.forecast_start_year: int = forecast_start_year or pd.Timestamp.now().year

        self.ytd_income = {k: int(v) for k, v in ytd_income.items()}
        self.annual_tax_estimate = 0
        self.monthly_tax_drip = 0
        self.records: List[Dict[str, Any]] = []
        self.tax_records: List[Dict[str, Any]] = []
        self.yearly_tax_log: Dict[int, Dict[str, int]] = {}

    def run(
        self, ledger_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        self._initialize_results()
        if not ledger_df.empty:
            first_month = pd.Period(ledger_df.iloc[0]["Month"], freq="M")
            self.forecast_start_year = first_month.start_time.year

        for _, row in ledger_df.iterrows():
            forecast_month = row["Month"]

            self._apply_sepp_withdrawal(forecast_month)
            self._apply_rule_transactions(self.buckets, forecast_month)
            self._apply_policy_transactions(self.buckets, forecast_month)

            self._apply_marketplace_premiums(forecast_month)
            self._apply_irmaa_premiums(forecast_month)

            gain_txns, monthly_returns = self.market_gains.apply(
                self.buckets, forecast_month
            )
            self._apply_market_gain_transactions(
                gain_txns, self.buckets, forecast_month
            )

            refill_txns = self.refill_policy.generate_refills(
                self.buckets, forecast_month
            )
            self._apply_refill_transactions(refill_txns, self.buckets, forecast_month)

            liq_txns = self.refill_policy.generate_liquidation(
                self.buckets, forecast_month
            )
            self._apply_liquidation_transactions(liq_txns, self.buckets, forecast_month)

            all_policy_txns = (
                self.policy_transactions + gain_txns + refill_txns + liq_txns
            )

            self._update_results(forecast_month, self.buckets, all_policy_txns)

            # Log monthly returns for audit/visualization
            self.monthly_return_records.append(
                {"Month": forecast_month, **monthly_returns}
            )

        return (
            pd.DataFrame(self.records),
            pd.DataFrame(self.tax_records),
            pd.DataFrame(self.monthly_return_records),
        )

    def _initialize_results(self):
        self.records = []
        self.tax_records = []
        self.yearly_tax_log = {}
        self.monthly_return_records = []

        # YTD baseline for the first simulation year
        self.ytd_baseline = {}
        if self.ytd_income:
            self.ytd_baseline = {
                "unemployment": self.ytd_income.get("unemployment", 0),
                "fixed_income_interest": self.ytd_income.get(
                    "fixed_income_interest", 0
                ),
                "salary": self.ytd_income.get("salary", 0),
                "ss_benefits": self.ytd_income.get("ss_benefits", 0),
                "withdrawals": self.ytd_income.get("withdrawals", 0),
                "gains": self.ytd_income.get("gains", 0),
                "roth": 0,
                "penalty_basis": 0,
                "tax_paid": self.ytd_income.get("tax_paid", 0),
            }

    def _get_age_in_years(self, period: pd.Period) -> float:
        """
        Compute age in years at the start of a given period.
        Assumes self.dob is a pd.Period("M").
        """
        return (period - self.dob).n / 12

    def _get_dependent_age(self, tx_month: pd.Period) -> int:
        return (tx_month.start_time.year - self.dep_dob.start_time.year) - (
            1 if tx_month.month < self.dep_dob.month else 0
        )

    def _get_prior_year_end_balance(self, tx_month: pd.Period, bucket_name: str) -> int:
        prior_year = tx_month.year - 1
        candidates = [r for r in self.records if r["Month"].year == prior_year]
        if not candidates:
            return 0
        latest_record = max(candidates, key=lambda r: r["Month"])
        return latest_record.get(bucket_name, 0)

    def _get_spend_basis(self, tx_month: pd.Period) -> float:
        """
        Sum all expense-type withdrawals from Cash for the given month.
        Uses FlowTracker records instead of re-applying transactions.
        """
        df = self.buckets["Cash"].flow_tracker.to_dataframe()
        if df.empty:
            return 0.0

        # Filter for this month and withdrawals
        month_records = df[(df["date"] == tx_month) & (df["type"] == "withdraw")]

        # Optional: filter out non-expense categories if needed
        expense_records = month_records[
            ~month_records["target"].isin(["Investment", "Transfer"])
        ]

        return float(expense_records["amount"].sum())

    def _calculate_sepp_amortized_annual_payment(
        self, principal: int, interest_rate: float, life_expectancy: float
    ) -> int:
        """
        Calculate annual SEPP payment using IRS amortization method.
        """
        if interest_rate == 0:
            return int(round(principal / life_expectancy))
        r = interest_rate
        payment = principal * (r / (1 - (1 + r) ** (-life_expectancy)))
        return int(round(payment))

    def _apply_sepp_withdrawal(self, tx_month: pd.Period):
        if not self.sepp_policies.get("Enabled", False):
            return

        start_month = pd.to_datetime(self.sepp_policies["Start Month"]).to_period("M")
        end_month = pd.to_datetime(self.sepp_policies["End Month"]).to_period("M")

        if not (start_month <= tx_month < end_month):
            return

        source_bucket = self.sepp_policies["Source"]
        target_bucket = self.sepp_policies["Target"]

        # Cache the monthly payment at the start of the SEPP period
        if not hasattr(self, "_sepp_monthly_amount"):
            principal = self._get_prior_year_end_balance(start_month, source_bucket)
            interest_rate = self.sepp_policies["Interest Rate"]
            age = int(self._get_age_in_years(start_month))
            life_expectancy = self._get_uniform_life_expectancy(age)

            annual_payment = self._calculate_sepp_amortized_annual_payment(
                principal, interest_rate, life_expectancy
            )
            self._sepp_monthly_amount = int(round(annual_payment / 12))

            logging.debug(
                f"[SEPP] Initialized IRS-compliant amortized monthly payment: ${self._sepp_monthly_amount} "
                f"from principal ${principal}, rate {interest_rate:.2%}, life expectancy {life_expectancy}"
            )

        monthly_amount = self._sepp_monthly_amount
        if monthly_amount <= 0:
            return

        logging.debug(
            f"[SEPP] Applying withdrawal of ${monthly_amount} from {source_bucket} to {target_bucket} in {tx_month}"
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

    def _inflated_premium(self, base_premium: float, tx_month: pd.Period) -> float:
        year = tx_month.start_time.year
        year_infl = self.inflation.get(year, {})
        health_rate = year_infl.get("Health", year_infl.get("default", 0.02))
        years_elapsed = max(0, year - self.forecast_start_year)
        return base_premium * ((1 + health_rate) ** years_elapsed)

    def _projected_annual_agi(
        self,
        year: int,
        tx_month: pd.Period,
        age_current_month: float,
        magi_factor: float,
    ) -> float:
        """
        Estimate annual AGI with year-locked application of magi_factor:
        - If MAGI override exists, use it.
        - For the first forecast year: AGI = YTD income already realized + projected remaining spend.
        - For future years: AGI = January spend * 12.
        - Apply magi_factor only if age on Jan 1 of the year is < 59.5 (no mid-year flips).
        """
        # 0) MAGI override
        if year in getattr(self, "magi", {}):
            return float(self.magi[year])

        forecast_start = getattr(self, "forecast_start_year", year)

        # Age lock at year start to avoid mid-year premium changes
        jan_period = pd.Period(f"{year}-01", freq="M")
        age_at_jan = self._get_age_in_years(jan_period)
        apply_factor = age_at_jan < 59.5

        if year == forecast_start:
            # First simulation year: YTD income + remaining spend
            ytd_income_total = (
                float(sum(getattr(self, "ytd_income", {}).values()))
                if getattr(self, "ytd_income", None)
                else 0.0
            )

            spend_ytd = sum(
                self._get_spend_basis(m)
                for m in pd.period_range(
                    start=pd.Period(f"{year}-01", freq="M"), end=tx_month, freq="M"
                )
            )
            months_elapsed = max(1, tx_month.month)
            avg_spend_per_month = spend_ytd / months_elapsed
            annual_spend_target = avg_spend_per_month * 12.0
            remaining_spend = max(0.0, annual_spend_target - spend_ytd)

            spend_component = remaining_spend * (magi_factor if apply_factor else 1.0)
            return ytd_income_total + spend_component

        else:
            # Future years: January spend sets the annual spend target
            jan_spend = self._get_spend_basis(jan_period)
            annual_spend_target = jan_spend * 12.0

            spend_component = annual_spend_target * (
                magi_factor if apply_factor else 1.0
            )
            return spend_component

    def _lookup_marketplace_credit(
        self, bands: list[dict], annual_agi: float, cap: float
    ) -> float:
        """
        Interpolate monthly credit from marketplace_credit_bands.
        Clamp to 0 if income > cap.
        """
        if annual_agi > cap:
            return 0.0

        points = sorted(bands, key=lambda b: b["income"])
        if not points:
            return 0.0

        if annual_agi <= points[0]["income"]:
            return points[0]["credit"]
        if annual_agi >= points[-1]["income"]:
            return points[-1]["credit"]

        for i in range(len(points) - 1):
            x0, y0 = points[i]["income"], points[i]["credit"]
            x1, y1 = points[i + 1]["income"], points[i + 1]["credit"]
            if x0 <= annual_agi <= x1:
                t = (annual_agi - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return 0.0

    def _apply_marketplace_premiums(self, tx_month: pd.Period) -> None:
        age = self._get_age_in_years(tx_month)
        if self.retirement_period > tx_month or age >= 65:
            return

        year = tx_month.start_time.year
        magi_factor = self.marketplace_premiums.get("magi_factor", 1.0)

        # --- Estimate annual AGI ---
        annual_agi = self._projected_annual_agi(year, tx_month, age, magi_factor)

        couple_cfg = self.marketplace_premiums["couple"]
        family_cfg = self.marketplace_premiums["family"]

        # --- Dependent age check ---
        dep_age = self._get_dependent_age(tx_month)
        dep_off_plan = (
            dep_age >= 25
        )  # once dependent turns 25, they move to own insurance

        # --- Free OHP for whole family ---
        if not dep_off_plan and annual_agi <= family_cfg["ohp_salary_cap"]:
            self.buckets["Cash"].withdraw(0, "OHP Coverage", tx_month)
            logging.debug(
                f"[OHP] {year} AGI=${annual_agi:.0f} <= cap ${family_cfg['ohp_salary_cap']}, "
                f"premium=$0 (full family covered by OHP)"
            )
            return

        # --- Marketplace bracket selection ---
        if dep_off_plan:
            # Dependent is 25+ → only couple plan applies
            bracket_name, bracket = "couple", couple_cfg
            cap = couple_cfg["adults_marketplace_salary_cap"]
        else:
            # Dependent still under 25
            if annual_agi <= couple_cfg["dependent_ohp_salary_cap"]:
                if annual_agi <= couple_cfg["adults_marketplace_salary_cap"]:
                    bracket_name, bracket = "couple", couple_cfg
                    cap = couple_cfg["adults_marketplace_salary_cap"]
                elif annual_agi <= family_cfg["marketplace_salary_cap"]:
                    bracket_name, bracket = "family", family_cfg
                    cap = family_cfg["marketplace_salary_cap"]
                else:
                    bracket_name, bracket = "family", family_cfg
                    cap = family_cfg["marketplace_salary_cap"]
            else:
                if annual_agi <= family_cfg["marketplace_salary_cap"]:
                    bracket_name, bracket = "family", family_cfg
                    cap = family_cfg["marketplace_salary_cap"]
                else:
                    bracket_name, bracket = "family", family_cfg
                    cap = family_cfg["marketplace_salary_cap"]

        # --- Inflate benchmark silver premium ---
        benchmark_monthly = self._inflated_premium(bracket["monthly_premium"], tx_month)

        # --- Lookup marketplace credit ---
        monthly_credit = self._lookup_marketplace_credit(
            bracket["marketplace_credit_bands"], annual_agi, cap
        )

        # --- Net premium ---
        monthly_premium_net = int(max(0.0, benchmark_monthly - monthly_credit))
        self.buckets["Cash"].withdraw(
            monthly_premium_net, "Marketplace Premiums", tx_month
        )

        logging.debug(
            f"[Marketplace] {year} bracket={bracket_name} dep_age={dep_age} dep_off_plan={dep_off_plan} "
            f"AGI=${annual_agi:.0f} credit=${monthly_credit:.0f} "
            f"benchmark=${benchmark_monthly:.0f} net=${monthly_premium_net:.0f}"
        )

    def _apply_irmaa_premiums(self, tx_month: pd.Period) -> None:
        age = self._get_age_in_years(tx_month)
        if age < 65:
            return

        # Use prior MAGI (two years back)
        record = self._get_minus_2_tax_record(tx_month)
        prior_magi = record["AGI"] + record["Tax-Exempt Interest"]

        year = tx_month.year

        # Get base premiums for this year (per person)
        base_premiums = self.base_premiums_by_year.get(
            year, {"part_b": 0.0, "part_d": 0.0}
        )

        # Find IRMAA surcharge bracket for this year
        surcharge_b = 0.0
        surcharge_d = 0.0
        bracket_info = "No IRMAA brackets found"

        for bracket in self.irmaa_brackets_by_year.get(year, []):
            if prior_magi <= float(bracket["max_magi"]):
                surcharge_b = bracket["part_b"]
                surcharge_d = bracket["part_d"]
                bracket_info = (
                    f"MAGI ${prior_magi:.0f}, bracket ≤ ${bracket['max_magi']}"
                )
                break
        else:
            if self.irmaa_brackets_by_year.get(year, []):
                top = self.irmaa_brackets_by_year[year][-1]
                surcharge_b = top["part_b"]
                surcharge_d = top["part_d"]
                bracket_info = f"MAGI ${prior_magi:.0f}, bracket > all thresholds"

        # Total monthly premium per person
        monthly_cost_per_person = (
            base_premiums["part_b"]
            + base_premiums["part_d"]
            + surcharge_b
            + surcharge_d
        )

        # Married filing jointly → two beneficiaries
        monthly_cost_total = int(round(2 * monthly_cost_per_person))

        self.buckets["Cash"].withdraw(monthly_cost_total, "Medicare Premiums", tx_month)
        logging.debug(
            f"[IRMAA] Deducted ${monthly_cost_total:.0f} in {tx_month} "
            f"(Base B ${base_premiums['part_b']}, Base D ${base_premiums['part_d']}, "
            f"Surcharge B ${surcharge_b}, Surcharge D ${surcharge_d}, {bracket_info}, "
            f"MFJ → doubled)"
        )

    def _get_minus_2_tax_record(self, tx_month: pd.Period) -> Dict[str, int]:
        year = tx_month.year - 2

        if year in self.magi:
            return {
                "AGI": self.magi[year],
                "Tax-Exempt Interest": 0,
            }

        record = next((r for r in self.tax_records if r.get("Year") == year), None)
        if record:
            return {
                "AGI": int(record.get("AGI", 0)),
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

    def _apply_market_gain_transactions(self, gain_txns, buckets, tx_month):
        for tx in gain_txns:
            tx.apply(buckets, tx_month, self.tax_calc)

    def _apply_refill_transactions(self, refill_txns, buckets, tx_month):
        for tx in refill_txns:
            tx.apply(buckets, tx_month, self.tax_calc)

    def _apply_liquidation_transactions(self, liq_txns, buckets, tx_month):
        for tx in liq_txns:
            tx.apply(buckets, tx_month, self.tax_calc)

    def _update_results(
        self,
        forecast_month: pd.Period,
        buckets: Dict[str, Bucket],
        all_policy_txns: List[PolicyTransaction],
    ):
        year = forecast_month.year

        (
            fixed_income_interest,
            fixed_income_withdrawals,
            unemployment,
            salary,
            ss,
            deferred,
            realized,
            taxable,
            penalty,
            taxfree,
        ) = self._accumulate_monthly_tax_inputs(forecast_month, all_policy_txns)

        self._update_tax_logs(
            year,
            self.yearly_tax_log,
            unemployment,
            salary,
            ss,
            deferred,
            realized,
            taxable,
            fixed_income_interest,
            fixed_income_withdrawals,
            taxfree,
            penalty,
        )

        self._update_tax_projection(forecast_month)
        self._withhold_monthly_taxes(forecast_month, buckets)

        if forecast_month.month == 12:
            self._apply_year_end_reconciliation(
                forecast_month,
                self.yearly_tax_log,
                buckets,
                self.tax_records,
            )

        self._record_snapshot(forecast_month, buckets)

    def _accumulate_monthly_tax_inputs(self, tx_month, txs):
        fixed_income_interest = sum(
            tx.get_fixed_income_interest(tx_month) for tx in txs
        )
        fixed_income_withdrawals = sum(
            tx.get_fixed_income_withdrawal(tx_month) for tx in txs
        )
        unemployment = sum(tx.get_unemployment(tx_month) for tx in txs)
        salary = sum(tx.get_salary(tx_month) for tx in txs)
        ss = sum(tx.get_social_security(tx_month) for tx in txs)
        deferred = sum(tx.get_withdrawal(tx_month) for tx in txs)
        realized = sum(tx.get_realized_gain(tx_month) for tx in txs)
        taxable = sum(tx.get_taxable_gain(tx_month) for tx in txs)
        penalty = sum(tx.get_penalty_eligible_withdrawal(tx_month) for tx in txs)
        taxfree = sum(tx.get_taxfree_withdrawal(tx_month) for tx in txs)
        return (
            fixed_income_interest,
            fixed_income_withdrawals,
            unemployment,
            salary,
            ss,
            deferred,
            realized,
            taxable,
            penalty,
            taxfree,
        )

    def _update_tax_logs(
        self,
        year: int,
        yearly_log: Dict[int, Dict[str, int]],
        unemployment: int,
        salary: int,
        ss: int,
        deferred: int,
        realized: int,
        taxable: int,
        fixed_income_interest: int,
        fixed_income_withdrawals: int,
        taxfree: int,
        penalty: int,
    ):
        if year not in yearly_log:
            yearly_log[year] = {
                "Tax-Deferred Withdrawals": 0,
                "Realized Gains": 0,
                "Taxable Gains": 0,
                "Penalty Tax": 0,
                "Roth Conversions": 0,
                "Fixed Income Interest": 0,
                "Social Security": 0,
                "Salary": 0,
                "Unemployment": 0,
                "Tax-Free Withdrawals": 0,
                "Fixed Income Withdrawals": 0,
            }

        ylog = yearly_log[year]
        ylog["Unemployment"] += unemployment
        ylog["Salary"] += salary
        ylog["Social Security"] += ss
        ylog["Tax-Deferred Withdrawals"] += deferred
        ylog["Fixed Income Interest"] += fixed_income_interest
        ylog["Realized Gains"] += realized
        ylog["Taxable Gains"] += taxable
        ylog["Penalty Tax"] += penalty
        ylog["Tax-Free Withdrawals"] += taxfree
        ylog["Fixed Income Withdrawals"] += fixed_income_withdrawals

    def _update_tax_projection(self, forecast_date: pd.Period):
        year = forecast_date.year
        age = self._get_age_in_years(forecast_date)
        magi_factor = self.marketplace_premiums.get("magi_factor", 1.0)

        # --- Project annual AGI using insurance-style method ---
        annual_agi = self._projected_annual_agi(year, forecast_date, age, magi_factor)

        # --- Map projected AGI into tax categories ---
        # Before 59.5 → treat projected AGI as capital gains (brokerage withdrawals)
        # After 59.5 → treat projected AGI as tax-deferred withdrawals (IRA/401k)
        jan_period = pd.Period(f"{year}-01", freq="M")
        age_at_jan = self._get_age_in_years(jan_period)

        if age_at_jan < 59.5:
            tax_inputs = {
                "salary": 0,
                "fixed_income_interest": 0,
                "unemployment": 0,
                "ss_benefits": 0,
                "withdrawals": 0,
                "gains": int(annual_agi),
                "roth": 0,
                "penalty_basis": 0,
            }
        else:
            tax_inputs = {
                "salary": 0,
                "fixed_income_interest": 0,
                "unemployment": 0,
                "ss_benefits": 0,
                "withdrawals": int(annual_agi),
                "gains": 0,
                "roth": 0,
                "penalty_basis": 0,
            }

        # --- Calculate annual tax liability ---
        tax_liability = self.tax_calc.calculate_tax(year=year, **tax_inputs)[
            "total_tax"
        ]

        # --- Spread evenly across months ---
        self.monthly_tax_drip = int(tax_liability / 12.0)

        logging.debug(
            f"[TaxProjection] {year} AGI=${annual_agi:.0f}, "
            f"annual_tax=${tax_liability:.0f}, "
            f"monthly_drip=${self.monthly_tax_drip:.0f}"
        )

    def _withhold_monthly_taxes(self, tx_month, buckets):
        buckets["Cash"].transfer(
            self.monthly_tax_drip, buckets["Tax Collection"], tx_month
        )

    def _estimate_roth_headroom(
        self,
        salary: int,
        ss_benefits: int,
        withdrawals: int,
        gains: int,
        fixed_income_interest: int,
        unemployment: int,
        penalty_basis: int,
        max_rate: float,
        max_conversion_amount: int,
        tx_month: Optional[pd.Period] = None,
        step: int = 1000,
    ) -> int:
        if tx_month is None:
            raise ValueError("tx_month is required to estimate Roth headroom")

        year = tx_month.year

        # Use MAGI if available, otherwise build from components
        if year in self.magi:
            base_income = self.magi[year]
            base_tax = self.tax_calc.calculate_tax(
                year=year,
                salary=base_income,
                ss_benefits=0,
                withdrawals=0,
                gains=0,
                fixed_income_interest=0,
                unemployment=0,
                roth=0,
                penalty_basis=0,
            )
        else:
            base_income = (
                salary
                + unemployment
                + withdrawals
                + gains
                + ss_benefits
                + fixed_income_interest
            )
            base_tax = self.tax_calc.calculate_tax(
                year=year,
                salary=salary,
                ss_benefits=ss_benefits,
                withdrawals=withdrawals,
                gains=gains,
                fixed_income_interest=fixed_income_interest,
                unemployment=unemployment,
                roth=0,
                penalty_basis=penalty_basis,
            )

        headroom = 0
        for roth_amount in range(step, max_conversion_amount + step, step):
            test_tax = self.tax_calc.calculate_tax(
                year=year,
                salary=salary if year not in self.magi else base_income,
                ss_benefits=0 if year in self.magi else ss_benefits,
                withdrawals=0 if year in self.magi else withdrawals,
                gains=0 if year in self.magi else gains,
                fixed_income_interest=0 if year in self.magi else fixed_income_interest,
                unemployment=0 if year in self.magi else unemployment,
                roth=roth_amount,
                penalty_basis=0 if year in self.magi else penalty_basis,
            )

            extra_tax = test_tax["total_tax"] - base_tax["total_tax"]
            effective_rate = extra_tax / roth_amount if roth_amount > 0 else 0.0

            if effective_rate > max_rate:
                break
            headroom = roth_amount

        return headroom

    def _apply_roth_conversion_if_eligible(
        self,
        forecast_month: pd.Period,
        ylog: dict,
        current_tax: Dict[str, Any],
    ) -> int:
        age = self._get_age_in_years(forecast_month)

        # Select phase policy
        for _, policy in self.roth_policies.items():
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

        # If current effective rate already exceeds max, skip conversion
        max_rate = phase_config.get("Max Tax Rate", 0.0)
        if current_tax.get("effective_tax_rate", 0.0) >= max_rate:
            return 0

        source_name = phase_config.get("Tax Source Name")
        min_threshold = phase_config.get("Tax Source Threshold")

        if isinstance(source_name, str) and isinstance(min_threshold, (int, float)):
            source_bucket = self.buckets.get(source_name)
            source_balance = source_bucket.balance() if source_bucket else 0
            if source_balance < min_threshold:
                logging.debug(
                    f"[Roth] Skipping conversion in {forecast_month} — {source_name} balance ${source_balance:,} below threshold ${min_threshold:,}"
                )
                return 0

        max_amt = int(phase_config.get("Max Conversion Amount", 0))
        headroom = self._estimate_roth_headroom(
            salary=ylog.get("Salary", 0),
            ss_benefits=ylog.get("Social Security", 0),
            withdrawals=ylog.get("Tax-Deferred Withdrawals", 0),
            gains=ylog.get("Taxable Gains", 0),
            fixed_income_interest=ylog.get("Fixed Income Interest", 0),
            unemployment=ylog.get("Unemployment", 0),
            penalty_basis=ylog.get("Penalty Tax", 0),
            max_rate=max_rate,
            max_conversion_amount=max_amt,
            tx_month=forecast_month,
        )

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

        baseline = self.ytd_baseline if year == self.forecast_start_year else {}

        # Combined snapshot for reporting (baseline + increments)
        combined = {
            "Unemployment": ylog.get("Unemployment", 0)
            + baseline.get("unemployment", 0),
            "Salary": ylog.get("Salary", 0) + baseline.get("salary", 0),
            "Social Security": ylog.get("Social Security", 0)
            + baseline.get("ss_benefits", 0),
            "Tax-Deferred Withdrawals": ylog.get("Tax-Deferred Withdrawals", 0)
            + baseline.get("withdrawals", 0),
            "Realized Gains": ylog.get("Realized Gains", 0),
            "Taxable Gains": ylog.get("Taxable Gains", 0) + baseline.get("gains", 0),
            "Fixed Income Interest": ylog.get("Fixed Income Interest", 0)
            + baseline.get("fixed_income_interest", 0),
            "Tax-Free Withdrawals": ylog.get("Tax-Free Withdrawals", 0),
            "Fixed Income Withdrawals": ylog.get("Fixed Income Withdrawals", 0),
            "Roth Conversions": ylog.get("Roth Conversions", 0)
            + baseline.get("roth", 0),
            "Penalty Tax": ylog.get("Penalty Tax", 0)
            + baseline.get("penalty_basis", 0),
        }

        # Calculate tax before Roth conversion
        pre_conversion_tax = self.tax_calc.calculate_tax(
            year=year,
            fixed_income_interest=combined.get("Fixed Income Interest", 0),
            salary=combined.get("Salary", 0),
            ss_benefits=combined.get("Social Security", 0),
            withdrawals=combined.get("Tax-Deferred Withdrawals", 0),
            gains=combined.get("Taxable Gains", 0),
            roth=combined.get("Roth Conversions", 0),
            penalty_basis=combined.get("Penalty Tax", 0),
        )

        # Apply Roth conversion if headroom exists
        converted = self._apply_roth_conversion_if_eligible(
            forecast_month=forecast_month,
            ylog=combined,
            current_tax=pre_conversion_tax,
        )
        combined["Roth Conversions"] = converted

        # Recalculate tax after Roth conversion
        final_tax = self.tax_calc.calculate_tax(
            year=year,
            fixed_income_interest=combined.get("Fixed Income Interest", 0),
            salary=combined.get("Salary", 0),
            ss_benefits=combined.get("Social Security", 0),
            withdrawals=combined.get("Tax-Deferred Withdrawals", 0),
            gains=combined.get("Taxable Gains", 0),
            roth=converted,
            penalty_basis=combined.get("Penalty Tax", 0),
        )

        # Baseline taxes actually paid
        baseline_paid = baseline.get("tax_paid", 0)

        # Liability to settle = full-year tax minus pre-forecast taxes already paid
        liability = max(final_tax["total_tax"] - baseline_paid, 0)

        # Consume withheld first, then Cash for any shortfall
        already_withheld = buckets["Tax Collection"].balance()
        if liability > 0:
            used_from_tc = buckets["Tax Collection"].withdraw(
                min(liability, already_withheld), "Taxes", forecast_month
            )
            if liability > used_from_tc:
                buckets["Cash"].withdraw(
                    liability - used_from_tc, "Taxes", forecast_month
                )

        # Recapture true excess withholding
        leftover = buckets["Tax Collection"].balance()
        if leftover > 0:
            buckets["Tax Collection"].transfer(
                leftover, buckets["Cash"], forecast_month
            )

        # Compute totals and log record
        total_withdrawals = (
            combined.get("Fixed Income Withdrawals", 0)
            + combined.get("Tax-Free Withdrawals", 0)
            + combined.get("Tax-Deferred Withdrawals", 0)
        )
        portfolio_value = sum(bucket.balance() for bucket in buckets.values())
        withdrawal_rate = (
            total_withdrawals / portfolio_value if portfolio_value > 0 else 0.0
        )

        tax_records.append(
            {
                "Year": year,
                "AGI": final_tax.get("agi"),
                "Taxable Income": final_tax.get("ordinary_income"),
                "Total Tax": final_tax["total_tax"],
                "Fixed Income Withdrawals": combined.get("Fixed Income Withdrawals", 0),
                "Tax-Free Withdrawals": combined.get("Tax-Free Withdrawals", 0),
                "Tax-Deferred Withdrawals": combined.get("Tax-Deferred Withdrawals", 0),
                "Penalty Tax": final_tax["penalty_tax"],
                "Realized Gains": combined.get("Realized Gains", 0),
                "Taxable Gains": combined.get("Taxable Gains", 0),
                "Capital Gains Tax": final_tax["capital_gains_tax"],
                "Roth Conversions": converted,
                "Fixed Income Interest": combined.get("Fixed Income Interest", 0),
                "Unemployment": combined.get("Unemployment", 0),
                "Salary": combined.get("Salary", 0),
                "Social Security": combined.get("Social Security", 0),
                "Taxable Social Security": final_tax.get("taxable_ss"),
                "Ordinary Tax": final_tax["ordinary_tax"],
                "Payroll Specific Tax": final_tax["payroll_specific_tax"],
                "Effective Tax Rate": final_tax["effective_tax_rate"],
                "Total Withdrawals": total_withdrawals,
                "Withdrawal Rate": withdrawal_rate,
            }
        )

    def _record_snapshot(self, forecast_date, buckets):
        snapshot = {"Month": forecast_date}
        for name, bucket in buckets.items():
            snapshot[name] = bucket.balance()
        self.records.append(snapshot)
