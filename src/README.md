# 📂 Source Code Overview

This directory contains the core modules of Nomad Wealth.  
Each module is designed for **audit clarity, modularity, and IRS compliance**.

---

## 📌 Entry Point

### `app.py`

Main entry point for the application. Responsibilities:

- **Load & Prep** → `stage_load`, `stage_prepare_timeframes`
- **Initialize Components** → `stage_init_components`
- **Run Trials** → `run_one_trial`, `run_simulation`
- **Aggregate Results** → build DataFrames for net worth, taxes, returns, balances
- **Visualize Outputs** → historical, per‑trial, and Monte Carlo charts

See [Simulation Logic](../docs/simulation_logic.md) for detailed flow.

---

## 🧩 Staging Functions

- **`stage_load()`** → loads JSON + CSV inputs, requires `buckets.json` under `json_data["buckets"]`.
- **`stage_prepare_timeframes()`** → builds historical (`hist_df`) and future (`future_df`) frames.
- **`stage_init_components()`** → seeds buckets, policies, inflation, tax calculator, market gains, and transactions.

### `stage_init_components(...)`

- Seeds buckets from `balances.csv` and `buckets.json`.
- Loads fixed transactions (`fixed_transactions.csv`) and recurring transactions (`recurring_transactions.csv`).
- Wires transactions into the forecast engine alongside salary, Social Security, property, RMD, unemployment, and Roth conversions.

---

## 🎲 Trial Execution

- **`run_one_trial()`** → executes a single Monte Carlo trial, returns forecast, taxes, monthly returns, and flow logs.
- **`run_simulation()`** → wrapper that injects trial index into results, used in parallel execution.

---

## 🛠️ Helper Functions

### `timed(label)`

- Context manager for timing simulation blocks.
- Logs elapsed seconds and number of trials (`SIM_SIZE`).
- **Audit Note:** Provides reproducible performance metrics.

### `build_description_inflation_modifiers(base_inflation, inflation_profiles, inflation_defaults, years)`

- Builds inflation modifiers for descriptive categories (e.g., Rent).
- Adjusts base inflation rates by sensitivity profiles.
- Produces year‑by‑year modifiers used in transaction inflation adjustments.
- **Audit Note:** Ensures consistent inflation application across descriptions.

### `create_bucket(name, starting_balance, holdings_config, flow_tracker, ...)`

- Constructs a `Bucket` from holdings config.
- Allocates starting balance across asset classes by weight.
- Adjusts for rounding drift to preserve total balance.
- **Audit Note:** Guarantees balance integrity at initialization.

### `seed_buckets_from_config(hist_df, buckets_cfg, flow_tracker)`

- Builds all buckets from `hist_df` columns and `buckets_cfg`.
- Validates that every column has a config entry.
- Creates holdings, applies flags (`can_go_negative`, `allow_cash_fallback`, `bucket_type`).
- Always creates a Tax Collection bucket.
- **Audit Note:** Ensures configuration and historical balances are consistent.

---

### `buckets.py`

Defines the core data structures for asset classes, holdings, and buckets.  
Buckets represent accounts (Cash, Brokerage, Tax‑Deferred, etc.) and support deposits, withdrawals, transfers, and audit tracking.

---

#### Buckets Key Classes

- **`AssetClass`**

  - Represents an asset class (e.g., Stocks, Bonds, Property).
  - Provides `sample_return(avg, std)` to generate stochastic returns using a normal distribution.

- **`Holding`**

  - Represents a single slice of a bucket.
  - Fields:
    - `asset_class` → AssetClass instance.
    - `weight` → relative allocation weight.
    - `amount` → current dollar amount.
    - `cost_basis` → optional cost basis for taxable gain tracking (defaults to 11 if not provided).
  - Methods:
    - `apply_return(avg, std)` → applies a sampled return to the holding balance.

- **`Bucket`**
  - A container of holdings with metadata flags:
    - `can_go_negative` → allows overdrafts.
    - `allow_cash_fallback` → enables shortfall coverage from Cash bucket.
    - `bucket_type` → classification (`cash`, `taxable`, `tax_deferred`, `tax_free`, `property`, `other`).
  - Integrates with `FlowTracker` to record deposits, withdrawals, and transfers.
  - Methods:
    - `balance()` → current total balance.
    - `balance_at_period_end(year, month)` → balance snapshot for audit.
    - `holdings_as_dicts()` → returns holdings metadata for serialization.
    - `deposit(amount, source, tx_month, flow_type="deposit")` → weighted deposit across holdings.
    - `transfer(amount, target_bucket, tx_month, flow_type="transfer")` → move funds between buckets with single flow record.
    - `withdraw(amount, target, tx_month, flow_type="withdraw")` → withdraw funds, respecting `can_go_negative`.
    - `partial_withdraw(amount)` → conservative withdrawal, never below zero.
    - `withdraw_with_cash_fallback(amount, cash_bucket)` → withdraw with optional fallback to Cash bucket.
    - Internal helper `_withdraw_from_holdings(amount)` → core withdrawal logic.

---

#### Buckets Audit Notes

- All flows (deposit, withdraw, transfer) are recorded via `FlowTracker` for reproducibility.
- Weighted deposits and transfers ensure allocations match holding weights, with residuals corrected in the last holding to avoid rounding drift.
- Negative balances are only allowed when `can_go_negative=True`.
- Cash fallback logic ensures liquidity by pulling shortfalls from the Cash bucket.
- End‑of‑month balances are tracked for audit snapshots.
- Cost basis field supports taxable gain tracking in property and taxable buckets.

---

### `load_data.py`

Provides helper functions to load CSV and JSON configuration files from the `data/` and `config/` directories.

---

#### Load Data Key Functions

- **`load_csv()`**

  - Loads required CSV inputs from the `data/` directory:
    - `balance.csv` → monthly seed balances.
    - `fixed.csv` → one‑time transactions.
    - `recurring.csv` → recurring transactions.
  - Returns a dictionary of pandas DataFrames keyed by file type.
  - Parses date columns (`Month`, `Start Month`, `End Month`) into `pandas.Period`.

- **`load_json()`**
  - Loads all JSON configuration files from the `config/` directory.
  - Returns a dictionary keyed by filename stem.
  - Requires `profile.json` to exist; exits with error if missing.

---

#### Load Data Audit Notes

