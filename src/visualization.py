import logging
import pandas as pd
import plotly.graph_objects as go

from numpy import ndarray


def plot_historical_balance(
    hist_df: pd.DataFrame,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves the historical balance chart.
    """
    total_net_worth = pd.DataFrame(
        {
            "Date": pd.to_datetime(hist_df["Date"]),
            "Total Net Worth": hist_df.drop("Date", axis=1).sum(axis=1),
        }
    )

    net_worth_gain_loss = pd.DataFrame(
        {
            "Date": hist_df["Date"],
            "Net Worth Gain/Loss %": total_net_worth["Total Net Worth"]
            .pct_change()
            .fillna(0),
        }
    )
    fig = go.Figure(
        data=[
            go.Scatter(
                x=total_net_worth["Date"],
                y=total_net_worth["Total Net Worth"],
                marker=dict(color="black", opacity=0.5),
                name="Total NW",
                mode="lines+markers",
                line=dict(
                    shape="spline",
                    smoothing=1,
                    width=2,
                    color="black",
                ),
                opacity=0.75,
            ),
            go.Bar(
                x=net_worth_gain_loss["Date"],
                y=net_worth_gain_loss["Net Worth Gain/Loss %"],
                marker=dict(
                    color=[
                        "darkgreen" if val > 0 else "darkred"
                        for val in net_worth_gain_loss["Net Worth Gain/Loss %"]
                    ],
                    opacity=0.5,
                ),
                name="NW Gain/Loss %",
                yaxis="y2",
            ),
        ]
    )
    fig.update_layout(
        title="Historical Net Worth (NW) and Monthly Gain/Loss %",
        title_x=0.5,
        xaxis_title="Date",
        yaxis_title="Total NW",
        yaxis_tickformat="$,.0f",
        yaxis2=dict(
            title="NW Gain/Loss %",
            overlaying="y",
            side="right",
            range=[-0.1, 0.3],
        ),
        yaxis2_tickformat=",.2p",
        template="plotly_white",
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_yaxes(showgrid=False)
    if show:
        fig.show()
    if save:
        fig.write_html(export_path + f"historical_nw_{ts}.html")


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
        yaxis_title="Amount",
        yaxis_tickformat="$,.0f",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", x=0.5, y=1.1),
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
    mc_samples_df: pd.DataFrame,
    dob_year: int,
    eol_year: int,
    summary: dict,
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
    SIMS = len(mc_df.columns)
    # compute percentiles
    pct_df = mc_df.quantile([0.15, 0.5, 0.85], axis=1).T
    pct_df.columns = ["p15", "median", "p85"]
    pct_df["mean"] = pct_df.mean(axis=1)

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
    pct_p15_final_nw = pct_df["p15"][eol_year]
    pct_mean_final_nw = pct_df["mean"][eol_year]
    pct_median_final_nw = pct_df["median"][eol_year]
    pct_p85_final_nw = pct_df["p85"][eol_year]
    mc_df_filtered = mc_df.loc[mc_df.index == eol_year]
    columns_to_drop = [
        column_name
        for column_name in mc_df_filtered.columns
        if mc_df_filtered[column_name].iloc[0] > pct_p85_final_nw
    ]
    mc_p85 = mc_df.drop(columns=columns_to_drop)
    networth = {
        "p15": "{:,.0f}".format(int(pct_p15_final_nw)),
        "Median": "{:,.0f}".format(int(pct_median_final_nw)),
        "Average": "{:,.0f}".format(int(pct_mean_final_nw)),
        "p85": "{:,.0f}".format(int(pct_p85_final_nw)),
    }

    # liquidation metrics
    min_liquidation_age = (
        summary["Minimum Property Liquidation Year"] - dob_year
        if summary["Minimum Property Liquidation Year"] is not None
        else None
    )
    avg_liquidation_age = (
        int(
            sum(date.year for date in summary["Property Liquidation Dates"])
            / len(summary["Property Liquidation Dates"])
            - dob_year
        )
        if len(summary["Property Liquidation Dates"]) > 0
        else None
    )
    max_liquidation_age = (
        summary["Maximum Property Liquidation Year"] - dob_year
        if summary["Maximum Property Liquidation Year"] is not None
        else None
    )
    pct_liquidation = summary["Property Liquidations"] / SIMS

    fig = go.Figure()

    # percentile lines
    fig.add_trace(
        go.Scatter(
            x=pct_df.index,
            y=pct_df["p85"],
            line=dict(color="blue", width=2, dash="dash"),
            name="Upper Bounds",
        )
    )
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
    # cloud of filtered sims and samples (purple)
    for col in mc_p85.columns:
        if col in mc_samples_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=mc_p85.index,
                    y=mc_p85[col],
                    line=dict(color="purple", width=1),
                    opacity=0.5,
                    showlegend=False,
                    hoverinfo="all",
                    name=col,
                )
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=mc_p85.index,
                    y=mc_p85[col],
                    line=dict(color="gray", width=1),
                    opacity=0.2,
                    showlegend=False,
                    hoverinfo="skip",
                    name=col,
                )
            )

    confidence_color = "green" if SIMS >= 1000 else "blue" if SIMS >= 100 else "red"

    def getPNWColor(value):
        return "green" if value > 0.95 else "blue" if value > 0.75 else "red"

    def getEOLNWColor(value):
        return "green" if value > 1000000 else "blue" if value > 0 else "red"

    def getPropertyLiquidationColor(value):
        return "green" if value < 0.2 else "blue" if value < 0.5 else "red"

    def getAgeColor(value):
        ageColor = (
            "green"
            if value is None
            else "green" if value > 75 else "blue" if value > 60 else "red"
        )
        return ageColor

    title = (
        f"Monte Carlo Net Worth Forecast"
        f" | <span style='color: {confidence_color}'>{SIMS} Simulations</span>"
        f"<br><br>Postive Net Worth: <span style='color: {getPNWColor(age_metrics['age_minus_20_pct'])}'>{age_metrics['age_minus_20_pct']:.1%}"
        f" @ {age_metrics['age_minus_20']} y.o.</span>"
        f" | <span style='color: {getPNWColor(age_metrics['age_minus_10_pct'])}'>{age_metrics['age_minus_10_pct']:.1%}"
        f" @ {age_metrics['age_minus_10']} y.o.</span>"
        f" | <span style='color: {getPNWColor(age_metrics['age_end_pct'])}'>{age_metrics['age_end_pct']:.1%}"
        f" @ {age_metrics['age_end']} y.o.</span>"
        f"<br><br>EOL Net Worth: <span style='color: {getEOLNWColor(pct_p15_final_nw)}'>p15 &#36;{networth['p15']}</span>"
        f" | <span style='color: {getEOLNWColor(pct_median_final_nw)}'>Median &#36;{networth['Median']}</span>"
        f" | <span style='color: {getEOLNWColor(pct_mean_final_nw)}'>Average &#36;{networth['Average']}</span>"
        f" | <span style='color: {getEOLNWColor(pct_p85_final_nw)}'>p85 &#36;{networth['p85']}</span>"
        f"<br><br>Property Liquidations: <span style='color: {getPropertyLiquidationColor(pct_liquidation)}'>{pct_liquidation:.1%} of Sims</span>"
    )
    if pct_liquidation != 0:
        title += (
            f" | <span style='color: {getAgeColor(min_liquidation_age)}'>Min {min_liquidation_age} y.o.</span>"
            f" | <span style='color: {getAgeColor(avg_liquidation_age)}'>Avg {avg_liquidation_age} y.o.</span>"
            f" | <span style='color: {getAgeColor(max_liquidation_age)}'>Max {max_liquidation_age} y.o.</span>"
        )
    fig.update_layout(
        title=title,
        title_x=0.5,
        xaxis_title="Year",
        yaxis_title="Net Worth",
        yaxis_tickformat="$,.0f",
        template="plotly_white",
        showlegend=False,
        hovermode="x unified",
    )

    if show:
        fig.show()
    if save:
        mc_df.to_csv(f"{export_path}mc_networth_{ts}.csv", index_label="Year")
        html = f"{export_path}mc_networth_{ts}.html"
        fig.write_html(html)
        logging.info(f"Monte Carlo files saved to {html}")
