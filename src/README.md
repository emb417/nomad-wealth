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

- `SIM_SIZE`: number of Monte Carlo simulations to run (default: 100); 100 takes ~10 seconds, 1000 takes ~1 minute
- `SIM_EXAMPLE_SIZE`: indices of the sample simulations for charting and exporting (default: 1)
- `SHOW_HISTORICAL_BALANCE_CHART`: whether to display the historical balance chart (default: True)
- `SAVE_HISTORICAL_BALANCE_CHART`: whether to save the historical balance chart (default: False)
- `SHOW_EXAMPLE_FORECAST_CHART`: whether to display the example forecast chart (default: True)
- `SAVE_EXAMPLE_FORECAST_CHART`: whether to save the example forecast chart (default: False)
- `SHOW_EXAMPLE_TRANSACTIONS_CHART`: whether to display the example transactions chart (default: True)
- `SAVE_EXAMPLE_TRANSACTIONS_CHART`: whether to save the example transactions chart (default: False)
- `SHOW_EXAMPLE_TRANSACTIONS_IN_CONTEXT_CHART`: whether to display the example transactions in context chart (default: True)
- `SAVE_EXAMPLE_TRANSACTIONS_IN_CONTEXT_CHART`: whether to save the example transactions in context chart (default: False)
- `SHOW_NETWORTH_CHART`: whether to display the net worth chart (default: True)
- `SAVE_NETWORTH_CHART`: whether to save the net worth chart (default: False)

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

## buckets.py

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

## policies_engine.py

`policies_engine.py` orchestrates how buckets are automatically refilled to maintain minimum balances and how `Cash` shortfalls trigger emergency liquidations through generated transactions.

### ThresholdRefillPolicy

ThresholdRefillPolicy defines how buckets are automatically topped up or liquidated based on configured thresholds, source mappings, and eligibility rules. It uses metadata attached to each Bucket (e.g., `bucket_type`, `allow_cash_fallback`) and an optional `taxable_eligibility` period to gate tax-advantaged sources.

Attributes:

- `thresholds` (Dict[str, int])  
  Maps each target bucket name to its minimum desired balance.

- `sources` (Dict[str, List[str]])  
  Lists source bucket names for each target bucket when topping up.

- `amounts` (Dict[str, int])  
  Specifies the per-period refill amount for each target bucket.

- `taxable_eligibility` (Optional[pd.Period])  
  Once the simulation reaches this month, tax-advantaged buckets become eligible refill sources.

- `liquidation_threshold` (int)  
  The minimum Cash balance; any shortfall triggers emergency liquidation.

- `liquidation_buckets` (List[str])  
  Ordered list of buckets to draw from when liquidating to cover Cash shortfall.

Methods:

- `generate_refills(buckets: Dict[str, Bucket], tx_month: pd.Period) → List[RefillTransaction]`

  1. Normalizes `tx_month` and `taxable_eligibility` to monthly `pd.Period`.
  2. For each target in `thresholds`:
     - Skips if bucket missing or already at/above threshold.
     - Determines `per_pass` from `amounts`; warns if zero.
     - Iterates each source in `sources[target]`:  
       • Skips missing buckets or, if pre-eligibility, tax-advantaged buckets.  
       • Calculates `transfer` based on available balance and `allow_cash_fallback`.  
       • Appends a `RefillTransaction(source, target, amount, is_tax_deferred, is_taxable)`.  
       • Stops once the target’s refill need is met.

- `generate_liquidation(buckets: Dict[str, Bucket], tx_month: pd.Period) → List[RefillTransaction]`
  1. Computes `shortfall = liquidation_threshold - Cash.balance()`.
  2. If `shortfall ≤ 0`, returns empty list.
  3. Iterates over `liquidation_buckets` (skipping “Cash”):
     - For “Property”:  
       • Sells full balance; splits proceeds into a normal take (up to `amounts["Cash"]`) and a taxable take.  
       • Emits two `RefillTransaction`s: one to “Cash” (taxable) and one to “Taxable.”
     - For other buckets:  
       • Takes `min(bucket.balance(), shortfall)`.  
       • Applies a 10% penalty if the bucket is tax-deferred and `tx_month` is before `taxable_eligibility`.  
       • Emits one `RefillTransaction(source, "Cash", amount, is_tax_deferred, is_taxable, penalty_rate)`.
     - Decrements `shortfall`; stops once Cash is replenished to threshold.

## policies_transactions.py

`policies_transactions.py` contains the core Transaction and RefillTransaction classes for generating and applying refill transactions.

### RefillTransaction

RefillTransaction is a conservative refill operation that moves funds between buckets, delegates actual money movement to each Bucket’s helper methods, flags tax attributes for downstream accounting, and estimates taxable gains when cost-basis data is missing. It inherits from Transaction for interface consistency and records runtime metrics on applied amounts, estimated gains, and penalties.

