# 🔄 Simulation Logic

Nomad Wealth’s simulation engine models financial flows month by month, applying transactions, policies, market returns, and taxes.  
This document explains the **sequencing logic** of the forecast loop, how trials are staged and executed, and how results are aggregated and visualized.

---

## 🧩 Relationship to Architecture

The simulation logic is the **operational core** of the architecture described in [Architecture Overview](architecture.md).  
Where architecture explains the system’s design principles and modular components, this page focuses on the **step‑by‑step execution flow** inside the `ForecastEngine` and `app.py`.

---

## 📂 Staging Phase

Before any trial runs, the system prepares inputs and components:

1. **Load Configuration (`stage_load`)**
    - Loads JSON configuration and CSV inputs.
    - Requires `buckets.json` under `json_data["buckets"]`.
    - Returns `(json_data, dfs)`.

2. **Prepare Timeframes (`stage_prepare_timeframes`)**
    - Converts `Month` column to `pandas.Period("M")`.
    - Adds `Tax Collection` column to historical balances.
    - Builds `future_df` with monthly periods until End Month.
    - Returns `(hist_df, future_df)`.

3. **Initialize Components (`stage_init_components`)**
    - Builds buckets from config (`seed_buckets_from_config`).
    - Creates `ThresholdRefillPolicy` with refill and liquidation rules.
    - Seeds inflation generator (`InflationGenerator`) and applies modifiers from `inflation_rates.json`.
    - Initializes `TaxCalculator` with `tax_brackets.json` + inflation adjustments.
    - Creates `MarketGains` using `gain_table.json` + `inflation_thresholds.json`.
    - Instantiates transactions from multiple sources:
        - **Fixed Transactions** → `fixed.csv`
        - **Recurring Transactions** → `recurring.csv`
        - **Property** → mortgage, maintenance, rent flows (`policies.json`)
        - **Rent** → property rental income (`policies.json`)
        - **RMD** → required minimum distributions (`policies.json`)
        - **Unemployment** → temporary income replacement (`policies.json`)
        - **Salary** → wages, bonuses, merit increases (`policies.json`)
        - **Social Security** → benefit profiles (`policies.json`)
    - Returns `(buckets, refill_policy, tax_calc, market_gains, base_inflation, rule_txns, policy_txns)`.

---

## 📅 Monthly Forecast Loop

Each month in the simulation proceeds through the following steps:

1. **Apply Transactions**
    - Fixed transactions from `fixed.csv` (e.g., tuition, travel).
    - Recurring transactions from `recurring.csv` (e.g., insurance, food, utilities).
    - Salary, Social Security, Roth conversions, unemployment, property flows.

2. **Trigger Refill Policies**
    - ThresholdRefillPolicy checks balances and taps sources.
    - Retirement‑age gating prevents early withdrawals.
    - Emergency liquidation if Cash < threshold.

3. **Apply Market Returns**
    - MarketGains samples inflation‑adjusted returns.
    - Asset classes update bucket balances.

4. **Tax Collection Drip**
    - Monthly withholding moves funds into Tax Collection bucket.

5. **Snapshot Balances**
    - Records bucket balances and flow logs for audit clarity.

6. **Year‑End Settlement (January)**
    - Applies ordinary income, capital gains, and penalty taxes.
    - Withdraws taxes from Cash; refills if negative.
    - Rolls forward estimates into next year.

---

## 🎲 Trial Execution

1. **`run_one_trial()`**

    - Seeds RNG with trial index.
    - Calls `stage_init_components()` to build buckets, policies, inflation, tax calculator, and transactions.
    - Wires `FlowTracker` into all buckets for audit clarity.
    - Runs `ForecastEngine` with monthly loop.
    - Returns `(forecast_df, taxes_df, monthly_returns_df, flow_df)`.

1. **`run_simulation()`**

    - Wrapper around `run_one_trial`.
    - Injects trial index into results.
    - Returns `(trial, forecast_df, taxes_df, monthly_returns_df, flow_df)`.

1. **Parallel Execution**
    - Trials are executed in parallel using `ProcessPoolExecutor`.
    - Results aggregated into dictionaries keyed by trial index.

---

## 📊 Aggregation Phase

After all trials complete:

- **Net Worth DataFrame (`mc_networth_df`)** → rows = months, columns = trials.
- **Tax DataFrame (`mc_tax_df`)** → multi‑indexed by trial and year.
- **Taxable Balances (`mc_taxable_df`)** → balances at SEPP end month.
- **Monthly Returns (`mc_monthly_returns_df`)** → consolidated across trials.
- **Summary Tracking** → property liquidation events and taxable balances logged for audit clarity.

---

## 📈 Visualization Integration

The aggregated results feed into the visualization layer:

- **Historical Charts** → bucket gains, net worth trajectory.
- **Per‑Trial Charts** → monthly expenses, transactions, taxes, forecasts.
- **Aggregate Monte Carlo Charts** → monthly returns, taxable balances, totals/rates, net worth distribution.
- All charts are exportable to HTML and CSV with timestamped filenames.

---

## 📝 ForecastEngine Audit Notes

- ForecastEngine orchestrates **monthly simulation flows**, integrating buckets, transactions, market gains, refills, liquidations, and taxes.
- All results are **auditable via structured records**: monthly snapshots, tax logs, and return records.
- Tax inputs (salary, unemployment, Social Security, withdrawals, gains, penalties, etc.) are consistently aggregated through structured getters.
- Yearly tax logs ensure reproducibility of IRS‑aligned categories (ordinary income, capital gains, Social Security, Roth conversions, penalties).
- Tax estimation and withholding logic provide **ongoing audit clarity**, spreading liabilities across months and reconciling at year‑end.
- SEPP withdrawals, marketplace premiums, and IRMAA surcharges are applied in compliance with IRS and SSA rules.
- Roth conversion logic enforces **policy‑driven thresholds** (age cutoffs, source balances, max tax rates) and calculates headroom before applying conversions.
- Year‑end reconciliation finalizes Roth conversions, computes tax liabilities, and records withdrawal rates and portfolio values.
- Monthly snapshots preserve bucket balances for downstream visualization and audit.

**Specialized audit notes:**

- **SEPP logic**: IRS amortization method ensures penalty‑exempt withdrawals.
- **Marketplace premiums**: capped at 8.5% of prior MAGI, withdrawn from Cash.
- **IRMAA premiums**: surcharge brackets applied based on prior MAGI, doubled for MFJ.
- **Roth conversions**: ordinary income withdrawals, penalty‑exempt, applied only within configured headroom.
- **Year‑end reconciliation**: ensures taxes are paid from Tax Collection first, then Cash, with leftover handling logged.

---

## 📚 Related Pages

- [Architecture Overview](architecture.md) → system design and modular components
- [Configuration Reference](configuration.md) → JSON and CSV inputs
- [Visualization Guide](visualization.md) → charts and exports
- [Usage Guide](usage.md) → workflow and output files
