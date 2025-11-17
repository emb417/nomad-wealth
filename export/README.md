# 📦 Export Artifacts

Nomad Wealth saves all simulation outputs under the `export/` directory.  
This catalog explains the file types, naming conventions, and audit notes.

---

## 🧮 Monte Carlo Aggregates

### Net Worth

- **File:** `mc_networth_<timestamp>.html`
- **Description:** Interactive chart showing all simulation paths, median trajectory, and 15th/85th percentile bounds.
- **CSV:** `mc_networth_<timestamp>.csv` → net worth trajectories across trials.

### Taxes

- **File:** `mc_tax_<timestamp>.csv`
- **Description:** Multi‑indexed DataFrame of tax liabilities, effective rates, withdrawals.
- **Audit Note:** Indexed by trial and year for reproducibility.

### Taxable Balances

- **File:** `mc_taxable_<timestamp>.csv`
- **Description:** Taxable balances at SEPP end month.
- **Audit Note:** Useful for liquidity checks at IRS milestones.

### Monthly Returns

- **File:** `mc_monthly_returns_<timestamp>.csv`
- **Description:** Consolidated monthly return samples across trials.
- **Chart:** `mc_monthly_returns_<timestamp>.html` → distribution of monthly returns.

---

## 📊 Per‑Trial Examples

Generated only for trials listed in `sim_examples`.

- **Bucket Forecasts**

  - `####_buckets_forecast_<timestamp>.csv` → bucket balances over time.
  - `####_buckets_forecast_<timestamp>.html` → interactive chart.

- **Tax Forecasts**

  - `####_taxes_forecast_<timestamp>.csv` → annual tax breakdowns.
  - `####_taxes_forecast_<timestamp>.html` → interactive chart.

- **Flow Logs**

  - `####_flow_<timestamp>.csv` → detailed transaction flows with trial index.

- **Charts**
  - Monthly expenses, transactions, transactions in context, income taxes, forecasts.
  - Filenames follow pattern: `####_<chart_type>_<timestamp>.html`.

---

## 📜 Historical Charts

Generated from seed balances (`balance.csv`):

- `historical_bucket_gains_<timestamp>.html` → bucket‑level gain/loss trends.
- `historical_balance_<timestamp>.html` → net worth trajectory + gain/loss bars.

---

## 🧾 Naming Conventions

- **Timestamp:** `YYYYMMDD_HHMMSS` → run time of simulation.
- **Trial Index:** `####` → zero‑padded trial number (e.g., `0005`).
- **Chart Type:** descriptive suffix (e.g., `networth`, `taxes`, `transactions`).

---

## 📚 Audit Notes

- All CSVs are reproducible and can be re‑loaded into pandas for verification.
- Flow logs (`flow_df`) capture every debit/credit for audit clarity.
- Taxable balances at SEPP end month are explicitly tracked for IRS compliance.
- Property liquidation events are summarized in `summary.json` (if enabled).

---

## 📚 Related Pages

- [Usage Guide](../docs/usage.md) → workflow and output files
- [Visualization Guide](../docs/visualization.md) → chart descriptions
- [Simulation Logic](../docs/simulation_logic.md) → aggregation and trial execution
