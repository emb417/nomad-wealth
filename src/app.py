import logging
import numpy as np
import pandas as pd
import time

from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
from typing import Dict, List


# Internal Imports
from audit import FlowTracker
from buckets import AssetClass, Holding, Bucket
from economic_factors import InflationGenerator, MarketGains
from forecast_engine import ForecastEngine
from load_data import load_csv, load_json
from policies_engine import ThresholdRefillPolicy
from policies_transactions import (
    RentalTransaction,
    RequiredMinimumDistributionTransaction,
    SalaryTransaction,
    SocialSecurityTransaction,
)
from rules_transactions import (
    FixedTransaction,
    RecurringTransaction,
)
from taxes import TaxCalculator
from visualization import (
    plot_example_forecast,
    plot_example_income_taxes,
    plot_example_transactions_in_context,
    plot_example_transactions,
    plot_historical_balance,
    plot_historical_bucket_gains,
    plot_mc_networth,
    plot_mc_tax_bars,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="app.log",
)

# Simulation settings
SIM_SIZE = 100
SIM_EXAMPLE_SIZE = 1
SHOW_HISTORICAL = True
SHOW_MONTE_CARLO = True
SHOW_EXAMPLES = True

# Visualization settings (overrides)
SHOW_HISTORICAL_BALANCE_CHART = False
SAVE_HISTORICAL_BALANCE_CHART = False
SHOW_HISTORICAL_BUCKET_GAINS_CHART = False
SAVE_HISTORICAL_BUCKET_GAINS_CHART = False
SHOW_EXAMPLE_FORECAST_CHART = False
SAVE_EXAMPLE_FORECAST_CHART = False
SHOW_EXAMPLE_INCOME_TAXES_CHART = False
SAVE_EXAMPLE_INCOME_TAXES_CHART = False
SHOW_EXAMPLE_TRANSACTIONS_CHART = False
SAVE_EXAMPLE_TRANSACTIONS_CHART = False
SHOW_EXAMPLE_TRANSACTIONS_IN_CONTEXT_CHART = False
SAVE_EXAMPLE_TRANSACTIONS_IN_CONTEXT_CHART = False
SHOW_NETWORTH_CHART = False
SAVE_NETWORTH_CHART = False
SHOW_TAXES_CHART = False
SAVE_TAXES_CHART = False

rng = np.random.default_rng()
sim_examples = np.sort(rng.choice(SIM_SIZE, size=SIM_EXAMPLE_SIZE, replace=False))


@contextmanager
def timed(label):
    start = time.time()
    yield
    logging.info(
        f"{label} with {SIM_SIZE} trials completed in {(time.time() - start):.1f} seconds."
    )


def build_description_inflation_modifiers(
    base_inflation: Dict[int, Dict[str, float]],
    inflation_profiles: Dict[str, Dict[str, float]],
    inflation_defaults: Dict[str, float],
    years: List[int],
) -> Dict[str, Dict[int, Dict[str, float]]]:
    modifiers = {}
    for desc, profile in inflation_profiles.items():
        # avoid name collision with outer profile object
        sensitivity = (
            profile.get("avg", inflation_defaults["avg"]) / inflation_defaults["avg"]
        )
        adjusted = {}
        modifier = 1.0
        for year in years:
            base_rate = base_inflation[year]["rate"]
            adjusted_rate = base_rate * sensitivity
            modifier *= 1 + adjusted_rate
            adjusted[year] = {"rate": adjusted_rate, "modifier": modifier}
        modifiers[desc] = adjusted
    return modifiers


def create_bucket(
    name: str,
    starting_balance: int,
    holdings_config: List[Dict],
    flow_tracker: FlowTracker,
    can_go_negative: bool = False,
    allow_cash_fallback: bool = False,
    bucket_type: str = "other",
) -> Bucket:
    holdings: List[Holding] = []
    for piece in holdings_config:
        cls_name = piece["asset_class"]
        weight = float(piece["weight"])
        amt = int(round(starting_balance * weight))
        holdings.append(Holding(AssetClass(cls_name), weight, amt))

    # adjust for rounding drift
    drift = starting_balance - sum(h.amount for h in holdings)
    if drift:
        holdings[-1].amount += drift

    return Bucket(
        name=name,
        holdings=holdings,
        flow_tracker=flow_tracker,
        can_go_negative=can_go_negative,
        allow_cash_fallback=allow_cash_fallback,
        bucket_type=bucket_type,
    )


