import logging
import pandas as pd
import plotly.express as px

from datetime import datetime
from pandas.tseries.offsets import MonthBegin
from typing import Dict, List

from load_data import load_csv, load_json
from logging_setup import setup_logging
from domain import AssetClass, Holding, Bucket
from policies import RefillPolicy
from strategies import InflationGenerator, GainStrategy
from transactions import FixedTransaction, RecurringTransaction, SocialSecurityTransaction
from engine import ForecastEngine

SHOW_CHART  = True
SAVE_CHART  = True
SAVE_LEDGER = True

def main():
    setup_logging()
    logging.info("Loading data…")
    
    ##########################
    # 1) Load configs and CSVs
    ##########################
    
    json_data    = load_json()
    dataframes   = load_csv()

    profile               = json_data["profile"]
    gain_table            = json_data["gain_table"]
    inflation_thresholds  = json_data["inflation_thresholds"]
    holdings_config       = json_data["holdings"]
    refill_cfg            = json_data["refill_policy"]

    balance_df   = dataframes["balance"]
    fixed_df     = dataframes["fixed"]
    recurring_df = dataframes["recurring"]

    ##########################
    # 2) Build buckets and ledger
    ##########################

    hist_df   = balance_df.copy()
    hist_df["Date"] = pd.to_datetime(hist_df["Date"])
    last_hist = hist_df["Date"].max()

    future_idx = pd.date_range(
        last_hist + MonthBegin(1),
        pd.to_datetime(profile["End Date"]),
        freq="MS"
    )
    future_df = pd.DataFrame({"Date": future_idx})

    ########################
    # 3) Seed buckets from last historical row
    ########################
    
    buckets: Dict[str, Bucket] = {}
    for bucket_name, breakdown in holdings_config.items():
        # Grab the last-known historical balance for this bucket
        start_bal = int(hist_df[bucket_name].iloc[-1])

        holdings: List[Holding] = []
        for h in breakdown:
            cls_name = h["asset_class"]
            weight   = float(h["weight"])

            # Compute how much of the existing balance lives in this slice
            raw_amt = start_bal * weight
            amt     = int(round(raw_amt))

            # Create the AssetClass (now only takes name)
            asset_cls = AssetClass(cls_name)

            # → Holding signature is (asset_class, weight, amount)
            holdings.append(Holding(asset_cls, weight, amt))

        # Fix any rounding drift on the last slice
        total_alloc = sum(h.amount for h in holdings)
        drift       = start_bal - total_alloc
        if drift:
            holdings[-1].amount += drift

        # Build the Bucket with its initial holdings
        buckets[bucket_name] = Bucket(bucket_name, holdings)
    
    ########################
    # 4) Build policy, strategies, and transactions
    ########################
    
    refill_policy = RefillPolicy(
        thresholds  = refill_cfg["thresholds"],
        amounts     = refill_cfg["amounts"],
        sources     = refill_cfg["sources"]
    )

    years            = sorted(set(future_df["Date"].dt.year))
    inflation_gen    = InflationGenerator(years, avg=0.03, std=0.02)
    annual_inflation = inflation_gen.generate()

    gain_strategy = GainStrategy(gain_table, inflation_thresholds, annual_inflation)

    fixed_tx = FixedTransaction(fixed_df)
    recur_tx = RecurringTransaction(recurring_df)
    ss_txn = SocialSecurityTransaction(
        start_date     = profile["Social Security Date"],
        monthly_amount = profile["Social Security Amount"],
        pct_cash       = profile["Social Security Percentage"],
        cash_bucket    = "Cash"
    )
    transactions = [fixed_tx, recur_tx, ss_txn]

    #########################
    # 5) Run forecast on future dates only
    #########################
    
    engine = ForecastEngine(
        buckets=buckets,
        transactions=transactions,
        refill_policy=refill_policy,
        gain_strategy=gain_strategy,
        inflation=annual_inflation
    )
    logging.info("Running forecast simulation…")
    forecasted_df = engine.run(future_df)

    ########################
    # 6) Combine history + forecast
    ########################
    
    full_ledger = pd.concat([hist_df, forecasted_df], ignore_index=True)

    ########################
    # 7) Compute end net worth
    ########################
    
    bucket_cols = [c for c in full_ledger.columns if c != "Date"]
    end_net     = full_ledger.iloc[-1][bucket_cols].sum()
    logging.info(f"Forecast complete. End Net Worth: ${end_net:,.0f}")

    ########################
    # 8) Visualization
    ########################
    
    if SHOW_CHART or SAVE_CHART:
        fig = px.line(
            full_ledger,
            x="Date",
            y=bucket_cols,
            color_discrete_sequence=px.colors.qualitative.Set1,
        )
        fig.update_layout(
            title="Bucket Balances: Historical + Forecast",
            legend_title="Bucket"
        )

        if SHOW_CHART:
            fig.show()
        if SAVE_CHART:
            ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path = f"export/forecast_{ts}.html"
            fig.write_html(path)
            logging.info(f"Chart saved: {path}")

    ########################
    # 9) Save ledger CSV
    ########################
    
    if SAVE_LEDGER:
        ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = f"export/ledger_{ts}.csv"
        full_ledger.to_csv(path, index=False)
        logging.info(f"Ledger saved: {path}")

if __name__ == "__main__":
    main()
