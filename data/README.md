# data/README.md

This document describes the required CSV files in the `data/` folder. These files supply historical balances and cash‐flow transactions for the forecasting engine. Ensure headers and bucket names exactly match those defined in `config/holdings.json`.

---

## balance.csv

Historical snapshots of bucket balances.

Columns:

- Date  
  - ISO format `YYYY-MM-DD`  
  - Represents the month‐start (e.g. `2025-09-01`)  
- One column per bucket name  
  - Column headers must exactly match keys in `config/holdings.json`  
  - Values are integer dollar balances  

You may include multiple rows to capture a history of balances. The engine will load these rows untouched and display them alongside the forecast in the final ledger and chart.

Example:

```csv
Date,Tax-Deferred,Tax-Free,Cash,Post-Education 529K,Depreciating,Fixed-Income,Taxable,Real-Estate,Health Savings Account
2025-01-01,950000,60000,70000,85000,130000,95000,220000,700000,30000
2025-09-01,1013049,62579,65479,90000,132470,95677,235694,734500,31929
```

---

## fixed.csv

One‐off transactions applied on specific dates.

Columns:

- Date  
  - ISO format `YYYY-MM-DD`  
- Type  
  - Target bucket name (must match a column in `balance.csv`)  
- Amount  
  - Integer dollars (positive for deposits, negative for withdrawals)  
- AssetClass (optional)  
  - If provided, directs the flow to a specific holding within the bucket  
- Description (optional)  
  - Free‐text label for reporting  

Example:

```csv
Date,Type,Amount,AssetClass,Description
2025-09-29,Taxable,60000,,Dell Severance
2026-07-01,Real-Estate,0,Real-Estate,Land for New House
```

---

## recurring.csv

Monthly cash‐flow transactions over a date range.

Columns:

- Start Date  
  - ISO format `YYYY-MM-DD` for first month of the series  
- End Date  
  - ISO format `YYYY-MM-DD` for last month of the series (leave blank for open‐ended)  
- Type  
  - Target bucket name (must match a column in `balance.csv`)  
- Amount  
  - Integer dollars per month (positive or negative)  
- AssetClass (optional)  
  - Directs the flow to a specific holding within the bucket  
- Description (optional)  

Example:

```csv
Start Date,End Date,Type,Amount,AssetClass,Description
2025-08-01,2031-07-01,Cash,-2315,,Mortgage
2025-09-01,2075-04-01,Cash,-75,,Subscriptions
```

---

## Tips and Common Pitfalls

- Check that all CSV headers exactly match bucket names in `config/holdings.json`.  
- Use consistent ISO date formatting (`YYYY-MM-DD`) to avoid parsing issues.  
- If `End Date` is blank in `recurring.csv`, the transaction continues through the forecast horizon.  
- Ensure integer dollar values—no decimals—to maintain type safety and clarity.
