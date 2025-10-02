# Data File Schemas

You must create and place your historical balances and forecasted transaction CSVs under `data/`. They should be named `balance.csv`, `fixed.csv`, and `recurring.csv`, respectively. All are required, but `fixed.csv` and `recurring.csv` can be empty, but with the correct headers. Copy and paste the examples below for a quick start.

---

## balance.csv

Monthly seed balances. Adding historical balances will allow for visualizations to compare the past to future scenarios.

Required header columns:

- `Date` (YYYY-MM-DD)
- One column per bucket (exact bucket names as in `holdings.json`)

At least one row of data is required to seed the forecasting.

Example:

```csv
Date,Cash,Fixed-Income,Taxable,Tax-Deferred,Tax-Free,Vehicles,Property
2025-10-01,10000,10000,10000,10000,0,0,0
```

---

## fixed.csv

One-off expected or pre-planned transactions like vacations, large purchases, etc. Only header columns are required.

Required header columns:

- `Date` (YYYY-MM--DD)
- `Bucket` (exact match)
- `Amount` (positive = inflow; negative = outflow)
- `Description` (optional)

Example:

```csv
Date,Bucket,Amount,Description
2028-07-01,Cash,-2000,Summer Vacation
2029-12-01,Cash,-2000,Winter Vacation
2031-04-01,Cash,-4000,New Car Downpayment
```

---

## recurring.csv

Monthly recurring expenses like food, rent, car payments, etc. You can include recurring deposits into buckets. Only header columns are required.

Required header columns:

- `Start Date` (YYYY-MM-DD)
- `End Date` (YYYY-MM-DD or blank)
- `Bucket`
- `Amount` (positive inflow; negative withdrawal)
- `Description`

Example:

```csv
Start Date,End Date,Bucket,Amount,Description
2026-01-01,2100-12-31,Cash,-2000,Monthly Living Expenses
2029-01-01,2034-12-31,Cash,-500,Monthly Car Loan Payment
2022-07-01,2032-07-01,Cash,-500,School Loan Payment
```

---
