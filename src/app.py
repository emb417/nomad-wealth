import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import time

from datetime import datetime
from pandas.tseries.offsets import MonthBegin

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

# toggle display/save
SHOW_NETWORTH_CHART = True
SAVE_NETWORTH_CHART = True
SIMS = 100
SIMS_SAMPLES = np.random.randint(0, SIMS, size=10)
SHOW_SIMS_SAMPLES = True
SAVE_SIMS_SAMPLES = True


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
    profile = json_data["profile"]
    holdings_config = json_data["holdings"]
    refill_cfg = json_data["refill_policy"]
    gain_table = json_data["gain_table"]
    inflation_thresholds = json_data["inflation_thresholds"]

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

    # gain strategy
    years = sorted(future_df["Date"].dt.year.unique())
    infl_gen = InflationGenerator(years, avg=0.03, std=0.02)
    annual_infl = infl_gen.generate()
    gain_strategy = GainStrategy(gain_table, inflation_thresholds, annual_infl)

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

    return buckets, refill_policy, tax_calc, gain_strategy, annual_infl, transactions


def main():
    setup_logging()
    start_time = time.time()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load & prep data
    json_data, dfs = stage_load()
    hist_df, future_df = stage_prepare_timeframes(
        dfs["balance"], json_data["profile"]["End Date"]
    )

    # We will collect year‐end net worth for each sim
    # Pre‐allocate a dictionary of year → list of net worths
    years = future_df["Date"].dt.year.unique()
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
            gain_strategy,
            inflation,
            transactions,
        ) = stage_init_components(json_data, dfs, hist_df, future_df)

        engine = ForecastEngine(
            buckets=buckets,
            transactions=transactions,
            refill_policy=refill_policy,
            gain_strategy=gain_strategy,
            inflation=inflation,
            tax_calc=tax_calc,
            profile=json_data["profile"],
        )

        # run the forecast
        forecast_df, taxes_df = engine.run(future_df)
        if sim in SIMS_SAMPLES:
            logging.info(f"Sim {sim+1:04d} | Sample forecast...")
            fig_title = f"Sim {sim+1:04d} | Forecast Breakdown by Bucket"
            fig = go.Figure(
                data=[
                    go.Scatter(
                        x=forecast_df["Date"],
                        y=forecast_df[col],
                        mode="lines",
                        name=col,
                    )
                    for col in forecast_df.columns[1:]
                ]
            )
            fig.update_layout(
                title=fig_title,
                xaxis_title="Date",
                yaxis_title="Amount ($)",
            )
            if SHOW_SIMS_SAMPLES:
                fig.show()
            if SAVE_SIMS_SAMPLES:
                path = f"export/{sim+1:04d}_"
                filename = f"forecast_{ts}"
                forecast_df.to_csv(f"{path}buckets_{filename}.csv", index=False)
                taxes_df.to_csv(f"{path}taxes_{filename}.csv", index=False)
                fig.write_html(f"{path}buckets_{filename}.html")
                logging.info(
                    f"Sim {sim+1:04d} | Saved forecast csv files and charts (html)!"
                )

        # compute 59.5 years old withdrawal
        dob = pd.to_datetime(json_data["profile"]["Date of Birth"])
        dob_59y6m = dob + pd.DateOffset(years=59, months=6)
        withdrawal_date = (
            forecast_df["Date"]
            .dt.to_period("M")
            .apply(lambda x: x >= dob_59y6m.to_period("M"))
        )
        cash_59y6m = forecast_df.loc[withdrawal_date, "Cash"].iloc[-1]
        fixed_income_59y6m = forecast_df.loc[withdrawal_date, "Fixed-Income"].iloc[-1]
        taxable_59y6m = forecast_df.loc[withdrawal_date, "Taxable"].iloc[-1]
        logging.debug(
            f"Sim {sim+1:4d} | 2034 | "
            f"Cash: ${int(cash_59y6m):,}, Fixed-Income: ${int(fixed_income_59y6m):,}, "
            f"Taxable: ${int(taxable_59y6m):,}"
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
    mc_df.columns = [f"sim_{i}" for i in range(SIMS)]

    # compute percentiles
    pct_df = mc_df.quantile([0.15, 0.5, 0.85], axis=1).T
    pct_df.columns = ["p15", "median", "p85"]

    # probability of positive net worth at final year
    eol = pd.to_datetime(json_data["profile"]["End Date"])
    age_minus_20_year = eol.year - 20
    age_minus_20 = age_minus_20_year - dob.year
    age_minus_20_pct = mc_df.loc[age_minus_20_year].gt(0).mean()
    age_minus_10_year = eol.year - 10
    age_minus_10 = age_minus_10_year - dob.year
    age_minus_10_pct = mc_df.loc[age_minus_10_year].gt(0).mean()
    age_end_year = eol.year
    age_end = age_end_year - dob.year
    age_end_pct = mc_df.loc[age_end_year].gt(0).mean()

    # Plotly chart
    fig = go.Figure()

    # all sim paths in light gray
    for col in mc_df.columns:
        fig.add_trace(
            go.Scatter(
                x=mc_df.index,
                y=mc_df[col],
                line=dict(color="lightgray"),
                opacity=0.2,
                showlegend=False,
            )
        )

    # percentile lines
    fig.add_trace(
        go.Scatter(
            x=pct_df.index,
            y=pct_df["median"],
            line=dict(color="green", width=3),
            name="Median",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=pct_df.index,
            y=pct_df["p15"],
            line=dict(color="blue", dash="dash"),
            name="85% Of Sims Are Higher",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=pct_df.index,
            y=pct_df["p85"],
            line=dict(color="red", dash="dash"),
            name="15% Of Sims Are Higher",
        )
    )

    fig.update_layout(
        title=f"Monte Carlo Net Worth Forecast<br>"
        f"{age_minus_20_pct:.0%} @ {age_minus_20} | "
        f"{age_minus_10_pct:.0%} @ {age_minus_10} | "
        f"{age_end_pct:.0%} @ {age_end}",
        xaxis_title="Year",
        yaxis_title="Net Worth ($)",
        template="plotly_white",
        legend=dict(
            orientation="h",
        ),
    )

    if SHOW_NETWORTH_CHART:
        fig.show()

    if SAVE_NETWORTH_CHART:
        path = f"export/mc_networth_{ts}.html"
        fig.write_html(path)
        logging.info(f"Monte Carlo chart saved to {path}")

    end_time = time.time()
    minutes = (end_time - start_time) / 60
    logging.info(f"Simulation completed in {minutes:.1f} minutes")


if __name__ == "__main__":
    main()
