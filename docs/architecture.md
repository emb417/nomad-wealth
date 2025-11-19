# 🏛️ Architecture Overview  

Nomad Wealth is a **policy‑driven Monte Carlo simulation framework** for financial planning. Its architecture is designed for **clarity, transparency, and extensibility**, ensuring that every projection, chart, and policy reflects IRS rules and produces trustworthy results.  

---

## 🔍 High‑Level Design  

Nomad Wealth is built from modular components that work together to run forecasts and generate charts:  

- **Entry Point (`app.py`)** → starts the process: loads your configuration, runs simulations, and produces outputs.  
- **Forecast Engine (`forecast_engine.py`)** → runs the monthly forecast loop, applying transactions, policies, market returns, and taxes.  
- **Buckets & Holdings (`buckets.py`)** → represent your accounts and investments.  
- **Policies (`policy_engine.py`, `policies_transactions.py`)** → enforce rules like refills, income deposits, conversions, withdrawals, RMDs, SEPPs, and unemployment.
- **Transactions (`rules_transactions.py`)** → handle fixed and recurring expenses.  
- **Economic Factors (`economic_factors.py`)** → simulate inflation and market returns based on historical data.  
- **Taxes (`taxes.py`)** → apply IRS‑compliant tax rules for income, gains, and Social Security.  
- **Visualization (`visualizations.py`)** → generate charts and exports that make your plan easy to understand.
- **Load Data (`load_data.py`)** → loads CSV and JSON files for simulation and visualization.
- **FlowTracker (`audit.py`)** → records every debit and credit for transparency.

---

## 📂 Data Flow  

Here’s how information moves through the system:  

1. **Configuration Loading**  
    - JSON files define your buckets, policies, tax brackets, and simulation settings.  
    - CSV files provide starting balances and transactions.  

2. **Staging**  
    - Loads all inputs (balances, fixed events, recurring expenses, policies, tax brackets, inflation, healthcare premiums).  
    - Prepares historical and future timeframes.  
    - Seeds buckets, policies, inflation, tax logic, and transactions.  
    - Helper functions ensure balances are correct, inflation is applied consistently, and performance is logged.  

3. **Parallel Simulation Loop (Forecast Engine)**  
    - Runs Monte Carlo trials in parallel for efficiency.  
    - Each trial applies monthly transactions, policies, market returns, and taxes.  
    - FlowTracker records every debit and credit for transparency.  

4. **Aggregation & Summary**  
    - Results are combined into net worth, taxes, balances, and returns.  
    - Property events and compliance checks are tracked.  

5. **Visualization Layer**  
    - Produces charts showing monthly details, aggregate distributions, and historical trends.  
    - All charts can be exported to HTML and CSV for easy sharing and reproducibility.  

---

## 🧾 IRS Compliance  

Nomad Wealth enforces IRS rules so your forecasts reflect reality:  

- Ordinary income brackets inflated annually.  
- Capital gains layered above ordinary income.  
- Social Security capped at 85% of provisional income.  
- Penalty taxes applied only when rules require it.  
- AGI includes salary, withdrawals, conversions, gains, and Social Security.  
- Taxable income calculated after deductions.  
- Inflation modeled stochastically, anchored to a base year.  

---

## 📊 Visualization Integration  

Visualization is built into the simulation loop, so you always see clear results:  

- **Historical context** → charts of bucket growth and net worth trends.  
- **Per‑trial transparency** → detailed monthly expenses, transactions, taxes, and forecasts.  
- **Aggregate clarity** → distributions of returns, balances, taxes, and net worth across Monte Carlo trials.  
- **Reproducibility** → charts exportable to HTML/CSV with consistent colors, overlays, and hover text.  

---

## 🎯 Design Principles  

- **Policy‑First** → all financial rules are transparent and repeatable.  
- **Clarity** → every dollar is traceable across buckets and scenarios.  
- **Extensibility** → modular design supports new rules and transaction types.  
- **Resilience** → Monte Carlo sampling shows how your plan holds up under uncertainty.  
- **Parallelism** → simulations run efficiently at scale.  
- **Integrity** → helper functions enforce correctness and reproducibility.  

---

## 📚 Related Pages  

- [Framework Overview](overview.md)  
- [Configuration Reference](configuration.md)  
- [Simulation Logic](simulation_logic.md)  
- [Visualization Guide](visualization.md)  
- [Usage Guide](usage.md)
