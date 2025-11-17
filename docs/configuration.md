# ⚙️ Configuration Reference

Nomad Wealth is **policy‑first**: all simulation behavior is driven by declarative configuration files. This page documents the JSON and CSV schemas that define buckets, policies, tax brackets, seed balances, and transactions.

---

## 🔑 Getting Started: Basic vs. Recommended vs. Advanced

### BASIC

To run a personalized simulation, you should revise these files:

- **`profile.json`** → defines birth month, MAGI, and simulation horizon (end month).
- **`balance.csv`** → seed buckets and their balances. These need to align to buckets defined in `buckets.json`. Forecasting starts in the month after the last month in `balance.csv`.
- **`recurring.csv`** → ongoing monthly expenses (e.g., insurance, food, utilities). Use today dollar amounts. Types need to align to category profiles in `inflation_rates.json` for proper inflation over the years.
- **`fixed.csv`** → one‑time events (e.g., tuition, travel). File is required, but may be empty. Use today dollar amounts. Types need to align to category profiles in `inflation_rates.json` for proper inflation over the years.

### RECOMMENDED

For meaningful results, you should also review and revise:

- **`buckets.json`** → defines portfolio buckets and sub‑holdings. **Note**: Align with `balance.csv`.
- **`policies.json`** → defines salary, social security, property details for mortgage payments, and unemployment. **Note**: Update salary, social security, property details and unemployment values as needed.
- **`tax_brackets.json`** → defaulting to Married‑Filing‑Jointly, defines federal and Oregon state tax brackets. **Note**: Code changes are needed for other filing types or states; contact me if interested.
- **`marketplace_premiums.json`** → healthcare premiums for marketplace plans. **Note**: update premium amounts as needed.

### ADVANCED

For deeper scenario analysis and IRS‑aligned modeling, configure:

- **`buckets.json`** → defines portfolio buckets and sub‑holdings. **Note**: Modify sub-holdings per bucket to drive forecasted gains based on your investment strategy.
- **`policies.json`** → defines refill rules, liquidation hierarchy, RMD, 3-phase roth conversion model, sepp withdrawals. **Note**: Update policies to tailor to your goals.
- **`inflation_rates.json`** → baseline inflation + category profiles. **Note**: currently based on 2000-2025 data. Update as needed.
- **`inflation_thresholds.json`** + **`gain_table.json`** → asset class return regimes for Monte Carlo sampling. **Note**: currently based on 2000-2025 data. Update as needed.

---

## 📂 JSON Configuration

### Profiles

Defines the simulation timeframe and baseline income assumptions. This file is consumed during staging (`stage_init_components`) to determine retirement eligibility, SEPP gating, and IRMAA premium thresholds.

Example (`profile.json`):

```json
{
  "Birth Month": "1975-04",
  "End Month": "2065-12",
  "MAGI": {
    "2023": 200000,
    "2024": 204000,
    "2025": 208000
  }
}
```

---

### 🔑 Profiles Field Definitions

- **Birth Month** → start of simulation, expressed as `YYYY-MM`.
- **End Month** → end of simulation horizon, expressed as `YYYY-MM`.
- **MAGI** → dictionary of Modified Adjusted Gross Income values by year.
  - Keys are years (`2023`, `2024`, `2025`).
  - Values are annual MAGI amounts.
  - Used for IRMAA premium calculations and tax logic.

---

### 🧾 Profiles Audit Notes

- Birth Month is used to calculate retirement eligibility (e.g., age 59.5 for penalty‑free withdrawals).
- End Month defines the final forecast period.
- MAGI values feed into IRMAA thresholds and Medicare premium adjustments.
- All dates are parsed into `pandas.Period("M")` for monthly granularity.
- Audit clarity: profiles must be updated annually to reflect current MAGI values.

---

### Buckets

Defines accounts and their attributes. Each bucket must have a corresponding entry in `buckets.json`.

Example (`buckets.json`):

