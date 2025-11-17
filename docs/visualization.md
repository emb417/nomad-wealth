# 📊 Visualization Guide

Nomad Wealth includes a visualization layer that generates interactive Plotly charts and CSV exports.  
These charts provide transparency, audit clarity, and intuitive insight into both historical data and Monte Carlo simulations.

---

## 📜 Historical Charts

### `plot_historical_bucket_gains()`

- **Purpose:** Shows monthly gain/loss trends for each bucket.
- **Why it matters:** Highlights which asset classes contributed to net worth changes over time.

### `plot_historical_balance()`

- **Purpose:** Net worth line chart + gain/loss bar chart.
- **Why it matters:** Provides a clear view of overall net worth trajectory and periods of increase/decrease.

---

## 🧾 Example Trial Charts

Generated only for trials listed in `sim_examples`.

### `plot_example_monthly_expenses()`

- **Purpose:** Visualizes monthly expense flows for a sample simulation.
- **Why it matters:** Helps identify spending patterns and stress points.

### `plot_example_transactions()`

- **Purpose:** Shows transactions for a given year in a sample simulation.
- **Why it matters:** Useful for tracing specific flows and verifying transaction logic.

### `plot_example_transactions_in_context()`

- **Purpose:** Displays transactions alongside bucket balances.
- **Why it matters:** Provides context for how transactions affect overall balances.

### `plot_example_income_taxes()`

- **Purpose:** Annual tax breakdown for a sample simulation.
- **Why it matters:** Clarifies how income, withdrawals, and gains translate into tax liabilities.

### `plot_example_forecast()`

- **Purpose:** Forecasted bucket balances over time for a sample simulation.
- **Why it matters:** Shows long‑term sustainability of asset allocations.

---

## 🎲 Monte Carlo Charts

Generated across all trials.

### `plot_mc_monthly_returns()`

- **Purpose:** Distribution of monthly returns across simulations.
- **Why it matters:** Quantifies volatility and return variability.

### `plot_mc_taxable_balances()`

- **Purpose:** Taxable balances at SEPP end month.
- **Why it matters:** Surfaces liquidity available in taxable accounts at critical milestones.

### `plot_mc_totals_and_rates()`

- **Purpose:** Total taxes, effective tax rates, and withdrawal rates across simulations.
- **Why it matters:** Provides audit clarity on tax burden and withdrawal sustainability.

### `plot_mc_networth()`

- **Purpose:** Net worth distribution with median trajectory and 15th/85th percentile bands.
- **Why it matters:** Summarizes overall financial sufficiency and risk bounds.

---

## ⚙️ Flags & Modes

- **`SHOW_*` flags** → control whether charts are displayed interactively.
- **`SAVE_*` flags** → control whether charts are exported to HTML/CSV.
- **`DETAILED_MODE`** → overrides show/save behavior for full audit clarity.

---

## 📝 Visualization Audit Notes

- Visualization helpers ensure **consistent labeling, coloring, and axis formatting** across all charts.
- Percentile overlays (p15, median, p85) provide clear scenario comparison and reproducibility across trials.
- Dual y‑axes allow simultaneous display of dollar values and percentage rates where relevant.
- Month coercion ensures reproducibility in CSV and HTML outputs.
- All charts are designed for **audit clarity**, with explicit labels, hover text, and reference lines.
- CSV/HTML exports preserve both tabular and interactive views, ensuring reproducibility and presentation quality.
- Logging records export paths for traceability.

**Specialized chart notes:**

- **Sankey diagrams**: visualize net flows between buckets, normalize gains/losses, order nodes by volume, and use color coding to distinguish deposits, withdrawals, transfers, gains, and losses. Sliders allow year‑by‑year inspection.
- **Transactions in context**: align flows with year‑end balances for audit clarity.
- **Forecast charts**: provide bucket‑level visibility, net worth trajectory, and age overlays for interpretability.
- **Historical charts**: deliver retrospective audit clarity of net worth and bucket‑level performance.
- **Monte Carlo charts**: visualize distributions of returns, net worth, taxes, withdrawals, and taxable balances across scenarios and trials.
  - Net worth charts highlight probabilistic retirement outcomes, example trials, age metrics, and property liquidation statistics.
  - Totals and rates charts show distributional clarity of tax burdens and withdrawal rates.
  - Taxable balance charts highlight sustainability of taxable accounts at critical milestones (e.g., SEPP end).
  - Scenario color coding (green/red for gains/losses, scenario colors for returns) ensures interpretability.
  - Highlighted trials allow auditors to trace specific scenarios.

---

## 📚 Related Pages

- [Usage Guide](usage.md) → explains workflow and output files
- [Architecture Overview](architecture.md) → system design and visualization integration
- [Simulation Logic](simulation_logic.md) → monthly loop and aggregation steps
