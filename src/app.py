import logging
import numpy as np
import pandas as pd
import time

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pandas.tseries.offsets import MonthBegin
from tqdm import tqdm
from typing import Dict, List


# Internal Imports
from domain import AssetClass, Holding, Bucket
from economic_factors import InflationGenerator, MarketGains
from engine import ForecastEngine
from load_data import load_csv, load_json
from policies import ThresholdRefillPolicy
from taxes import TaxCalculator
from transactions import (
    FixedTransaction,
    RecurringTransaction,
    SocialSecurityTransaction,
    SalaryTransaction,
    RothConversionTransaction,
)
from visualization import plot_sample_forecast, plot_mc_networth

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

rng = np.random.default_rng()

# Simulation settings
SIMS = 100
SIMS_SAMPLES = np.sort(rng.choice(SIMS, size=3, replace=False))
SHOW_SIMS_SAMPLES = True
SAVE_SIMS_SAMPLES = False
SHOW_NETWORTH_CHART = True
SAVE_NETWORTH_CHART = False


def create_bucket(
    name: str,
    starting_balance: int,
    holdings_config: List[Dict],
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
        can_go_negative=can_go_negative,
        allow_cash_fallback=allow_cash_fallback,
        bucket_type=bucket_type,
    )


def seed_buckets_from_config(
    hist_df: pd.DataFrame, buckets_cfg: Dict
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
        if col != "Date":
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
    dob = pd.to_datetime(dob_str).to_pydatetime()
    cutoff = dob + relativedelta(years=59, months=6)
    return pd.Period(cutoff, freq="M")


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
    hist_df["Date"] = pd.to_datetime(hist_df["Date"])
    hist_df["Tax Collection"] = 0
    last_date = hist_df["Date"].max()
    future_idx = pd.date_range(
        start=last_date + MonthBegin(1), end=pd.to_datetime(end_date), freq="MS"
    )
    future_df = pd.DataFrame({"Date": future_idx})
    return hist_df, future_df


def stage_init_components(
    json_data: Dict, dfs: Dict, hist_df: pd.DataFrame, future_df: pd.DataFrame
):
    gain_table = json_data["gain_table"]
    buckets_config = json_data["buckets"]
    inflation_rate = json_data["inflation_rate"]
    inflation_thresholds = json_data["inflation_thresholds"]
    profile = json_data["profile"]
    policies_config = json_data["policies"]
    tax_brackets = json_data["tax_brackets"]

    # Build buckets from canonical buckets.json
    buckets = seed_buckets_from_config(hist_df, buckets_config)

    # Taxable eligibility
    dob = profile.get("Date of Birth")
    eligibility = retirement_period_from_dob(dob) if dob else None

    # Refill policy & tax calculator (taxable_eligibility uses same retirement cutoff)
    refill_policy = ThresholdRefillPolicy(
        thresholds=policies_config["thresholds"],
        source_by_target=policies_config["sources"],
        amounts=policies_config["amounts"],
        taxable_eligibility=eligibility,
        liquidation_threshold=policies_config["liquidation"]["threshold"],
        liquidation_buckets=policies_config["liquidation"]["buckets"],
    )
    tax_calc = TaxCalculator(refill_policy, tax_brackets)

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
        salary_buckets=policies_config["salary"],
        retirement_date=profile["Retirement Date"],
    )

    ss_txn = SocialSecurityTransaction(
        start_date=profile["Social Security Date"],
        monthly_amount=profile["Social Security Amount"],
        pct_cash=profile["Social Security Percentage"],
        cash_bucket=policies_config["social_security"],
    )

    roth_conv = RothConversionTransaction(
        start_date=policies_config["roth_conversion"]["Start Date"],
        monthly_target=policies_config["roth_conversion"]["Amount"],
        source_bucket=policies_config["roth_conversion"]["Source"],
        target_bucket=policies_config["roth_conversion"]["Target"],
    )

    transactions = [fixed_tx, recur_tx, salary_tx, ss_txn, roth_conv]

    return buckets, refill_policy, tax_calc, market_gains, annual_infl, transactions


def main():
    start_time = time.time()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load & prep data
    json_data, dfs = stage_load()
    hist_df, future_df = stage_prepare_timeframes(
        dfs["balance"], json_data["profile"]["End Date"]
    )

    # Pre-allocate year → list of net worths
    years = sorted(future_df["Date"].dt.year.unique())
    mc_dict = {year: [] for year in years}
    mc_samples_dict = {year: [] for year in years}
    summary = {
        "Property Liquidations": 0,
        "Property Liquidation Dates": [],
        "Minimum Property Liquidation Year": None,
        "Maximum Property Liquidation Year": None,
    }

    for sim in tqdm(range(SIMS), desc="Running Monte Carlo simulations..."):
        np.random.seed(sim)

        # re-init components so each sim starts fresh
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
        property_liquidation_row = forecast_df.loc[forecast_df["Property"] == 0]
        if not property_liquidation_row.empty:
            summary["Property Liquidations"] = (
                summary.get("Property Liquidations", 0) + 1
            )
            summary["Property Liquidation Dates"].append(
                property_liquidation_row["Date"].iloc[0]
            )
            summary["Minimum Property Liquidation Year"] = (
                property_liquidation_row["Date"].iloc[0].year
                if (
                    summary["Minimum Property Liquidation Year"] is None
                    or property_liquidation_row["Date"].iloc[0].year
                    < summary["Minimum Property Liquidation Year"]
                )
                else summary["Minimum Property Liquidation Year"]
            )
            summary["Maximum Property Liquidation Year"] = (
                property_liquidation_row["Date"].iloc[0].year
                if (
                    summary["Maximum Property Liquidation Year"] is None
                    or property_liquidation_row["Date"].iloc[0].year
                    > summary["Maximum Property Liquidation Year"]
                )
                else summary["Maximum Property Liquidation Year"]
            )
        # compute net worth and collect year-end values
        forecast_df["NetWorth"] = forecast_df.drop(columns=["Date"]).sum(axis=1)
        forecast_df["Year"] = forecast_df["Date"].dt.year
        ye_nw = forecast_df.groupby("Year")["NetWorth"].last().to_dict()

        for year, nw in ye_nw.items():
            mc_dict[year].append(nw)
            if sim in SIMS_SAMPLES:
                mc_samples_dict[year].append(nw)

    mc_df = pd.DataFrame(mc_dict).T
    mc_df.columns = [f"Sim {'{:04d}'.format(int(col) + 1)}" for col in mc_df.columns]
    mc_samples_df = pd.DataFrame(mc_samples_dict).T
    mc_samples_df.columns = [f"Sim {sim+1:04d}" for sim in SIMS_SAMPLES]

    plot_mc_networth(
        mc_df=mc_df,
        mc_samples_df=mc_samples_df,
        dob_year=pd.to_datetime(json_data["profile"]["Date of Birth"]).year,
        eol_year=pd.to_datetime(json_data["profile"]["End Date"]).year,
        summary=summary,
        ts=ts,
        show=SHOW_NETWORTH_CHART,
        save=SAVE_NETWORTH_CHART,
    )

    end_time = time.time()
    logging.info(f"Simulation completed in {(end_time - start_time):.1f} seconds.")


if __name__ == "__main__":
    main()
