# Inflation Forecasting & Portfolio Projections

A Python framework that merges historical balances with forward simulations. It applies fixed and recurring transactions, enforces refill policies, models asset-class growth under inflation scenarios, and generates both a forecast ledger and interactive HTML chart.

---

## Features

- Fixed & recurring cash-flow ingestion from CSV
- Threshold-driven refill policies (full-amount or top-off)
- Per-asset inflation cutoffs driving Low/Average/High growth scenarios
- Monte Carlo or deterministic gain sampling via a customizable gain table
- Tax-aware withdrawals (deferred vs. taxable)
- Pluggable logging and cash-balance alerts

---

## Quick Start

1. Clone and install dependencies

   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -r requirements.txt
   ```

2. Configure JSONs in `config/` (see `config/README.md`)
3. Prepare your CSVs in `data/` (see `data/README.md`)
4. Review and set flags in `src/app.py`:
   - `SHOW_CHART`
   - `SAVE_CHART`
   - `SAVE_LEDGER`
   - `CASH_WARNING_THRESHOLD`
5. Run the simulation

   ```bash
   python src/app.py
   ```

---

## Folder Structure

- `config/` JSON definitions for buckets, market assumptions, thresholds, refill rules
- `data/`  CSV files: balances, fixed, recurring transactions
- `src/`  Application code (see `src/README.md`)
- `export/`  Generated forecast CSV and HTML charts

---

## Running & Reviewing

1. Ensure bucket names match exactly across `config/` and `data/`
2. Launch with debug/info logging enabled to trace refill, returns, and tax events
3. Inspect `export/forecast.csv` and `export/forecast.html`
4. Adjust refill strategies or gain tables, then rerun

---

## Roadmap

- JSON schema validation
- Percentage-based refill rules
- Full Monte Carlo sampling & confidence intervals
- Extend policy engine to multi-bucket pro-rata top-ups
- Category-specific inflation for expenses

---

_Last updated:_ 2025-09-20

---
