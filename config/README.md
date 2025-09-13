# config/README.md

This document describes the JSON configuration files in the `config/` folder. Each file drives a different aspect of the forecast engine: user profile, bucket allocations, market assumptions, and automated refill rules.

---

## profile.json

Defines the overall simulation timeline and social security settings.

Keys:

- `Name`  
  User’s full name (string).  
- `Retirement Date`  
  Target retirement date (`YYYY-MM-DD`).  
- `End Date`  
  Simulation end date (`YYYY-MM-DD`).  
- `Social Security Date`  
  Date to begin Social Security (`YYYY-MM-DD`).  
- `Social Security Amount`  
  Annual Social Security payout (integer dollars).  
- `Social Security Percentage`  
  Portion of payout taken as cash vs. reinvested (float between 0 and 1).

Example:

```json
{
  "Name": "Eric Brousseau",
  "Retirement Date": "2035-06-01",
  "End Date": "2075-04-01",
  "Social Security Date": "2035-07-01",
  "Social Security Amount": 30000,
  "Social Security Percentage": 1.0
}
```

---

## holdings.json

Maps each high-level bucket to one or more asset-class weightings for starting balances.

- Top-level keys: bucket names (must match columns in `data/balance.csv`).  
- Values: arrays of objects with:  
  - `asset_class`: Name matching a key in `gain_table.json`.  
  - `weight`: Fractional allocation that sums to 1.0 for that bucket.

Example:

```json
{
  "Cash": [
    { "asset_class": "MMF", "weight": 1.00 }
  ],
  "Taxable": [
    { "asset_class": "SmallCap", "weight": 0.50 },
    { "asset_class": "Bond", "weight": 0.50 }
  ]
}
```

---

## gain_table.json

Specifies expected returns (`avg`) and volatility (`std`) for each asset class under three inflation scenarios.

- Top-level keys: asset-class names.  
- Nested keys: `"Low"`, `"Average"`, `"High"`.  
- Scenario objects contain:  
  - `avg`: Mean return (float).  
  - `std`: Standard deviation (float).

Example:

```json
{
  "LargeCap": {
    "Average": { "avg": 0.06, "std": 0.15 },
    "High":    { "avg": 0.08, "std": 0.20 },
    "Low":     { "avg": 0.04, "std": 0.10 }
  },
  "Bond": {
    "Average": { "avg": 0.03, "std": 0.05 }
  }
}
```

---

## inflation_thresholds.json

Defines the cut-off bounds that determine which scenario table to use for each asset class.

- Keys: asset-class names.  
- Values: objects with:  
  - `low`: Lower inflation bound (float).  
  - `high`: Upper inflation bound (float).

Example:

```json
{
  "LargeCap": { "low": 0.02, "high": 0.06 },
  "MMF":      { "low": 0.00, "high": 0.03 }
}
```

---

## refill_policy.json

Automates bucket top-ups when balances drop below safety thresholds. All values use whole dollars (integers).

- `thresholds`: Map bucket → minimum balance before refill.  
- `amounts`: Map bucket → flat refill amount.  
- `sources`: Map target bucket → bucket to draw funds from.

Example:

```json
{
  "thresholds": {
    "Cash": 25000,
    "Tax-Deferred": 50000
  },
  "amounts": {
    "Cash": 15000,
    "Tax-Deferred": 20000
  },
  "sources": {
    "Cash": "Taxable",
    "Tax-Deferred": "Taxable"
  }
}
```

---

## Tips

- Ensure bucket names in JSON exactly match column headers in `data/balance.csv`.  
- Validate that all weightings in `holdings.json` sum to 1.0 per bucket.  
- Use ISO date format (`YYYY-MM-DD`) consistently.  
- Keep all amounts as integers to maintain type safety.
