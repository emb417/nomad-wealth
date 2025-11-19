# 🔄 Simulation Logic

Nomad Wealth’s simulation engine models financial flows month by month, applying transactions, policies, market returns, and taxes. This page explains the **step‑by‑step logic** of the forecast loop — how trials are prepared, executed, and turned into charts you can use to understand your retirement outlook.

---

## 🧩 Relationship to Architecture

The simulation logic is the **operational core** of the system described in [Architecture Overview](architecture.md). Where architecture explains the design and components, this page focuses on the **execution flow** inside the `ForecastEngine` and `app.py`.

---

## 📂 Staging Phase

Before any trial runs, the system prepares your inputs and builds the components that drive the forecast:

1. **Load Configuration** → reads your JSON and CSV files (buckets, balances, policies, transactions).
2. **Prepare Timeframes** → sets up historical and future monthly periods until your chosen end date.
3. **Initialize Components** → builds buckets, applies refill/liquidation rules, sets inflation and tax logic, and wires in transactions like salary, Social Security, property flows, and healthcare premiums.

---

## 📅 Monthly Forecast Loop

Each month in the simulation follows a clear sequence:

1. **Apply Transactions** → tuition, travel, insurance, food, utilities, salary, Social Security, Roth conversions, unemployment, property flows.
2. **Trigger Refill Policies** → keeps cash balances above thresholds, prevents early withdrawals, and triggers liquidation if needed.
3. **Apply Market Returns** → updates bucket balances based on inflation‑adjusted returns.
4. **Tax Collection Drip** → monthly withholding moves funds into the Tax Collection bucket.
5. **Snapshot Balances** → records bucket balances and logs flows for transparency.
6. **Year‑End Settlement** → applies IRS rules for income, gains, and penalties, reconciles taxes, and rolls forward estimates.

---

## 🎲 Trial Execution

Forecasts are run as **Monte Carlo trials** to capture uncertainty:

- **`run_one_trial()`** → builds buckets, policies, inflation, tax logic, and transactions, then runs the monthly loop.
- **`run_simulation()`** → wraps each trial and tags results with the trial index.
- **Parallel Execution** → trials run in parallel for efficiency, with results aggregated by trial index.

---

## 📊 Aggregation Phase

After all trials complete, results are combined into clear outputs:

- **Net Worth DataFrame** → monthly net worth across trials.
- **Tax DataFrame** → detailed tax records by trial and year.
- **Taxable Balances** → balances at SEPP end month for compliance checks.
- **Monthly Returns** → consolidated returns across trials.
- **Summary Tracking** → property events and taxable balances logged for transparency.

---

## 📈 Visualization Integration

Aggregated results feed directly into charts and reports:

- **Historical Charts** → bucket growth and net worth trajectory.
- **Per‑Trial Charts** → monthly details for expenses, transactions, taxes, and forecasts.
- **Aggregate Monte Carlo Charts** → probability distributions for returns, balances, taxes, and net worth.
- **Exports** → all charts available in HTML/CSV with consistent colors, overlays, and hover text.

---

## 📝 ForecastEngine Notes

The ForecastEngine ensures every forecast is **transparent and IRS‑aligned**:

- Monthly flows integrate buckets, transactions, market gains, refills, liquidations, and taxes.
- All results are auditable via structured records: snapshots, tax logs, and return records.
- Yearly tax logs reproduce IRS categories (income, gains, Social Security, Roth conversions, penalties).
- SEPP withdrawals, marketplace premiums, and IRMAA surcharges are applied correctly.
- Roth conversions follow policy‑driven thresholds (age cutoffs, balances, tax rates).
- Year‑end reconciliation ensures taxes are paid from the Tax Collection bucket first, then Cash.

---

## 📚 Related Pages

- [Architecture Overview](architecture.md) → system design and modular components
- [Configuration Reference](configuration.md) → JSON and CSV inputs
- [Visualization Guide](visualization.md) → charts and exports
- [Usage Guide](usage.md) → workflow and output files