```json
{
  "Cash": {
    "holdings": [{ "asset_class": "Cash", "weight": 1.0 }],
    "can_go_negative": true,
    "allow_cash_fallback": false,
    "bucket_type": "cash"
  },
  "CD Ladder": {
    "holdings": [
      { "asset_class": "Fixed-Income", "weight": 0.995 },
      { "asset_class": "Cash", "weight": 0.005 }
    ],
    "can_go_negative": false,
    "allow_cash_fallback": false,
    "bucket_type": "taxable"
  },
  "Brokerage": {
    "holdings": [
      { "asset_class": "Fixed-Income", "weight": 0.32 },
      { "asset_class": "Stocks", "weight": 0.66 },
      { "asset_class": "Cash", "weight": 0.02 }
    ],
    "can_go_negative": false,
    "allow_cash_fallback": false,
    "bucket_type": "taxable"
  },
  "Tax-Deferred": {
    "holdings": [
      { "asset_class": "Stocks", "weight": 0.9 },
      { "asset_class": "Fixed-Income", "weight": 0.05 },
      { "asset_class": "Cash", "weight": 0.05 }
    ],
    "can_go_negative": false,
    "allow_cash_fallback": false,
    "bucket_type": "tax_deferred"
  },
  "Tax-Free": {
    "holdings": [
      { "asset_class": "Stocks", "weight": 0.45 },
      { "asset_class": "Fixed-Income", "weight": 0.45 },
      { "asset_class": "Cash", "weight": 0.1 }
    ],
    "can_go_negative": false,
    "allow_cash_fallback": false,
    "bucket_type": "tax_free"
  },
  "Health Savings Account": {
    "holdings": [
      { "asset_class": "Stocks", "weight": 0.1 },
      { "asset_class": "Fixed-Income", "weight": 0.85 },
      { "asset_class": "Cash", "weight": 0.05 }
    ],
    "can_go_negative": false,
    "allow_cash_fallback": true,
    "bucket_type": "other"
  },
  "Vehicles": {
    "holdings": [{ "asset_class": "Vehicles", "weight": 1.0 }],
    "can_go_negative": false,
    "allow_cash_fallback": false,
    "bucket_type": "other"
  },
  "Property": {
    "holdings": [
      { "asset_class": "Property", "weight": 1.0, "cost_basis": 388000 }
    ],
    "can_go_negative": false,
    "allow_cash_fallback": false,
    "bucket_type": "property"
  },
  "529K": {
    "holdings": [
      { "asset_class": "Stocks", "weight": 0.5 },
      { "asset_class": "Fixed-Income", "weight": 0.5 }
    ],
    "can_go_negative": false,
    "allow_cash_fallback": true,
    "bucket_type": "other"
  },
  "SEPP IRA": {
    "holdings": [
      { "asset_class": "Fixed-Income", "weight": 0.4 },
      { "asset_class": "Stocks", "weight": 0.6 }
    ],
    "can_go_negative": false,
    "allow_cash_fallback": false,
    "bucket_type": "tax_deferred"
  },
  "Tax Collection": {
    "holdings": [{ "asset_class": "Cash", "weight": 1.0 }],
    "can_go_negative": false,
    "allow_cash_fallback": true,
    "bucket_type": "other"
  }
}
```

---

### 🔑 Buckets Field Definitions

- **`holdings`** → list of asset allocations with weights (must sum to ~1.0).
  - Optional: `cost_basis` for property or other assets.
- **`can_go_negative`** → allows overdrafts (e.g., Cash bucket).
- **`allow_cash_fallback`** → allows automatic fallback to Cash if bucket is insufficient.
- **`bucket_type`** → classification:
  - `cash` → liquid cash bucket.
  - `taxable` → brokerage or CD ladder accounts.
  - `tax_deferred` → retirement accounts (401k, IRA, SEPP IRA).
  - `tax_free` → Roth or other tax‑free accounts.
  - `property` → real estate holdings with explicit cost basis.
  - `other` → vehicles, HSAs, 529K, or miscellaneous accounts.

---

### 🧾 Buckets Audit Notes

- Buckets are seeded from the last row of `balance.csv` via `seed_buckets_from_config`.
- `create_bucket` ensures rounding drift is corrected when allocating holdings.
- A **Tax Collection bucket** is always present for withholding and settlement.
- Property buckets should include `cost_basis` for IRS compliance.
- Cash bucket may allow negative balances to model overdrafts.

