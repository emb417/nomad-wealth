import logging
import pandas as pd
import plotly.graph_objects as go


def plot_sample_forecast(
    sim_index: int,
    hist_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    taxes_df: pd.DataFrame,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves the bucket‐by‐bucket forecast for one simulation.
    """
    full_df = pd.concat([hist_df, forecast_df], ignore_index=True)
    title = f"Sim {sim_index+1:04d} | Forecast by Bucket"

    fig = go.Figure(
        data=[
            go.Scatter(
                x=full_df["Date"],
                y=full_df[col],
                mode="lines",
                name=col,
            )
            for col in full_df.columns
            if col != "Date"
        ]
    )
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Amount ($)",
        template="plotly_white",
        legend=dict(orientation="h", x=0.35, y=1.1),
    )

    if show:
        fig.show()
    if save:
        prefix = f"{export_path}{sim_index+1:04d}_"
        bucket_csv = f"{prefix}buckets_{ts}.csv"
        taxes_csv = f"{prefix}taxes_{ts}.csv"
        html = f"{prefix}buckets_{ts}.html"

        full_df.to_csv(bucket_csv, index=False)
        taxes_df.to_csv(taxes_csv, index=False)
        fig.write_html(html)
        logging.info(f"Sim {sim_index+1:04d} | Saved sample forecast to {html}")


def plot_mc_networth(
    mc_df: pd.DataFrame,
    SIMS: int,
    dob_year: int,
    eol_year: int,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves the Monte Carlo net-worth chart.
    age_metrics: {
       'age_minus_20': pct,
       'age_minus_10': pct,
       'age_end': pct,
       'age_minus_20_label': int,
       ...
    }
    """
    mc_df.columns = [f"sim_{i}" for i in range(SIMS)]

    # compute percentiles
    pct_df = mc_df.quantile([0.15, 0.5, 0.85], axis=1).T
    pct_df.columns = ["p15", "median", "p85"]

    # probability of positive net worth at final year
    age_metrics = {
        "age_minus_20": eol_year - 20 - dob_year,
        "age_minus_20_pct": (mc_df.loc[eol_year - 20] > 0).mean(),
        "age_minus_10": eol_year - 10 - dob_year,
        "age_minus_10_pct": (mc_df.loc[eol_year - 10] > 0).mean(),
        "age_end": eol_year - dob_year,
        "age_end_pct": (mc_df.loc[eol_year] > 0).mean(),
    }

    # filter mc_df based on final net worth for chart
    pct_p85_final_nw = pct_df["p85"][eol_year]
    mc_df_filtered = mc_df.loc[mc_df.index == eol_year]
    columns_to_drop = [
        column_name
        for column_name in mc_df_filtered.columns
        if mc_df_filtered[column_name].iloc[0] > pct_p85_final_nw
    ]
    mc_p85 = mc_df.drop(columns=columns_to_drop)

    fig = go.Figure()

    # cloud of filtered sims
    for col in mc_p85.columns:
        fig.add_trace(
            go.Scatter(
                x=mc_p85.index,
                y=mc_p85[col],
                line=dict(color="gray", width=1),
                opacity=0.2,
                showlegend=False,
            )
        )

    # percentile lines
    fig.add_trace(
        go.Scatter(
            x=pct_df.index,
            y=pct_df["median"],
            line=dict(color="green", width=2),
            name="Median",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=pct_df.index,
            y=pct_df["p15"],
            line=dict(color="blue", width=2, dash="dash"),
            name="Lower Bounds",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=pct_df.index,
            y=pct_df["p85"],
            line=dict(color="blue", width=2, dash="dash"),
            name="Upper Bounds",
        )
    )

    title = (
        f"Monte Carlo Net Worth Forecast<br>"
        f"{age_metrics['age_minus_20_pct']:.0%} @ {age_metrics['age_minus_20']} y.o. | "
        f"{age_metrics['age_minus_10_pct']:.0%} @ {age_metrics['age_minus_10']} y.o. | "
        f"{age_metrics['age_end_pct']:.0%} @ {age_metrics['age_end']} y.o."
    )
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Net Worth ($)",
        template="plotly_white",
        showlegend=False,
    )

    if show:
        fig.show()
    if save:
        mc_df.to_csv(f"{export_path}mc_networth_{ts}.csv", index_label="Year")
        html = f"{export_path}mc_networth_{ts}.html"
        fig.write_html(html)
        logging.info(f"Monte Carlo files saved to {html}")
