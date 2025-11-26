# ⚙️ Configuration Directory

This folder contains all configuration files (JSON + CSV) that drive Nomad Wealth simulations.  
Each file defines a specific aspect of the forecast, from personal parameters to buckets, policies, taxes, inflation, and transactions.

---

## 📌 Required

- **`profile.json`** → Defines personal simulation parameters (birth month, end month, income actuals).  
  This file **must exist** for simulations to run.

- **`balance.csv`** → Historical monthly balances for all buckets.  
  Seeds the simulation with starting balances.

---

## ✅ Recommended

- **`buckets.json`** → Portfolio buckets and sub‑holdings (cash, taxable, tax‑deferred, tax‑free, property, vehicles, HSA, 529K, SEPP IRA, tax collection).
- **`policies.json`** → Refill rules, liquidation hierarchy, salary, Social Security, RMD, Roth conversions, SEPP, property, unemployment.
- **`tax_brackets.json`** → Federal/state/local tax brackets, payroll taxes, capital gains, Social Security taxability, IRMAA thresholds, Medicare premiums.
- **`inflation_rates.json`** → Baseline inflation assumptions and category‑specific profiles (food, health, property, travel, etc.).
- **`inflation_thresholds.json`** → Low/average/high inflation cutoffs per asset class.
- **`gain_table.json`** → Monthly return assumptions by asset class under Low, Average, High regimes.
- **`marketplace_premiums.json`** → Marketplace health insurance premiums (e.g., silver family, silver couple).

---

## 🎲 Optional

- **`fixed.csv`** → One‑time transactions (e.g., tuition, travel).
- **`recurring.csv`** → Ongoing monthly transactions (e.g., insurance, food, utilities, healthcare).

---

## 📚 Documentation

For full schema details, examples, and audit notes, see the  
👉 [Configuration Reference](../docs/configuration.md) in the documentation site.
