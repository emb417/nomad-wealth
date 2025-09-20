# data/README.md

## Data File Schemas

Place your historical and transaction CSVs under `data/`.

---

## balance.csv

Monthly seed balances. Header columns:

- `Date` (YYYY-MM-DD)
- One column per bucket (exact bucket names as in `holdings.json`)

Example:

```csv
Date,Cash,Taxable,Tax-Deferred,Deferred Compensation
2025-09-01,50000,200000,150000,300000
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
2025-09-29,Deferred Compensation,-228000,Deferred Compensation Distribution
2025-09-29,Taxable,135984,Post-Tax Distribution
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
2025-01-01,,Cash,3000,Monthly Expenses
2025-01-01,2040-12-31,Tax-Deferred,-2000,401k Contribution
```

---

Place any additional CSVs in `data/` and update `src/app.py` to load them.

---
