# Data File Schemas

Place your historical and transaction CSVs under `data/`.

---

## balance.csv

Monthly seed balances. Header columns:

- `Date` (YYYY-MM-DD)
- One column per bucket (exact bucket names as in `holdings.json`)

Example:

```csv
Date,Cash,Fixed-Income,Taxable,Tax-Deferred,Tax-Free,Health Savings Account,Vehicles,Property,529K
2026-01-01,10000,20000,30000,400000,5000,6000,70000,80000,9000
```

---

## fixed.csv

One-off transactions. Header columns:

- `Date` (YYYY-MM--DD)
- `Bucket` (exact match)
- `Amount` (positive = inflow; negative = outflow)
- `Description` (optional)

Example:

```csv
2028-07-01,Fixed-Income,10000,New Investments
2028-12-01,Cash,-4000,New Car Downpayment
2030-07-01,Taxable,10000,New Investments
2030-09-01,529K,-9000,Final Tuition
```

---

## recurring.csv

Scheduled cash flows. Header columns:

- `Start Date` (YYYY-MM-DD)
- `End Date` (YYYY-MM-DD or blank)
- `Bucket`
- `Amount` (positive inflow; negative withdrawal)
- `Description`

Example:

```csv
Start Date,End Date,Bucket,Amount,Description
2026-01-01,2100-12-31,Cash,-3000,Monthly Living Expenses
2029-01-01,2034-12-31,Cash,-500,Monthly Car Loan Payment
```

---