- File names are **singular** (`balance.csv`, `fixed.csv`, `recurring.csv`, `profile.json`).
- Logging provides clear error messages if required files are missing.
- All JSON files in `config/` are loaded automatically, ensuring extensibility.

---

### `economic_factors.py`

Implements inflation generation and market gain application logic.  
These components connect inflation assumptions, thresholds, and gain tables to bucket holdings.

---

#### Economic Factors Key Classes

- **`InflationGenerator`**

  - Seeds inflation rates and cumulative modifiers for a list of years.
  - Parameters:
    - `years` → list of years to generate inflation for.
    - `avg` → average annual inflation rate.
    - `std` → volatility of inflation.
    - `seed` → RNG seed for reproducibility.
  - Method:
    - `generate()` → returns a dictionary keyed by year with:
      - `rate` → annual inflation rate.
      - `modifier` → cumulative inflation multiplier up to that year.

- **`MarketGains`**
  - Applies market gains to bucket holdings based on inflation thresholds and gain tables.
  - Parameters:
    - `gain_table` → asset class return distributions (`gain_table.json`).
    - `inflation_thresholds` → low/high cutoffs per asset class (`inflation_thresholds.json`).
    - `inflation` → generated inflation rates (`InflationGenerator` output).
  - Method:
    - `apply(buckets, forecast_date)` → evaluates gains/losses for each bucket:
      1. Determines scenario (Low/Average/High) per asset class based on inflation rate.
      2. Samples monthly return from `gain_table`.
      3. Applies return to each holding in each bucket.
      4. Emits `MarketGainTransaction` objects for audit tracking.
      5. Returns `(transactions, metadata)` where metadata includes inflation rate and sampled monthly returns.

---

#### Economic Factors Audit Notes

- Inflation rates are generated stochastically but reproducibly (seeded RNG).
- Scenarios (Low/Average/High) are determined by comparing inflation against thresholds.
- Gain sampling uses normal distribution with `avg` and `std` from `gain_table.json`.
- Transactions are logged as `gain`, `loss`, or `deposit` (special case: Fixed‑Income in taxable buckets).
- Metadata returned includes inflation rate and monthly returns for transparency.
- Ensures audit clarity by linking each transaction to its bucket, asset class, and scenario.

---

### `audit.py`

Provides the **FlowTracker** class, which records all transactional flows for audit and reproducibility.  
This ensures every deposit, withdrawal, transfer, and market gain/loss can be traced back to its source.

---

#### Audit Key Class

- **`FlowTracker`**
  - Maintains an internal list of transaction records.
  - Methods:
    - `record(source, target, amount, tx_month, flow_type)`
      - Appends a transaction record with:
        - `date` → month of transaction (`pandas.Period`).
        - `source` → originating bucket.
        - `target` → destination bucket.
        - `amount` → transaction value.
        - `type` → flow type (`deposit`, `withdraw`, `transfer`, `gain`, `loss`).
    - `to_dataframe()`
      - Converts all recorded flows into a `pandas.DataFrame` for analysis, visualization, or export.

---

#### Audit Audit Notes

- FlowTracker is integrated into `Bucket` operations (`deposit`, `withdraw`, `transfer`) and `MarketGains`.
- Ensures **symmetry** between debits and credits for audit clarity.
- Provides a reproducible log of all flows, enabling validation against external statements.
- Records are lightweight dictionaries, making them easy to serialize or extend.
- DataFrame output supports downstream reporting, charting, and compliance checks.

---

### `taxes.py`

Provides the **TaxCalculator** class, which models federal and payroll taxes, capital gains, Social Security taxability, IRMAA surcharges, Medicare premiums, and early withdrawal penalties.  
This class inflates brackets and deductions by year using inflation modifiers, ensuring audit clarity and reproducibility. It is designed to integrate with `ForecastEngine` by consuming **actual year‑to‑date baselines** and monthly increments, so simulated withholding and liability align with real‑world outcomes.

---

#### Taxes Key Class

- **`TaxCalculator`**
  - Parameters:
    - `base_brackets` → tax bracket definitions from `tax_brackets.json`.
    - `base_inflation` → inflation modifiers from `InflationGenerator`.
  - Responsibilities:
    - Inflates standard deduction, ordinary brackets, payroll brackets, capital gains brackets, Social Security taxability thresholds, IRMAA brackets, and Medicare base premiums by year.
    - Calculates taxable Social Security benefits based on provisional income.
    - Applies ordinary, payroll, and capital gains taxes to income streams.
    - Applies penalties for early withdrawals.
    - Returns a detailed tax breakdown for a given year, including marginal and effective rates.
    - Supports monthly marginal tax estimation by comparing prior vs. current cumulative income logs.

---

#### Taxes Important Methods

- **`calculate_tax(...)`**  
  Computes AGI, ordinary income, taxable SS, ordinary tax, payroll tax, capital gains tax, penalty tax, total tax, and effective tax rate.

  - Accepts both cumulative year‑to‑date values and baseline actuals from `profile.json`.
  - Returns a dictionary with all components for audit clarity.

- **`_inflate_deductions(deduction)`** → inflates standard deduction by year.
- **`_inflate_brackets_by_year(brackets_by_label)`** → inflates ordinary and payroll brackets.
- **`_inflate_cap_gains_brackets(brackets_by_type)`** → inflates capital gains brackets.
- **`_inflate_social_security_brackets(base_brackets)`** → inflates SS taxability thresholds.
- **`_inflate_irmaa_brackets(base_brackets)`** → inflates IRMAA thresholds and surcharges.
- **`_inflate_base_premiums(base_premiums)`** → inflates Medicare Part B/D base premiums.
- **`_taxable_social_security(year, ss_benefits, agi)`** → calculates taxable SS benefits based on provisional income rules.
- **`_calculate_ordinary_tax(bracket_list, income)`** → applies bracketed tax rates to ordinary income.
- **`_calculate_capital_gains_tax(ordinary_income, gains, brackets)`**
  - Applies capital gains tax using bracketed thresholds.
  - Considers ordinary income floor when determining taxable gains.
  - Iterates through capital gains brackets, applying rates progressively.
  - Returns total capital gains tax owed.

---

#### Taxes Audit Notes

