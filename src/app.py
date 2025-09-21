import logging
import pandas as pd
import plotly.express as px

from datetime import datetime
from pandas.tseries.offsets import MonthBegin
from typing import Dict

# Internal Imports
from domain import AssetClass, Holding, Bucket
from engine import ForecastEngine
from load_data import load_csv, load_json
from logging_setup import setup_logging
from policies import ThresholdRefillPolicy
from strategies import InflationGenerator, GainStrategy
from taxes import TaxCalculator
from transactions import (
    FixedTransaction,
    RecurringTransaction,
    SocialSecurityTransaction,
    SalaryTransaction,
    RothConversionTransaction,
)

SHOW_CHART = True
SAVE_CHART = False
SAVE_LEDGER = False
SAVE_TAXES = False


def create_bucket(name, starting_balance, breakdown, allow_negative=False):
    holdings = []
    for piece in breakdown:
        cls_name = piece["asset_class"]
        weight = float(piece["weight"])
        amt = int(round(starting_balance * weight))
        holdings.append(Holding(AssetClass(cls_name), weight, amt))

    drift = starting_balance - sum(h.amount for h in holdings)
    if drift:
        holdings[-1].amount += drift

    return Bucket(name, holdings, can_go_negative=allow_negative)


def seed_buckets(hist_df, holdings_config):
    last = hist_df.iloc[-1]
    buckets = {}
    for name, breakdown in holdings_config.items():
        bal = int(last[name])
        buckets[name] = create_bucket(
            name, bal, breakdown, allow_negative=(name == "Cash")
        )
    return buckets


def stage_load():
    """1) Load JSON + CSVs."""
    json_data = load_json()
    dfs = load_csv()
    return json_data, dfs


def stage_prepare_timeframes(balance_df, end_date):
    """2) Build hist_df and future_df."""
    hist_df = balance_df.copy()
    hist_df["Date"] = pd.to_datetime(hist_df["Date"])
    last_date = hist_df["Date"].max()

    future_idx = pd.date_range(
        last_date + MonthBegin(1), pd.to_datetime(end_date), freq="MS"
    )
    future_df = pd.DataFrame({"Date": future_idx})
    return hist_df, future_df


def stage_init_components(
    json_data: dict,
    dfs: Dict[str, pd.DataFrame],
    hist_df: pd.DataFrame,
    future_df: pd.DataFrame,
):
    """3) Seed buckets, policies, strategies, and transactions."""
    profile = json_data["profile"]
    holdings_config = json_data["holdings"]
    refill_cfg = json_data["refill_policy"]
    gain_table = json_data["gain_table"]
    inflation_thresholds = json_data["inflation_thresholds"]

    # Buckets
    buckets = seed_buckets(hist_df, holdings_config)

    # Refill policy & tax calculator
    dob_period = pd.to_datetime(profile["Date of Birth"]).to_period("M")
    eligibility = dob_period + (59 * 12 + 6)
    refill_policy = ThresholdRefillPolicy(
        thresholds=refill_cfg["thresholds"],
        source_by_target=refill_cfg["sources"],
        amounts=refill_cfg["amounts"],
        taxable_eligibility=eligibility,
    )
    tax_calc = TaxCalculator(refill_policy)

    # Gain strategy
    years = sorted(future_df["Date"].dt.year.unique())
    infl_gen = InflationGenerator(years, avg=0.03, std=0.02)
    annual_infl = infl_gen.generate()
    gain_strategy = GainStrategy(gain_table, inflation_thresholds, annual_infl)

    # Transactions
    fixed_tx = FixedTransaction(json_data["fixed_df"] if False else dfs["fixed"])
    recur_tx = RecurringTransaction(
        json_data["recurring_df"] if False else dfs["recurring"]
    )
    salary_tx = SalaryTransaction(
        annual_gross=profile["Annual Gross Income"],
        annual_bonus=profile["Annual Bonus Amount"],
        bonus_date=profile["Annual Bonus Date"],
        salary_bucket="Cash",
        retirement_date=profile["Retirement Date"],
    )
    ss_txn = SocialSecurityTransaction(
        start_date=profile["Social Security Date"],
        monthly_amount=profile["Social Security Amount"],
        pct_cash=profile["Social Security Percentage"],
        cash_bucket="Cash",
    )
    roth_conv = RothConversionTransaction(
        start_date=profile["Roth Conversion Start Date"],
        monthly_target=profile["Roth Conversion Amount"],
        source_bucket="Tax-Deferred",
        target_bucket="Tax-Free",
    )
    transactions = [fixed_tx, recur_tx, salary_tx, ss_txn, roth_conv]

    return buckets, refill_policy, tax_calc, gain_strategy, annual_infl, transactions


def stage_run_engine(
    buckets,
    transactions,
    refill_policy,
    gain_strategy,
    inflation,
    tax_calc,
    future_df,
    profile,
):
    """4) Run ForecastEngine and return forecast + taxes DataFrames."""
    engine = ForecastEngine(
        buckets=buckets,
        transactions=transactions,
        refill_policy=refill_policy,
        gain_strategy=gain_strategy,
        inflation=inflation,
        tax_calc=tax_calc,
        profile=profile,
    )
    logging.info(f"Running forecast for {len(future_df)} months…")
    return engine.run(future_df)


def main():
    setup_logging()

    # Stage 1: Load
    json_data, dfs = stage_load()

    # Stage 2: Timeframes
    hist_df, future_df = stage_prepare_timeframes(
        dfs["balance"], json_data["profile"]["End Date"]
    )

    # Stage 3: Init components
    buckets, refill_policy, tax_calc, gain_strategy, inflation, transactions = (
        stage_init_components(json_data, dfs, hist_df, future_df)
    )

    # Stage 4: Run
    forecasted_df, taxes_df = stage_run_engine(
        buckets,
        transactions,
        refill_policy,
        gain_strategy,
        inflation,
        tax_calc,
        future_df,
        json_data["profile"],
    )

    # Combine & log results
    full_ledger = pd.concat([hist_df, forecasted_df], ignore_index=True)
    end_net = full_ledger.iloc[-1].drop("Date").sum()
    logging.info(f"Forecast complete. End Net Worth: ${end_net:,.0f}")

    # Visualize / save
    bucket_cols = [c for c in full_ledger.columns if c != "Date"]
    if SHOW_CHART or SAVE_CHART:
        fig = px.line(
            full_ledger,
            x="Date",
            y=bucket_cols,
            color_discrete_sequence=px.colors.qualitative.Set1,
        )
        fig.update_layout(title="Bucket Balances", legend_title="Bucket")
        if SHOW_CHART:
            fig.show()
        if SAVE_CHART:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"export/forecast_{ts}.html"
            fig.write_html(path)
            logging.info(f"Chart saved to {path}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if SAVE_LEDGER:
        full_ledger.to_csv(f"export/ledger_{ts}.csv", index=False)
    if SAVE_TAXES:
        taxes_df.to_csv(f"export/taxes_{ts}.csv", index=False)


if __name__ == "__main__":
    main()
