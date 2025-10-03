# Inflation Forecasting & Portfolio Projections

This Python framework offers a complete, policy-driven engine for Monte Carlo simulation of portfolio balances, cash flows, and tax liabilities. It ingests your historical balances and transactions to seed an auditable bucket model, then applies configurable refill rules, retirement-age gating, inflation-aware market returns, and tax calculations to project thousands of possible futures. Interactive charts and CSV exports turn these complex simulations into clear, actionable insights for smarter financial planning.

---

## Why This Framework Matters

- Scenario-driven forecasts that capture uncertainty in returns, cash flows, and tax events
- Policy-first architecture: define thresholds, refill rules, and liquidation order in JSON
- Tax-aware modeling that handles ordinary income, capital gains, early-withdrawal penalties, and Roth conversions
- Inflation-adjusted gain sampling from user-supplied tables
- Auditable, bucket-level transaction engine for transparent cash-flow tracking
- Interactive Plotly charts and CSV outputs for deep analysis and reporting

---

## 🔧 Features

- Fixed and recurring transaction ingestion from CSV
- Inflation-aware market return simulation via user-defined gain tables
- Threshold-driven refill policies with retirement-age gating to avoid penalties
- Configurable emergency liquidation hierarchy across buckets
- Automated recurring rental transactions after property liquidation event
- Tax-aware withdrawals distinguishing ordinary income, capital gains, and penalties
- Independent Roth conversion scheduling
- Monte Carlo sampling with percentile bands and probability metrics
- Interactive Plotly visualizations and CSV exports of net worth, bucket balances, and tax breakdowns

---

## 🚀 Quick Start

1. Clone repo:

   ```bash
   git clone https://github.com/emb417/nomad-wealth
   ```

   - use a virtual environment to install dependencies.
   - Or install dependencies manually:

   ```bash
   cd nomad-wealth
   pip install -r requirements.txt
   ```

2. Configure profiles and policies in `config/` (see `config/README.md`)
3. Supply historical balances and transactions in `data/` (see `data/README.md`)
4. Adjust flags in `src/app.py`:
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
| `data/`   | CSVs for historical balances and transactions                          |
| `src/`    | Application code (see [`src/README.md`](src/README.md))                |
| `export/` | Outputs: Monte Carlo charts, sample forecasts, tax records             |

---

## 📈 Outputs

- `mc_networth_<timestamp>.html`: Monte Carlo net worth chart with percentile lines and probability metrics
- `####_buckets_forecast_<timestamp>.csv`: Bucket balance trajectories for sampled simulations
- `####_taxes_forecast_<timestamp>.csv`: Year-end tax breakdowns
- `####_buckets_forecast_<timestamp>.html`: Interactive bucket balance visualizations

See [`export/README.md`](export/README.md) for details.

---

## 🧠 Simulation Logic

Each month the engine sequentially applies:

1. Core transactions (fixed, recurring, rental, salary, SS, Roth)
2. Threshold-based refills (age-gated for tax-deferred sources)
3. Market returns via inflation-aware gain sampling
4. Emergency liquidation when cash falls below threshold, bypassing age-gating if needed (i.e. tax-penalized)
5. Monthly tax drip and tax collection
6. Balance snapshot and tax aggregation
7. January year-end tax payment and penalty integration

---

## 🛣️ Roadmap

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
- Handle Required Minimium Distributions programatically instead of using date-based policy with static amounts
- Handle Health Savings Account spending programatically, instead of using date-based recurring transactions
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

_Last updated:_ 2025-10-02