- **Capital gains tax** is applied progressively, with ordinary income acting as a floor for bracket eligibility.
- **Social Security taxability** is capped at maximum taxable benefit, consistent with IRS rules.
- **IRMAA surcharges and Medicare premiums** are modeled explicitly, inflated annually, and doubled for MFJ.
- **Penalty logic** applies a fixed rate to early withdrawal basis.
- **Monthly marginal tax estimation** now derives directly from cumulative logs, eliminating reliance on cached snapshots (`_last_ylog_by_year`).
- All outputs are structured for **audit reproducibility** and can be validated against IRS tables and SSA premium schedules.
- Integration with `ForecastEngine` ensures that withholding and reconciliation are based on **actual year‑to‑date baselines**, preventing cold‑start distortions.

---

### `rules_transactions.py`

Defines transaction classes that apply external data (from `fixed.csv` and `recurring.csv`) to buckets.  
These classes handle inflation adjustments, eligibility rules, and cash fallback logic.

---

#### Rules Transactions Key Classes

- **`RuleTransaction` (abstract base class)**

  - Provides a common interface for all transaction types.
  - Attributes:
    - `is_tax_deferred` → flag for tax‑deferred transactions.
    - `is_taxable` → flag for taxable transactions.
  - Abstract method:
    - `apply(buckets, tx_month)` → must be implemented by subclasses.

- **`FixedTransaction`**

  - Applies one‑time transactions from `fixed.csv`.
  - Parameters:
    - `df` → DataFrame of fixed transactions.
    - `taxable_eligibility` → optional cutoff period for tax‑deferred/tax‑free withdrawals.
    - `description_inflation_modifiers` → inflation multipliers by transaction type.
    - `simulation_start_year` → base year for inflation scaling.
  - Behavior:
    - Matches transactions by `Month`.
    - Adjusts amounts using inflation multipliers.
    - Deposits positive amounts into buckets.
    - Withdraws negative amounts, with pre‑eligibility routing to Cash if needed.
    - Falls back to Cash if bucket withdrawal is insufficient.

- **`RecurringTransaction`**
  - Applies ongoing transactions from `recurring.csv`.
  - Parameters mirror `FixedTransaction`.
  - Behavior:
    - Iterates through rows, checking if `tx_month` falls between `Start Month` and `End Month`.
    - Adjusts amounts using inflation multipliers.
    - Deposits positive amounts into buckets.
    - Withdraws negative amounts, with pre‑eligibility routing to Cash if needed.
    - Falls back to Cash if bucket withdrawal is insufficient.

---

#### Rules Transactions Audit Notes

- Both transaction types integrate with `Bucket` operations (`deposit`, `withdraw`).
- Inflation multipliers ensure expenses grow realistically over time.
- Pre‑eligibility logic enforces IRS rules: withdrawals from tax‑deferred/tax‑free buckets before eligibility are routed to Cash.
- Cash fallback ensures liquidity when buckets cannot cover withdrawals.
- Logging provides warnings when buckets are missing or inflation adjustments fail.
- Ensures reproducibility by applying transactions deterministically based on CSV inputs.

---

### `policy_engine.py`

Implements the **ThresholdRefillPolicy**, which governs how buckets are refilled or liquidated based on thresholds, eligibility rules, and SEPP gating.  
This class consumes configuration from `policies.json` and produces `RefillTransaction` objects for audit clarity.

---

#### Key Class

- **`ThresholdRefillPolicy`**
  - Parameters:
    - `refill_thresholds` → minimum balances required per bucket.
    - `source_by_target` → mapping of source buckets to refill targets.
    - `refill_amounts` → per‑pass refill amounts per target bucket.
    - `liquidation_sources` → ordered list of buckets to liquidate when Cash falls below threshold.
    - `liquidation_targets` → distribution map for liquidation proceeds (e.g., property split).
    - `liquidation_threshold` → minimum Cash balance before liquidation triggers.
    - `taxable_eligibility` → cutoff period for tax‑advantaged withdrawals.
    - `sepp_start_month`, `sepp_end_month` → SEPP gating period for tax‑deferred buckets.
  - Responsibilities:
    - Enforces refill rules when target buckets fall below thresholds.
    - Enforces liquidation rules when Cash falls below threshold.
    - Applies IRS‑aligned gating:
      - **Taxable eligibility** → blocks withdrawals from tax‑deferred/tax‑free buckets before eligibility date.
      - **SEPP gating** → blocks withdrawals from tax‑deferred buckets during SEPP period.
    - Produces `RefillTransaction` objects with flags for tax status and penalty applicability.

---

#### Important Methods

- **`generate_refills(buckets, tx_month)`**

  - Iterates over target buckets and checks thresholds.
  - Pulls funds from source buckets according to configuration.
  - Applies age‑gating and SEPP rules.
  - Emits `RefillTransaction` objects for each transfer.

- **`generate_liquidation(buckets, tx_month)`**
  - Checks Cash balance against liquidation threshold.
  - Iterates over liquidation sources to cover shortfall.
  - Applies SEPP gating and penalty logic.
  - Routes proceeds to targets (Cash or property splits).
  - Emits `RefillTransaction` objects for each liquidation.

---

#### Audit Notes

- All refill and liquidation flows are logged as `RefillTransaction` objects for reproducibility.
- IRS compliance is enforced via **taxable eligibility** and **SEPP gating**.
- Cash shortfalls trigger liquidation in a controlled, auditable sequence.
- Property liquidation supports multi‑target distribution (e.g., mortgage, maintenance, rent).
- Logging provides warnings when buckets are missing or thresholds are unmet.

---

### `policies_transactions.py`

Defines the abstract base class for policy‑driven transactions and concrete implementations such as market gains and property flows.  
These transactions are distinct from rule‑based CSV transactions (`rules_transactions.py`) and are driven by configuration (`policies.json`) and economic factors.

---

#### Policies Transactions Key Classes

- **`PolicyTransaction` (abstract base class)**

  - Provides a common interface for all policy‑driven transactions.
  - Attributes:
    - `is_tax_deferred`, `is_taxable` → flags for tax treatment.
  - Abstract method:
    - `apply(buckets, tx_month)` → must be implemented by subclasses.
  - Getter methods (default return 0, overridden by subclasses):
    - `get_unemployment(tx_month)`
    - `get_salary(tx_month)`
    - `get_social_security(tx_month)`
    - `get_withdrawal(tx_month)`
    - `get_penalty_eligible_withdrawal(tx_month)`
    - `get_realized_gain(tx_month)`
    - `get_taxable_gain(tx_month)`
    - `get_taxfree_withdrawal(tx_month)`
    - `get_fixed_income_interest(tx_month)`
    - `get_fixed_income_withdrawal(tx_month)`

