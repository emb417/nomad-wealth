# 📊 Data Directory

This folder contains the CSV inputs required to seed and drive Nomad Wealth simulations.  
These files act as **data configuration**, complementing the JSON files in `config/`.

---

## 📌 Required Files

- **`balances.csv`** → Historical monthly balances for each bucket.
- **`fixed.csv`** → One‑time transactions (e.g., tuition, travel, large purchases).
- **`recurring.csv`** → Ongoing monthly transactions (e.g., insurance, food, utilities, healthcare).

> All three files must exist. `fixed.csv` and `recurring.csv` may be empty, but must include the correct headers.

---

## 🧾 Examples

Minimal examples are provided below. See the full documentation for schema details.

- **balances.csv**

```csv
Month,Cash,CD Ladder,Brokerage,Tax-Deferred,Tax-Free,Health Savings Account,Vehicles,Property,529K,SEPP IRA
2025-10,10000,15000,20000,30000,5000,2000,8000,250000,10000,0
```

- **fixed.csv**

```csv
Month,Bucket,Amount,Type,Description
2028-09,529K,-25000,Education,College Tuition #1
2029-07,CD Ladder,-10000,Travel,Travel to Europe
```

- **recurring.csv**

```csv
Start Month,End Month,Bucket,Amount,Type,Description
2026-01,2030-12,Cash,-400,Food,Groceries
2027-01,2075-12,Cash,-250,Voice and Data,Mobile + Internet
```

---

## 📚 Documentation

For complete schema definitions, configuration cross‑links, and audit notes, see the  
👉 [Configuration Reference](../docs/configuration.md) in the documentation site.