Attributes:

- `source` (str)  
  Name of the bucket to withdraw funds from.

- `target` (str)  
  Name of the bucket to deposit funds into.

- `amount` (int)  
  Planned transfer amount.

- `is_tax_deferred` (bool)  
  Marks whether the withdrawal should be treated as tax-deferred.

- `is_taxable` (bool)  
  Marks whether the withdrawal should be treated as taxable.

- `penalty_rate` (float)  
  Penalty rate applied to withdrawals (e.g., early-withdrawal fees).

- `_applied_amount` (int)  
  Actual amount moved during the last `apply` call.

- `_taxable_gain` (int)  
  Estimated taxable gain portion of the withdrawal.

- `_penalty_tax` (int)  
  Tax incurred due to penalty rate on withdrawn funds.

Methods:

- `__init__(source: str, target: str, amount: int, is_tax_deferred: bool = False, is_taxable: bool = False, penalty_rate: float = 0.0) → None`  
  Initializes a refill transaction with source/target names, amount, tax flags, and any penalty rate.

- `apply(buckets: Dict[str, Bucket], tx_month: pd.Period) → None`

  1. Resets runtime metrics.
  2. If the source bucket allows cash fallback and Cash exists, calls `withdraw_with_cash_fallback(amount, cash)`, deposits the sum into target, logs debug, and records `_applied_amount`.
  3. Otherwise, calls `partial_withdraw(amount)` on source, deposits whatever is returned, and records `_applied_amount`.
  4. If the source is taxable and marked `is_taxable`, estimates `_taxable_gain` as 50% of applied amount.
  5. Applies `_penalty_tax` by multiplying `_applied_amount` by `penalty_rate`.

- `get_withdrawal(tx_month: pd.Period) → int`  
  Returns `_applied_amount` if `is_tax_deferred` is True; otherwise returns 0.

- `get_taxable_gain(tx_month: pd.Period) → int`  
  Returns the estimated taxable gain (`_taxable_gain`) from the last `apply` call.

- `get_penalty_tax(tx_month: pd.Period) → int`  
  Returns the tax owed on any penalty applied during the last `apply` call.

### RentalTransaction

`RentalTransaction` represents a conditional monthly expense (e.g. rent) that withdraws directly from the Cash bucket, but only when the Property bucket has zero balance.

Attributes:

- `monthly_amount`: monthly expense amount (int)
- `source_bucket`: name of the bucket to withdraw from ("Cash")
- `condition_bucket`: name of the bucket whose zero balance triggers the withdrawal ("Property")

Methods:

- `apply(buckets: Dict[str, Bucket], tx_month: pd.Period) → None`  
  Checks the balance of the condition_bucket; if it exists and its balance is zero (or if it’s missing), attempts to withdraw monthly_amount from the source_bucket. If either bucket is missing or the condition_bucket has a positive balance, no action is taken.

### RothConversionTransaction

`RothConversionTransaction` represents a Roth conversion transaction that occurs at a specific date and contains the following attributes:

- `start_date`: date of the transaction
- `amount`: amount of the transaction
- `source_bucket`: source bucket of the transaction
- `target_bucket`: target bucket of the transaction

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

`SocialSecurityTransaction` represents a Social Security transaction that occurs at a specific date and contains the following attributes:

- `start_date`: date of the first transaction
- `monthly_amount`: monthly amount of the transaction
- `pct_cash`: percentage of the transaction to be withdrawn as cash
- `cash_bucket`: cash bucket for the transaction

The `apply()` method applies the transaction to the given `buckets` by transferring the specified amount from the source bucket to the target bucket.

The `get_withdrawal()` method returns the amount withdrawn from the source bucket.

The `get_taxable_gain()` method returns the amount of taxable gain from the transaction.

### TaxDeferredTransaction

`TaxDeferredTransaction` represents a tax-deferred income stream that deposits a monthly base salary, a year-end remainder, and an annual bonus into a designated bucket until a specified retirement date. It inherits from Transaction and flags all deposits as tax-deferred.

Attributes:

- `annual_gross`: Total gross salary for the year (int)
- `annual_bonus`: One-time bonus amount paid once per year (int)
- `bonus_date`: Date string (YYYY-MM-DD) when the bonus is paid
- `target_bucket`: Name of the bucket receiving the deposits (str)
- `retirement_date`: Date string (YYYY-MM-DD) after which no further deposits occur

Methods:

- `apply(buckets: Dict[str, Bucket], tx_month: pd.Period) → None`  
  Deposits the pro-rated monthly base salary (including any December remainder) and, if tx_month matches bonus_date, the annual bonus into the target bucket. No action once tx_month exceeds retirement_date.