- **`MarketGainTransaction`**

  - Represents gains, losses, or fixed‑income deposits applied to a bucket.
  - Parameters:
    - `bucket_name` → target bucket.
    - `asset_class` → asset type (e.g., Stocks, Fixed‑Income).
    - `amount` → gain/loss amount.
    - `flow_type` → `"gain"`, `"loss"`, or `"deposit"`.
  - Behavior:
    - Deposits gains/losses into the target bucket.
    - Labels flows for audit clarity (`Market Gains`, `Market Losses`, `Fixed Income Interest`).
    - Provides `get_fixed_income_interest()` for taxable interest tracking.

- **`PropertyTransaction`**

  - Models property‑related flows: mortgage, escrow, maintenance, taxes, insurance.
  - Parameters:
    - `property_config` → property details from `policies.json`.
    - `inflation_modifiers` → inflation multipliers by category (taxes, insurance, maintenance).
  - Behavior:
    - Applies monthly maintenance costs (scaled by inflation).
    - Applies mortgage payments (principal + interest).
    - Applies escrow payments (taxes + insurance).
    - Tracks remaining principal and transitions to post‑mortgage escrow logic.
    - Withdraws all payments from the Cash bucket.
  - Internal helper:
    - `_inflated(key, tx_month)` → calculates inflation multiplier for a category.

- **`RefillTransaction`**

  - Internal refill transaction used by `ThresholdRefillPolicy` and liquidation logic.
  - Uses `Bucket.transfer` for clean internal movement.
  - Records tax flags only (tax accounting handled externally).
  - Estimates taxable gains for withdrawals from taxable buckets.
  - Supports penalty logic for tax‑deferred and tax‑free buckets.
  - Provides getters for realized gains, taxable gains, penalty‑eligible withdrawals, tax‑free withdrawals, and fixed‑income withdrawals.

- **`RentTransaction`**

  - Models rental income flows when property is not owned.
  - Withdraws rent from Cash bucket if Property bucket balance is zero.
  - Inflation multipliers scale rent payments over time.
  - Provides `_inflated_amount_for_month()` helper for monthly adjustment.

- **`RequiredMinimumDistributionTransaction`**

  - Models IRS‑mandated RMD withdrawals from tax‑deferred accounts.
  - Parameters:
    - `dob` → date of birth for age calculation.
    - `targets` → distribution percentages across buckets.
    - `start_age` → age when RMDs begin (default 75).
    - `rmd_month` → month when RMD is applied (default December).
    - `monthly_spread` → option to spread RMD across months.
  - Uses IRS divisor table to compute annual RMD amounts.
  - Aggregates balances across tax‑deferred buckets.
  - Distributes withdrawals across target buckets proportionally.
  - Provides getters for withdrawals (tax‑deferred), taxable gains, and penalty‑eligible withdrawals.

- **`RothConversionTransaction`**

  - Models Roth conversions from tax‑deferred to Roth buckets.
  - Parameters:
    - `source_bucket` → tax‑deferred source.
    - `target_bucket` → Roth target.
  - Behavior:
    - Transfers funds from tax‑deferred to Roth bucket.
    - Treated as ordinary income (withdrawal) but not capital gains.
    - Exempt from early withdrawal penalties.
  - Getters:
    - `get_withdrawal()` → converted amount.
    - `get_taxable_gain()` → always 0.
    - `get_penalty_eligible_withdrawal()` → always 0.

- **`SalaryTransaction`**

  - Models earned income flows with merit increases and bonuses.
  - Parameters:
    - `annual_gross` → base salary.
    - `annual_bonus` → annual bonus amount.
    - `merit_increase_rate` → compounded annual merit increase rate.
    - `merit_increase_month` → month when merit increases apply.
    - `bonus_month` → month when bonus is paid.
    - `salary_buckets` → distribution percentages across buckets.
    - `retirement_date` → cutoff period for salary flows.
  - Behavior:
    - Deposits monthly salary into buckets according to distribution.
    - Applies compounded merit increases annually.
    - Distributes annual bonus in the configured month.
    - Stops salary flows after retirement date.
  - Getters:
    - `get_salary()` → monthly salary (excluding tax‑deferred allocations).
    - `get_unemployment()` → always 0.

- **`SEPPTransaction`**

  - Models IRS SEPP (Substantially Equal Periodic Payments) withdrawals.
  - Parameters:
    - `source_bucket` → tax‑deferred source.
    - `target_bucket` → destination bucket.
  - Behavior:
    - Transfers fixed SEPP withdrawal amounts from tax‑deferred to target.
    - SEPP amounts are calculated externally (e.g., ForecastEngine).
    - Records monthly withdrawals for audit.
    - Treated as ordinary income but penalty‑exempt.
  - Getters:
    - `get_withdrawal()` → monthly SEPP withdrawal amount.
    - `get_taxable_gain()` → always 0.
    - `get_penalty_eligible_withdrawal()` → always 0.

- **`SocialSecurityTransaction`**

  - Models Social Security benefit flows for one or more profiles.
  - Parameters:
    - `profiles` → list of profile dicts with DOB, start age, full age, full benefit, payout %, and target bucket.
    - `annual_infl` → inflation multipliers by year.
  - Behavior:
    - Calculates monthly benefit based on start age vs. full retirement age.
    - Applies SSA reduction (early claiming) or enhancement (delayed claiming).
    - Adjusts benefits for inflation and payout percentage.
    - Supports spousal benefit logic (spouse receives up to 50% of full benefit if eligible).
    - Deposits benefits into target bucket(s).
  - Getter:
    - `get_social_security()` → returns total monthly Social Security income across all profiles.

- **`UnemploymentTransaction`**
  - Models unemployment income flows for a fixed period.
  - Parameters:
    - `start_month`, `end_month` → eligibility window.
    - `monthly_amount` → unemployment benefit amount.
    - `target_bucket` → destination bucket for deposits.
  - Behavior:
    - Deposits unemployment income into target bucket if `tx_month` is within eligibility window.
    - Stops deposits once end month is reached.
  - Getters:
    - `get_unemployment()` → monthly unemployment income if eligible.
    - `get_salary()` → always 0 (unemployment is distinct from salary).

---

#### Policies Transactions Audit Notes