def seed_buckets_from_config(
    hist_df: pd.DataFrame, buckets_cfg: Dict, flow_tracker: FlowTracker
) -> Dict[str, Bucket]:
    """
    Build buckets from the columns of hist_df. Each column is expected to have a corresponding entry in buckets_cfg containing:
        - name: str
        - holdings: list of { asset_class, weight }
        - can_go_negative: bool (optional)
        - allow_cash_fallback: bool (optional)
    Starting balances are taken from the last row of hist_df (balance.json).
    A Tax Collection bucket is always created.
    """

    buckets: Dict[str, Bucket] = {}

    for col in hist_df.columns:
        if col != "Month":
            if col not in buckets_cfg:
                raise ValueError(
                    f"hist_df column '{col}' does not exist in buckets_cfg"
                )

            meta = buckets_cfg[col]
            raw = hist_df[col].iloc[-1]
            bal = int(raw.item())

            holdings_config = meta.get("holdings", [])
            can_go_negative = bool(meta.get("can_go_negative", False))
            allow_cash_fallback = bool(meta.get("allow_cash_fallback", False))
            bucket_type = str(meta.get("bucket_type")).lower()

            buckets[col] = create_bucket(
                name=col,
                starting_balance=bal,
                holdings_config=holdings_config,
                flow_tracker=flow_tracker,
                can_go_negative=can_go_negative,
                allow_cash_fallback=allow_cash_fallback,
                bucket_type=bucket_type,
            )

    return buckets


def retirement_period_from_dob(dob_str: str) -> pd.Period:
    """
    Compute the first month withdrawals are allowed: DOB + 59 years 6 months.
    Returns a pandas Period with monthly frequency.
    """
    dob = pd.to_datetime(dob_str)
    cutoff = dob + relativedelta(years=59, months=6)
    return cutoff.to_period("M")


def stage_load():
    """
    Load required files. buckets.json is now required inside the loaded json_data
    under the key 'buckets'.
    """
    json_data = load_json()
    dfs = load_csv()
    return json_data, dfs


def stage_prepare_timeframes(balance_df: pd.DataFrame, end_date: str):
    hist_df = balance_df.copy()
    hist_df["Month"] = pd.to_datetime(hist_df["Month"]).dt.to_period("M")
    hist_df["Tax Collection"] = 0

    last_period = hist_df["Month"].max()
    end_period = pd.Period(end_date, freq="M")

    future_periods = pd.period_range(start=last_period + 1, end=end_period, freq="M")
    future_df = pd.DataFrame({"Month": future_periods})

    return hist_df, future_df


def stage_init_components(
    json_data: Dict,
    dfs: Dict,
    hist_df: pd.DataFrame,
    future_df: pd.DataFrame,
    flow_tracker: FlowTracker,
):
    gain_table = json_data["gain_table"]
    buckets_config = json_data["buckets"]
    inflation_rate = json_data["inflation_rate"]
    inflation_thresholds = json_data["inflation_thresholds"]
    profile = json_data["profile"]
    policies_config = json_data["policies"]
    tax_brackets = json_data["tax_brackets"]

    # Build buckets from canonical buckets.json
    buckets = seed_buckets_from_config(hist_df, buckets_config, flow_tracker)

    # Penalty tax eligibility period
    dob = profile.get("Birth Month")
    eligibility = retirement_period_from_dob(dob) if dob else None

    # Refill policy
    refill_policy = ThresholdRefillPolicy(
        thresholds=policies_config["thresholds"],
        source_by_target=policies_config["sources"],
        amounts=policies_config["amounts"],
        taxable_eligibility=eligibility,
        liquidation_threshold=policies_config["liquidation"]["threshold"],
        liquidation_buckets=policies_config["liquidation"]["buckets"],
    )

    # Tax calculator
    ordinary_brackets = tax_brackets["ordinary"]
    capital_gains_brackets = tax_brackets["capital_gains"]
    social_security_brackets = tax_brackets["social_security_taxability"]
    tax_calc = TaxCalculator(
        ordinary_brackets=ordinary_brackets,
        capital_gains_brackets=capital_gains_brackets,
        social_security_brackets=social_security_brackets,
    )

    # base inflation and modifiers
    inflation_defaults = inflation_rate.get("default", {"avg": 0.02, "std": 0.01})
    inflation_profiles = inflation_rate.get("profiles", {})
    years = sorted(future_df["Month"].dt.year.unique())
    infl_gen = InflationGenerator(
        years, avg=inflation_defaults["avg"], std=inflation_defaults["std"]
    )
    base_inflation = infl_gen.generate()
    description_inflation_modifiers = build_description_inflation_modifiers(
        base_inflation, inflation_profiles, inflation_defaults, years
    )

    # gains
    market_gains = MarketGains(gain_table, inflation_thresholds, base_inflation)

    # transactions
    fixed_tx = FixedTransaction(dfs["fixed"])

    recur_tx = RecurringTransaction(
        df=dfs["recurring"],
        taxable_eligibility=eligibility,
        description_inflation_modifiers=description_inflation_modifiers,
    )

    rental_profile = description_inflation_modifiers.get("Rental", {})
    rental_tx = RentalTransaction(
        monthly_amount=policies_config["liquidation"]["Monthly Rent"],
        annual_infl=rental_profile,
        description_key="Rental",
    )

    rmd_tx = RequiredMinimumDistributionTransaction(dob=dob)

    salary_tx = SalaryTransaction(
        annual_gross=policies_config["Salary"]["Annual Gross Income"],
        annual_bonus=policies_config["Salary"]["Annual Bonus Amount"],
        bonus_date=policies_config["Salary"]["Annual Bonus Month"],
        salary_buckets=policies_config["Salary"]["Targets"],
        retirement_date=policies_config["Salary"]["Retirement Month"],
    )

    ss_txn = SocialSecurityTransaction(
        start_date=policies_config["Social Security"]["Start Month"],
        monthly_amount=policies_config["Social Security"]["Amount"],
        pct_payout=policies_config["Social Security"]["Percentage"],
        target_bucket=policies_config["Social Security"]["Target"],
        annual_infl=base_inflation,
    )

    rule_txns = [fixed_tx, recur_tx]
    policy_txns = [
        tx for tx in [rental_tx, rmd_tx, salary_tx, ss_txn] if tx is not None
    ]

    return (
        buckets,
        refill_policy,
        tax_calc,
        market_gains,
        base_inflation,
        rule_txns,
        policy_txns,
    )


