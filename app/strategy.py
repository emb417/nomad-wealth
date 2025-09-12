import numpy as np
import pandas as pd
import logging

from datetime import datetime


def get_bucket_asset_class(bucket):
    return {"Fixed-Income": "Fixed-Income", "Real-Estate": "Real-Estate"}.get(
        bucket, "Market" if bucket != "Cash" and bucket != "Depreciating" else None
    )


def get_refill_threshold(bucket):
    # Define refill thresholds for each bucket
    thresholds = {"Cash": 30000, "Fixed-Income": 100000}
    return thresholds.get(bucket, 0)


def get_refill_amount(bucket, row):
    # Define refill amounts for each bucket
    amounts = {"Cash": 20000, "Fixed-Income": 20000}
    return amounts.get(bucket, 0)


def get_refill_from(bucket):
    # Define source buckets for each refill
    sources = {"Cash": "Fixed-Income", "Fixed-Income": "Taxable"}
    return sources.get(bucket, None)


def generate_annual_inflation(
    forecast_years, avg_inflation=0.03, std_dev=0.02, seed=42
):
    rng = np.random.default_rng(seed)
    annual_inflation = {}

    # Initialize the modifier to 1
    modifier = 1.0

    for year in forecast_years:
        infl_rate = rng.normal(avg_inflation, std_dev)
        if infl_rate < 0:
            infl_rate = 0
        # Calculate the modifier based on the cumulative effect of interest rates
        modifier *= 1 + infl_rate
        annual_inflation[year] = {"rate": infl_rate, "modifier": modifier}

    return annual_inflation


def apply_inflation_scenario(new_row, row, annual_inflation, inflation_thresholds, gain_table):
    for bucket in new_row.index:
        if bucket != "Date":
            asset_class = get_bucket_asset_class(bucket)
            if asset_class is not None:
                infl_scenario = "Average"
                year = pd.to_datetime(row["Date"]).year
                infl_rate = annual_inflation.get(year, {}).get("rate", 0)
                thresholds = inflation_thresholds.get(asset_class, {})
                if infl_rate > thresholds.get("high", 0):
                    infl_scenario = "High"
                elif infl_rate < thresholds.get("low", 0):
                    infl_scenario = "Low"
                gain_data = gain_table[asset_class].get(infl_scenario, {})
                gain_avg = gain_data.get("avg", 0)
                gain_std = gain_data.get("std", 0)
                gain_rate = np.random.normal(gain_avg, gain_std)
                new_row[bucket] *= 1 + gain_rate
    return new_row


def get_recurring_for_month(
    recurring_transactions, bucket_names, forecast_months, month_of_interest
):
    recurring_credits = {bucket: 0.0 for bucket in bucket_names}
    start_date = month_of_interest.replace(day=1)
    end_date = forecast_months[-1].replace(day=1)

    for transaction_index, transaction in recurring_transactions.iterrows():
        transaction_start = pd.to_datetime(transaction["Start Date"])
        transaction_end = (
            pd.to_datetime(transaction["End Date"])
            if not pd.isna(transaction["End Date"])
            else end_date
        )

        if start_date >= transaction_start and start_date <= transaction_end:
            recurring_credits[transaction["Type"]] += transaction["Amount"]

    return recurring_credits


def refill_bucket(row, bucket):
    if row[bucket] < get_refill_threshold(bucket):
        refill_amount = get_refill_amount(bucket, row)
        refill_from = get_refill_from(bucket)
        if refill_from is not None:
            row[refill_from] -= refill_amount
            row[bucket] += refill_amount


def apply_fixed_transactions(row, fixed_df, month):
    month_fixed = fixed_df[
        pd.to_datetime(fixed_df["Date"]).dt.to_period("M") == month.to_period("M")
    ]
    if not month_fixed.empty:
        for _, fixed_row in month_fixed.iterrows():
            bucket = fixed_row["Type"]
            amount = fixed_row["Amount"]
            # hack to simulate using all of the 529K without knowing the exact amount
            if bucket == "Post-Education 529K" and abs(amount) >= (0.8 * row[bucket]):
                row[bucket] = 0
            else:
                row[bucket] += amount
            refill_bucket(row, bucket)

    return row


def apply_recurring_transactions(
    row, recurring_df, month, annual_inflation, profile_data
):
    recurring_credits = get_recurring_for_month(
        recurring_df, [col for col in row.index if col != "Date"], [month], month
    )
    year = month.year
    infl_modifier = annual_inflation.get(year, 0).get("modifier", 0)

    # Add Social Security payment to cash bucket if eligible
    if month >= datetime.strptime(profile_data["Social Security Date"], "%Y-%m-%d").replace(day=1):
        recurring_credits["Cash"] += (
            profile_data["Social Security Amount"]
            * profile_data["Social Security Percentage"]
            * infl_modifier
        )

    for bucket, amount in recurring_credits.items():
        if bucket in row.index and bucket != "Mortgage":
            row[bucket] += infl_modifier * amount
            refill_bucket(row, bucket)

    return row


def apply_forecasting(ledger_df, fixed_df, recurring_df, profile_data, inflation_thresholds, gain_table):
    # Apply fixed and recurring transactions to updated asset values
    updated_ledger_df = ledger_df.copy()

    # Precompute annual inflation for each year in the ledger
    forecast_years = sorted(
        set([pd.to_datetime(d).year for d in updated_ledger_df["Date"]])
    )
    annual_inflation = generate_annual_inflation(forecast_years)

    for index, row in updated_ledger_df.iterrows():
        if index == 0:
            prev_row = row
        else:
            prev_row = updated_ledger_df.loc[
                index - 1, updated_ledger_df.columns != "Date"
            ]

        # Initialize the new row with the previous row
        new_row = prev_row.copy()

        # Depreciate the depreciating bucket by 1% per month
        if "Depreciating" in new_row:
            new_row["Depreciating"] *= 0.99

        # Apply gains/losses based on the inflation scenarios per bucket
        gains_row = apply_inflation_scenario(new_row, row, annual_inflation, inflation_thresholds, gain_table)

        # Apply fixed transactions
        fixed_row = apply_fixed_transactions(
            gains_row, fixed_df, pd.to_datetime(row["Date"])
        )

        # Apply recurring transactions
        recurring_row = apply_recurring_transactions(
            fixed_row,
            recurring_df,
            pd.to_datetime(row["Date"]),
            annual_inflation,
            profile_data,
        )

        # Update the updated_ledger_df with the new row
        updated_ledger_df.loc[index, updated_ledger_df.columns != "Date"] = (
            recurring_row
        )

    return updated_ledger_df