---

### Policies

Defines refill, liquidation, salary, retirement, and special rules. These policies drive how transactions, withdrawals, and conversions are applied in the simulation.

Example (`policies.json`):

```json
{
  "Refill": {
    "Thresholds": { "Cash": 30000 },
    "Amounts": { "Cash": 20000 },
    "Sources": { "Cash": ["SEPP IRA", "Tax-Deferred", "Brokerage", "Tax-Free"] }
  },
  "Liquidation": {
    "Threshold": -15000,
    "Sources": ["CD Ladder", "Tax-Free", "Vehicles", "Property"],
    "Targets": { "Cash": 0.2, "Brokerage": 0.8 }
  },
  "Salary": {
    "Targets": { "Cash": 0.9, "Tax-Deferred": 0.1 },
    "Annual Gross Income": 180000,
    "Annual Bonus Month": "2026-04",
    "Annual Bonus Amount": 15000,
    "Annual Merit Increase Rate": 0.025,
    "Annual Merit Increase Month": "2026-03",
    "Retirement Month": "2033-12"
  },
  "Social Security": [
    {
      "Profile": "p1",
      "DOB": "1975-04",
      "Target": "Cash",
      "Full Age": "67",
      "Full Benefit": 4058,
      "Start Age": "67",
      "Percentage Payout": 0.8
    },
    {
      "Profile": "p2",
      "DOB": "1978-07",
      "Target": "Cash",
      "Full Age": "67",
      "Full Benefit": 1569,
      "Start Age": "67",
      "Percentage Payout": 0.8
    }
  ],
  "RMD": {
    "Targets": { "Cash": 0.2, "CD Ladder": 0.4, "Brokerage": 0.4 }
  },
  "Roth Conversions": {
    "early": {
      "Max Tax Rate": 0.15,
      "Max Conversion Amount": 50000,
      "Tax Source Threshold": 500000,
      "Tax Source Name": "Brokerage",
      "Allow Conversion": true,
      "Cutoff Age": 60
    },
    "prime": {
      "Max Tax Rate": 0.2,
      "Max Conversion Amount": 80000,
      "Tax Source Threshold": 1200000,
      "Tax Source Name": "Tax-Deferred",
      "Allow Conversion": true,
      "Cutoff Age": 80
    },
    "late": {
      "Max Tax Rate": 0.2,
      "Max Conversion Amount": 100000,
      "Tax Source Threshold": 800000,
      "Tax Source Name": "Tax-Deferred",
      "Allow Conversion": true,
      "Cutoff Age": 100
    }
  },
  "SEPP": {
    "Enabled": false,
    "Start Month": "2029-10",
    "End Month": "2034-09",
    "Interest Rate": 0.05,
    "Source": "SEPP IRA",
    "Target": "Cash"
  },
  "Property": {
    "Market Value": 550000,
    "Annual Maintenance": 0.0075,
    "Remaining Principal": 247102.54,
    "Mortgage APR": 0.05375,
    "Monthly Principal and Interest": 2666.43,
    "Monthly Taxes": 724.0,
    "Monthly Insurance": 169.4,
    "Monthly Rent": 2500
  },
  "Unemployment": {
    "Start Month": "2034-01",
    "End Month": "2034-07",
    "Monthly Amount": "4000",
    "Target": "Cash"
  }
}
```

---

### 🔑 Policies Field Definitions

- **Refill**

  - `Thresholds` → minimum balances to maintain (e.g., Cash ≥ 30,000).
  - `Amounts` → refill increments when thresholds are breached.
  - `Sources` → buckets tapped to refill targets.

- **Liquidation**

  - `Threshold` → minimum balance before liquidation triggers.
  - `Sources` → buckets liquidated in order.
  - `Targets` → distribution of liquidation proceeds across buckets.