- `get_withdrawal(tx_month: pd.Period) → int`  
  Returns the total amount that would be deposited for tx_month (monthly base + December remainder + bonus if applicable). Returns 0 after retirement_date.

### TaxableTransaction

`TaxableTransaction` represents a fully taxable income stream that deposits a monthly base salary, a year-end remainder, an annual bonus, and any realized investment gains into a designated bucket until a specified retirement date. It inherits from Transaction and flags all deposits as taxable.

Attributes:

- `annual_gross`: Total gross salary for the year (int)
- `annual_bonus`: One-time bonus amount paid once per year (int)
- `bonus_date`: Date string (YYYY-MM-DD) when the bonus is paid
- `target_bucket`: Name of the bucket receiving the deposits (str)
- `retirement_date`: Date string (YYYY-MM-DD) after which no further deposits occur
- `gain_log`: Mapping of each monthly period (pd.Period) to realized gains (Dict[pd.Period, int])

Methods:

- `apply(buckets: Dict[str, Bucket], tx_month: pd.Period) → None`  
  Deposits the pro-rated monthly base salary (including any December remainder) and, if tx_month matches bonus_date, the annual bonus. Additionally, looks up any realized gain in gain_log for tx_month and deposits that amount. No action once tx_month exceeds retirement_date.

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

`taxes.py` encapsulates U.S. federal tax rules and computes a year’s tax liability for the simulation engine. It exposes the `TaxCalculator` class, which applies married-filing-jointly ordinary income brackets, Social Security taxation rules, and long-term capital gains brackets. During calculation, it withdraws owed tax from the Cash bucket (permitting a negative balance) and then invokes a `ThresholdRefillPolicy` to pull from other buckets so that only Cash remains negative.

### TaxCalculator

`TaxCalculator` computes federal tax on combined income—including ordinary income, Social Security benefits, withdrawals, and long-term capital gains—withdraws from Cash (allowing it to go negative), then uses a `ThresholdRefillPolicy` to pull from other buckets so only Cash remains negative.

Attributes:

- `refill_policy`: `ThresholdRefillPolicy` instance used to replenish Cash from other buckets
- `ordinary_tax_brackets`: mapping of filing status to lists of ordinary income tax brackets
- `capital_gains_tax_brackets`: mapping of filing status to capital gains tax brackets

Methods:

- `__init__(refill_policy: ThresholdRefillPolicy, tax_brackets: Dict[str, Dict[str, List[Dict[str, float]]]]) → None`  
  Initializes the tax calculator with a given refill policy and a dictionary containing both ordinary and capital gains tax brackets.

- `_taxable_social_security(ss_benefits: int, other_income: int) → int`  
  Calculates the taxable portion of Social Security benefits based on provisional income thresholds (0% up to \$32,000; 50% between \$32,001–\$44,000; 85% above \$44,000).

- `calculate_tax(salary: int = 0, ss_benefits: int = 0, withdrawals: int = 0, gains: int = 0) → int`  
  Orchestrates the full tax calculation:

  1. Computes ordinary income tax on salary + withdrawals + taxable SS.
  2. Computes long-term capital gains tax layered on top of ordinary income.  
     Returns the sum of both tax liabilities.

- `_calculate_ordinary_tax(brackets: Dict[str, List[Dict[str, float]]], income: int) → int`  
  Applies 2025 married-filing-jointly ordinary income tax brackets against the specified income to determine the ordinary income tax owed.

- `_calculate_capital_gains_tax(ordinary_income: int, gains: int) → int`  
  Applies 2025 long-term capital gains tax brackets on gains, layering them above the ordinary income to compute the gains tax.

---

## rules_transactions.py

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

---

## visualization.py

This module contains functions for generating interactive charts and exporting dataframes to CSV files.

The `plot_historical_balance()` generates an interactive chart based on the historical dataframe. The chart shows the net worth over time on a line chart and the net worth gain/loss over time on a bar chart. This chart allows for visualization of the overall trend of the net worth over time and the specific months where the net worth increased or decreased relative to the previous month and the previous year.

The `plot_example_transactions()` generates interactive chart based on the random example simulation, showing the transactions for a given year, to help identify patterns or trends in the data.

The `plot_example_transactions_in_context()` generates interactive chart based on the random example simulation, showing the transactions for a given year in context to the bucket balances, to help identify patterns or trends in the data.

The `plot_example_forecast()` generates interactive charts based on the random example simulation. This chart provides a visualization of the forecasted bucket balances over time to help identify patterns or trends in the data.

The `plot_mc_networth()` generates interactive chart based on the monte carlo simulation dataframes. This chart provides a visualization of the forecasted net worth over time for each simulation including the median net worth and 15th and 85th percentile bounds. The chart allows for comparison of multiple simulations and helps identify patterns or trends in the data. The upper 85th percentile is hidden to reduce the range of the chart.

---