- All policy transactions are auditable via FlowTracker and expose structured getters for tax integration.
- Policy transactions are **config‑driven** and integrate with buckets for deposits/withdrawals.
  - Inflation multipliers ensure property, rent, salary, and Social Security flows scale realistically over time.
  - Market gains/losses are labeled for audit clarity and tax treatment.
  - Getter methods allow the tax engine (`TaxCalculator`) to query realized gains, taxable gains, withdrawals, and income streams.
- **PropertyTransaction** enforces mortgage amortization, escrow, and maintenance flows, ensuring IRS‑aligned treatment of property expenses.
- **RefillTransaction** enforces IRS rules for taxable gains and penalties, with internal transfers logged for audit.
- **RentTransaction** ensures liquidity when property is not owned, applying inflation adjustments to rent payments.
- **RequiredMinimumDistributionTransaction (RMD)** enforces IRS compliance with divisor tables, age thresholds, and proportional distribution across targets.
- **RothConversionTransaction** models conversions as ordinary income withdrawals, penalty‑exempt and not capital gains.
- **SalaryTransaction** incorporates merit increases, bonuses, and retirement cutoff, scaling realistically over time.
- **SEPPTransaction** enforces IRS rules for penalty‑exempt periodic withdrawals from tax‑deferred accounts.
- **SocialSecurityTransaction** enforces SSA rules for early/late claiming, spousal benefits, and inflation adjustments.
- **UnemploymentTransaction** provides temporary income replacement, bounded by start/end months.

---

### `forecast_engine.py`

Implements the **ForecastEngine**, the central orchestration class that runs monthly simulations.  
It integrates buckets, rule transactions, policy transactions, refill/liquidation policies, market gains, inflation, and tax calculations into a unified forecast.

---

#### Forecast Engine Key Class

- **`ForecastEngine`**
  - Parameters:
    - `buckets` → initialized bucket objects.
    - `rule_transactions` → list of rule‑driven transactions (`FixedTransaction`, `RecurringTransaction`).
    - `policy_transactions` → list of policy‑driven transactions (salary, SS, RMD, Roth, SEPP, property, etc.).
    - `refill_policy` → `ThresholdRefillPolicy` instance.
    - `market_gains` → `MarketGains` instance.
    - `inflation` → inflation modifiers by year.
    - `tax_calc` → `TaxCalculator` instance.
    - `dob` → date of birth for age calculations.
    - `magi` → dictionary of **actual MAGI values** by year.
    - `retirement_period` → cutoff period for retirement.
    - `sepp_policies` → SEPP configuration (enabled, source, target, start/end months, interest rate).
    - `roth_policies` → Roth conversion configuration.
    - `marketplace_premiums` → ACA marketplace premiums by household type.
  - Responsibilities:
    - Runs monthly forecast loop over ledger.
    - Applies SEPP withdrawals, marketplace premiums, IRMAA premiums.
    - Applies rule and policy transactions.
    - Applies market gains and records monthly returns.
    - Generates refill and liquidation transactions.
    - Updates results and tax records.
    - Produces three DataFrames: records, tax_records, monthly_return_records.

---

#### Forecast Engine Important Methods

- **`run(ledger_df)`**

  - Main loop over forecast months.
  - Applies SEPP, marketplace premiums, IRMAA premiums, rule transactions, policy transactions, market gains, refills, and liquidations.
  - Updates results and logs monthly returns.
  - Returns `(records_df, tax_records_df, monthly_returns_df)`.

- **`_initialize_results()`**

  - Resets records, tax logs, and monthly return records at the start of a run.
  - Seeds YTD baseline from `profile.json` actuals (salary, withdrawals, gains, SS benefits, unemployment, fixed income interest, tax paid).
  - No longer initializes `_last_ylog_by_year` — snapshots are derived directly from current vs. prior month logs.

- **`_get_age_in_years(period)`**

  - Computes age in years at the start of a given period using DOB.

- **`_get_prior_year_end_balance(tx_month, bucket_name)`**

  - Retrieves prior year‑end balance for a bucket from records.

- **`_calculate_sepp_amortized_annual_payment(principal, interest_rate, life_expectancy)`**

  - Calculates annual SEPP payment using IRS amortization method.

- **`_apply_sepp_withdrawal(tx_month)`**

  - Applies SEPP withdrawals if enabled and within configured period.
  - Caches monthly payment at SEPP start using amortization method.
  - Creates and applies `SEPPTransaction`.

- **`_get_uniform_life_expectancy(age)`**

  - Returns IRS uniform life expectancy divisor for SEPP calculations.

- **`_apply_marketplace_premiums(tx_month)`**

  - Applies ACA marketplace premiums if before retirement and under age 65.
  - Caps premiums at 8.5% of prior MAGI.
  - Withdraws capped premium from Cash bucket.

- **`_apply_irmaa_premiums(tx_month)`**

  - Applies Medicare Part B/D premiums and IRMAA surcharges for age ≥ 65.
  - Uses prior MAGI (two years back) to determine surcharge bracket.
  - Doubles cost for married filing jointly.
  - Withdraws premiums from Cash bucket.

- **`_get_minus_2_tax_record(tx_month)`**

  - Retrieves prior MAGI (two years back) for IRMAA and ACA calculations.
  - Sources from `self.magi` if available, otherwise from `tax_records`.
  - Raises error if MAGI is missing for required year.

- **`_apply_rule_transactions(buckets, tx_month)`**

  - Applies all rule‑driven transactions (`FixedTransaction`, `RecurringTransaction`) for the given month.

- **`_apply_policy_transactions(buckets, tx_month)`**

  - Applies all policy‑driven transactions except Roth conversions and SEPP (those are handled separately).

- **`_apply_market_gain_transactions(gain_txns, buckets, tx_month)`**

  - Applies market gain transactions using `TaxCalculator` for taxable gain attribution.

- **`_apply_refill_transactions(refill_txns, buckets, tx_month)`**

  - Applies refill transactions generated by `ThresholdRefillPolicy`.

- **`_apply_liquidation_transactions(liq_txns, buckets, tx_month)`**

  - Applies liquidation transactions generated by `ThresholdRefillPolicy`.

- **`_update_results(forecast_month, buckets, all_policy_txns)`**

  - Central monthly update routine:
    - Accumulates tax inputs from all transactions.
    - Updates yearly tax logs.
    - Updates tax estimate and monthly withholding.
    - Applies year‑end reconciliation in December.
    - Records snapshot of bucket balances.