- **Salary**

  - `Targets` → allocation of salary into buckets (e.g., 90% Cash, 10% Tax‑Deferred).
  - `Annual Gross Income` → base salary.
  - `Annual Bonus Month` / `Annual Bonus Amount` → bonus timing and value.
  - `Annual Merit Increase Rate` / `Month` → annual raise percentage and timing.
  - `Retirement Month` → month salary stops.

- **Social Security**

  - Array of profiles (one per person).
  - `DOB` → date of birth.
  - `Target` → bucket receiving benefits.
  - `Full Age` / `Full Benefit` → baseline entitlement.
  - `Start Age` → age benefits begin.
  - `Percentage Payout` → fraction of full benefit taken.

- **RMD (Required Minimum Distribution)**

  - `Targets` → distribution of mandatory withdrawals across buckets.

- **Roth Conversions**

  - Multiple phases (`early`, `prime`, `late`).
  - Each defines max tax rate, conversion amount, source thresholds, and cutoff age.
  - `Allow Conversion` → enables/disables conversions.

- **SEPP (Substantially Equal Periodic Payments)**

  - `Enabled` → toggle for IRS 72(t) withdrawals.
  - `Start Month` / `End Month` → duration of SEPP plan.
  - `Interest Rate` → used in SEPP calculation.
  - `Source` / `Target` → buckets for SEPP transfers.

- **Property**

  - `Market Value` → current property valuation.
  - `Annual Maintenance` → fraction of value spent annually.
  - `Remaining Principal` → outstanding mortgage balance.
  - `Mortgage APR` → loan interest rate.
  - `Monthly Principal and Interest` → scheduled mortgage payment.
  - `Monthly Taxes` / `Insurance` → fixed monthly costs.
  - `Monthly Rent` → rental income if applicable.

- **Unemployment**
  - `Start Month` / `End Month` → duration of unemployment benefits.
  - `Monthly Amount` → benefit amount.
  - `Target` → bucket receiving benefits.

---

### 🧾 Policies Audit Notes

- Policies are consumed by `stage_init_components` and wired into the `ForecastEngine`.
- Refill and liquidation rules enforce liquidity thresholds.
- Salary and Social Security profiles model income streams.
- RMD and SEPP enforce IRS withdrawal rules.
- Roth conversions model tax‑optimized transfers across phases.
- Property policy integrates mortgage, maintenance, and rental flows.
- Unemployment policy allows temporary income replacement.

---

### 📂 Tax Brackets

Defines IRS‑aligned brackets, payroll taxes, capital gains, Social Security taxability, and Medicare premiums. These rules are consumed by the `TaxCalculator` and applied in the monthly forecast loop.

Example (`tax_brackets.json`):

```json
{
  "Standard Deduction": 31500,
  "Ordinary": {
    "Federal 2025": [
      { "min_salary": 0, "tax_rate": 0.1 },
      { "min_salary": 22000, "tax_rate": 0.12 },
      { "min_salary": 89450, "tax_rate": 0.22 },
      { "min_salary": 190750, "tax_rate": 0.24 },
      { "min_salary": 364200, "tax_rate": 0.32 },
      { "min_salary": 462500, "tax_rate": 0.35 },
      { "min_salary": 751600, "tax_rate": 0.37 }
    ],
    "Oregon State 2025": [
      { "min_salary": 0, "tax_rate": 0.0475 },
      { "min_salary": 8601, "tax_rate": 0.0675 },
      { "min_salary": 21501, "tax_rate": 0.0875 },
      { "min_salary": 250000, "tax_rate": 0.099 }
    ],
    "Portland Metro SHS 2025": [{ "min_salary": 200000, "tax_rate": 0.01 }]
  },
  "Payroll Specific": {
    "Social Security 2025": [
      { "min_salary": 0, "tax_rate": 0.062 },
      { "min_salary": 176100, "tax_rate": 0.0 }
    ],
    "Medicare 2025": [
      { "min_salary": 0, "tax_rate": 0.0145 },
      { "min_salary": 200000, "tax_rate": 0.0235 }
    ]
  },
  "Capital Gains": {
    "long_term": [
      { "min_salary": 0, "tax_rate": 0.0 },
      { "min_salary": 89250, "tax_rate": 0.15 },
      { "min_salary": 553850, "tax_rate": 0.2 }
    ]
  },
  "Social Security Taxability": [
    { "min_provisional": 0, "rate": 0.0 },
    { "min_provisional": 32000, "rate": 0.5 },
    { "min_provisional": 44000, "rate": 0.85 }
  ],
  "IRMAA 2025": [
    { "max_magi": 206000, "part_b": 185.0, "part_d": 0.0 },
    { "max_magi": 258000, "part_b": 259.2, "part_d": 12.9 },
    { "max_magi": 322000, "part_b": 331.7, "part_d": 33.3 },
    { "max_magi": 386000, "part_b": 404.2, "part_d": 53.8 },
    { "max_magi": 750000, "part_b": 476.7, "part_d": 74.2 },
    { "max_magi": 999999999, "part_b": 549.3, "part_d": 81.0 }
  ],
  "Medicare Base Premiums 2025": {
    "part_b": 174.7,
    "part_d": 30.0
  }
}
```

