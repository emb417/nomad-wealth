# 🏛️ Architecture Overview

Nomad Wealth is a **policy-driven Monte Carlo simulation framework** for financial planning.  
Its architecture is designed for **audit clarity, transparency, and extensibility**, ensuring that every projection, chart, and policy is IRS-aligned and defensible.

---

## 🔍 High-Level Design

The system is organized into modular components under `src/`:

- **Entry Point (`app.py`)** → orchestrates configuration loading, staging, parallel execution, aggregation, and visualization.
- **Forecast Engine (`forecast_engine.py`)** → runs the monthly simulation loop, applying transactions, policies, market returns, and taxes.
- **Buckets & Holdings (`buckets.py`)** → core data structures representing accounts, holdings, and asset classes.
- **Policies (`policy_engine.py`, `policies_transactions.py`)** → enforce refill rules, liquidation hierarchies, and penalty logic.
- **Transactions (`rules_transactions.py`)** → define fixed, recurring, salary, Social Security, Roth conversions, and other flows.
- **Economic Factors (`economic_factors.py`)** → simulate inflation and market returns using historical distributions.
- **Taxes (`taxes.py`)** → apply IRS-compliant tax rules for ordinary income, capital gains, and Social Security.
- **Visualization (`visualizations.py`)** → generate interactive charts (historical, per‑trial, Monte Carlo) and CSV/HTML exports for audit clarity.
- **Helper Functions (`app.py`)** → utilities for timing, inflation modifiers, and bucket creation.

---

## 📂 Data Flow

1. **Configuration Loading**

   - JSON files in `config/` define buckets, policies, tax brackets, and simulation parameters.
   - CSV files in `data/` seed historical balances and define fixed/recurring transactions.

2. **Staging**

   - `stage_load()` → loads JSON configs and CSV inputs.
     - Inputs include:
       - `balances.csv` → seed balances.
       - `fixed.csv` → one‑time events.
       - `recurring.csv` → ongoing monthly flows.
     - Policies (`policies.json`), tax brackets (`tax_brackets.json`), inflation (`inflation_rates.json` + thresholds + gain table), and marketplace premiums (`marketplace_premiums.json`) are also loaded.
   - `stage_prepare_timeframes()` → builds historical (`hist_df`) and future (`future_df`) frames.
   - `stage_init_components()` → seeds buckets, policies, inflation, tax calculator, market gains, and transactions.
     - Helper functions ensure integrity:
       - `create_bucket()` → allocates balances across holdings, correcting rounding drift.
       - `seed_buckets_from_config()` → validates bucket definitions against historical balances.
       - `build_description_inflation_modifiers()` → applies inflation profiles consistently across categories.
       - `timed()` → logs performance metrics for reproducibility.

3. **Parallel Simulation Loop (Forecast Engine)**

   - Monte Carlo trials executed in parallel with `ProcessPoolExecutor`.
   - Each trial applies monthly transactions, refill policies, market returns, and taxes.
   - FlowTracker records all debits/credits for audit clarity.

4. **Aggregation & Summary**

   - Trial results aggregated into DataFrames for net worth, taxes, taxable balances, and monthly returns.
   - Property liquidation events tracked across simulations.
   - Taxable balances at SEPP end month recorded for compliance checks.

5. **Visualization Layer**
   - Per-trial charts: monthly expenses, transactions, taxes, forecasts.
   - Aggregate Monte Carlo charts: monthly returns, taxable balances, totals/rates, net worth distribution.
   - Historical charts: bucket gains and net worth trajectory.
   - All charts exportable to HTML and CSV for reproducibility.

---

## 🧾 IRS Compliance

The tax engine enforces IRS rules with explicit, layered logic:

- Ordinary income brackets inflated annually.
- Capital gains layered above ordinary income.
- Social Security capped at 85% of provisional income.
- Penalty tax applied only when flagged in metadata.
- AGI includes salary, withdrawals, conversions, gains, and Social Security.
- Taxable income calculated after deductions.
- Inflation modeled stochastically, anchored to a base year.

---

## 📊 Visualization Integration

Visualization is embedded in the simulation loop:

- **Historical context** → charts of bucket gains and net worth trends.
- **Per-trial transparency** → expenses, transactions, taxes, forecasts.
- **Aggregate clarity** → distributions of returns, balances, taxes, and net worth across Monte Carlo trials.
- **Audit reproducibility** → all charts exportable to HTML/CSV with timestamped filenames, with consistent color palettes, percentile overlays, and hover text for interpretability.

---

## 🎯 Design Principles

- **Policy-First** → all financial rules are declarative JSON, transparent and repeatable.
- **Audit Clarity** → every dollar is traceable across buckets and scenarios.
- **Extensibility** → modular design allows new transaction types, policies, or tax rules.
- **Resilience** → Monte Carlo sampling embraces volatility, quantifying sufficiency and optimization.
- **Parallelism** → simulations scale efficiently with `ProcessPoolExecutor`.
- **Integrity** → helper functions enforce balance correctness, inflation consistency, and reproducible timing.

---

## 📚 Related Pages

- [Framework Overview](overview.md)
- [Configuration Reference](configuration.md)
- [Simulation Logic](simulation_logic.md)
- [Visualization Guide](visualization.md)
- [Usage Guide](usage.md)
