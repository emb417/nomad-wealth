import logging
import pandas as pd
import plotly.graph_objects as go


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


def plot_sample_flow(
    sim: int,
    forecast_df: pd.DataFrame,
    flow_df: pd.DataFrame,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    forecast_df = forecast_df.copy()
    forecast_df["Date"] = pd.to_datetime(forecast_df["Date"])
    forecast_df = forecast_df[forecast_df["Date"].dt.month == 1].sort_values("Date")
    bucket_names = [col for col in forecast_df.columns if col != "Date"]
    years = forecast_df["Date"].dt.year.tolist()
    transitions = [(years[i], years[i + 1]) for i in range(len(years) - 1)]

    flow_df = flow_df.copy()
    flow_df["date"] = flow_df["date"].dt.to_timestamp()
    flow_df = flow_df[flow_df["sim"] == sim]
    flow_df["year"] = flow_df["date"].dt.year

    sankey_traces = []
    for y0, y1 in transitions:
        bal_end = forecast_df[forecast_df["Date"].dt.year == y1].iloc[0]
        flows_y0 = flow_df[flow_df["year"] == y0].copy()
        agg = flows_y0.groupby(["source", "target"])["amount"].sum().reset_index()

        sorted_buckets = sorted(bucket_names, key=lambda b: -bal_end[b])
        external_sources = sorted(set(agg["source"]) - set(bucket_names))
        sources_raw = sorted_buckets + external_sources
        external_targets = sorted(set(agg["target"]) - set(bucket_names))
        targets_raw = sorted(set(sorted_buckets + external_targets))

        source_nodes = [f"{s}@{y0}" for s in sources_raw]
        target_nodes = [f"{t}@{y1}" for t in targets_raw]
        labels = source_nodes + target_nodes

        source_idx = {label: i for i, label in enumerate(source_nodes)}
        target_idx = {
            f"{t}@{y1}": i + len(source_nodes) for i, t in enumerate(targets_raw)
        }

        sources, targets, values = [], [], []

        for _, row in agg.iterrows():
            s_label = f"{row['source']}@{y0}"
            t_label = f"{row['target']}@{y1}"
            s = source_idx.get(s_label)
            t = target_idx.get(t_label)
            v = row["amount"]
            if s is not None and t is not None and v > 0:
                sources.append(s)
                targets.append(t)
                values.append(v)

        inflows = (
            agg[agg["target"].isin(bucket_names)]
            .groupby("target")["amount"]
            .sum()
            .reindex(bucket_names, fill_value=0)
        )
        for b in bucket_names:
            residual = bal_end[b] - inflows.get(b, 0)
            s_label = f"{b}@{y0}"
            t_label = f"{b}@{y1}"
            s = source_idx.get(s_label)
            t = target_idx.get(t_label)
            if residual != 0 and s is not None and t is not None:
                sources.append(s)
                targets.append(t)
                values.append(residual)

        sankey = go.Sankey(
            node=dict(
                label=labels,
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
            ),
            link=dict(source=sources, target=targets, value=values),
            domain=dict(x=[0, 1]),
            visible=(len(sankey_traces) == 0),
        )
        sankey_traces.append(sankey)

    fig = go.Figure(data=sankey_traces)
    steps = []
    for i, (y0, y1) in enumerate(transitions):
        vis = [False] * len(transitions)
        vis[i] = True
        steps.append(
            dict(
                method="update",
                args=[
                    {"visible": vis},
                    {"title": {"text": f"Sim {sim+1:04d} | Flows: {y0} → {y1}"}},
                ],
                label=f"{y0}→{y1}",
            )
        )
    sliders = [
        dict(active=0, currentvalue={"prefix": "Period: "}, pad={"t": 50}, steps=steps)
    ]
    fig.update_layout(
        title={
            "text": f"Sim {sim+1:04d} | Flows: {transitions[0][0]} → {transitions[0][1]}"
        },
        sliders=sliders,
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if show:
        fig.show()
    if save:
        fig.write_html(f"{export_path}{sim+1:04d}_sankey_{ts}.html")


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
        logging.debug(f"Sim {sim_index+1:04d} | Saved sample forecast to {html}")


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