---

### 🔑 Tax Brackets Field Definitions

- **Tax Brackets: Standard Deduction** → baseline deduction applied before taxable income calculation.
- **Tax Brackets: Ordinary** → progressive brackets for federal, state, and local income taxes.
  - Keys are jurisdiction + year (e.g., `Federal 2025`, `Oregon State 2025`).
  - Each bracket defines `min_salary` and `tax_rate`.
- **Tax Brackets: Payroll Specific** → Social Security and Medicare payroll taxes.
  - Social Security capped at wage base (`176,100` in 2025).
  - Medicare includes additional surtax above thresholds.
- **Tax Brackets: Capital Gains** → long‑term capital gains brackets layered above ordinary income.
- **Tax Brackets: Social Security Taxability** → provisional income thresholds (0%, 50%, 85%).
- **Tax Brackets: IRMAA 2025** → income‑related Medicare premium adjustments (Part B and Part D).
- **Tax Brackets: Medicare Base Premiums 2025** → baseline monthly premiums for Part B and Part D.

---

### 🧾 Tax Brackets Audit Notes

- Tax brackets are consumed by `TaxCalculator` during year‑end settlement.
- Federal, state, and local brackets are layered to compute total ordinary income tax.
- Payroll taxes (Social Security, Medicare) are applied monthly to salary flows.
- Capital gains brackets are applied after ordinary income.
- Social Security taxability capped at 85% of provisional income.
- IRMAA thresholds adjust Medicare premiums based on MAGI.
- Standard deduction reduces taxable income before bracket application.
- All values are year‑specific and must be updated annually for compliance.

---

### Inflation

Defines baseline inflation assumptions, category‑specific profiles, and how inflation interacts with asset class returns. These values are consumed by `InflationGenerator` and adjusted via `build_description_inflation_modifiers` to produce year‑by‑year modifiers. The `MarketGains` component then uses `inflation_thresholds.json` and `gain_table.json` to determine asset class returns under Low, Average, or High regimes.

---

#### Example (`inflation_rates.json`)

```json
{
  "default": { "avg": 0.023, "std": 0.02 },
  "profiles": {
    "Education": { "avg": 0.045, "std": 0.025 },
    "Entertainment": { "avg": 0.028, "std": 0.02 },
    "Food": { "avg": 0.03, "std": 0.02 },
    "Goods": { "avg": 0.02, "std": 0.015 },
    "Health": { "avg": 0.035, "std": 0.015 },
    "Property Insurance": { "avg": 0.05, "std": 0.03 },
    "Property Maintenance": { "avg": 0.025, "std": 0.012 },
    "Property Taxes": { "avg": 0.03, "std": 0.015 },
    "Rent": { "avg": 0.025, "std": 0.01 },
    "Restaurants": { "avg": 0.033, "std": 0.02 },
    "Subscriptions": { "avg": 0.02, "std": 0.01 },
    "Travel": { "avg": 0.035, "std": 0.03 },
    "Utilities": { "avg": 0.02, "std": 0.02 },
    "Vehicle Insurance": { "avg": 0.025, "std": 0.02 },
    "Vehicle Maintenance": { "avg": 0.025, "std": 0.015 },
    "Voice and Data": { "avg": 0.0075, "std": 0.01 }
  }
}
```