- **`_accumulate_monthly_tax_inputs(tx_month, txs)`**

  - Aggregates monthly tax inputs across all transactions:
    - Fixed income interest and withdrawals.
    - Unemployment income.
    - Salary.
    - Social Security.
    - Tax‑deferred withdrawals.
    - Realized gains.
    - Taxable gains.
    - Penalty‑eligible withdrawals.
    - Tax‑free withdrawals.
  - Returns tuple of all values for downstream tax logging.

- **`_update_tax_logs(year, yearly_log, …)`**

  - Updates yearly tax log dictionary with accumulated monthly values.
  - Ensures categories exist and increments totals:
    - Salary, unemployment, Social Security.
    - Tax‑deferred withdrawals, Roth conversions.
    - Fixed income interest and withdrawals.
    - Realized gains, taxable gains.
    - Tax‑free withdrawals, penalty tax.

- **`_update_tax_estimate_if_needed(forecast_date)`**

  - Computes year‑to‑date tax estimate using `TaxCalculator`.
  - Compares current cumulative log against prior month’s log (no cached snapshots).
  - Incorporates YTD baseline actuals from `profile.json`.
  - Updates `monthly_tax_drip` to reflect marginal liability for the current month.

- **`_withhold_monthly_taxes(tx_month, buckets)`**

  - Transfers monthly tax drip from Cash to Tax Collection bucket.
  - Ensures ongoing withholding aligns with estimated liability.

- **`_estimate_roth_headroom(...)`**

  - Iteratively tests Roth conversion amounts against a maximum effective tax rate.
  - Uses `TaxCalculator` to compute tax liability at each step.
  - Returns maximum Roth conversion amount allowed without exceeding configured tax rate.

- **`_apply_roth_conversion_if_eligible(buckets, forecast_month, ylog)`**

  - Applies Roth conversions if policy permits and source bucket meets thresholds.
  - Determines phase based on age and cutoff rules in `roth_policies`.
  - Uses `_estimate_roth_headroom` to calculate conversion headroom.
  - Creates and applies `RothConversionTransaction` if eligible.
  - Returns converted amount.

- **`_apply_year_end_reconciliation(forecast_month, yearly_tax_log, buckets, tax_records)`**

  - Performs year‑end reconciliation:
    - Applies Roth conversion using finalized year‑end snapshot.
    - Computes final tax liability with `TaxCalculator`.
    - Pays taxes from Tax Collection bucket, then Cash if needed.
    - Handles leftover balances in Tax Collection.
    - Computes total withdrawals and withdrawal rate.
    - Logs detailed tax record for the year (AGI, taxable income, total tax, gains, conversions, effective tax rate, withdrawal rate).

- **`_record_snapshot(forecast_date, buckets)`**
  - Records monthly snapshot of all bucket balances.
  - Appends snapshot to `self.records` for audit and visualization.

---

#### ForecastEngine Audit Notes

- ForecastEngine orchestrates **monthly simulation flows**, integrating buckets, transactions, market gains, refills, liquidations, and taxes.
- All results are **auditable via structured records**: monthly snapshots, tax logs, and return records.
- Tax inputs (salary, unemployment, Social Security, withdrawals, gains, penalties, etc.) are consistently aggregated through structured getters.
- Yearly tax logs ensure reproducibility of IRS‑aligned categories (ordinary income, capital gains, Social Security, Roth conversions, penalties).
- **Tax estimation now uses actual YTD baselines** from `profile.json`, eliminating cold‑start distortions.
- **No cached snapshots**: marginal tax is calculated by comparing current vs. prior month logs directly.
- SEPP withdrawals, marketplace premiums, and IRMAA surcharges are applied in compliance with IRS and SSA rules.
- Roth conversion logic enforces **policy‑driven thresholds** (age cutoffs, source balances, max tax rates) and calculates headroom before applying conversions.
- Year‑end reconciliation finalizes Roth conversions, computes tax liabilities, and records withdrawal rates and portfolio values.
- Monthly snapshots preserve bucket balances for downstream visualization and audit.

**Specialized audit notes:**

- **SEPP logic**: IRS amortization method ensures penalty‑exempt withdrawals.
- **Marketplace premiums**: capped at 8.5% of prior MAGI, withdrawn from Cash.
- **IRMAA premiums**: surcharge brackets applied based on prior MAGI, doubled for MFJ.
- **Roth conversions**: ordinary income withdrawals, penalty‑exempt, applied only within configured headroom.
- **Year‑end reconciliation**: ensures taxes are paid from Tax Collection first, then Cash, with leftover handling logged.

---

### `visualizations.py`

Provides helper functions for chart construction, color assignment, and data normalization.  
All visualization is built using **Plotly**, with outputs saved as CSV and HTML chart files for audit clarity and reproducibility.

---

#### Visualization Charting and Export Functions

- **`plot_example_income_taxes(taxes_df, trial, show=True, save=False, export_path="export/", ts="")`**

  - Renders stacked bar + marker charts for **income** and **taxes** for one trial.
  - Inputs:
    - `taxes_df` → DataFrame with yearly tax results.
    - `trial` → trial index (used in titles and filenames).
    - `show` → whether to display charts interactively.
    - `save` → whether to export CSV and HTML files.
    - `export_path` → directory for exports.
    - `ts` → timestamp suffix for filenames.
  - Behavior:
    - Income chart:
      - Bars for unemployment, salary, Social Security, withdrawals, gains, conversions.
      - Markers for AGI, taxable income, taxable gains, taxable SS, withdrawal rate, effective tax rate.
      - Dual y‑axes: dollars (primary) and percentages (secondary).
    - Taxes chart:
      - Bars for ordinary, payroll, capital gains, and penalty taxes.
      - Markers for total tax and effective tax rate.
      - Dual y‑axes: dollars (primary) and percentages (secondary).
    - Show/save logic:
      - Displays charts if `show=True`.
      - Saves CSV of tax data and HTML charts if `save=True`.

- **`plot_example_monthly_expenses(flow_df, trial, ts, show, save, export_path="export/")`**

  - Renders stacked bar chart of monthly cash withdrawals by category, with overlay line for total withdrawals.
  - Inputs:
    - `flow_df` → DataFrame of flow records.
    - `trial` → trial index.
    - `ts` → timestamp suffix.
    - `show` → whether to display chart.
    - `save` → whether to export CSV and HTML.
    - `export_path` → directory for exports.
  - Behavior:
    - Filters withdrawals from Cash bucket.
    - Aggregates by month and target category.
    - Assigns consistent colors via `assign_colors_by_base_label`.
    - Builds stacked bar chart with hover labels.
    - Adds overlay line for total monthly withdrawals.
    - Show/save logic:
      - Displays chart if `show=True`.
      - Saves CSV of monthly totals and HTML chart if `save=True`.

