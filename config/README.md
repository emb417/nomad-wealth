# Configuration Reference

All simulation parameters live in `config/`. Each JSON drives one aspect of the forecast.

## REQUIRED

- create a `profile.json` file in `config/`, which defines your personal simulation parameters.

Copy and paste the example below for a quick start.

## RECOMMENDED

You should also review and revise these existing files:

- `buckets.json`, which defines your portfolio buckets sub-holdings. This drives the forecasted gains and tax events for each bucket.
- `policies.json`, which defines your refill rules and liquidation hierarchy.
- `tax_brackets.json`, which defines the tax brackets, defaulting to Married-Filing-Jointly in Oregon State.

## OPTIONAL

These files drive the forecasting based on interest rates and market returns data from 2000-2025. Statistical analysis was used to generate these values. Over time you may need to replace the values with updated data.

- `gain_table.json`, which defines the average and standard deviation of monthly returns for each asset class and growth scenario.
- `inflation_rate.json`, which defines the average and standard deviation of inflation rates over the forecast period.
- `inflation_thresholds.json`, which defines the low, average, and high inflation thresholds for each asset class.

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
- `Monthly Rent`: int
  Example:

```json
{
  "Date of Birth": "2000-01-01",
  "Retirement Date": "2060-01-01",
  "End Date": "2100-01-01",
  "Social Security Date": "2067-01-01",
  "Social Security Amount": 5000,
  "Social Security Percentage": 0.5,
  "Annual Gross Income": 100000,
  "Annual Bonus Date": "2027-04-01",
  "Annual Bonus Amount": 10000,
  "Monthly Rent": 3000
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

Sets `(avg, std)` annual inflation rate assumptions for different profiles.

The "default" profile provides the general inflation rate assumptions for all buckets not explicitly listed in the "profiles" section.

The "profiles" section lists specific inflation rate assumptions for each asset class. For example, the "Mortgage" profile defines the average and standard deviation of annual inflation for mortgage-based assets.

- "profile" names must match the Description in recurring transactions

These numbers are based on modern inflation rates using 1990-2025 data.

---

## inflation_thresholds.json

Per-asset inflation cutoffs dictate Low/Average/High.

---

## policies.json

Controls auto-refill rules per bucket:

- `thresholds`: mapping of bucket names to balance floors
- `amounts`: mapping of bucket names to full refill amounts per event
- `sources`: mapping of target bucket names to ordered lists of source buckets
- `salary`: mapping of bucket names to percentage of salary
- `social_security`: target bucket name
- `roth_conversion`: mapping of Roth conversion parameters (max tax rate, start date, source, target, chunk size)
- `sepp`: mapping of SEPP parameters (enabled, start date, end date, source, target)
- `liquidation`: mapping of liquidation parameters (threshold, ordered list of buckets to withdraw from)

---

## tax_brackets.json

Defines tax brackets for salary, SS benefits, tax-deferred withdrawals, and long-term capital gains.

- `ordinary` is a dictionary of { `bracket_name`: [ { `min_salary`: int, `tax_rate`: float } ] } that will be iterated over to calculate different types of income taxes. Modify for your local income taxes.
- `capital_gains` is a dictionary of { `bracket_name`: [ { `min_salary`: int, `tax_rate`: float } ] }
- `social_security_taxability` is a list of dictionaries containing the provisional income thresholds and applicable tax rates for Social Security benefits.

---