---

#### Example (`inflation_thresholds.json`)

```json
{
  "Stocks": { "low": 0.015, "high": 0.035 },
  "Fixed-Income": { "low": 0.01, "high": 0.03 },
  "Property": { "low": 0.015, "high": 0.04 },
  "Vehicles": { "low": 0.0, "high": 0.0 },
  "Cash": { "low": 0.0, "high": 0.0 }
}
```

---

#### Example (`gain_table.json`)

```json
{
  "Stocks": {
    "Low": { "avg": 0.004, "std": 0.04 },
    "Average": { "avg": 0.0065, "std": 0.044 },
    "High": { "avg": 0.008, "std": 0.05 }
  },
  "Fixed-Income": {
    "Low": { "avg": 0.0015, "std": 0.0002 },
    "Average": { "avg": 0.0025, "std": 0.0004 },
    "High": { "avg": 0.004, "std": 0.0004 }
  },
  "Property": {
    "Low": { "avg": 0.0005, "std": 0.0008 },
    "Average": { "avg": 0.0025, "std": 0.0012 },
    "High": { "avg": 0.0025, "std": 0.0012 }
  },
  "Vehicles": {
    "Low": { "avg": -0.01, "std": 0.0 },
    "Average": { "avg": -0.01, "std": 0.0 },
    "High": { "avg": -0.01, "std": 0.0 }
  },
  "Cash": {
    "Low": { "avg": 0.0, "std": 0.0 },
    "Average": { "avg": 0.0, "std": 0.0 },
    "High": { "avg": 0.0, "std": 0.0 }
  }
}
```

---

### 🔑 Inflation Field Definitions

- **default**

  - `avg` → baseline average annual inflation rate.
  - `std` → baseline standard deviation (volatility).

- **profiles**

  - Each key represents a spending or asset category (e.g., Education, Food, Rent).
  - `avg` → category‑specific average inflation rate.
  - `std` → category‑specific volatility.
  - Categories include property costs (insurance, maintenance, taxes), household expenses (utilities, food, subscriptions), and discretionary spending (travel, entertainment).

- **thresholds** (`inflation_thresholds.json`)

  - Defines inflation cutoffs for each asset class.
  - If inflation < `low` → Low regime.
  - If between `low` and `high` → Average regime.
  - If inflation > `high` → High regime.

- **gain table** (`gain_table.json`)
  - Defines return distributions for each asset class under Low, Average, and High regimes.
  - `avg` → mean monthly return.
  - `std` → volatility of monthly returns.
  - Vehicles modeled as depreciating assets (negative returns).
  - Cash modeled as stable with zero returns.

---

### 🧾 Inflation Audit Notes

- Inflation defaults anchor the stochastic generator (`InflationGenerator`).
- Profiles are adjusted against defaults by `build_description_inflation_modifiers`.
- Thresholds determine which regime (Low, Average, High) applies to each asset class.
- Gain tables provide stochastic return distributions for the selected regime.
- Each profile produces year‑by‑year modifiers applied to transactions (e.g., rent, property maintenance, healthcare).
- Ensures category‑specific realism (e.g., healthcare inflates faster than goods, vehicles depreciate).
- Randomness seeded per trial for reproducibility.
- Audit clarity: modifiers, thresholds, and gain tables are logged and can be traced back to configuration definitions.

---

### Marketplace Premiums

Defines health insurance premiums for marketplace plans. These values are consumed by the simulation to model monthly healthcare costs and interact with MAGI thresholds (e.g., IRMAA adjustments).

Example (`marketplace_premiums.json`):

```json
{
  "silver_family": {
    "monthly_premium": 1750
  },
  "silver_couple": {
    "monthly_premium": 1250
  }
}
```

---

### 🔑 Marketplace Premiums Field Definitions

- **Plan Key** → identifier for the plan type (e.g., `silver_family`, `silver_couple`).
- **monthly_premium** → monthly premium cost in dollars.
  - Applied as a recurring monthly expense in the forecast loop.
  - Can be extended to include additional tiers (e.g., `silver_individual`, `gold_family`).

