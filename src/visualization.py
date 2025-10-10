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

    monthly_net_worth_gain_loss = pd.DataFrame(
        {
            "Date": hist_df["Date"],
            "Net Worth Gain": total_net_worth["Total Net Worth"].pct_change().fillna(0),
        }
    )
    annual_net_worth_gain_loss = pd.DataFrame(
        {
            "Date": hist_df["Date"],
            "Net Worth Gain": total_net_worth["Total Net Worth"]
            .pct_change(12)
            .fillna(0),
        }
    )
    fig = go.Figure(
        data=[
            go.Scatter(
                x=total_net_worth["Date"],
                y=total_net_worth["Total Net Worth"],
                marker=dict(color="black", opacity=0.5),
                name="Net Worth",
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
                x=monthly_net_worth_gain_loss["Date"],
                y=monthly_net_worth_gain_loss["Net Worth Gain"],
                marker=dict(
                    color=[
                        "darkgreen" if val > 0 else "darkred"
                        for val in monthly_net_worth_gain_loss["Net Worth Gain"]
                    ],
                    opacity=0.5,
                ),
                name="Monthly Gain",
                yaxis="y2",
            ),
            go.Bar(
                x=annual_net_worth_gain_loss["Date"],
                y=annual_net_worth_gain_loss["Net Worth Gain"],
                marker=dict(
                    color=[
                        "darkblue" if val > 0 else "darkorange"
                        for val in annual_net_worth_gain_loss["Net Worth Gain"]
                    ],
                    opacity=0.5,
                ),
                name="Annual Gain",
                yaxis="y2",
            ),
        ]
    )
    fig.update_layout(
        title="Historical Net Worth and Annual/Monthly Gain %",
        title_x=0.5,
        yaxis_tickformat="$,.0f",
        yaxis2=dict(
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
    dob_year: int,
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

    traces = [
        go.Scatter(
            x=full_df["Date"],
            y=[
                (date.year - dob_year) + (date.month - x.month) / 12
                for x, date in zip(full_df["Date"], full_df["Date"])
            ],
            mode="lines",
            name="Age",
            line=dict(width=0, color="white"),
            showlegend=False,
            hovertemplate=("Age %{y:.0f}<extra></extra>"),
        )
    ]
    traces.extend(
        go.Scatter(
            x=full_df["Date"],
            y=full_df[col],
            mode="lines",
            name=col,
        )
        for col in full_df.columns
        if col != "Date"
    )

    fig = go.Figure(data=traces)

    fig.update_layout(
        title=title,
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

    years = pct_df.index.to_list()
    ages = [year - dob_year for year in years]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=years,
            y=pct_df["median"],
            customdata=ages,
            mode="markers",
            marker=dict(size=0, opacity=0),
            line=dict(width=0),
            showlegend=False,
            hovertemplate=("Age %{customdata:.0f}<extra></extra>"),
        )
    )

    def make_trace(name, x, y, **line_kwargs):
        return go.Scatter(
            x=x,
            y=y,
            name=name,
            line=line_kwargs,
            hovertemplate=f"{name}: %{{y:$,.0f}}<extra></extra>",
        )

    # Percentile lines
    fig.add_trace(
        make_trace(
            "Upper Bounds", years, pct_df["p85"], color="blue", dash="dash", width=2
        )
    )
    fig.add_trace(make_trace("Median", years, pct_df["median"], color="green", width=2))
    fig.add_trace(
        make_trace(
            "Lower Bounds", years, pct_df["p15"], color="blue", dash="dash", width=2
        )
    )

    # Monte-Carlo sample lines (purple only)
    samples = set(mc_samples_df.columns)
    for col in mc_p85.columns:
        is_sample = col in samples
        color, opacity = ("purple", 0.5) if is_sample else ("gray", 0.2)
        hover_kwargs = (
            {"hovertemplate": f"{col}: %{{y:$,.0f}}<extra></extra>"}
            if is_sample
            else {"hoverinfo": "skip"}
        )

        fig.add_trace(
            go.Scatter(
                x=years,
                y=mc_p85[col],
                showlegend=False,
                line=dict(color=color, width=1),
                opacity=opacity,
                **hover_kwargs,
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
        yaxis_tickformat="$,.0f",
        template="plotly_white",
        showlegend=False,
        hovermode="x unified",
        hoverlabel=dict(align="left"),
    )

    if show:
        fig.show()
    if save:
        mc_df.to_csv(f"{export_path}mc_networth_{ts}.csv", index_label="Year")
        html = f"{export_path}mc_networth_{ts}.html"
        fig.write_html(html)
        logging.info(f"Monte Carlo files saved to {html}")


def plot_flows(
    sim: int,
    mc_monthly_df: pd.DataFrame,
    flow_df: pd.DataFrame,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    sim             : simulation index (int)
    mc_monthly_df   : index='YYYY-MM', cols=real buckets, values=end-of-month balances
    flow_df         : DataFrame with columns ['date','source','target','amount','type','sim']
    """

    # 1) Build a year‐column off your monthly balances
    df_bal = mc_monthly_df.copy().reset_index().rename(columns={"index": "month_str"})
    # month_str is 'YYYY-MM'
    df_bal["date"] = pd.to_datetime(df_bal["month_str"] + "-01")
    df_bal["year"] = df_bal["date"].dt.year

    # 2) Prepare flows: parse source dates, extract year_src
    df_fl = flow_df.copy()
    # ensure 'date' is the 'YYYY-MM' string
    df_fl["month_src_dt"] = df_fl["date"]
    df_fl["year_src"] = df_fl["month_src_dt"].dt.year

    # compute target = next calendar month (not used for grouping)
    df_fl["month_tgt_dt"] = df_fl["month_src_dt"].shift(1)
    df_fl["month_tgt"] = df_fl["month_tgt_dt"].dt.strftime("%Y-%m")

    # 3) Synthetic buckets for unknown sources/targets
    real_buckets = list(mc_monthly_df.columns)
    df_fl["src_bucket"] = df_fl["source"].where(
        df_fl["source"].isin(real_buckets), "Income"
    )
    df_fl["tgt_bucket"] = df_fl["target"].where(
        df_fl["target"].isin(real_buckets), "Expense"
    )

    # 4) Determine calendar years present in balances
    years = sorted(df_bal["year"].unique())

    # 5) Extend bucket list if Income/Expense appear
    buckets_ext = real_buckets.copy()
    if df_fl["src_bucket"].eq("Income").any():
        buckets_ext.append("Income")
    if df_fl["tgt_bucket"].eq("Expense").any():
        buckets_ext.append("Expense")

    # 6) Color palette for nodes
    palette = [
        "#4C78A8",
        "#F58518",
        "#E45756",
        "#72B7B2",
        "#54A24B",
        "#EECA3B",
        "#B279A2",
        "#FF9DA6",
        "#9D755D",
        "#BAB0AC",
    ]
    bucket_color = {b: palette[i % len(palette)] for i, b in enumerate(buckets_ext)}

    frames = []
    for yr in years:
        # a) Node index map
        node_idx = {b: i for i, b in enumerate(buckets_ext)}
        labels = buckets_ext
        N = len(buckets_ext)

        # b) Node positions: x fixed at 0.5, y stacked evenly
        node_x = [0.5] * N
        node_y = [i / (N - 1) if N > 1 else 0.5 for i in range(N)]

        # c) End-of-year balances
        df_year_bal = df_bal[df_bal["year"] == yr].sort_values("date")
        if not df_year_bal.empty:
            last_row = df_year_bal.iloc[-1]
            end_bal = last_row[real_buckets]
        else:
            end_bal = pd.Series(0, index=real_buckets)

        customdata = [end_bal.get(b, 0) for b in buckets_ext]

        # d) Aggregate flows by src_bucket→tgt_bucket for year_src==yr
        sub_fl = df_fl[df_fl["year_src"] == yr]
        agg = sub_fl.groupby(["src_bucket", "tgt_bucket"], as_index=False)[
            "amount"
        ].sum()
        link_src = [node_idx[s] for s in agg["src_bucket"]]
        link_tgt = [node_idx[t] for t in agg["tgt_bucket"]]
        link_val = agg["amount"].tolist()
        link_col = ["gray"] * len(link_val)

        # e) Build Sankey trace
        sankey = go.Sankey(
            arrangement="fixed",
            node=dict(
                label=labels,
                color=[bucket_color[b] for b in buckets_ext],
                x=node_x,
                y=node_y,
                customdata=customdata,
                hovertemplate=(
                    "Bucket: %{label}<br>"
                    "End-of-Year Balance: $%{customdata:,.0f}<extra></extra>"
                ),
                pad=15,
                thickness=15,
                line=dict(color="black", width=0.5),
            ),
            link=dict(
                source=link_src,
                target=link_tgt,
                value=link_val,
                color=link_col,
            ),
        )
        frames.append(go.Frame(data=[sankey], name=str(yr)))

    # 7) Assemble figure with a year slider
    fig = go.Figure(data=frames[0].data, frames=frames)
    steps = [
        dict(
            method="animate",
            label=fr.name,
            args=[
                [fr.name],
                {"mode": "immediate", "frame": {"duration": 500, "redraw": True}},
            ],
        )
        for fr in frames
    ]
    slider = dict(active=0, pad={"t": 50}, steps=steps)

    fig.update_layout(
        sliders=[slider],
        title_text=f"Sim {sim+1:04d}: Annual Bucket Balances & Flows",
        font_size=12,
    )

    # 8) Show or save
    if show:
        fig.show()
    if save:
        fig.write_html(f"{export_path}flows_{ts}.html")

    return fig
