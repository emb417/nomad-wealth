# Source Code Overview

All application logic lives under `src/`.

---

## app.py

This script serves as the entry point for the application. It is responsible for:

- Loading the configuration and historical data from the `config` and `data` directories, respectively.
- Initializing the necessary components, including:
  - Buckets and holdings
  - Transactions (Fixed, Recurring, Salary, Social Security, Roth Conversion)
  - `ThresholdRefillPolicy` with:
    - JSON-driven thresholds
    - Configurable liquidation order (via `policies.json: liquidation.buckets`)
    - Retirement-age gating for tax-deferred withdrawals
  - `MarketGains` (inflation-aware return simulator)
  - `TaxCalculator` (ordinary income, capital gains, early-withdrawal penalties)
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
- `SIMS_SAMPLES`: indices of the sample simulations to display (default: 3 randomly selected)
- `SHOW_SIMS_SAMPLES`: whether to display the sample simulations (default: True)
- `SAVE_SIMS_SAMPLES`: whether to save the sample simulations (default: False)
- `SHOW_NETWORTH_CHART`: whether to display the net worth chart (default: True)
- `SAVE_NETWORTH_CHART`: whether to save the net worth chart (default: False)
- `SHOW_HISTORICAL_NW_CHART`: whether to display the historical net worth chart (default: True)
- `SAVE_HISTORICAL_NW_CHART`: whether to save the historical net worth chart (default: False)

These settings allow you to customize the simulation behavior to suit your needs.

---

## engine.py

This module defines the [`ForecastEngine`](src/engine.py) class, which is responsible for orchestrating the monthly forecast loop.

### ForecastEngine

`ForecastEngine` orchestrates the monthly forecast loop by applying core transactions, triggering refill policies, simulating market returns, computing taxes, and logging year-end tax summaries.

The monthly forecast loop consists of the following steps:

1. Apply core transactions: fixed, recurring, salary, social security, and Roth conversions
2. Trigger refill policy: age-gated for tax-deferred sources
3. Apply market returns via `MarketGains`: simulates inflation-adjusted market returns
4. Emergency liquidation when Cash < threshold
   - Follows the JSON-configured `liquidation.buckets` priority
   - Fully sells off Property; partially liquidates others as needed
   - Tags early withdrawals from tax-deferred buckets (before retirement age) with a 10% penalty
5. Monthly tax drip: withdraw from Cash → deposit into Tax Collection
6. Snapshot bucket balances: records the current balances of all buckets
7. Log monthly flows, including:
   - Salary
   - Social Security
   - Tax-deferred withdrawals
   - Taxable gains
   - Early-withdrawal penalties
8. January year-end settlement:
   - Calculate ordinary + capital gains tax
   - Add accumulated penalty tax
   - Pay total tax from Tax Collection + Cash
   - Roll forward any leftover estimate

By executing these steps, `ForecastEngine` generates a detailed monthly forecast of bucket balances, cash flows, tax liabilities, and penalties.

---

## domain.py

Core data structures:

### AssetClass

Represents an asset class with sampling behavior for returns, e.g. Cash, Bonds, Stocks.

### Holding

A slice in a `Bucket`, a percent of the bucket assigned to an asset class.

### Bucket

`Bucket` represents a financial bucket and contains information about the bucket name, holdings, whether it can go negative, whether cash can be fallback, and the bucket type.

Encapsulates:

- Name
- Holdings
- Negative balance allowed flag
- Cash-fallback when empty flag
- `bucket_type`
  - e.g. `"taxable"`, `"tax_deferred"`, `"tax_free"`, `"other"`

---

## policies.py

This module defines the refill and liquidation policy logic.

### RefillTransaction

`RefillTransaction` represents a refill transaction that is triggered by the refill policy. It contains information about the source and target buckets, the amount of funds being transferred, and whether the transaction is tax-deferred or taxable.

### ThresholdRefillPolicy

`ThresholdRefillPolicy` implements the refill policy logic based on thresholds. It triggers bucket top-offs when the balance of a bucket falls below a certain threshold. This policy includes age-based gating for tax-deferred withdrawals. It also includes emergency logic for negative Cash balances.

- Configured via `policies.json` with:
  - `"thresholds"` (per-bucket top-off levels)
  - `"liquidation": { "threshold": …, "buckets": […] }`
  - `taxable_eligibility` (retirement gating date)
