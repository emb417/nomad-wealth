# config/README.md

## Configuration Reference

All simulation parameters live under `config/`. Each JSON drives one aspect of the forecast.

---

## profile.json

Defines simulation parameters:

- `Date of Birth`: ISO-date string
- `Retirement Date`: ISO-date string
- `End Date`: ISO-date string
- `Social Security Date`: ISO-date string
- `Social Security Amount`: int
- `Social Security Percentage`: float
- `Annual Gross Income`: int
- `Annual Bonus Date`: ISO-date string
- `Annual Bonus Amount`: int
- `Roth Conversion Start Date`: ISO-date string
- `Roth Conversion Amount`: int

Example:

```json
{
  "Date of Birth": "2000-01-01",
  "Retirement Date": "2060-01-01",
  "End Date": "2100-01-01",
  "Social Security Date": "2067-01-01",
  "Social Security Amount": 5000,
  "Social Security Percentage": 0.5, // 50% of expected payout
  "Annual Gross Income": 100000,
  "Annual Bonus Date": "2027-04-01",
  "Annual Bonus Amount": 0,
  "Roth Conversion Start Date": "2055-01-01",
  "Roth Conversion Amount": 2000
}
```

## holdings.json

Defines your portfolio buckets and their sub-holdings:

- `BucketName`:
  - `asset_class`: string key matching `gain_table.json`
  - `weight`: relative allocation within that bucket
  - `initial_amount`: starting balance

Example:

```json
{
  "Taxable": [
    { "asset_class": "LargeCap", "weight": 0.6, "initial_amount": 100000 },
    { "asset_class": "Bond", "weight": 0.4, "initial_amount": 100000 }
  ]
}
```

---

## gain_table.json

Maps each `asset_class` × growth scenario to `(avg, std)` monthly returns:

```json
{
  "LargeCap": {
    "Low": { "avg": 0.0058, "std": 0.005 },
    "Average": { "avg": 0.0042, "std": 0.005 },
    "High": { "avg": -0.001, "std": 0.005 }
  }
}
```

---

## inflation_thresholds.json

Per-asset inflation cutoffs dictate Low/Average/High:

```json
{
  "LargeCap": { "low": 0.02, "high": 0.06 },
  "Bond": { "low": 0.0, "high": 0.06 },
  "MMF": { "low": 0.0, "high": 0.03 }
}
```

---

## refill_policy.json

Controls auto-refill rules per bucket:

- `thresholds`: balance floor to trigger refill
- `amounts`: full refill amount per event
- `sources`: ordered lists of source buckets
- `taxable_eligibility`: ISO-date string for unlocking taxable draws

Example:

```json
{
  "thresholds": { "Cash": 50000, "Taxable": 100000 },
  "amounts": { "Cash": 10000, "Taxable": 50000 },
  "sources": { "Cash": ["Taxable", "Tax-Deferred"], "Taxable": ["Cash"] },
  "taxable_eligibility": "2025-10-01"
}
```

---

See code comments in `policies/ThresholdRefillPolicy` for extensibility hooks.

---