---

### 🧾 Marketplace Premiums Audit Notes

- Premiums are modeled as fixed monthly expenses unless overridden by inflation profiles (e.g., Health).
- Values feed into expense transactions and reduce available cash balances.
- MAGI values from `profile.json` interact with IRMAA thresholds, but marketplace premiums are modeled separately.
- Audit clarity: premiums must be updated annually to reflect marketplace rates.
- Plan keys should match naming conventions used in transaction logic to avoid misalignment.

---

## 📂 CSV Inputs

### Balances

Defines historical monthly balances for each bucket. This file seeds the simulation with starting balances and is consumed by `stage_prepare_timeframes` and `seed_buckets_from_config`.

Example (`balances.csv`):

```csv
Month,Cash,CD Ladder,Brokerage,Tax-Deferred,Tax-Free,Health Savings Account,Vehicles,Property,529K,SEPP IRA
2023-01,19678,31757,145633,478275,66656,12017,54580,661474,68434,0
2023-02,20188,32347,154680,541963,71379,12652,55476,672413,64942,0
...
2025-12,23256,73685,182139,793123,136612,33079,81526,1068649,116233,0
```

---

### 🔑 Balances Field Definitions

- **Month** → simulation period in `YYYY-MM` format.
- **Cash** → liquid cash balance.
- **CD Ladder** → certificate of deposit ladder account.
- **Brokerage** → taxable brokerage account.
- **Tax-Deferred** → retirement accounts (e.g., 401k, IRA).
- **Tax-Free** → Roth or other tax‑free accounts.
- **Health Savings Account** → HSA balances.
- **Vehicles** → depreciating vehicle assets.
- **Property** → real estate holdings (linked to `Property` policy).
- **529K** → education savings account.
- **SEPP IRA** → IRA designated for Substantially Equal Periodic Payments.

---

### 🧾 Balances Audit Notes

- The last row of `balances.csv` is used by `seed_buckets_from_config` to initialize starting balances for each bucket.
- All bucket names must match those defined in `buckets.json`.
- Vehicles and Property balances are tracked as assets but modeled with depreciation or mortgage flows.
- SEPP IRA balance is critical for IRS 72(t) withdrawal modeling.
- FlowTracker records debits/credits against these balances for audit clarity.
- Audit reproducibility: balances must align with external statements for defensibility.

---

### Fixed Transactions

Defines one‑time transactions that occur in a specific month. This file is consumed by `stage_init_components` and applied in the monthly forecast loop.

Example (`fixed.csv`):

```csv
Month,Bucket,Amount,Type,Description
2026-09,529K,-25000,Education,College Tuition #1
2027-09,529K,-25000,Education,College Tuition #2
2028-09,529K,-35000,Education,College Tuition #3
2029-09,529K,-35000,Education,College Tuition #4
2026-07,CD Ladder,-10000,Travel,Travel to Japan
2027-07,CD Ladder,-10000,Travel,Travel to Alaska
2030-10,CD Ladder,-10000,Travel,Travel to Europe
2035-10,CD Ladder,-10000,Travel,Travel to SE Asia
2040-07,CD Ladder,-10000,Travel,Travel to Aus/NZ
```

---

### 🔑 Fixed Transactions Field Definitions

