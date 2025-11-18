# 🚀 Usage Guide  

This guide explains how to run Nomad Wealth simulations, adjust settings, and understand the results.  

---

## ▶️ Running the Simulation  

1. **Navigate to the project root**  
   Make sure you’re in the directory containing `src/app.py`.  

2. **Run the entry point**  

   ```bash
   python src/app.py
   ```  

   This command:  
   - Loads your configuration files (accounts, balances, policies, taxes).  
   - Prepares historical and future timelines.  
   - Runs Monte Carlo trials in parallel to capture uncertainty.  
   - Aggregates results into clear tables.  
   - Generates interactive charts and CSV/HTML exports.  

3. **Check the `export/` directory**  
   All outputs (charts and CSVs) are saved here with timestamped filenames for easy tracking.  

---

## ⚙️ Controlling Behavior  

You can control how the simulation runs by adjusting flags in `app.py`:  

- **Simulation Size** → `SIM_SIZE` sets the number of Monte Carlo trials.  
- **Chart Display** → `SHOW_*` flags decide which charts open interactively (e.g., net worth, examples, historical).  
- **Chart Export** → `SAVE_*` flags decide which charts are saved to HTML/CSV.  
- **Detailed Mode** → `DETAILED_MODE` forces all charts and exports to be generated for full transparency.  
- **Example Trials** → `sim_examples` sets how many random trials are shown in detail (expenses, transactions, taxes, forecasts).  

---

## 📂 Inputs Required  

Nomad Wealth uses configuration files to define your plan:  

- **profile.json** → retirement horizon and income assumptions.  
- **buckets.json** → account definitions (must align with `balance.csv`).  
- **balance.csv** → starting balances for each account.  
- **policies.json** → rules for income, withdrawals, property, unemployment, Roth conversions.  
- **tax_brackets.json** → IRS‑aligned federal, state, payroll, capital gains, IRMAA, Medicare premiums.  
- **inflation_rates.json** → baseline inflation + category profiles.  
- **inflation_thresholds.json** + **gain_table.json** → asset class return regimes.  
- **marketplace_premiums.json** → healthcare premiums.  
- **fixed.csv** → one‑time events (e.g., tuition, travel).  
- **recurring.csv** → ongoing monthly flows (e.g., insurance, food, utilities).  

> All inputs must follow the schemas in [Configuration Reference](configuration.md).  

---

## 📈 Outputs  

Nomad Wealth produces results you can explore in charts and exports:  

- **Historical Charts** → account gains/losses and net worth trajectory.  
- **Per‑Trial Example Charts** → detailed views of monthly expenses, transactions, taxes, and forecasts.  
- **Aggregate Monte Carlo Charts** → distributions of returns, balances, taxes, withdrawals, and net worth.  
- **CSV Exports** → tables of balances, tax breakdowns, monthly returns, and flow logs for reproducibility.  

---

## 🧾 Notes  

- Filenames include timestamps (`YYYYMMDD_HHMMSS`) for traceability.  
- Net worth = sum of all account balances each month.  
- SEPP rules enforce IRS 72(t) withdrawal compliance.  
- Roth conversions can occur before age 59.5 if configured.  
- Logging records export paths for transparency.  
- Detailed Mode ensures **IRS‑aligned reproducibility** across all charts and exports.  

---

## 📚 Related Pages  

- [Framework Overview](overview.md) → conceptual landing page  
- [Configuration Reference](configuration.md) → JSON and CSV schemas  
- [Architecture Overview](architecture.md) → modular system design  
- [Simulation Logic](simulation_logic.md) → monthly forecast loop and aggregation  
- [Visualization Guide](visualization.md) → charts and exports  