- `generate_refills()` handles normal top-offs
- `generate_liquidation()`:
  - Calculates cash shortfall (`threshold - Cash.balance()`)
  - Iterates the configured bucket order (skips Cash)
  - Fully liquidates `"Property"`; partial otherwise
  - Applies 10% penalty to tax-deferred buckets before eligibility

---

## economic_factors.py

Simulates market returns and inflation.

### MarketGains

`MarketGains` represents the market gains for a given period and contains the following attributes:

- `date`: date of the period
- `returns`: returns for different asset classes
- `inflation`: inflation rate for the period
- `tax_rate`: marginal tax rate for the period

The `apply()` method applies market gains to each `Bucket`'s holdings by:

1. Looking up that asset's low/high inflation thresholds
2. Comparing the year's inflation rate to pick Low/Average/High
3. Sampling gain from `gain_table[asset][scenario]`

### InflationGenerator

`InflationGenerator` generates historical inflation rates for a given period and contains the following attributes:

- `start_date`: start date of the period
- `end_date`: end date of the period
- `inflation_data`: historical inflation rates for the period

The `generate()` method generates a list of inflation rates for each year in the specified period.

This module provides the economic factors used by the application to simulate market returns and inflation.

---

## taxes.py

This module encapsulates U.S. federal tax rules and produces a year’s tax liability for the engine to settle.

### TaxCalculator

`TaxCalculator` computes:

- Ordinary income tax on salary, Social Security benefits, and tax-deferred withdrawals
- Long-term capital gains tax on realized gains

Any early-withdrawal penalties are tracked by the engine (via `RefillTransaction`) and added to the final tax bill outside of this class.

#### Methods

- `__init__(self)`:  
  Initializes tax-bracket tables for married filing jointly and links to the configured refill policy.

- `_taxable_social_security(self, salary: int, ss_benefits: int) -> int`:  
  Calculates the taxable portion of Social Security benefits based on combined income.

- `calculate_tax(  
  self,  
  salary: int,  
  ss_benefits: int,  
  withdrawals: int,  
  gains: int  
) -> int`:  
   Returns the total federal tax liability for the year by summing ordinary-income and capital-gains components.

- `_calculate_ordinary_tax(self, taxable_income: int) -> int`:  
  Applies the 2025 ordinary-income tax brackets to compute tax on salary and withdrawals.

- `_calculate_capital_gains_tax(self, gains: int) -> int`:  
  Applies the 2025 long-term capital-gains brackets to compute tax on realized gains.

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

### RentalTransaction

`RentalTransaction` represents a rental transaction that occurs when `Property` has zero balance. This will typically happen after a property liquidation. It contains the following attributes:

- `monthly_amount`: monthly amount of the transaction which is configured in profile.json as "Monthly Rent"

### SalaryTransaction

`SalaryTransaction` represents a salary transaction that occurs at a specific date and contains the following attributes:

- `start_date`: date of the first transaction
- `monthly_amount`: monthly amount of the transaction
- `source_bucket`: source bucket of the transaction

The `apply()` method applies the transaction to the given `buckets` by transferring the specified amount from the source bucket to the target bucket.

The `get_withdrawal()` method returns the amount withdrawn from the source bucket.

The `get_taxable_gain()` method returns the amount of taxable gain from the transaction.

### SocialSecurityTransaction

`SocialSecurityTransaction` represents a Social Security transaction that occurs at a specific date and contains the following attributes:

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

## visualization.py

This module contains functions for generating interactive charts and exporting dataframes to CSV files.

### plot_historical_balance()

Generates an interactive chart based on the historical dataframe. The chart shows the net worth over time on a line chart and the net worth gain/loss over time on a bar chart. This chart allows for visualization of the overall trend of the net worth over time and the specific months where the net worth increased or decreased.

### plot_sample_forecast()

Generates interactive charts based on the sampled simulation dataframes. These charts provide a visualization of the forecasted bucket balances over time for each sampled simulation. The chart allows for comparison of multiple simulations and helps identify patterns or trends in the data.

### plot_mc_networth()

Generates interactive chart based on the monte carlo simulation dataframes. This chart provides a visualization of the forecasted net worth over time for each simulation including the median net worth and 15th and 85th percentile bounds. The chart allows for comparison of multiple simulations and helps identify patterns or trends in the data. The upper 85th percentile is hidden to reduce the range of the chart.

---