- **Month** → date of transaction (`YYYY-MM`).
- **Bucket** → target bucket impacted by the transaction (e.g., `529K`, `CD Ladder`).
- **Amount** → transaction value (negative for outflows, positive for inflows).
- **Type** → category of transaction (e.g., Education, Travel).
- **Description** → human‑readable label for audit clarity (e.g., “College Tuition #1”).

---

### 🧾 Fixed Transactions Audit Notes

- Fixed transactions are applied once at the specified month.
- Amounts reduce or increase balances in the designated bucket.
- Categories (Education, Travel) can be linked to inflation profiles for realism (e.g., tuition inflates faster than goods).
- FlowTracker logs each transaction for reproducibility.
- Audit clarity: descriptions should match external records (e.g., tuition invoices, travel receipts).

---

### Recurring Transactions

Defines ongoing monthly transactions that repeat between a start and end month. This file is consumed by `stage_init_components` and applied in the monthly forecast loop.

Example (`recurring.csv`):

```csv
Start Month,End Month,Bucket,Amount,Type,Description
2025-09,2029-09,Cash,-290,Vehicle Insurance,Vehicle Insurance
2029-10,2075-12,Cash,-190,Vehicle Insurance,Vehicle Insurance
2025-09,2029-09,Cash,-400,Vehicle Maintenance,Vehicle Maintenance
2029-10,2075-12,Cash,-300,Vehicle Maintenance,Vehicle Maintenance
2025-09,2029-09,Cash,-140,Entertainment,Entertainment Parks and Rec
2029-10,2075-12,Cash,-140,Entertainment,Entertainment Parks and Rec
2025-09,2029-09,Cash,-95,Subscriptions,Entertainment Subscriptions
2029-10,2075-12,Cash,-95,Subscriptions,Entertainment Subscriptions
2025-09,2029-09,Cash,-800,Food,Food Groceries
2029-10,2075-12,Cash,-600,Food,Food Groceries
2025-09,2029-09,Cash,-200,Restaurants,Food Restaurants
2029-10,2075-12,Cash,-200,Restaurants,Food Restaurants
2025-09,2029-09,Cash,-800,Goods,Goods
2029-10,2075-12,Cash,-600,Goods,Goods
2025-08,2029-09,Cash,-500,Health,Health Medical Insurance
2025-08,2029-09,Cash,-15,Health,Health Dental Insurance
2025-08,2029-09,Cash,-5,Health,Health Vision Insurance
2025-09,2030-04,Cash,-325,Health,Health Prescriptions etc
2029-10,2050-04,Health Savings Account,-425,Health,Health Prescriptions etc
2050-04,2075-12,Health Savings Account,-725,Health,Health Prescriptions etc
2025-09,2029-09,Cash,-400,Travel,Travel in US
2029-10,2075-12,Cash,-600,Travel,Travel in US
2025-09,2075-12,Cash,-345,Utilities,Utils Elec and Gas
2025-09,2075-12,Cash,-300,Utilities,Utils Waste and Water
2025-08,2026-12,Cash,-345,Voice and Data,Utils Voice and Data
2027-01,2075-12,Cash,-250,Voice and Data,Utils Voice and Data
```

---

### 🔑 Recurring Transactions Field Definitions

- **Start Month** → first month the transaction occurs (`YYYY-MM`).
- **End Month** → last month the transaction occurs (`YYYY-MM`).
- **Bucket** → target bucket impacted by the transaction (e.g., `Cash`, `Health Savings Account`).
- **Amount** → monthly transaction value (negative for outflows, positive for inflows).
- **Type** → category of transaction (e.g., Vehicle Insurance, Food, Health, Utilities).
- **Description** → human‑readable label for audit clarity (e.g., “Health Prescriptions etc”).

---

### 🧾 Recurring Transactions Audit Notes

- Recurring transactions are applied every month between `Start Month` and `End Month`.
- Amounts reduce or increase balances in the designated bucket.
- Categories (Food, Health, Utilities, Entertainment) can be linked to inflation profiles for realism.
- Health transactions may shift buckets (Cash → HSA) depending on policy and time horizon.
- FlowTracker logs each transaction for reproducibility.
- Audit clarity: descriptions should match external records (e.g., insurance policies, utility bills).

---

## 🧾 Notes

- All months stored as `YYYY-MM` and parsed into `pandas.Period("M")`.
- Buckets must be defined in both `balance.csv` and `buckets.json`.
- Inflation profiles ensure category‑specific realism (e.g., Rent inflates faster than Cash).
- FlowTracker records all debits/credits for audit clarity.

---

## 📚 Related Pages

- [Framework Overview](overview.md)
- [Architecture Overview](architecture.md)
- [Simulation Logic](simulation_logic.md)
- [Visualization Guide](visualization.md)
- [Usage Guide](usage.md)
- See `../src/README.md` for source code details.
