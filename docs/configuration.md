# ⚙️ Configuration Reference

Nomad Wealth is **policy‑first**: all simulation behavior is driven by configuration files. These files represent your accounts (buckets), income, expenses, and policies — the building blocks of your retirement plan. By adjusting them, you can personalize forecasts, explore scenarios, and see how IRS rules, state surcharges, and inflation shape your financial future.

---

## 🔑 Getting Started: Levels of Personalization

### BASIC

Minimum inputs to run your own forecast:

- **`profile.json`** → sets your birth month, income actuals, and retirement horizon.
- **`balance.csv`** → starting balances for each bucket.
- **`recurring.csv`** → ongoing monthly expenses (insurance, food, utilities).
- **`fixed.csv`** → one‑time events (tuition, travel).

### RECOMMENDED

Add details for more realistic results:

- **`buckets.json`** → defines your buckets and sub‑holdings.
- **`policies.json`** → income streams (salary, Social Security), property details, unemployment.
- **`tax_brackets.json`** → IRS‑aligned federal and Oregon state brackets.
- **`marketplace_premiums.json`** → healthcare premiums for marketplace plans.

### ADVANCED

Fine‑tune rules for deeper scenario analysis:

- **`buckets.json`** → customize holdings to reflect your investment strategy.
- **`policies.json`** → add refill rules, liquidation hierarchy, Roth conversions, SEPP withdrawals.
- **`inflation_rates.json`** → category‑specific inflation (healthcare, rent, travel).
- **`inflation_thresholds.json`** + **`gain_table.json`** → asset class return regimes for Monte Carlo sampling.

---

## 📂 JSON Configuration

### Profiles

Profiles define your retirement horizon, dependent context, income actuals, and year‑to‑date baselines. They drive calculations for ACA marketplace eligibility, Medicare premiums, and tax sufficiency.

**Example (`profile.json`):**

```json
{
  "Birth Month": "1975-04",
  "Dependent Birth Month": "2009-07",
  "End Month": "2065-12",
  "MAGI": {
    "2023": 200000,
    "2024": 204000
  },
  "YTD Income": {
    "salary": 173333,
    "withdrawals": 0,
    "gains": 0,
    "ss_benefits": 0,
    "fixed_income_interest": 200,
    "unemployment": 0,
    "tax_paid": 56000
  }
}
```

---

### 🔑 Profiles Field Definitions

- **Birth Month** → start of simulation, expressed as `YYYY-MM`.  
- **Dependent Birth Month** → date of birth for dependent coverage logic.  
  - Used to determine ACA eligibility.  
  - Once dependent turns 25, only couple plan applies.  
- **End Month** → end of simulation horizon, expressed as `YYYY-MM`.  
- **MAGI** → dictionary of Modified Adjusted Gross Income values by year.  
  - Keys are years (`2023`, `2024`, …).  
  - Values are annual MAGI amounts.  
  - Used for IRMAA premium calculations, ACA marketplace brackets, and tax logic.  
- **YTD Income** → snapshot of income and taxes already earned/paid in the current year.  
  - Keys include `salary`, `withdrawals`, `gains`, `ss_benefits`, `fixed_income_interest`, `unemployment`, and `tax_paid`.  
  - Values are cumulative amounts up to the current month.  
  - Used to seed simulations with realistic year‑to‑date baselines, ensuring withholding and liability match real‑world outcomes.  
  - In the first forecast year, YTD income is combined with projected spend to estimate annual AGI for both insurance premiums and tax collection.

---

### 🧾 Profiles Audit Notes

- **Birth Month** → determines retirement eligibility (e.g., age 59.5 for penalty‑free withdrawals).  
- **Dependent Birth Month** → ensures ACA coverage logic transitions correctly when dependent turns 25.  
- **End Month** → defines the final forecast period.  
- **MAGI** → feeds into IRMAA thresholds, Medicare premium adjustments, and ACA marketplace credits.  
- **YTD Income** → ensures simulations start from actual year‑to‑date earnings and taxes, preventing cold‑start distortions.  
  - First forecast year: YTD income + projected remaining spend used for annual AGI.  
  - Future years: January spend × 12 sets annual AGI baseline.  
