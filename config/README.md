# Configuration Reference

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
  "Annual Bonus Amount": 10000
}
```

## buckets.json

Defines your portfolio buckets and their sub-holdings:

- `BucketName`:
  - `holdings`: list of { `asset_class`: string, `weight`: float }
  - `can_go_negative`: bool
  - `allow_cash_fallback`: bool
  - `bucket_type`: string

---

## gain_table.json

Maps each `asset_class` × growth scenario to `(avg, std)` monthly returns.

---

## inflation_rate.json

Sets `(avg, std)` annual inflation rate assumptions.
These numbers are based on modern inflation rates using 1990-2025 data.

---

## inflation_thresholds.json

Per-asset inflation cutoffs dictate Low/Average/High.

---

## policies.json

Controls auto-refill rules per bucket:

- `thresholds`: balance floor to trigger refill
- `amounts`: full refill amount per event
- `sources`: ordered lists of source buckets
- `salary`: target buckets get percentage of salary
- `social_security`: target bucket
- `roth_conversion`: start date, amount, source, target
- `liquidation_threshold`: emergency liquidation threshold
