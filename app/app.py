import logging
import pandas as pd
import plotly.express as px
from datetime import datetime

from extract import load_dataframes
from logging_setup import setup_logging
from strategy import apply_forecasting


def main():
    setup_logging()
    dataframes = load_dataframes()
    profile_data = dataframes["profile"].iloc[0].to_dict()
    balance_df = dataframes["balance"]
    fixed_df = dataframes["fixed"]
    recurring_df = dataframes["recurring"]
    logging.info(f"Dataframes loaded: {', '.join(sorted(dataframes.keys()))}")
    
    years_to_retirement = (
        datetime.strptime(profile_data["Retirement Date"], "%Y-%m-%d")
        - datetime.strptime(datetime.now().strftime("%Y-%m-%d"), "%Y-%m-%d")
    ).days / 365
    logging.info(
        "Profile data set. Years to Retirement: {:.2f}".format(
            years_to_retirement
        )
    )

    # Set initial balance of each bucket
    balance_columns = [col for col in balance_df.columns if col != "Date"]
    balance_df[balance_columns] = balance_df[balance_columns].apply(
        lambda x: x.apply(lambda y: round(int(y)) if not pd.isna(y) else y)
    )
    total_net_worth = balance_df[balance_columns].sum(axis=1).iloc[0]
    logging.info(
        "Balance DataFrame set. Total Net Worth: ${:,.0f}".format(total_net_worth)
    )

    # add forecast months to ledger
    forecast_months = pd.date_range(
        balance_df["Date"].iloc[0], profile_data["End Date"], freq="MS"
    )
    ledger_df = pd.concat(
        [balance_df, pd.DataFrame({"Date": forecast_months})], ignore_index=True
    )
    logging.info(
        f"Ledger initiatlized with {len(ledger_df)-1} forecast months. Forecasting..."
    )

    # Apply forecasting strategy
    forecasted_ledger_df = apply_forecasting(
        ledger_df, fixed_df, recurring_df, profile_data
    )
    logging.info(
        f"Ledger updated with {len(forecasted_ledger_df)-1} months forecasted."
    )

    # Log result
    logging.info(
        "End Net Worth: ${:,.0f}".format(
            forecasted_ledger_df.iloc[-1][balance_columns].sum()
        )
    )

    # Visualize forecasted_ledger_df
    fig = px.line(
        forecasted_ledger_df,
        x="Date",
        y=balance_columns,
        color_discrete_sequence=px.colors.qualitative.Set1,
    )
    fig.update_layout(
        title_text="Buckets over Time Line Chart",
        legend_title_text="Bucket"
    )
    fig.show()

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Save visualization to html file
    fig.write_html(f"export/forecasted_ledger_{now}.html")
    logging.info(f"Forecasted ledger visualization saved to forecasted_ledger_{now}.html")

    # Save forecasted ledger to csv file
    forecasted_ledger_df.to_csv(
        f"export/forecasted_ledger_{now}.csv", index=False
    )
    logging.info(f"Forecasted ledger saved to forecasted_ledger_{now}.csv")

if __name__ == "__main__":
    main()