- **`plot_example_transactions(flow_df, trial, show=True, save=False, export_path="export/", ts="")`**

  - Renders a **Sankey diagram** of annual transaction flows for one trial.
  - Inputs:
    - `flow_df` → DataFrame of flow records (source, target, type, amount).
    - `trial` → trial index.
    - `show` → whether to display chart interactively.
    - `save` → whether to export CSV and HTML files.
    - `export_path` → directory for exports.
    - `ts` → timestamp suffix for filenames.
  - Behavior:
    - Aggregates flows by year, source, target, and type.
    - Normalizes gain/loss rows into net flows.
    - Computes node volumes and sorts nodes by activity.
    - Assigns consistent colors to nodes and flow types:
      - Green for deposits/gains.
      - Red for withdrawals/losses.
      - Blue for transfers.
    - Builds Sankey traces per year with slider to toggle visibility.
    - Layout includes title, slider steps, and margins.
    - Show/save logic:
      - Displays chart if `show=True`.
      - Saves CSV of transactions and HTML Sankey chart if `save=True`.

- **`plot_example_transactions_in_context(trial, forecast_df, flow_df, ts, show, save, export_path="export/")`**

  - Renders a **Sankey diagram** showing transactions in the context of year‑end balances.
  - Inputs:
    - `forecast_df` → bucket balances at year‑end (December).
    - `flow_df` → transaction flows for each year.
    - `trial` → trial index.
    - `ts` → timestamp suffix.
    - `show` → whether to display chart.
    - `save` → whether to export HTML.
  - Behavior:
    - Aligns flows with year‑end balances for each bucket.
    - Builds Sankey nodes for prior year vs. current year (`bucket@year`).
    - Routes deposits, withdrawals, transfers, gains, and losses between nodes.
    - Assigns consistent colors to nodes and flows.
    - Provides slider to toggle visibility across years.
    - Show/save logic:
      - Displays chart if `show=True`.
      - Saves HTML Sankey chart if `save=True`.

- **`plot_example_forecast(trial, hist_df, forecast_df, dob, ts, show, save, export_path="export/")`**

  - Renders a **bucket‑by‑bucket forecast chart** with net worth and age overlays.
  - Inputs:
    - `hist_df` → historical balances.
    - `forecast_df` → forecasted balances.
    - `dob` → date of birth (for age trace).
    - `trial` → trial index.
    - `ts` → timestamp suffix.
    - `show` → whether to display chart.
    - `save` → whether to export CSV and HTML.
  - Behavior:
    - Combines historical and forecast data into one DataFrame.
    - Computes net worth as sum of all buckets.
    - Adds “Age” trace based on DOB and month offsets.
    - Plots each bucket as a line, with hover showing dollar value and percent share of net worth.
    - Assigns consistent colors to bucket traces.
    - Show/save logic:
      - Displays chart if `show=True`.
      - Saves CSV of balances and HTML chart if `save=True`.

- **`plot_historical_balance(hist_df, ts, show, save, export_path="export/")`**

  - Renders historical net worth chart with monthly and annual gain/loss overlays.
  - Inputs:
    - `hist_df` → DataFrame of historical bucket balances.
    - `ts` → timestamp suffix.
    - `show` → whether to display chart.
    - `save` → whether to export HTML.
  - Behavior:
    - Computes total net worth from all buckets.
    - Calculates monthly and annual percent changes.
    - Plots:
      - Line trace for net worth.
      - Bars for monthly and annual gains/losses (green/red, blue/orange).
    - Show/save logic:
      - Displays chart if `show=True`.
      - Saves HTML chart if `save=True`.

- **`plot_historical_bucket_gains(hist_df, ts, show, save, export_path="export/")`**

  - Renders historical monthly gain/loss chart per bucket.
  - Inputs:
    - `hist_df` → DataFrame of historical bucket balances.
    - `ts` → timestamp suffix.
    - `show` → whether to display chart.
    - `save` → whether to export HTML.
  - Behavior:
    - Computes monthly percent change for each bucket.
    - Plots:
      - Marker trace for net worth change.
      - Bar traces for each bucket, colored by gain/loss magnitude (green/red intensity).
    - Hover shows percent change and corresponding balance.
    - Show/save logic:
      - Displays chart if `show=True`.
      - Saves HTML chart if `save=True`.

- **`plot_mc_monthly_returns(mc_monthly_returns_df, ts, show, save, export_path="export/")`**

  - Renders scatter plots of monthly return distributions for each asset class across trials.
  - Inputs:
    - `mc_monthly_returns_df` → DataFrame of Monte Carlo monthly returns.
    - `ts` → timestamp suffix.
    - `show` → whether to display chart.
    - `save` → whether to export CSV and HTML.
  - Behavior:
    - Extracts asset classes from `monthly_returns` column.
    - Plots scenario‑colored scatter points (Low, Average, High).
    - Hover shows month, trial number, inflation rate, scenario, and return.
    - Title includes confidence color based on number of trials (green ≥1000, blue ≥100, red otherwise).
    - Show/save logic:
      - Displays chart if `show=True`.
      - Saves CSV of returns and HTML chart per asset class if `save=True`.

- **`plot_mc_networth(mc_networth_df, sim_examples, dob, eol, summary, ts, show, save, export_path="export/")`**

  - Renders Monte Carlo net worth forecast with percentile overlays, example trials, and property liquidation metrics.
  - Inputs:
    - `mc_networth_df` → DataFrame of net worth trajectories across trials.
    - `sim_examples` → array of trial indices to highlight.
    - `dob` → date of birth (for age calculations).
    - `eol` → end‑of‑life period (for age metrics).
    - `summary` → dictionary of property liquidation statistics (min/avg/max years, counts).
    - `ts` → timestamp suffix.
    - `show` → whether to display chart.
    - `save` → whether to export CSV and HTML.
    - `export_path` → directory for exports.
  - Behavior:
    - Computes percentiles (15th, median, 85th) and mean across trials.
    - Calculates age metrics (20 years before EOL, 10 years before EOL, at EOL).
    - Computes property liquidation ages and percentage of simulations with liquidation.
    - Plots:
      - Example trial traces (purple for highlighted, gray for others).
      - Percentile lines (p15, median, p85).
      - Invisible age trace for hover.
      - Annotations at end‑of‑life for percentile values.
    - Title includes:
      - Number of trials (confidence color coded).
      - Positive net worth probabilities at age milestones.
      - Property liquidation statistics (percentage and ages).
    - Show/save logic:
      - Displays chart if `show=True`.
      - Saves CSV of net worth trajectories and HTML chart if `save=True`.

