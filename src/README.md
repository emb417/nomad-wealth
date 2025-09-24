# Source Code Overview

All application logic lives under `src/`.

---

## app.py

This script serves as the entry point for the application. It is responsible for:

- Loading the configuration and historical data from the `config` and `data` directories, respectively.
- Initializing the necessary components, including:
  - Buckets and holdings
  - Transactions (Fixed, Recurring, Salary, Social Security, Roth Conversion)
  - ThresholdRefillPolicy with age-based eligibility
  - MarketGains (inflation-aware return simulator)
  - TaxCalculator
- Running a Monte Carlo simulation loop using the `ForecastEngine.run(...)` method.
- Aggregating the year-end net worth across simulations.
- Exporting various outputs, including:
  - Sample forecast charts and CSVs
  - Monte Carlo percentile chart
  - Probability of positive net worth at key ages

This script is the core of the application and orchestrates the entire simulation process.

### Simulation settings

The following settings can be adjusted in `app.py` to customize the simulation behavior:

- `SIMS`: number of Monte Carlo simulations to run (default: 100)
- `SIMS_SAMPLES`: indices of the sample simulations to display (default: randomly selected)
- `SHOW_SIMS_SAMPLES`: whether to display the sample simulations (default: True)
- `SAVE_SIMS_SAMPLES`: whether to save the sample simulations (default: False)
- `SHOW_NETWORTH_CHART`: whether to display the net worth chart (default: True)
- `SAVE_NETWORTH_CHART`: whether to save the net worth chart (default: False)

These settings allow you to customize the simulation behavior to suit your needs.

---

## engine.py