- All dates are parsed into `pandas.Period("M")` for monthly granularity.  
- **Audit clarity**: profiles should be updated annually to reflect current MAGI, dependent age, and YTD income values.  

---

### Buckets

Buckets represent your accounts — cash, brokerage, retirement, property — and define how money grows or is spent.

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

Buckets represent your accounts and how money flows through them. Each field defines how the system treats that bucket:

- **`holdings`** → how your money is invested (stocks, bonds, cash).
    - Optional: `cost_basis` for property or assets where IRS rules require tracking.
- **`can_go_negative`** → whether the bucket can dip below zero (e.g., overdraft in Cash).
- **`allow_cash_fallback`** → whether the system automatically pulls from Cash if another bucket runs short.
- **`bucket_type`** → tells the system what kind of bucket this is:
    - `cash` → liquid money you can spend immediately.
    - `taxable` → brokerage or CD ladder accounts.
    - `tax_deferred` → retirement accounts (401k, IRA, SEPP IRA).
    - `tax_free` → Roth accounts.
    - `property` → real estate holdings with explicit cost basis.
    - `other` → vehicles, HSAs, 529K, or miscellaneous accounts.

---

### 🧾 Buckets Audit Notes

Behind the scenes, Nomad Wealth ensures your buckets are modeled consistently and IRS‑aligned:

- Buckets are initialized from your starting balances (`balance.csv`).
- The system corrects rounding drift automatically when allocating holdings.
- A **Tax Collection bucket** is always present to handle withholding and settlement.
- Property buckets should include `cost_basis` to stay IRS‑compliant.
- Cash buckets can allow negative balances to realistically model overdrafts.

---

### Policies

Policies define how income, withdrawals, and conversions happen in your plan — from salary and Social Security to Roth conversions and property flows.

Example (`policies.json`):

