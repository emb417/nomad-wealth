import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from plotly.subplots import make_subplots
from datetime import datetime


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


def coerce_month_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures the 'Month' column is datetime64[ns] at month-end.
    Avoids using pd.api.types.
    """
    month_col = df["Month"]

    if isinstance(month_col.iloc[0], pd.Period):
        df["Month"] = month_col.dt.to_timestamp("M")
    elif isinstance(month_col.iloc[0], (pd.Timestamp, datetime)):
        df["Month"] = month_col.dt.to_period("M").dt.to_timestamp("M")
    else:
        df["Month"] = pd.to_datetime(month_col).dt.to_period("M").dt.to_timestamp("M")

    return df


def plot_example_income_taxes(
    taxes_df: pd.DataFrame,
    trial: int,
    show: bool = True,
    save: bool = False,
    export_path: str = "export/",
    ts: str = "",
):
    """
    Renders and optionally saves the income and taxes chart for one trial.
    """

    title = f"Trial {trial+1:04d} | Income & Taxes"
    years = taxes_df["Year"]

    # Color palettes
    income_colors = {
        "Unemployment": "#08306b",
        "Salary": "#08306b",
        "Social Security": "#08306b",
        "Tax-Deferred Withdrawals": "#1f77b4",
        "Fixed Income Interest": "#74b6da",
        "Roth Conversions": "#4dabf7",
        "Realized Gains": "#accfe1",
        "Fixed Income Withdrawals": "#b1b1b1",
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
    fig.update_yaxes(tickformat="$,.0f", row=1, col=1)
    fig.update_yaxes(tickformat="$,.0f", row=1, col=2)

    if show:
        fig.show()
    if save:
        prefix = f"{export_path}{trial+1:04d}_"
        taxes_csv = f"{prefix}income_taxes_{ts}.csv"
        html = f"{prefix}income_taxes_{ts}.html"

        taxes_df.to_csv(taxes_csv, index=False)
        fig.write_html(html)
        logging.debug(f"Trial {trial+1:04d} | Saved sample forecast to {html}")


def plot_example_monthly_expenses(
    flow_df: pd.DataFrame,
    trial: int,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves a stacked bar chart of monthly cash withdrawals by category,
    with an overlay line for total monthly withdrawals.
    """
    # Filter for withdrawals from Cash
    cash_outflows = flow_df[
        (flow_df["source"] == "Cash") & (flow_df["type"] == "withdraw")
    ]

    # Aggregate by month and target category
    monthly_totals = (
        cash_outflows.groupby(["date", "target"])["amount"].sum().unstack(fill_value=0)
    )

    # Convert PeriodIndex to string for Plotly compatibility
    x_labels = monthly_totals.index.astype(str)

    # Align category colors using shared label logic
    base_labels = [f" {label} " for label in monthly_totals.columns]
    bar_colors = assign_colors_by_base_label(base_labels, COLOR_PALETTE)
    color_map = dict(zip(monthly_totals.columns, bar_colors))

    # Build stacked bar chart using graph_objects
    fig = go.Figure()

    for category in monthly_totals.columns:
        fig.add_bar(
            x=x_labels,
            y=monthly_totals[category],
            name=category,
            marker_color=color_map[category],
            hovertemplate=f"{category}: $%{{y:,.0f}}<extra></extra>",
        )

    # Add total monthly withdrawal trace
    monthly_sums = monthly_totals.sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=monthly_sums,
            mode="markers",
            marker=dict(symbol="line-ew-open", color="black"),
            name="Total Monthly Withdrawal",
            hovertemplate="Total: $%{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"Trial {trial+1:04d} | Monthly Expenses",
        yaxis_tickformat="$,.0f",
        barmode="stack",
        template="plotly_white",
        hovermode="x unified",
        hoverlabel=dict(align="left"),
    )

    if show:
        fig.show()
    if save:
        csv_path = f"{export_path}{trial+1:04d}_monthly_expenses_{ts}.csv"
        html_path = f"{export_path}{trial+1:04d}_monthly_expenses_{ts}.html"
        monthly_totals.to_csv(csv_path, index_label="Month")
        fig.write_html(html_path)
        logging.debug(f"Monthly cash withdrawals saved to {html_path}")