def run_one_trial(
    trial: int,
    future_df: pd.DataFrame,
    json_data: dict,
    dfs: dict,
    hist_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Runs Monte Carlo trial, returns (forecast_df, flow_df).
    """
    np.random.seed(trial)
    flow_tracker = FlowTracker()

    (
        buckets,
        refill_policy,
        tax_calc,
        market_gains,
        base_inflation,
        rule_txns,
        policy_txns,
    ) = stage_init_components(json_data, dfs, hist_df, future_df, flow_tracker)

    # wire up flow_tracker
    for b in buckets.values():
        b.flow_tracker = flow_tracker

    engine = ForecastEngine(
        buckets=buckets,
        rule_transactions=rule_txns,
        policy_transactions=policy_txns,
        refill_policy=refill_policy,
        market_gains=market_gains,
        inflation=base_inflation,
        tax_calc=tax_calc,
        dob=(json_data["profile"]["Birth Month"]),
        magi=json_data["profile"]["MAGI"],
        retirement_period=json_data["policies"]["Salary"]["Retirement Month"],
        sepp_policies=json_data["policies"]["SEPP"],
        roth_policies=json_data["policies"]["Roth Conversions"],
        irmaa_brackets=json_data["tax_brackets"]["IRMAA 2025 MFJ"],
        marketplace_premiums=json_data["marketplace_premiums"],
    )
    forecast_df, taxes_df = engine.run(future_df)

    flow_df = flow_tracker.to_dataframe()
    flow_df["trial"] = trial

    return forecast_df, taxes_df, flow_df


def run_simulation(trial, future_df, json_data, dfs, hist_df):
    """
    Wrapper for run_one_trial to inject trial index into the result.
    """
    forecast_df, taxes_df, flow_df = run_one_trial(
        trial, future_df, json_data, dfs, hist_df
    )
    return trial, forecast_df, taxes_df, flow_df


def update_property_liquidation_summary(summary, forecast_df):
    row = forecast_df.loc[forecast_df["Property"] == 0]
    if row.empty:
        return
    date = row["Month"].iloc[0]
    year = date.year
    summary["Property Liquidations"] += 1
    summary["Property Liquidation Months"].append(date)
    summary["Minimum Property Liquidation Year"] = (
        year
        if summary["Minimum Property Liquidation Year"] is None
        else min(summary["Minimum Property Liquidation Year"], year)
    )
    summary["Maximum Property Liquidation Year"] = (
        year
        if summary["Maximum Property Liquidation Year"] is None
        else max(summary["Maximum Property Liquidation Year"], year)
    )


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with timed("Simulation"):
        # load & prep
        json_data, dfs = stage_load()
        dob = pd.to_datetime(json_data["profile"]["Birth Month"]).to_period("M")
        eol = pd.to_datetime(json_data["profile"]["End Month"]).to_period("M")

        plot_historical_bucket_gains(
            dfs["balance"],
            ts,
            (
                SHOW_HISTORICAL_BUCKET_GAINS_CHART
                if not SHOW_HISTORICAL
                else SHOW_HISTORICAL
            ),
            SAVE_HISTORICAL_BUCKET_GAINS_CHART,
        )
        plot_historical_balance(
            dfs["balance"],
            ts,
            SHOW_HISTORICAL_BALANCE_CHART if not SHOW_HISTORICAL else SHOW_HISTORICAL,
            SAVE_HISTORICAL_BALANCE_CHART,
        )

        hist_df, future_df = stage_prepare_timeframes(dfs["balance"], eol)

        summary = {
            "Property Liquidations": 0,
            "Property Liquidation Months": [],
            "Minimum Property Liquidation Year": None,
            "Maximum Property Liquidation Year": None,
        }

        mc_networth_by_trial = {}
        mc_tax_by_trial = {}

        with ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(
                    run_simulation, trial, future_df, json_data, dfs, hist_df
                )
                for trial in range(SIM_SIZE)
            ]

            for future in tqdm(
                as_completed(futures),
                total=SIM_SIZE,
                desc="Running Monte Carlo Simulation",
            ):
                trial, forecast_df, taxes_df, flow_df = future.result()

                update_property_liquidation_summary(summary, forecast_df)

                forecast_df["Net Worth"] = forecast_df.iloc[:, 1:].sum(axis=1)
                forecast_df["Year"] = forecast_df["Month"].dt.year

                # Store year-end net worth per trial
                monthly_nw_series = forecast_df.set_index("Month")["Net Worth"]
                mc_networth_by_trial[trial] = monthly_nw_series
                tax_series = taxes_df.set_index("Year")["Total Tax"]
                mc_tax_by_trial[trial] = tax_series

                if trial in sim_examples:
                    plot_example_transactions(
                        flow_df=flow_df,
                        trial=trial,
                        ts=ts,
                        show=(
                            SHOW_EXAMPLE_TRANSACTIONS_CHART
                            if not SHOW_EXAMPLES
                            else SHOW_EXAMPLES
                        ),
                        save=SAVE_EXAMPLE_TRANSACTIONS_CHART,
                    )
                    plot_example_transactions_in_context(
                        trial=trial,
                        forecast_df=forecast_df.drop(columns=["Net Worth", "Year"]),
                        flow_df=flow_df,
                        ts=ts,
                        show=(
                            SHOW_EXAMPLE_TRANSACTIONS_IN_CONTEXT_CHART
                            if not SHOW_EXAMPLES
                            else SHOW_EXAMPLES
                        ),
                        save=SAVE_EXAMPLE_TRANSACTIONS_IN_CONTEXT_CHART,
                    )
                    plot_example_income_taxes(
                        taxes_df=taxes_df,
                        trial=trial,
                        ts=ts,
                        show=(
                            SHOW_EXAMPLE_INCOME_TAXES_CHART
                            if not SHOW_EXAMPLES
                            else SHOW_EXAMPLES
                        ),
                        save=SAVE_EXAMPLE_INCOME_TAXES_CHART,
                    )
                    plot_example_forecast(
                        trial=trial,
                        hist_df=hist_df,
                        forecast_df=forecast_df.drop(columns=["Year"]),
                        dob=dob,
                        ts=ts,
                        show=(
                            SHOW_EXAMPLE_FORECAST_CHART
                            if not SHOW_EXAMPLES
                            else SHOW_EXAMPLES
                        ),
                        save=SAVE_EXAMPLE_FORECAST_CHART,
                    )

        # Build DataFrame: rows = simulations, columns = years
        mc_networth_df = (
            pd.DataFrame.from_dict(mc_networth_by_trial, orient="index").sort_index().T
        )
        mc_tax_df = (
            pd.DataFrame.from_dict(mc_tax_by_trial, orient="index").sort_index().T
        )

        plot_mc_tax_bars(
            mc_tax_df=mc_tax_df,
            sim_examples=sim_examples,
            ts=ts,
            show=SHOW_TAXES_CHART if not SHOW_MONTE_CARLO else SHOW_MONTE_CARLO,
            save=SAVE_TAXES_CHART,
        )

        plot_mc_networth(
            mc_networth_df=mc_networth_df,
            sim_examples=sim_examples,
            dob=dob,
            eol=eol,
            summary=summary,
            ts=ts,
            show=SHOW_NETWORTH_CHART if not SHOW_MONTE_CARLO else SHOW_MONTE_CARLO,
            save=SAVE_NETWORTH_CHART,
        )


if __name__ == "__main__":
    main()
