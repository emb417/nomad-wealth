import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from plotly.subplots import make_subplots


COLOR_PALETTE = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
    "#aec7e8",
    "#ffbb78",
    "#98df8a",
    "#ff9896",
    "#c5b0d5",
    "#c49c94",
    "#f7b6d2",
    "#c7c7c7",
    "#dbdb8d",
    "#9edae5",
    "#393b79",
    "#637939",
    "#8c6d31",
    "#843c39",
    "#7b4173",
    "#5254a3",
    "#6b6ecf",
    "#9c9ede",
    "#17becf",
    "#bcbd22",
    "#e6550d",
    "#31a354",
]

label_color_map = {}


def base_label(label):
    base = label.split("(")[0]
    if "Gains" in base:
        return base.replace(" Gains", "")
    if "Losses" in base:
        return base.replace(" Losses", "")
    base = base.strip()
    return base


def normalize_source(label):
    return label.split(" Gains")[0].split(" Losses")[0]


def assign_colors_by_base_label(labels, color_palette):
    for lbl in labels:
        base = base_label(lbl)
        if base not in label_color_map:
            label_color_map[base] = color_palette[
                len(label_color_map) % len(color_palette)
            ]
    return [label_color_map[base_label(lbl)] for lbl in labels]


def plot_example_income_taxes(
    taxes_df: pd.DataFrame,
    sim: int,
    show: bool = True,
    save: bool = False,
    export_path: str = "export/",
    ts: str = "",
):
    """
    Renders and optionally saves the income and taxes chart for one simulation.
    """

    title = f"Sim {sim+1:04d} | Income & Taxes"
    years = taxes_df["Year"]

    # Color palettes
    income_colors = {
        "Salary": "#022239",
        "Social Security": "#08306b",
        "Tax-Deferred Withdrawals": "#1f77b4",
        "Roth Conversions": "#4dabf7",
        "Realized Gains": "#a6cee3",
        "Tax-Free Withdrawals": "#1b9e77",
    }
    tax_colors = {
        "Ordinary Tax": "#f39c12",
        "Capital Gains Tax": "#ff7f0e",
        "Penalty Tax": "#e74c3c",
    }
    marker_config = {
        "Adjusted Gross Income (AGI)": {
            "symbol": "triangle-up",
            "size": 8,
            "color": "black",
        },
        "Ordinary Income": {"symbol": "bowtie", "size": 10, "color": "black"},
        "Taxable Gains": {"symbol": "cross", "size": 8, "color": "black"},
        "Taxable Social Security": {
            "symbol": "triangle-down",
            "size": 8,
            "color": "black",
        },
        "Total Tax": {"symbol": "line-ew-open", "size": 10, "color": "red"},
    }

    # Create subplots
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Income", "Taxes"),
    )

    # Income bars
    for col in income_colors:
        fig.add_trace(
            go.Bar(
                x=years,
                y=taxes_df[col],
                name=col,
                marker_color=income_colors[col],
                opacity=0.5,
                hovertemplate=f"{col} %{{y:$,.0f}}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # Income markers
    for col in [
        "Adjusted Gross Income (AGI)",
        "Ordinary Income",
        "Taxable Gains",
        "Taxable Social Security",
    ]:
        fig.add_trace(
            go.Scatter(
                x=years,
                y=taxes_df[col],
                name=col,
                mode="markers",
                marker=marker_config[col],
                hovertemplate=f"{col}: %{{y:$,.0f}}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # Tax bars
    for col in tax_colors:
        fig.add_trace(
            go.Bar(
                x=years,
                y=taxes_df[col],
                name=col,
                marker_color=tax_colors[col],
                opacity=0.5,
                hovertemplate=f"{col} %{{y:$,.0f}}<extra></extra>",
            ),
            row=1,
            col=2,
        )

    # Total tax marker
    fig.add_trace(
        go.Scatter(
            x=years,
            y=taxes_df["Total Tax"],
            name="Total Tax",
            mode="markers",
            marker=marker_config["Total Tax"],
            hovertemplate="Total Tax: %{y:$,.0f}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    # Layout
    fig.update_layout(
        title=title,
        barmode="stack",
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
        yaxis_tickformat="$,.0f",
        legend=dict(orientation="h", x=0.5, y=-0.05, xanchor="center", yanchor="top"),
    )

    # Sync y-axis range
    max_y = max(
        taxes_df["Adjusted Gross Income (AGI)"].max(), taxes_df["Total Tax"].max()
    )
    fig.update_yaxes(range=[0, max_y], tickformat="$,.0f", row=1, col=1)
    fig.update_yaxes(range=[0, max_y], tickformat="$,.0f", row=1, col=2)

    if show:
        fig.show()
    if save:
        prefix = f"{export_path}{sim+1:04d}_"
        taxes_csv = f"{prefix}income_taxes_{ts}.csv"
        html = f"{prefix}income_taxes_{ts}.html"

        taxes_df.to_csv(taxes_csv, index=False)
        fig.write_html(html)
        logging.debug(f"Sim {sim+1:04d} | Saved sample forecast to {html}")


def plot_example_transactions(
    flow_df: pd.DataFrame,
    sim: int,
    show: bool = True,
    save: bool = False,
    export_path: str = "export/",
    ts: str = "",
):
    df = flow_df.copy()
    df["date"] = df["date"].dt.to_timestamp()
    df["year"] = df["date"].dt.year
    df = df[df["sim"] == sim]

    years = sorted(df["year"].unique())

    sankey_traces = []

    for i, year in enumerate(years):
        df_year = df[df["year"] == year]
        agg = (
            df_year.groupby(["source", "target", "type"])["amount"].sum().reset_index()
        )
        agg = agg[agg["amount"] != 0]

        gain_loss_rows = agg[agg["type"].isin(["gain", "loss"])].copy()
        if not gain_loss_rows.empty:
            gain_loss_rows["source"] = gain_loss_rows["source"].apply(normalize_source)
            gain_loss_rows["signed_amount"] = gain_loss_rows.apply(
                lambda row: row["amount"] if row["type"] == "gain" else row["amount"],
                axis=1,
            )
            agg_gain_loss = (
                gain_loss_rows.groupby(["source", "target"])["signed_amount"]
                .sum()
                .reset_index()
            )
            agg_gain_loss = agg_gain_loss[agg_gain_loss["signed_amount"] != 0]

            # Replace original gain/loss rows with net flows
            agg = agg[~agg["type"].isin(["gain", "loss"])]
            net_flows = agg_gain_loss.copy()
            net_flows["type"] = net_flows["signed_amount"].apply(
                lambda x: "gain" if x > 0 else "loss"
            )
            net_flows["amount"] = net_flows["signed_amount"].abs()
            agg = pd.concat(
                [agg, net_flows[["source", "target", "type", "amount"]]],
                ignore_index=True,
            )

        # Compute total volume per node
        volume_counter = {}
        for _, row in agg.iterrows():
            volume_counter[row["source"]] = volume_counter.get(row["source"], 0) + abs(
                row["amount"]
            )
            volume_counter[row["target"]] = volume_counter.get(row["target"], 0) + abs(
                row["amount"]
            )
        sorted_keys = sorted(volume_counter, key=lambda k: -volume_counter[k])
        labels = [f" {k} " for k in sorted_keys]
        label_idx = {k: i for i, k in enumerate(sorted_keys)}
        sources = [label_idx[row["source"]] for _, row in agg.iterrows()]
        targets = [label_idx[row["target"]] for _, row in agg.iterrows()]
        values = [abs(row["amount"]) for _, row in agg.iterrows()]

        color_map = {
            "deposit": "rgba(0,128,0,0.4)",
            "withdraw": "rgba(255,0,0,0.4)",
            "transfer": "rgba(135,206,235,0.4)",
            "gain": "rgba(0,128,0,0.4)",
            "loss": "rgba(255,0,0,0.4)",
        }
        colors = [
            color_map.get(row["type"], "rgba(128,128,128,0.3)")
            for _, row in agg.iterrows()
        ]
        node_colors = assign_colors_by_base_label(labels, COLOR_PALETTE)

        sankey = go.Sankey(
            node=dict(
                label=labels,
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                hoverinfo="none",
                color=node_colors,
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=colors,
                hovertemplate=" %{value:$,.0f}%{source.label}→%{target.label}<extra></extra>",
            ),
            visible=(i == 0),
            name=f"{year}",
        )
        sankey_traces.append(sankey)

    fig = go.Figure(data=sankey_traces)

    # Slider steps
    steps = []
    for i, year in enumerate(years):
        visibility = [j == i for j in range(len(sankey_traces))]
        steps.append(
            dict(
                method="update",
                args=[
                    {"visible": visibility},
                    {"title": {"text": f"Sim {sim+1:04d} | {year} Transactions"}},
                ],
                label=str(year),
            )
        )

    fig.update_layout(
        title={"text": f"Sim {sim+1:04d} | {years[0]} Transactions"},
        sliders=[
            {
                "active": 0,
                "currentvalue": {"visible": False},
                "pad": {"t": 50},
                "steps": steps,
            }
        ],
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if show:
        fig.show()
    if save:
        fig.write_html(f"{export_path}{sim+1:04d}_flow_transitions_{ts}.html")
        flow_df.to_csv(f"{export_path}{sim+1:04d}_flow_transitions_{ts}.csv")


def plot_example_transactions_in_context(
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
        bal_end = forecast_df[forecast_df["Date"] == pd.Timestamp(f"{y1}-01-01")].iloc[
            0
        ]
        flows_y0 = flow_df[flow_df["year"] == y0].copy()
        agg = (
            flows_y0.groupby(["source", "target", "type"])["amount"].sum().reset_index()
        )

        sources_raw, targets_raw, values, colors = [], [], [], []
        used_keys = set()

        # Balances
        for b in bucket_names:
            s_key = f"{b}@{y0}"
            t_key = f"{b}@{y1}"
            v = bal_end[b]
            if v != 0:
                sources_raw.append(s_key)
                targets_raw.append(t_key)
                values.append(v)
                colors.append("rgba(0,0,0,0.1)")
                used_keys.update([s_key, t_key])
        # Routed flows (excluding gain/loss)
        for _, row in agg.iterrows():
            if row["type"] not in ["gain", "loss"]:
                v = row["amount"]
                if v != 0:
                    s_key = f"{row['source']}@{y0}"
                    t_key = f"{row['target']}@{y1}"
                    used_keys.update([s_key, t_key])
                    sources_raw.append(s_key)
                    targets_raw.append(t_key)
                    values.append(abs(v))
                    if row["type"] == "deposit":
                        colors.append("rgba(0,128,0,0.4)")
                    elif row["type"] == "withdraw":
                        colors.append("rgba(255,0,0,0.4)")
                    elif row["type"] == "transfer":
                        colors.append("rgba(135,206,235,0.4)")
                    else:
                        colors.append("rgba(128,128,128,0.3)")

        # Net gain/loss routing with normalized source
        gain_loss_rows = agg[agg["type"].isin(["gain", "loss"])].copy()
        gain_loss_rows["source"] = gain_loss_rows["source"].apply(normalize_source)
        gain_loss_rows["signed_amount"] = gain_loss_rows.apply(
            lambda row: row["amount"] if row["type"] == "gain" else row["amount"],
            axis=1,
        )
        agg_gain_loss = (
            gain_loss_rows.groupby(["source", "target"])["signed_amount"]
            .sum()
            .reset_index()
        )
        for _, row in agg_gain_loss.iterrows():
            v = row["signed_amount"]
            if v != 0:
                s_key = f"{row['source']}@{y0}"
                t_key = f"{row['target']}@{y1}"
                used_keys.update([s_key, t_key])
                sources_raw.append(s_key)
                targets_raw.append(t_key)
                values.append(abs(v))
                colors.append("rgba(0,128,0,0.4)" if v > 0 else "rgba(255,0,0,0.4)")

        # Aggregate volume
        volume_counter = {}
        for s, v in zip(sources_raw, values):
            volume_counter[s] = volume_counter.get(s, 0) + v
        for t, v in zip(targets_raw, values):
            volume_counter[t] = volume_counter.get(t, 0) + v

        # Sort keys by volume
        left_keys = sorted(
            {k for k in volume_counter if k.endswith(f"@{y0}")},
            key=lambda k: -volume_counter[k],
        )
        right_keys = sorted(
            {k for k in volume_counter if k.endswith(f"@{y1}")},
            key=lambda k: -volume_counter[k],
        )
        sorted_keys = left_keys + right_keys

        # Build label list and index
        key_to_label = {k: f" {k.split('@')[0]} " for k in sorted_keys}
        labels = [key_to_label[k] for k in sorted_keys]
        label_idx = {k: i for i, k in enumerate(sorted_keys)}

        # Reindex sources and targets
        sources = [label_idx[k] for k in sources_raw]
        targets = [label_idx[k] for k in targets_raw]

        # Assign node colors consistently by base label
        node_colors = assign_colors_by_base_label(labels, COLOR_PALETTE)
        sankey = go.Sankey(
            node=dict(
                label=labels,
                pad=15,
                thickness=150,
                line=dict(color="black", width=0.5),
                color=node_colors,
                hovertemplate=["%{label}<extra></extra>"],
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=colors,
                hovertemplate="%{source.label} → %{target.label}<br>  %{value:$,.0f}<extra></extra>",
            ),
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
                    {
                        "title": {
                            "text": f"Sim {sim+1:04d} | Jan {y0} → Jan {y1} Transactions In-Context"
                        }
                    },
                ],
                label=f"{y0}→{y1}",
            )
        )
    sliders = [
        dict(active=0, currentvalue={"prefix": "Period: "}, pad={"t": 50}, steps=steps)
    ]
    fig.update_layout(
        title={
            "text": f"Sim {sim+1:04d} | Jan {transitions[0][0]} → Jan {transitions[0][1]} Transactions In-Context",
        },
        sliders=sliders,
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if show:
        fig.show()
    if save:
        fig.write_html(f"{export_path}{sim+1:04d}_sankey_{ts}.html")


def plot_example_forecast(
    sim: int,
    hist_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    dob: str,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves the bucket‐by‐bucket forecast for one simulation.
    """
    full_df = pd.concat([hist_df, forecast_df], ignore_index=True)
    cols = list(full_df.columns)
    cols.insert(1, cols.pop(cols.index("Net Worth")))
    full_df = full_df[cols]
    title = f"Sim {sim+1:04d} | Forecast by Bucket"

    # Extract bucket labels (excluding Date)
    bucket_labels = [col for col in full_df.columns if col != "Date"]

    # Assign colors using base_label logic
    color_list = assign_colors_by_base_label(bucket_labels, COLOR_PALETTE)
    line_colors = dict(zip(bucket_labels, color_list))

    # Age trace
    traces = [
        go.Scatter(
            x=full_df["Date"],
            y=[(date - pd.to_datetime(dob)).days / 365 for date in full_df["Date"]],
            mode="lines",
            name="Age",
            line=dict(width=0, color="white"),
            showlegend=False,
            hovertemplate="Age %{y:.1f}<extra></extra>",
        )
    ]

    # Bucket traces with percent share
    for col in bucket_labels:
        if col == "Net Worth":
            share_data = [100.0] * len(full_df)  # Net Worth is always 100% of itself
        else:
            share_data = (
                (full_df[col] / full_df["Net Worth"])
                .replace([np.inf, -np.inf], np.nan)
                .fillna(0)
                .mul(100)
                .round(2)
            )

        traces.append(
            go.Scatter(
                x=full_df["Date"],
                y=full_df[col],
                mode="lines",
                name=col,
                line=dict(
                    color="gray" if col == "Net Worth" else line_colors[col],
                    dash="dot" if col == "Net Worth" else None,
                ),
                customdata=share_data,
                hovertemplate=(
                    f"{col}: %{{y:$,.0f}}" + " (%{customdata:.0f}%)<extra></extra>"
                ),
            )
        )

    fig = go.Figure(data=traces)

    fig.update_layout(
        title=title,
        yaxis_tickformat="$,.0f",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", x=0.5, y=1.05, xanchor="center"),
    )

    if show:
        fig.show()
    if save:
        prefix = f"{export_path}{sim+1:04d}_"
        bucket_csv = f"{prefix}buckets_{ts}.csv"
        html = f"{prefix}buckets_{ts}.html"

        full_df.to_csv(bucket_csv, index=False)
        fig.write_html(html)
        logging.debug(f"Sim {sim+1:04d} | Saved sample forecast to {html}")


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


def plot_historical_bucket_gains(
    hist_df: pd.DataFrame,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves the historical buckets chart,
    showing monthly and annual percent gain/loss per bucket.
    """
    import plotly.graph_objects as go

    df = hist_df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    # Identify bucket columns
    bucket_cols = [col for col in df.columns]

    # Monthly percent change
    monthly_pct = df[bucket_cols].pct_change().fillna(0)
    monthly_pct.reset_index(inplace=True)
    monthly_networth_change = df[bucket_cols].sum(axis=1).pct_change().fillna(0)
    monthly_networth_total = df[bucket_cols].sum(axis=1).values

    # Build traces
    traces = []

    traces.append(
        go.Scatter(
            x=monthly_pct["Date"],
            y=monthly_networth_change.values,
            mode="markers",
            name="Net Worth",
            marker=dict(color="black", size=20, symbol="line-ew-open"),
            customdata=monthly_networth_total,
            hovertemplate="Net Worth: %{y:.2%} to %{customdata:$,.0f}<extra></extra>",
        )
    )

    for col in bucket_cols:
        monthly_vals = monthly_pct[col].values
        dates = monthly_pct["Date"]

        # Get corresponding balance values from original df
        balance_vals = df[col].reindex(dates).fillna(0).values

        rgba_colors = []
        for val in monthly_vals:
            if val > 0:
                base = "0,128,0"  # green
            elif val < 0:
                base = "178,34,34"  # red
            else:
                base = "0,0,0"  # black

            alpha = round(min(abs(val) / 0.1, 1), 2)
            rgba_colors.append(f"rgba({base},{alpha})")

        traces.append(
            go.Bar(
                x=dates,
                y=monthly_vals,
                name=col,
                marker=dict(color=rgba_colors),
                yaxis="y",
                customdata=balance_vals,
                hovertemplate=(
                    f"{col}: %{{y:.2%}} " f"to %{{customdata:$,.0f}}<extra></extra>"
                ),
            )
        )

    fig = go.Figure(data=traces)

    fig.update_layout(
        title="Historical Monthly Gain % per Bucket",
        title_x=0.5,
        yaxis=dict(
            tickformat=".2%",
            range=[-0.25, 0.25],
        ),
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
    )

    fig.update_yaxes(showgrid=False)

    if show:
        fig.show()
    if save:
        fig.write_html(export_path + f"historical_buckets_{ts}.html")


def plot_mc_networth(
    mc_networth_df: pd.DataFrame,
    sim_examples: np.ndarray,
    dob: str,
    eol: str,
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
    sim_size = len(mc_networth_df.columns)
    # compute percentiles
    pct_df = mc_networth_df.quantile([0.15, 0.5, 0.85], axis=1).T
    pct_df.columns = ["p15", "median", "p85"]
    pct_df["mean"] = pct_df.mean(axis=1)
    dob_year = pd.to_datetime(dob).year
    eol_year = pd.to_datetime(eol).year
    eol_age = eol_year - dob_year

    # probability of positive net worth at final year
    age_metrics = {
        "age_minus_20": eol_age - 20,
        "age_minus_20_pct": (mc_networth_df.loc[eol_year - 20] > 0).mean(),
        "age_minus_10": eol_age - 10,
        "age_minus_10_pct": (mc_networth_df.loc[eol_year - 10] > 0).mean(),
        "age_end": eol_age,
        "age_end_pct": (mc_networth_df.loc[eol_year] > 0).mean(),
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
    pct_liquidation = summary["Property Liquidations"] / sim_size

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
    # Monte-Carlo samples - top/bottom 5%, examples in purple

    # Compute 5th and 95th percentiles
    final_values = mc_networth_df.iloc[-1]
    lower_bound = final_values.quantile(0.1)
    upper_bound = final_values.quantile(0.9)
    filtered_cols = [
        col
        for col in mc_networth_df.columns
        if lower_bound <= final_values[col] <= upper_bound
    ]

    for col in filtered_cols:
        is_sample = col in sim_examples
        color, opacity, width = ("purple", 0.6, 2) if is_sample else ("gray", 0.2, 1)
        hover_kwargs = (
            {"hovertemplate": f"Sim {int(col)+1:04d}: %{{y:$,.0f}}<extra></extra>"}
            if is_sample
            else {"hoverinfo": "skip"}
        )

        fig.add_trace(
            go.Scatter(
                x=years,
                y=mc_networth_df[col],
                showlegend=False,
                line=dict(color=color, width=width),
                opacity=opacity,
                **hover_kwargs,
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
            "85th Percentile", years, pct_df["p85"], color="blue", dash="dash", width=2
        )
    )
    fig.add_trace(make_trace("Median", years, pct_df["median"], color="green", width=2))
    fig.add_trace(
        make_trace(
            "15th Percentile", years, pct_df["p15"], color="blue", dash="dash", width=2
        )
    )

    for y, label, color in [
        (pct_df["p15"][eol_year], "15th Percentile", "blue"),
        (pct_df["median"][eol_year], "Median", "green"),
        (pct_df["p85"][eol_year], "85th Percentile", "blue"),
    ]:
        fig.add_annotation(
            x=eol_year,
            y=y,
            text=f"{label}: ${y:,.0f}",
            showarrow=False,
            font=dict(color=color),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=color,
            borderwidth=1,
            xanchor="right",
            yanchor="bottom",
        )

    confidence_color = (
        "green" if sim_size >= 1000 else "blue" if sim_size >= 100 else "red"
    )

    def getPNWColor(value):
        return "green" if value > 0.85 else "blue" if value > 0.75 else "red"

    def getPropertyLiquidationColor(value):
        return "green" if value < 0.25 else "blue" if value < 0.5 else "red"

    def getAgeColor(value):
        ageColor = (
            "green"
            if value is None
            else "green" if value > 75 else "blue" if value > 65 else "red"
        )
        return ageColor

    title = (
        f"Monte Carlo Net Worth Forecast"
        f" | <span style='color: {confidence_color}'>{sim_size} Simulations</span>"
        f"<br><br>Postive Net Worth: <span style='color: {getPNWColor(age_metrics['age_minus_20_pct'])}'>{age_metrics['age_minus_20_pct']:.1%}"
        f" @ {age_metrics['age_minus_20']} y.o.</span>"
        f" | <span style='color: {getPNWColor(age_metrics['age_minus_10_pct'])}'>{age_metrics['age_minus_10_pct']:.1%}"
        f" @ {age_metrics['age_minus_10']} y.o.</span>"
        f" | <span style='color: {getPNWColor(age_metrics['age_end_pct'])}'>{age_metrics['age_end_pct']:.1%}"
        f" @ {age_metrics['age_end']} y.o.</span>"
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
        mc_networth_df.to_csv(f"{export_path}mc_networth_{ts}.csv", index_label="Year")
        html = f"{export_path}mc_networth_{ts}.html"
        fig.write_html(html)
        logging.info(f"Monte Carlo files saved to {html}")


def plot_mc_tax_bars(
    mc_tax_df: pd.DataFrame,
    sim_examples: np.ndarray,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves a bar chart of total taxes per simulation.
    """
    sim_size = len(mc_tax_df.columns)
    mc_tax_df = mc_tax_df.copy()
    mc_tax_df.index = pd.Index(mc_tax_df.index).astype(int)
    total_taxes = mc_tax_df.sum()

    p15 = total_taxes.quantile(0.15)
    median = total_taxes.median()
    p85 = total_taxes.quantile(0.85)

    # Exclude the top 10% of total taxes from the chart
    threshold = total_taxes.quantile(0.90)
    total_taxes = total_taxes[total_taxes <= threshold]
    sim_labels = [f"Sim {int(sim)+1:04d}" for sim in total_taxes.index]
    bar_colors = [
        "purple" if sim in sim_examples else "lightgray" for sim in total_taxes.index
    ]
    hover_texts = [f"Total Taxes: ${total:,.0f}" for total in total_taxes.values]

    fig = go.Figure(
        go.Bar(
            x=sim_labels,
            y=total_taxes.values,
            marker_color=bar_colors,
            opacity=0.5,
            hovertext=hover_texts,
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )

    # Reference lines using same x labels
    fig.add_trace(
        go.Scatter(
            x=sim_labels,
            y=[p85] * sim_size,
            mode="lines",
            name="85th Percentile",
            line=dict(color="blue", dash="dash"),
            hovertemplate="85th Percentile: %{y:$,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sim_labels,
            y=[median] * sim_size,
            mode="lines",
            name="Median",
            line=dict(color="green", width=2),
            hovertemplate="Median: %{y:$,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sim_labels,
            y=[p15] * sim_size,
            mode="lines",
            name="15th Percentile",
            line=dict(color="blue", dash="dash"),
            hovertemplate="15th Percentile: %{y:$,.0f}<extra></extra>",
        )
    )

    # Annotate reference lines
    for y, label, color in [
        (p15, "15th Percentile", "blue"),
        (median, "Median", "green"),
        (p85, "85th Percentile", "blue"),
    ]:
        fig.add_annotation(
            x=sim_labels[-1],
            y=y,
            text=f" {label}: ${y:,.0f} ",
            showarrow=False,
            font=dict(color=color),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=color,
            borderwidth=1,
        )

    confidence_color = (
        "green" if sim_size >= 1000 else "blue" if sim_size >= 100 else "red"
    )

    title = (
        f"Total Tax Burden per Simulation"
        f" | <span style='color: {confidence_color}'>{sim_size} Simulations</span>"
    )

    fig.update_layout(
        title=title,
        title_x=0.5,
        yaxis=dict(tickformat="$,.0f"),
        template="plotly_white",
        hoverlabel=dict(align="left"),
        hovermode="x unified",
        showlegend=False,
    )

    if show:
        fig.show()
    if save:
        total_taxes.to_csv(
            f"{export_path}mc_tax_totals_{ts}.csv", index_label="Simulation"
        )
        html = f"{export_path}mc_tax_totals_{ts}.html"
        fig.write_html(html)
        logging.info(f"Monte Carlo tax totals saved to {html}")