def plot_example_transactions(
    flow_df: pd.DataFrame,
    trial: int,
    show: bool = True,
    save: bool = False,
    export_path: str = "export/",
    ts: str = "",
):
    df = flow_df.copy()
    df["date"] = df["date"].dt.to_timestamp()
    df["year"] = df["date"].dt.year

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
                ],
                label=str(year),
            )
        )

    fig.update_layout(
        title={"text": f"Trial {trial+1:04d} | {years[0]} Transactions"},
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
        fig.write_html(f"{export_path}{trial+1:04d}_transactions_{ts}.html")
        flow_df.to_csv(f"{export_path}{trial+1:04d}_transactions_{ts}.csv")


def plot_example_transactions_in_context(
    trial: int,
    forecast_df: pd.DataFrame,
    flow_df: pd.DataFrame,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    forecast_df = coerce_month_column(forecast_df.copy())
    forecast_df = forecast_df[forecast_df["Month"].dt.month == 12].sort_values("Month")

    bucket_names = [col for col in forecast_df.columns if col != "Month"]
    years = forecast_df["Month"].dt.year.tolist()
    transitions = [(y - 1, y) for y in years]

    flow_df = flow_df.copy()
    flow_df["date"] = flow_df["date"].dt.to_timestamp()
    flow_df["year"] = flow_df["date"].dt.year

    sankey_traces = []
    for y0, y1 in transitions:
        target_month = pd.Period(f"{y1}-12", freq="M").to_timestamp("M")
        bal_end = forecast_df.loc[forecast_df["Month"] == target_month].iloc[0]
        flows_y = flow_df[flow_df["year"] == y1].copy()
        agg = (
            flows_y.groupby(["source", "target", "type"])["amount"].sum().reset_index()
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
                            "text": f"Trial {trial+1:04d} | {y1} Transactions In-Context"
                        }
                    },
                ],
                label=y1,
            )
        )

    sliders = [
        dict(active=0, currentvalue={"prefix": "Period: "}, pad={"t": 50}, steps=steps)
    ]
    fig.update_layout(
        title={
            "text": f"Trial {trial+1:04d} | {transitions[0][1]} Transactions In-Context",
        },
        sliders=sliders,
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if show:
        fig.show()
    if save:
        fig.write_html(f"{export_path}{trial+1:04d}_transactions_in_context_{ts}.html")


def plot_example_forecast(
    trial: int,
    hist_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    dob: str,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves the bucket‐by‐bucket forecast for one trial.
    """
    hist_df = coerce_month_column(hist_df.copy())
    cols_to_sum = [col for col in hist_df.columns if col != "Month"]
    hist_df["Net Worth"] = hist_df[cols_to_sum].sum(axis=1)

    forecast_df = coerce_month_column(forecast_df.copy())
    full_df = pd.concat([hist_df, forecast_df], ignore_index=True)

    cols = list(full_df.columns)
    cols.insert(1, cols.pop(cols.index("Net Worth")))
    full_df = full_df[cols]
    full_df["Net Worth"] = full_df["Net Worth"].astype(int)

    title = f"Trial {trial+1:04d} | Forecast by Bucket"

    # Extract bucket labels (excluding Month)
    bucket_labels = [col for col in full_df.columns if col != "Month"]

    # Assign colors using base_label logic
    color_list = assign_colors_by_base_label(bucket_labels, COLOR_PALETTE)
    line_colors = dict(zip(bucket_labels, color_list))

    # Age trace
    dob_period = pd.Period(dob, freq="M")
    month_periods = pd.to_datetime(full_df["Month"]).dt.to_period("M")
    month_offsets = month_periods.astype("int64")
    dob_offset = dob_period.ordinal
    age_years = (month_offsets - dob_offset) / 12

    traces = [
        go.Scatter(
            x=full_df["Month"],
            y=age_years,
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
            share_data = [100.0] * len(full_df)
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
                x=full_df["Month"],
                y=full_df[col],
                mode="lines",
                name=col,
                line=dict(
                    color="gray" if col == "Net Worth" else line_colors[col],
                    dash="dot" if col == "Net Worth" else None,
                ),
                customdata=share_data,
                hovertemplate=(
                    f"{col}: %{{y:$,.0f}} (%{{customdata:.0f}}%)<extra></extra>"
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
        prefix = f"{export_path}{trial+1:04d}"
        bucket_csv = f"{prefix}_forecast_{ts}.csv"
        html = f"{prefix}_forecast_{ts}.html"

        full_df.to_csv(bucket_csv, index=False)
        fig.write_html(html)
        logging.debug(f"Trial {trial+1:04d} | Saved sample forecast to {html}")


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
    hist_df = coerce_month_column(hist_df.copy())
    total_net_worth = pd.DataFrame(
        {
            "Month": hist_df["Month"],
            "Total Net Worth": hist_df.drop("Month", axis=1).sum(axis=1),
        }
    )

    monthly_net_worth_gain_loss = pd.DataFrame(
        {
            "Month": hist_df["Month"],
            "Net Worth Gain": total_net_worth["Total Net Worth"].pct_change().fillna(0),
        }
    )
    annual_net_worth_gain_loss = pd.DataFrame(
        {
            "Month": hist_df["Month"],
            "Net Worth Gain": total_net_worth["Total Net Worth"]
            .pct_change(12)
            .fillna(0),
        }
    )
    fig = go.Figure(
        data=[
            go.Scatter(
                x=total_net_worth["Month"],
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
                x=monthly_net_worth_gain_loss["Month"],
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
                x=annual_net_worth_gain_loss["Month"],
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
    df["Month"] = pd.to_datetime(df["Month"]).dt.to_period("M").dt.to_timestamp("M")
    df.set_index("Month", inplace=True)

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
            x=monthly_pct["Month"],
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
        dates = monthly_pct["Month"]

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


def plot_mc_monthly_returns(
    mc_monthly_returns_df: pd.DataFrame,
    sim_examples: np.ndarray,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves a scatter plot of monthly return distributions for each asset class,
    showing scenario, trial number, inflation rate, and modifier in hover info.
    """
    df = coerce_month_column(mc_monthly_returns_df.copy())

    if "monthly_returns" not in df.columns or "inflation_rate" not in df.columns:
        logging.warning("monthly_returns or inflation_rate missing from DataFrame.")
        return

    sim_size = df["Trial"].nunique()
    df["MonthStr"] = df["Month"].dt.strftime("%Y-%m")

    # Discover asset classes from first row
    asset_classes = [
        a
        for a in list(df["monthly_returns"].iloc[0].keys())
        if a not in ["Cash", "Vehicles"]
    ]
    scenario_color_map = {"Low": "#1f77b4", "Average": "#2ca02c", "High": "#d62728"}

    for asset_class in asset_classes:
        df_asset = df.copy()
        df_asset["Scenario"] = df_asset["monthly_returns"].apply(
            lambda d: d[asset_class]["scenario"]
        )
        df_asset["Rate"] = df_asset["monthly_returns"].apply(
            lambda d: d[asset_class]["rate"]
        )
        df_asset["Inflation"] = df_asset["inflation_rate"]

        fig = go.Figure()

        for scenario, color in scenario_color_map.items():
            scenario_df = df_asset[df_asset["Scenario"] == scenario]
            fig.add_trace(
                go.Scatter(
                    x=scenario_df["MonthStr"],
                    y=scenario_df["Rate"],
                    mode="markers",
                    marker=dict(color=color, size=6, opacity=0.6),
                    name=scenario,
                    text=(scenario_df["Trial"] + 1).map("{:04.0f}".format),
                    customdata=scenario_df[["Inflation"]],
                    hovertemplate=(
                        "Month: %{x}<br>"
                        "Trial: %{text}<br>"
                        "Inflation: %{customdata[0]:.2%}<br>"
                        f"Scenario: {scenario}<br>"
                        "Return: %{y:.2%}<extra></extra>"
                    ),
                )
            )

        confidence_color = (
            "green" if sim_size >= 1000 else "blue" if sim_size >= 100 else "red"
        )

        title = (
            f"Monthly Return Distribution for {asset_class}"
            f" | <span style='color: {confidence_color}'>{sim_size} Trials</span>"
        )

        fig.update_layout(
            title=title,
            title_x=0.5,
            template="plotly_white",
            hoverlabel=dict(align="left"),
            hovermode="closest",
            showlegend=False,
            yaxis=dict(tickformat=".2%"),
        )

        if show:
            fig.show()
        if save:
            csv_path = f"{export_path}mc_monthly_returns_{ts}.csv"
            html_path = f"{export_path}mc_monthly_returns_{asset_class}_{ts}.html"
            df.to_csv(csv_path, index=False)
            fig.write_html(html_path)
            logging.debug(f"Monthly returns for {asset_class} saved to {html_path}")


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
    sim_size = len(mc_networth_df.columns)
    mc_networth_df.index = pd.PeriodIndex(mc_networth_df.index, freq="M")

    # Compute percentiles across trials
    pct_df = mc_networth_df.quantile([0.15, 0.5, 0.85], axis=1).T
    pct_df.columns = ["p15", "median", "p85"]
    pct_df["mean"] = pct_df.mean(axis=1)
    pct_df.index = mc_networth_df.index  # align index

    # Age logic
    dob_period = pd.Period(dob, freq="M")
    eol_period = pd.Period(eol, freq="M")
    eol_age = (eol_period - dob_period).n // 12
    dob_period = pd.Period(dob, freq="M")
    ages = mc_networth_df.index.map(lambda p: (p - dob_period).n // 12).tolist()

    def get_pct_at_age(age):
        target_period = dob_period + age * 12
        mask = mc_networth_df.index == target_period
        if mask.any():
            row = mc_networth_df[mask].iloc[0]
            return (row > 0).mean()
        else:
            return np.nan

    age_metrics = {
        "age_minus_20": eol_age - 20,
        "age_minus_20_pct": get_pct_at_age(eol_age - 20),
        "age_minus_10": eol_age - 10,
        "age_minus_10_pct": get_pct_at_age(eol_age - 10),
        "age_end": eol_age,
        "age_end_pct": get_pct_at_age(eol_age),
    }

    # Liquidation metrics
    dob_year = dob_period.year
    min_liquidation_age = (
        summary["Minimum Property Liquidation Year"] - dob_year
        if summary["Minimum Property Liquidation Year"] is not None
        else None
    )
    avg_liquidation_age = (
        int(
            sum(date.year for date in summary["Property Liquidation Months"])
            / len(summary["Property Liquidation Months"])
            - dob_year
        )
        if len(summary["Property Liquidation Months"]) > 0
        else None
    )
    max_liquidation_age = (
        summary["Maximum Property Liquidation Year"] - dob_year
        if summary["Maximum Property Liquidation Year"] is not None
        else None
    )
    pct_liquidation = summary["Property Liquidations"] / sim_size

    fig = go.Figure()

    # Invisible age trace for hover
    fig.add_trace(
        go.Scatter(
            x=mc_networth_df.index.to_timestamp(),
            y=pct_df["median"],
            customdata=ages,
            mode="markers",
            marker=dict(size=0, opacity=0),
            line=dict(width=0),
            showlegend=False,
            hovertemplate="Age %{customdata:.0f}<extra></extra>",
        )
    )

    # Monte Carlo examples
    final_values = mc_networth_df.iloc[-1]
    lower_bound = final_values.quantile(0.05)
    upper_bound = final_values.quantile(0.95)
    filtered_cols = [
        col
        for col in mc_networth_df.columns
        if lower_bound <= final_values[col] <= upper_bound
    ]

    for col in filtered_cols:
        is_example = col in sim_examples
        color, opacity, width = ("purple", 0.6, 2) if is_example else ("gray", 0.2, 1)
        hover_kwargs = (
            {"hovertemplate": f"Trial {int(col)+1:04d}: %{{y:$,.0f}}<extra></extra>"}
            if is_example
            else {"hoverinfo": "skip"}
        )

        fig.add_trace(
            go.Scatter(
                x=mc_networth_df.index.to_timestamp(),
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
    timestamp_index = mc_networth_df.index.to_timestamp()
    fig.add_trace(
        make_trace(
            "85th Percentile",
            timestamp_index,
            pct_df["p85"],
            color="blue",
            width=1,
        )
    )
    fig.add_trace(
        make_trace("Median", timestamp_index, pct_df["median"], color="green", width=2)
    )
    fig.add_trace(
        make_trace(
            "15th Percentile",
            timestamp_index,
            pct_df["p15"],
            color="blue",
            width=1,
        )
    )

    # Annotations at EOL
    eol_ts = pd.Period(eol, freq="M").to_timestamp()
    if eol_ts in timestamp_index:
        for col, label, color in [
            ("p15", "15th Percentile", "blue"),
            ("median", "Median", "green"),
            ("p85", "85th Percentile", "blue"),
        ]:
            y = pct_df.loc[eol_ts, col]
            fig.add_annotation(
                x=eol_ts,
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

    # Title logic
    confidence_color = (
        "green" if sim_size >= 1000 else "blue" if sim_size >= 100 else "red"
    )

    def getPNWColor(value):
        return "green" if value > 0.85 else "blue" if value > 0.75 else "red"

    def getPropertyLiquidationColor(value):
        return "green" if value < 0.25 else "blue" if value < 0.5 else "red"

    def getAgeColor(value):
        return (
            "green"
            if value is None
            else "green" if value > 75 else "blue" if value > 65 else "red"
        )

    title = (
        f"Monte Carlo Net Worth Forecast"
        f" | <span style='color: {confidence_color}'>{sim_size} Trials</span>"
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
        mc_networth_df.to_csv(f"{export_path}mc_networth_{ts}.csv", index_label="Month")
        html = f"{export_path}mc_networth_{ts}.html"
        fig.write_html(html)
        logging.debug(f"Monte Carlo files saved to {html}")


def plot_mc_tax_totals(
    mc_tax_df: pd.DataFrame,
    sim_examples: np.ndarray,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves a bar chart of total taxes per trial.
    """
    sim_size = len(mc_tax_df.columns)
    mc_tax_df = mc_tax_df.copy()
    mc_tax_df.index = pd.Index(mc_tax_df.index).astype(int)
    total_taxes = mc_tax_df.sum()

    p15 = total_taxes.quantile(0.15)
    median = total_taxes.median()
    p85 = total_taxes.quantile(0.85)

    # Exclude the top 10% of total taxes from the chart
    threshold = total_taxes.quantile(0.95)
    total_taxes = total_taxes[total_taxes <= threshold]
    trial_labels = [f"Trial {int(trial)+1:04d}" for trial in total_taxes.index]
    bar_colors = [
        "purple" if trial in sim_examples else "lightgray"
        for trial in total_taxes.index
    ]
    hover_texts = [f"Total Taxes: ${total:,.0f}" for total in total_taxes.values]

    fig = go.Figure(
        go.Bar(
            x=trial_labels,
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
            x=trial_labels,
            y=[p85] * sim_size,
            mode="lines",
            name="85th Percentile",
            line=dict(color="blue", dash="dash"),
            hovertemplate="85th Percentile: %{y:$,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trial_labels,
            y=[median] * sim_size,
            mode="lines",
            name="Median",
            line=dict(color="green", width=2),
            hovertemplate="Median: %{y:$,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trial_labels,
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
            x=trial_labels[-1],
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
        f"Total Tax Burden per Trial"
        f" | <span style='color: {confidence_color}'>{sim_size} Trials</span>"
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
        total_taxes.to_csv(f"{export_path}mc_tax_totals_{ts}.csv", index_label="Trial")
        html = f"{export_path}mc_tax_totals_{ts}.html"
        fig.write_html(html)
        logging.debug(f"Monte Carlo tax totals saved to {html}")


def plot_mc_taxable_balances(
    mc_taxable_df: pd.DataFrame,
    sim_examples: np.ndarray,
    sepp_end_month: str,
    ts: str,
    show: bool,
    save: bool,
    export_path: str = "export/",
):
    """
    Renders and optionally saves a bar chart of Taxable balances in Jan 2035 per trial.
    """
    sim_size = len(mc_taxable_df)
    mc_taxable_df = mc_taxable_df.copy()
    mc_taxable_df.index = pd.Index(mc_taxable_df.index).astype(int)
    taxable_balances = mc_taxable_df["Taxable"]

    p15 = taxable_balances.quantile(0.15)
    median = taxable_balances.median()
    p85 = taxable_balances.quantile(0.85)

    trial_labels = [f"Trial {int(trial)+1:04d}" for trial in taxable_balances.index]
    bar_colors = [
        "purple" if trial in sim_examples else "lightgray"
        for trial in taxable_balances.index
    ]
    hover_texts = [f"Taxable Balance: ${val:,.0f}" for val in taxable_balances.values]

    percent_positive = 100 * (mc_taxable_df["Taxable"] > 0).sum() / len(mc_taxable_df)

    def get_color(value):
        return "green" if value > 84 else "blue" if value > 74 else "red"

    confidence_color = (
        "green" if sim_size >= 1000 else "blue" if sim_size >= 100 else "red"
    )

    fig = go.Figure(
        go.Bar(
            x=trial_labels,
            y=taxable_balances.values,
            marker_color=bar_colors,
            opacity=0.5,
            hovertext=hover_texts,
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )

    # Reference lines
    fig.add_trace(
        go.Scatter(
            x=trial_labels,
            y=[p85] * len(trial_labels),
            mode="lines",
            name="85th Percentile",
            line=dict(color="blue", dash="dash"),
            hovertemplate="85th Percentile: %{y:$,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trial_labels,
            y=[median] * len(trial_labels),
            mode="lines",
            name="Median",
            line=dict(color="green", width=2),
            hovertemplate="Median: %{y:$,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trial_labels,
            y=[p15] * len(trial_labels),
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
            x=trial_labels[-1],
            y=y,
            text=f" {label}: ${y:,.0f} ",
            showarrow=False,
            font=dict(color=color),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=color,
            borderwidth=1,
        )

    fig.update_layout(
        title=f"Taxable Balance {sepp_end_month} | <span style='color: {confidence_color}'>{sim_size} Trials</span>"
        f"<br><span style='color: {get_color(percent_positive)}'>{percent_positive:.1f}% Positive Taxable Balance</span>",
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
        csv_path = f"{export_path}mc_taxable_balances_{ts}.csv"
        html_path = f"{export_path}mc_taxable_balances_{ts}.html"
        taxable_balances.to_csv(csv_path, index_label="Trial")
        fig.write_html(html_path)
        logging.debug(f"Monte Carlo taxable balances saved to {html_path}")
