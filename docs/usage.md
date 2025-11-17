# 🚀 Usage Guide

This guide explains how to run Nomad Wealth simulations, control output behavior, and interpret results.

---

## ▶️ Running the Simulation

1. **Navigate to the project root**  
   Ensure you are in the directory containing `src/app.py`.

2. **Run the entry point**

   ```bash
   python src/app.py
   ```

   This executes the `main()` method, which:

   - Loads JSON and CSV configuration files.
   - Prepares historical and future timeframes.
   - Runs Monte Carlo trials via `forecast_engine.py` in parallel.
   - Aggregates results into DataFrames.
   - Generates interactive charts and CSV/HTML exports.

3. **Check the `export/` directory**  
   All outputs (HTML charts, CSVs) are saved here with timestamped filenames.

---

## ⚙️ Controlling Behavior

Simulation behavior is controlled by flags in `app.py`:

1. **Simulation Size**
    - `SIM_SIZE` → number of Monte Carlo trials.

1. **Chart Display**
    - `SHOW_*` flags → control whether charts open interactively.
    - Examples: `SHOW_NETWORTH_CHART`, `SHOW_EXAMPLES`, `SHOW_HISTORICAL`.

1. **Chart Export**
    - `SAVE_*` flags → control whether charts are saved to HTML/CSV.
    - Examples: `SAVE_NETWORTH_CHART`, `SAVE_EXAMPLE_TRANSACTIONS_CHART`.

1. **Detailed Mode**
    - `DETAILED_MODE` → overrides show/save flags to ensure all charts and exports are generated for IRS‑aligned audit clarity.

1. **Example Trials**
    - `sim_examples` → number of random trials selected for which detailed charts are generated (expenses, transactions, taxes, forecasts).

---

## 📂 Inputs Required

- **profile.json** → simulation horizon and MAGI.
- **buckets.json** → account definitions (must align with `balance.csv`).
- **balance.csv** → seed balances.
- **policies.json** → refill, liquidation, salary, SEPP, property, unemployment, Roth conversions.
- **tax_brackets.json** → federal, state, payroll, capital gains, IRMAA, Medicare premiums.
- **inflation_rates.json** → baseline inflation + category profiles.
- **inflation_thresholds.json** + **gain_table.json** → asset class return regimes.
- **marketplace_premiums.json** → healthcare premiums.
- **fixed.csv** → one‑time events (e.g., tuition, travel).
- **recurring.csv** → ongoing monthly flows (e.g., insurance, food, utilities).

> All inputs must conform to schemas in [Configuration Reference](configuration.md).

---

## 📈 Outputs

Nomad Wealth produces:

1. **Historical Charts**

    - `plot_historical_bucket_gains()` → bucket-level gain/loss trends.
    - `plot_historical_balance()` → net worth trajectory + gain/loss bars.

1. **Per-Trial Example Charts** (for trials in `sim_examples`)

    - Monthly expenses, transactions, transactions in context, income taxes, forecasts.

1. **Aggregate Monte Carlo Charts**

    - Monthly returns distribution.
    - Taxable balances at SEPP end month.
    - Total taxes, effective rates, withdrawal rates.
    - Net worth distribution with median and percentile bands.

1. **CSV Exports**
    - Bucket balances, tax breakdowns, monthly returns, flow logs (debits/credits for audit reproducibility).

---

## 🧾 Notes

- Timestamps in filenames use format `YYYYMMDD_HHMMSS`.
- Net worth = sum of all bucket balances at each month.
- SEPP gating enforces IRS 72(t) rules for tax-deferred withdrawals.
- Roth conversions are modeled independently and may occur before age 59.5.
- Logging records export paths for traceability.
- Detailed Mode ensures **IRS-aligned audit reproducibility** across all charts and exports.

---

## 📚 Related Pages

- [Framework Overview](overview.md) → conceptual landing page
- [Configuration Reference](configuration.md) → JSON and CSV schemas
- [Architecture Overview](architecture.md) → modular system design
- [Simulation Logic](simulation_logic.md) → monthly forecast loop and aggregation
- [Visualization Guide](visualization.md) → charts and exports