This module defines the [ForecastEngine](cci:2://file:///Users/eric/Dev/nomad-wealth/src/engine.py:14:0-136:63) class, which is responsible for orchestrating the monthly forecast loop.

### ForecastEngine

[ForecastEngine](cci:2://file:///Users/eric/Dev/nomad-wealth/src/engine.py:14:0-136:63) orchestrates the monthly forecast loop by applying core transactions, triggering refill policies, simulating market returns, computing taxes, and logging year-end tax summaries.

The monthly forecast loop consists of the following steps:

1. Apply core transactions: fixed, recurring, salary, social security, and Roth conversions
2. Trigger refill policy: age-gated for tax-deferred sources
3. Apply market returns via `MarketGains`: simulates inflation-adjusted market returns
4. Compute taxes and withdraw from Cash: calculates tax liabilities and withdraws funds from Cash bucket
5. Snapshot bucket balances: records the current balances of all buckets
6. Log year-end tax summary: logs the total tax liabilities for the year

By executing these steps, [ForecastEngine](cci:2://file:///Users/eric/Dev/nomad-wealth/src/engine.py:14:0-136:63) generates a monthly forecast of bucket balances and tax liabilities for the entire simulation period.

---

## domain.py

This module defines the core data structures and business logic of the application.

### AssetClass

`AssetClass` represents an asset class with a name and return-sampling behavior.

### Holding

`Holding` represents a single slice in a `Bucket` and contains information about the asset class, weight, amount, and cost basis.

### Bucket

`Bucket` represents a financial bucket and contains information about the bucket name, holdings, whether it can go negative, whether cash can be fallback, and the bucket type.

---

## policies.py

This module defines the refill policy used by the application.

### RefillTransaction

`RefillTransaction` represents a refill transaction that is triggered by the refill policy. It contains information about the source and target buckets, the amount of funds being transferred, and whether the transaction is tax-deferred or taxable.

### ThresholdRefillPolicy

`ThresholdRefillPolicy` implements the refill policy logic based on thresholds. It triggers bucket top-offs when the balance of a bucket falls below a certain threshold. This policy includes age-based gating for tax-deferred withdrawals. It also includes emergency logic for negative Cash balances.

---

## economic_factors.py

This module defines the economic factors used by the application to simulate market returns and inflation.

### MarketGains

[MarketGains](cci:2://file:///Users/eric/Dev/nomad-wealth/src/economic_factors.py:27:0-68:60) represents the market gains for a given period and contains the following attributes:

- `date`: date of the period
- `returns`: returns for different asset classes
- `inflation`: inflation rate for the period
- `tax_rate`: marginal tax rate for the period

The [apply()](cci:1://file:///Users/eric/Dev/nomad-wealth/src/economic_factors.py:45:4-68:60) method applies market gains to each `Bucket`'s holdings by:

1. Looking up that asset's low/high inflation thresholds
2. Comparing the year's inflation rate to pick Low/Average/High
3. Sampling gain from `gain_table[asset][scenario]`

### InflationGenerator

[InflationGenerator](cci:2://file:///Users/eric/Dev/nomad-wealth/src/economic_factors.py:9:0-24:18) generates historical inflation rates for a given period and contains the following attributes:

- `start_date`: start date of the period
- `end_date`: end date of the period
- `inflation_data`: historical inflation rates for the period

The `generate()` method generates a list of inflation rates for each year in the specified period.

This module provides the economic factors used by the application to simulate market returns and inflation.

---

## taxes.py

This module defines the tax-related functionality used by the application.

### TaxCalculator

`TaxCalculator` calculates the federal tax on combined income (married-filing-jointly brackets + SS rules), withdraws from Cash (allowing negative), and lets the RefillPolicy pull from other buckets (down to zero) so only Cash can stay negative.

The `TaxCalculator` class has the following methods:

- `__init__()`: initializes the `TaxCalculator` with a `ThresholdRefillPolicy` object.
- `_taxable_social_security()`: calculates the taxable Social Security benefits based on the other income.
- `calculate_tax()`: calculates the federal tax based on the salary, Social Security benefits, withdrawals, and gains.
- `_calculate_ordinary_tax()`: applies the 2025 ordinary income tax brackets for married-filing-jointly.
- `_calculate_capital_gains_tax()`: applies the 2025 long-term capital gains brackets for married-filing-jointly.

---

## transactions.py

This module defines all transaction types used by the application.

### FixedTransaction

`FixedTransaction` represents a fixed transaction that occurs at a specific date and contains the following attributes:

- `start_date`: date of the transaction
- `amount`: amount of the transaction
- `source_bucket`: source bucket of the transaction
- `target_bucket`: target bucket of the transaction

The `apply()` method applies the transaction to the given `buckets` by transferring the specified amount from the source bucket to the target bucket.

The `get_withdrawal()` method returns the amount withdrawn from the source bucket.

The `get_taxable_gain()` method returns the amount of taxable gain from the transaction.

### RecurringTransaction

`RecurringTransaction` represents a recurring transaction that occurs at a specific date and contains the following attributes:

- `start_date`: date of the first transaction
- `monthly_amount`: monthly amount of the transaction
- `pct_cash`: percentage of the transaction to be withdrawn as cash
- `cash_bucket`: cash bucket for the transaction
- `source_bucket`: source bucket of the transaction

The `apply()` method applies the transaction to the given `buckets` by transferring the specified amount from the source bucket to the target bucket.

The `get_withdrawal()` method returns the amount withdrawn from the source bucket.

The `get_taxable_gain()` method returns the amount of taxable gain from the transaction.

### SalaryTransaction

`SalaryTransaction` represents a salary transaction that occurs at a specific date and contains the following attributes:

- `start_date`: date of the first transaction
- `monthly_amount`: monthly amount of the transaction
- `source_bucket`: source bucket of the transaction

The `apply()` method applies the transaction to the given `buckets` by transferring the specified amount from the source bucket to the target bucket.

The `get_withdrawal()` method returns the amount withdrawn from the source bucket.

The `get_taxable_gain()` method returns the amount of taxable gain from the transaction.

### SocialSecurityTransaction

[SocialSecurityTransaction](cci:2://file:///Users/eric/Dev/nomad-wealth/src/transactions.py:256:0-270:73) represents a Social Security transaction that occurs at a specific date and contains the following attributes:

- `start_date`: date of the first transaction
- `monthly_amount`: monthly amount of the transaction
- `pct_cash`: percentage of the transaction to be withdrawn as cash
- `cash_bucket`: cash bucket for the transaction

The `apply()` method applies the transaction to the given `buckets` by transferring the specified amount from the source bucket to the target bucket.

The `get_withdrawal()` method returns the amount withdrawn from the source bucket.

The `get_taxable_gain()` method returns the amount of taxable gain from the transaction.

### RothConversionTransaction

`RothConversionTransaction` represents a Roth conversion transaction that occurs at a specific date and contains the following attributes:

- `start_date`: date of the transaction
- `amount`: amount of the transaction
- `source_bucket`: source bucket of the transaction
- `target_bucket`: target bucket of the transaction

The `apply()` method applies the transaction to the given `buckets` by transferring the specified amount from the source bucket to the target bucket.

The `get_withdrawal()` method returns the amount withdrawn from the source bucket.

The `get_taxable_gain()` method returns the amount of taxable gain from the transaction.

---