- **`plot_mc_totals_and_rates(mc_tax_df, sim_examples, ts, show, save, export_path="export/")`**

  - Renders Monte Carlo charts of **total taxes** and **total withdrawals** per trial, with effective tax rate and withdrawal rate overlays.
  - Inputs:
    - `mc_tax_df` → DataFrame of Monte Carlo tax results (multi‑index columns).
    - `sim_examples` → array of trial indices to highlight.
    - `ts` → timestamp suffix.
    - `show` → whether to display charts.
    - `save` → whether to export CSV and HTML.
  - Behavior:
    - Aggregates total taxes and withdrawals across trials.
    - Computes percentiles (p15, median, p85, max) for both totals and rates.
    - Builds bar charts with highlighted trials (purple) and others (gray).
    - Adds percentile reference lines on both primary (dollars) and secondary (percentages) axes.
    - Show/save logic:
      - Displays charts if `show=True`.
      - Saves CSV of totals and HTML charts if `save=True`.

- **`plot_mc_taxable_balances(mc_taxable_df, sim_examples, sepp_end_month, ts, show, save, export_path="export/")`**
  - Renders Monte Carlo chart of **taxable balances** at a specific month (e.g., Jan 2035).
  - Inputs:
    - `mc_taxable_df` → DataFrame of taxable balances per trial.
    - `sim_examples` → array of trial indices to highlight.
    - `sepp_end_month` → month label for chart title.
    - `ts` → timestamp suffix.
    - `show` → whether to display chart.
    - `save` → whether to export CSV and HTML.
  - Behavior:
    - Computes percentiles (p15, median, p85) from full dataset.
    - Filters out top 10% of trials for display (to reduce skew).
    - Builds bar chart with highlighted trials (purple) and others (gray).
    - Adds percentile reference lines and annotations.
    - Title includes:
      - Number of trials (confidence color coded).
      - Percentage of trials with positive taxable balance (color coded).
    - Show/save logic:
      - Displays chart if `show=True`.
      - Saves CSV of balances and HTML chart if `save=True`.

---

#### Visualization Helper Functions

- **`COLOR_PALETTE`**

  - Predefined list of hex colors used for consistent chart styling.
  - Ensures reproducible color assignment across trials and scenarios.

- **`label_color_map`**

  - Global dictionary mapping base labels to assigned colors.
  - Populated dynamically by `assign_colors_by_base_label`.

- **`add_percentile_lines(fig, trial_labels, percentiles, axis, labels, colors, dash="dash")`**

  - Adds percentile reference lines and annotations to a Plotly figure.
  - Supports primary (`y`) and secondary (`y2`) axes.
  - Annotates values with labels and formatted text (currency or percentage).

- **`base_label(label)`**

  - Normalizes labels by stripping suffixes like “Gains” or “Losses”.
  - Used for consistent color assignment and legend clarity.

- **`build_chart(title, trial_labels, bar_values, bar_colors, bar_hovertext, yaxis_title, yaxis2_title)`**

  - Constructs a base Plotly bar chart with dual y‑axes.
  - Configures layout: title, hover labels, unified hover mode, overlay bars.
  - Formats primary axis as currency and secondary axis as percentage.

- **`normalize_source(label)`**

  - Simplifies source labels by removing “Gains” or “Losses” suffixes.
  - Used for consistent grouping in charts.

- **`assign_colors_by_base_label(labels, color_palette)`**

  - Assigns colors to labels based on normalized base label.
  - Ensures consistent color mapping across multiple charts.
  - Returns list of colors aligned with input labels.

- **`coerce_month_column(df)`**
  - Ensures the `Month` column is standardized to `datetime64[ns]` at month‑end.
  - Handles inputs as `pd.Period`, `pd.Timestamp`, or generic datetime.
  - Guarantees consistent time axis for charts and CSV exports.

---

#### Visualization Audit Notes

- Visualization helpers ensure **consistent labeling, coloring, and axis formatting** across all charts.
- Percentile overlays (p15, median, p85) provide clear scenario comparison and reproducibility across trials.
- Dual y‑axes allow simultaneous display of dollar values and percentage rates where relevant.
- Month coercion ensures reproducibility in CSV and HTML outputs.
- All charts are designed for **audit clarity**, with explicit labels, hover text, and reference lines.
- CSV/HTML exports preserve both tabular and interactive views, ensuring reproducibility and presentation quality.
- Logging records export paths for traceability.

**Specialized chart notes:**

- **Sankey diagrams**: visualize net flows between buckets, normalize gains/losses, order nodes by volume, and use color coding to distinguish deposits, withdrawals, transfers, gains, and losses. Sliders allow year‑by‑year inspection.
- **Transactions in context**: align flows with year‑end balances for audit clarity.
- **Forecast charts**: provide bucket‑level visibility, net worth trajectory, and age overlays for interpretability.
- **Historical charts**: deliver retrospective audit clarity of net worth and bucket‑level performance.
- **Monte Carlo charts**: visualize distributions of returns, net worth, taxes, withdrawals, and taxable balances across scenarios and trials.
  - Net worth charts highlight probabilistic retirement outcomes, example trials, age metrics, and property liquidation statistics.
  - Totals and rates charts show distributional clarity of tax burdens and withdrawal rates.
  - Taxable balance charts highlight sustainability of taxable accounts at critical milestones (e.g., SEPP end).
  - Scenario color coding (green/red for gains/losses, scenario colors for returns) ensures interpretability.
  - Highlighted trials allow auditors to trace specific scenarios.

---

## 📚 Related Pages

- [Architecture Overview](../docs/architecture.md)
- [Simulation Logic](../docs/simulation_logic.md)
- [Visualization Guide](../docs/visualization.md)
- [Usage Guide](../docs/usage.md)
- [Configuration Reference](../docs/configuration.md)
