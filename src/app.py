import logging
import numpy as np
import pandas as pd
import time

from datetime import datetime
from pandas.tseries.offsets import MonthBegin

# Internal Imports
from domain import AssetClass, Holding, Bucket
from engine import ForecastEngine
from load_data import load_csv, load_json
from policies import ThresholdRefillPolicy
from economic_factors import InflationGenerator, MarketGains
from taxes import TaxCalculator
from transactions import (
    FixedTransaction,
    RecurringTransaction,
    SocialSecurityTransaction,
    SalaryTransaction,
    RothConversionTransaction,
)
from visualization import plot_sample_forecast, plot_mc_networth

# Set Number of Simulations and Sample Size
# Show or Save Sample Simulations and Net Worth
SIMS = 100
SIMS_SAMPLES = np.random.randint(0, SIMS, size=2)
SHOW_SIMS_SAMPLES = True
SAVE_SIMS_SAMPLES = True
SHOW_NETWORTH_CHART = True
SAVE_NETWORTH_CHART = True


def create_bucket(name, starting_balance, breakdown, allow_negative=False):
    holdings = []
    for piece in breakdown:
        cls_name = piece["asset_class"]
        weight = float(piece["weight"])
        amt = int(round(starting_balance * weight))
        holdings.append(Holding(AssetClass(cls_name), weight, amt))

    # adjust for rounding drift
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
    json_data = load_json()
    dfs = load_csv()
    return json_data, dfs


def stage_prepare_timeframes(balance_df, end_date):
    hist_df = balance_df.copy()
    hist_df["Date"] = pd.to_datetime(hist_df["Date"])
    last_date = hist_df["Date"].max()
    future_idx = pd.date_range(
        start=last_date + MonthBegin(1),
        end=pd.to_datetime(end_date),
        freq="MS",
    )
    future_df = pd.DataFrame({"Date": future_idx})
    return hist_df, future_df


def stage_init_components(json_data, dfs, hist_df, future_df):
    gain_table = json_data["gain_table"]
    holdings_config = json_data["holdings"]
    inflation_rate = json_data["inflation_rate"]
    inflation_thresholds = json_data["inflation_thresholds"]
    profile = json_data["profile"]
    refill_cfg = json_data["refill_policy"]

    # buckets seeded from last historical row
    buckets = seed_buckets(hist_df, holdings_config)

    # refill policy & tax calculator
    dob_period = pd.to_datetime(profile["Date of Birth"]).to_period("M")
    eligibility = dob_period + (59 * 12 + 6)
    refill_policy = ThresholdRefillPolicy(
        thresholds=refill_cfg["thresholds"],
        source_by_target=refill_cfg["sources"],
        amounts=refill_cfg["amounts"],
        taxable_eligibility=eligibility,
    )
    tax_calc = TaxCalculator(refill_policy)

    # apply gains
    years = sorted(future_df["Date"].dt.year.unique())
    infl_gen = InflationGenerator(
        years, avg=inflation_rate["avg"], std=inflation_rate["std"]
    )
    annual_infl = infl_gen.generate()
    market_gains = MarketGains(gain_table, inflation_thresholds, annual_infl)

    # transactions
    fixed_tx = FixedTransaction(dfs["fixed"])
    recur_tx = RecurringTransaction(dfs["recurring"])
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

    return buckets, refill_policy, tax_calc, market_gains, annual_infl, transactions


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    start_time = time.time()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load & prep data
    json_data, dfs = stage_load()
    hist_df, future_df = stage_prepare_timeframes(
        dfs["balance"], json_data["profile"]["End Date"]
    )

    # We will collect year‐end net worth for each sim
    # Pre‐allocate a dictionary of year → list of net worths
    years = sorted(future_df["Date"].dt.year.unique())
    mc_dict = {year: [] for year in years}

    # Monte Carlo loop
    logging.info(f"Running {SIMS} Monte Carlo simulations…")
    for sim in range(SIMS):
        np.random.seed(sim)

        # re‐init all components so buckets & txns start fresh
        (
            buckets,
            refill_policy,
            tax_calc,
            market_gains,
            inflation,
            transactions,
        ) = stage_init_components(json_data, dfs, hist_df, future_df)

        engine = ForecastEngine(
            buckets=buckets,
            transactions=transactions,
            refill_policy=refill_policy,
            market_gains=market_gains,
            inflation=inflation,
            tax_calc=tax_calc,
            profile=json_data["profile"],
        )

        # run the forecast
        forecast_df, taxes_df = engine.run(future_df)
        if sim in SIMS_SAMPLES:
            plot_sample_forecast(
                sim_index=sim,
                hist_df=hist_df,
                forecast_df=forecast_df,
                taxes_df=taxes_df,
                ts=ts,
                show=SHOW_SIMS_SAMPLES,
                save=SAVE_SIMS_SAMPLES,
            )

        # compute net worth and grab year‐end
        forecast_df["NetWorth"] = forecast_df.drop(columns=["Date"]).sum(axis=1)
        forecast_df["Year"] = forecast_df["Date"].dt.year
        ye_nw = forecast_df.groupby("Year")["NetWorth"].last().to_dict()

        # append each year‐end value to mc_dict
        for year, nw in ye_nw.items():
            mc_dict[year].append(nw)
            if year == (pd.to_datetime(json_data["profile"]["End Date"])).year - 10:
                nw = mc_dict[year][-1]
                logging.debug(f"Sim {sim+1:4d} | {year} | ${int(nw):,}")

    # build DataFrame: index=Year, columns=sim_0…sim_{SIMS-1}
    mc_df = pd.DataFrame(mc_dict).T

    plot_mc_networth(
        SIMS=SIMS,
        mc_df=mc_df,
        dob_year=pd.to_datetime(json_data["profile"]["Date of Birth"]).year,
        eol_year=pd.to_datetime(json_data["profile"]["End Date"]).year,
        ts=ts,
        show=SHOW_NETWORTH_CHART,
        save=SAVE_NETWORTH_CHART,
    )

    end_time = time.time()
    minutes = (end_time - start_time) / 60
    logging.info(f"Simulation completed in {minutes:.1f} minutes")


if __name__ == "__main__":
    main()