```json
{
  "Refill": {
    "Thresholds": { "Cash": 30000 },
    "Amounts": { "Cash": 20000 },
    "Sources": {
      "Cash": ["SEPP IRA", "Tax-Deferred", "Brokerage", "Tax-Free"]
    }
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

Policies describe the rules that shape how money flows in your plan — income, withdrawals, conversions, and special cases. Each section defines how the system applies real‑world rules to your buckets:

- **Refill** → Keeps your cash balance above a minimum by automatically topping it up from other buckets when needed.
- **Liquidation** → Defines when assets are sold to cover shortfalls, which buckets are tapped first, and where proceeds go.
- **Salary** → Models your income stream: base salary, bonuses, annual raises, and when you retire.
- **Social Security** → Profiles for each person, including date of birth, benefit amounts, and when payouts begin.
- **RMD (Required Minimum Distribution)** → Specifies how mandatory withdrawals from retirement buckets are distributed.
- **Roth Conversions** → Rules for converting tax‑deferred money into Roth accounts, with limits by age, tax rate, and amount.
- **SEPP (Substantially Equal Periodic Payments)** → IRS 72(t) withdrawals, including timing, interest rate, and source/target buckets.
- **Property** → Models real estate: market value, mortgage details, maintenance costs, and rental income.
- **Unemployment** → Temporary income replacement, including start/end dates and monthly benefit amounts.

---

### 🧾 Policies Audit Notes

Behind the scenes, Nomad Wealth ensures these policies are applied consistently and IRS‑aligned:

- Refill and liquidation rules enforce liquidity thresholds so you don’t run out of cash.
- Salary and Social Security profiles generate realistic income streams.
- RMD and SEPP enforce IRS withdrawal requirements.
- Roth conversions model tax‑optimized transfers across different phases of retirement.
- Property policies integrate mortgage payments, maintenance, and rental flows.
- Unemployment policies allow temporary income replacement during gaps.

---

### Tax Brackets

Tax brackets ensure your forecasts reflect real IRS rules — from income and capital gains to Medicare premiums and IRMAA thresholds.

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

Tax brackets define how income, gains, and premiums are calculated in your plan. They ensure your forecasts reflect real IRS rules and healthcare costs:

- **Standard Deduction** → the baseline deduction applied before taxable income is calculated.
- **Ordinary Income Brackets** → progressive tax brackets for federal, state, and local income taxes.
    - Each bracket specifies a minimum income level (`min_salary`) and the tax rate applied.
- **Payroll Taxes** → Social Security and Medicare contributions.
    - Social Security is capped at the annual wage base (e.g., $176,100 in 2025).
    - Medicare includes an additional surtax above certain thresholds.
- **Capital Gains** → long‑term capital gains brackets layered on top of ordinary income.
- **Social Security Taxability** → thresholds that determine how much of your Social Security benefits are taxable (0%, 50%, or 85%).
- **IRMAA (Income‑Related Monthly Adjustment Amount)** → Medicare premium adjustments based on your income (Part B and Part D).
- **Medicare Base Premiums** → the baseline monthly premiums for Medicare coverage.

---

### 🧾 Tax Brackets Audit Notes

Behind the scenes, Nomad Wealth applies these rules exactly as the IRS does, so your forecasts remain defensible:

- Federal, state, and local brackets are layered to compute total ordinary income tax.
- Payroll taxes (Social Security and Medicare) are applied monthly to salary flows.
- Capital gains brackets are applied after ordinary income.
- Social Security taxability is capped at 85% of provisional income.
- IRMAA thresholds adjust Medicare premiums based on your Modified Adjusted Gross Income (MAGI).
- The standard deduction reduces taxable income before brackets are applied.
- All values are year‑specific and must be updated annually to stay compliant.

---

### Inflation

Inflation profiles make your plan realistic — healthcare inflates faster than groceries, vehicles depreciate, and property costs rise over time.

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

Inflation settings make your forecasts realistic by showing how costs rise and assets behave over time:

- **default** → baseline inflation assumptions for the overall economy.

    - `avg` → average annual inflation rate.
    - `std` → volatility (how much inflation varies year to year).

- **profiles** → category‑specific inflation for different types of spending or assets.

    - Each profile represents a category (e.g., Education, Food, Rent).
    - `avg` → typical inflation rate for that category.
    - `std` → volatility for that category.
    - Examples: healthcare inflates faster than groceries, property taxes rise steadily, vehicles depreciate.

- **thresholds** (`inflation_thresholds.json`) → cutoffs that determine which regime applies to each asset class.

    - If inflation is below `low` → Low regime.
    - Between `low` and `high` → Average regime.
    - Above `high` → High regime.

- **gain table** (`gain_table.json`) → defines how assets perform under each regime.
    - `avg` → expected monthly return.
    - `std` → volatility of returns.
    - Vehicles are modeled as depreciating assets (negative returns).
    - Cash is modeled as stable with zero returns.

---

### 🧾 Inflation Audit Notes

Behind the scenes, Nomad Wealth applies these rules to keep forecasts defensible and reproducible:

- Default inflation anchors the generator that drives year‑by‑year adjustments.
- Profiles adjust spending categories against the baseline for realism.
- Thresholds determine which regime (Low, Average, High) applies to each asset class.
- Gain tables provide return distributions for the selected regime.
- Each profile produces modifiers applied to transactions (e.g., rent, property maintenance, healthcare).
- Ensures category‑specific realism (e.g., healthcare inflates faster than goods, vehicles depreciate).
- Randomness is seeded per trial so results are reproducible.
- All modifiers, thresholds, and gain tables are logged for transparency.

---

### Marketplace Premiums

Marketplace premiums model your monthly healthcare costs, so you can see how insurance affects your retirement outlook.

Example (`marketplace_premiums.json`):

```json
{
  "family": {
    "monthly_premium": 1750
  },
  "couple": {
    "monthly_premium": 1250
  }
}
```

---

### 🔑 Marketplace Premiums Field Definitions

Marketplace premiums represent your monthly health insurance costs. These values ensure your forecasts account for real, recurring expenses:

- **Plan Key** → the name of the plan type (e.g., `family`, `couple`).
- **monthly_premium** → the monthly cost of the plan in dollars.
    - Treated as a recurring expense in your forecast.
    - Can be extended to include other tiers (e.g., `individual`, `family`).

---

### 🧾 Marketplace Premiums Audit Notes

Behind the scenes, Nomad Wealth applies these premiums consistently so your plan reflects reality:

- Premiums are modeled as fixed monthly expenses unless linked to inflation (e.g., healthcare costs rising over time).
- Values feed directly into expense transactions and reduce available cash balances.
- MAGI values from `profile.json` interact with IRMAA thresholds, but marketplace premiums are tracked separately.
- Premiums should be updated annually to reflect current marketplace rates.
- Plan keys must match naming conventions used in transaction logic to avoid misalignment.

---

## 📂 CSV Inputs

### Balances

Balances seed the simulation with your current bucket values, so forecasts begin from where you are today.

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

Balances define your starting point — the buckets and assets you hold when the simulation begins. Each column represents one type of bucket:

- **Month** → the period of the balance snapshot, in `YYYY-MM` format.
- **Cash** → checking and savings accounts, used for expenses, i.e., outflows.
- **CD Ladder** → certificate of deposit accounts.
- **Brokerage** → taxable investment accounts.
- **Tax‑Deferred** → retirement accounts like 401(k) or traditional IRA.
- **Tax‑Free** → Roth accounts or other tax‑free holdings.
- **Health Savings Account** → HSA balances for medical expenses.
- **Vehicles** → depreciating assets such as cars.
- **Property** → real estate holdings, linked to the Property policy.
- **529K** → education savings accounts.
- **SEPP IRA** → IRA designated for Substantially Equal Periodic Payments (IRS 72(t)).

---

### 🧾 Balances Audit Notes

Behind the scenes, Nomad Wealth uses these balances to ensure forecasts are realistic and IRS‑aligned:

- The last row of `balances.csv` seeds the simulation with your starting bucket values.
- All bucket names must match those defined in `buckets.json` for consistency.
- Vehicles and Property balances are tracked as assets but modeled with depreciation or mortgage flows.
- SEPP IRA balances are critical for IRS 72(t) withdrawal modeling.
- FlowTracker records every debit and credit against these balances for transparency.
- For reproducibility, balances should align with external statements so forecasts remain defensible.

---

### Fixed Transactions

One‑time events like tuition or travel.

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

Fixed transactions represent **one‑time events** that occur in a specific month. They help you model major expenses or inflows that don’t repeat regularly:

- **Month** → the date of the transaction (`YYYY-MM`).
- **Bucket** → the bucket impacted (e.g., `529K`, `CD Ladder`).
- **Amount** → the value of the transaction (negative for expenses, positive for income).
- **Type** → the category of the transaction (e.g., Education, Travel).
- **Description** → a human‑readable label for clarity (e.g., “College Tuition #1”).

---

### 🧾 Fixed Transactions Audit Notes

Behind the scenes, Nomad Wealth ensures these one‑time events are applied consistently and transparently:

- Fixed transactions are applied once at the specified month.
- Amounts reduce or increase balances in the designated bucket.
- Categories (Education, Travel) can be linked to inflation profiles for realism (e.g., tuition inflates faster than goods).
- FlowTracker logs each transaction so every debit and credit is traceable.
- For audit clarity, descriptions should match external records (e.g., tuition invoices, travel receipts).

---

### Recurring Transactions

Ongoing monthly expenses like insurance, utilities, or groceries.

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

Recurring transactions represent **ongoing monthly expenses or income** that repeat over time. They help you capture the rhythm of everyday life in your plan:

- **Start Month** → when the transaction begins (`YYYY-MM`).
- **End Month** → when the transaction ends (`YYYY-MM`).
- **Bucket** → the bucket impacted (e.g., `Cash`, `Health Savings Account`).
- **Amount** → the monthly value (negative for expenses, positive for income).
- **Type** → the category of the transaction (e.g., Vehicle Insurance, Food, Health, Utilities).
- **Description** → a clear label for easy tracking (e.g., “Health Prescriptions”).

---

### 🧾 Recurring Transactions Audit Notes

Behind the scenes, Nomad Wealth applies these recurring flows consistently so your forecasts reflect real life:

- All months are stored in `YYYY-MM` format for monthly precision.
- Buckets must be defined consistently across files to avoid mismatches.
- Inflation profiles adjust categories over time for realism (e.g., healthcare costs rise faster than groceries).
- FlowTracker logs every debit and credit, ensuring transparency and reproducibility.

---

## 📚 Related Pages

- [Framework Overview](overview.md)
- [Architecture Overview](architecture.md)
- [Simulation Logic](simulation_logic.md)
- [Visualization Guide](visualization.md)
- [Usage Guide](usage.md)
- See `../src/README.md` for source code details.
