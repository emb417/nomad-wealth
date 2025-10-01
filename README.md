# Inflation Forecasting & Portfolio Projections

A Python framework for simulating long-term portfolio outcomes under inflation-adjusted market conditions. It merges historical balances with forward-looking cash flows, applies refill policies and tax-aware logic, and generates both deterministic and Monte Carlo forecasts with interactive charts.

---

## 🔧 Features

- Fixed & recurring transaction ingestion from CSV files
- Threshold-driven refill policies with retirement age-based gating to eliminate penalties
- Roth conversions modeled independently from refill logic
- Inflation-aware market return simulation via gain tables
- Monte Carlo sampling with percentile bands and probability metrics
- Tax-aware withdrawals (ordinary vs. capital gains)
- Interactive Plotly charts and CSV exports
- Configurable logging and emergency cash alerts

---

## 🚀 Quick Start

1. Clone and install dependencies:

   ```bash
   git clone https://github.com/emb417/nomad-wealth
   cd nomad-wealth
   pip install -r requirements.txt
   ```

2. Configure your profile and rules in `config/` (see `config/README.md`)
3. Prepare historical balances and transaction data in `data/` (see `data/README.md`)
4. Review flags in `src/app.py`:
   - `SIMS`, `SIMS_SAMPLES`
   - `SHOW_NETWORTH_CHART`, `SAVE_NETWORTH_CHART`
   - `SHOW_SIMS_SAMPLES`, `SAVE_SIMS_SAMPLES`
5. Run the simulation:

   ```bash
   python src/app.py
   ```

---

## 📁 Folder Structure

| Folder    | Description                                                            |
| --------- | ---------------------------------------------------------------------- |
| `config/` | JSON definitions for buckets, thresholds, gain tables, inflation rules |
| `data/`   | CSVs for historical balances, fixed and recurring transactions         |
| `src/`    | Application code (see [`src/README.md`](src/README.md))                |
| `export/` | Generated outputs: Monte Carlo charts, sample forecasts, tax records   |

---

## 📈 Outputs

- `mc_networth_<timestamp>.html`: Monte Carlo net worth chart with:
  - All simulation paths
  - Median, 15th, and 85th percentile lines
  - Probability of positive net worth at key ages
- `####_buckets_forecast_<timestamp>.csv`: Bucket balances for sampled simulations
- `####_taxes_forecast_<timestamp>.csv`: Year-end tax breakdowns
- `####_buckets_forecast_<timestamp>.html`: Interactive chart of bucket balances

See [`export/README.md`](export/README.md) for details.

---

## 🧠 Simulation Logic

- Historical balances are merged with forward projections
- Each month applies:
  1. Core transactions (fixed, recurring, salary, SS, Roth)
  2. Refill logic (age-gated for tax-deferred sources)
  3. Market returns via inflation-aware gain sampling
  4. Tax computation and cash withdrawal
  5. Balance snapshot and tax logging
- Year-end taxes are paid in January of the following year

---

## 🛣️ Roadmap

- Handle Liquidation event by adding "rent" or "lease" to expenses
- Handle Required Minimium Distributions
- Visualize historical totals using combo line (net worth) and bar (periodic gains) chart
- Visualize historical bucket balances using line (balance) and bar (periodic gains) charts
- Visualize annual income sources using stacked bar chart
- Visualize annual expenses using stacked bar chart
- Visualize comparison of income to expenses
- Visualize cash flows using multi-level sankey chart
- Visualize tax liabilities per year per bucket
- UI to enter balances and manage individual accounts and assign them to buckets
- UI for tuning configurations: profile, holdings, gains, inflation, policies
- UI for managing future transactions: fixed and recurring
- UI for managing income sources: unemployement, salary, bonuses, social security
- Include contributions to 401k as well as tax implications
- Handle unemployment and delayed salary expectations
- Handle self-employment taxes
- Handle self and spousal IRA contributions
- Handle specified equities with current market values and forecasted gains
- Support various vesting schedules and maturity dates
- Scenario tagging and multi-profile support
- Interactive forecast comparison across scenarios
- Support "smile" expenses curve
- Category-specific inflation for expenses

---

_Last updated:_ 2025-09-23
