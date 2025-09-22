# Source Code Overview

All application logic lives under `src/`.

---

## app.py

Entry point. Loads configuration and historical data, initializes:

- Buckets & holdings
- Transactions (Fixed, Recurring, Salary, Social Security, Roth Conversion)
- ThresholdRefillPolicy with age-based eligibility
- MarketGains (inflation-aware return simulator)
- TaxCalculator

Runs a Monte Carlo loop using `ForecastEngine.run(...)`, aggregates year-end net worth across simulations, and exports:

- Sample forecast charts and CSVs
- Monte Carlo percentile chart
- Probability of positive net worth at key ages

---

## engine.py

`ForecastEngine` orchestrates the monthly forecast loop:

1. Apply core transactions (fixed, recurring, salary, SS, Roth)
2. Trigger refill policy (age-gated for tax-deferred sources)
3. Apply market returns via `MarketGains`
4. Compute taxes and withdraw from Cash
5. Snapshot bucket balances
6. Log year-end tax summary (paid in January of following year)

---

## domain.py

- `AssetClass` & `Holding`: define asset types and weights
- `Bucket`: manages deposits, withdrawals, and balance tracking

---

## policies.py

- `ThresholdRefillPolicy`: triggers bucket top-offs based on thresholds
- Includes age-based gating for tax-deferred withdrawals
- Emergency logic for negative Cash balances

---

## economic_factors.py

- `MarketGains`: simulates inflation-adjusted market returns
- `InflationGenerator`: produces annual inflation series with randomness

---

## taxes.py

- `TaxCalculator`: computes ordinary and capital gains tax
- Supports marginal brackets, SS inclusion, and age-based logic

---

## transactions.py

Defines all transaction types:

- `FixedTransaction`
- `RecurringTransaction`
- `SalaryTransaction`
- `SocialSecurityTransaction`
- `RothConversionTransaction`
- `RefillTransaction` (used by refill policy)

Each transaction exposes:

- `apply(...)`: mutates buckets
- `get_withdrawal(...)`: for tax-deferred tracking
- `get_taxable_gain(...)`: for capital gains tracking

---

## Logging & Flags

Use logging levels (`DEBUG`, `INFO`) to trace simulation behavior.  
Adjust flags in `app.py` to control:

- Chart display and export
- Sample simulation selection
- Monte Carlo run count
