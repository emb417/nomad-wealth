# src/README.md

## Source Code Overview

All application logic lives under `src/`.

---

## app.py

Entry point. Parses `config/` and `data/`, initializes:

- Buckets & holdings
- Transactions (Fixed, Recurring, Salary, SS, Deferred, Taxable)
- ThresholdRefillPolicy
- MarketGains & inflation data
- TaxCalculator

Runs `ForecastEngine.run(...)` and writes exports.

---

## engine.py

`ForecastEngine` orchestrates the monthly loop:

1. Core transactions (fixed, recurring, salary, SS)
2. Refill policy
3. Market returns via MarketGains
4. Tax computation & cash withdrawal
5. Snapshot balances & export

---

## domain.py

- `AssetClass` & `Holding`
- `Bucket`: deposit/withdraw logic, pro-rata weight handling

---

## policies.py

- `ThresholdRefillPolicy`: top-off vs. full refill modes
- Hooks for per-bucket eligibility and refill amounts

---

## strategies.py

- `MarketGains`: applies per-asset returns based on inflation thresholds
- Logs each holding’s scenario and sampled gain

---

## taxes.py

- `TaxCalculator`: ordinary vs. capital gains tax
- Bracketed rates, social-security inclusion

---

## transactions.py

Defines transaction types:

- `FixedTransaction`
- `RecurringTransaction`
- `SalaryTransaction`
- `SocialSecurityTransaction`
- `TaxDeferredTransaction`
- `TaxableTransaction`

---

_Use logging levels to trace details._ Adjust flags in `app.py` as needed.
