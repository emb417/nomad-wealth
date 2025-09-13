# Inflation Forecasting and Portfolio Projections

A simulation framework that blends historical balances with forward forecasts. It applies fixed and recurring transactions, invokes a refill policy to top up under-funded buckets, and models asset-class growth under different inflation scenarios.

---

## Quick Start

1. Install dependencies  

   ```bash
   pip install -r requirements.txt
   ```

2. Update JSON files in `config/` as needed. See `config/README.md`.  
3. Prepare your CSV files in `data/`. See `data/README.md`.  
4. Configure flags in `src/app.py`:  
   - `SHOW_CHART`  
   - `SAVE_CHART`  
   - `SAVE_LEDGER`  
5. Run the forecast  

   ```bash
   python src/app.py
   ```

---

## Folder Structure

- `config/`  
  JSON files driving bucket allocations, market assumptions, inflation thresholds, and refill rules  
- `data/`  
  CSV files for historical balances, fixed transactions, and recurring transactions  
- `src/`  
  Application code  
- `export/`  
  Generated forecast ledger CSV and HTML chart files  

---

## Configuration

All bucket and market settings live in `config/`. Refer to `config/README.md` for details on each JSON:

- `holdings.json`  
- `gain_table.json`  
- `inflation_thresholds.json`  
- `refill_policy.json`  

---

## Data Files

Your historical and transaction data live in `data/`. Refer to `data/README.md` for required CSV schemas:

- `balance.csv`  
- `fixed.csv`  
- `recurring.csv`  

---

## Running the Forecast

Once configuration and data are in place:

1. Verify your `config/` and `data/` files match exactly on bucket names  
2. Adjust simulation flags in `src/app.py`  
3. Execute the script  
4. Review INFO-level logs for load, simulation start, refill events, and final net worth  
5. View the exported chart in `export/` to compare actual history with forecast  

---

## TODOs

- Validate JSON schemas for config files  
- Support percentage-based refill rules  
- Add tax-implication calculations for withdrawals  
- Implement Monte Carlo projections  
- Extend refill policy to multi-source pro-rata top-ups  
- Allow category-specific inflation rates for recurring expenses  

---

*Last updated:* 2025-09-12
