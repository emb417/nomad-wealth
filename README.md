# 🕊️ Nomad Wealth: Policy-Driven Financial Freedom

Nomad Wealth is a policy-driven Python framework that acts as a complete engine for Monte Carlo simulation of your financial future. It starts with your historical data to seed an auditable, bucket-level model, then applies your explicit, configurable rules—covering everything from cash flow triggers to tax-optimized withdrawals—along with inflation-aware market returns. By projecting thousands of possible futures, it transforms complex simulations into clear, actionable insights for achieving and maintaining financial freedom.

---

## 🔍 What Can Nomad Wealth Help Me Discover?

This framework moves your financial outlook beyond simple spreadsheets and generic rules. By embracing the complexity of **real-world market volatility, inflation, and taxes**, Nomad Wealth provides clear, auditable answers to your most critical financial questions:

### Resillience & Sufficiency

- **How likely is my current plan to fail?** It quantifies the probability of running out of money under thousands of volatile market scenarios, giving you a scientific success rate, not just a hope.
- **What is my true maximum sustainable spending limit?** It calculates the highest spending rate you can afford in retirement while maintaining a user-defined risk tolerance (e.g., less than a 5% chance of failure), adjusted for inflation.
- **What specific policy changes are required to survive a major market downturn?** You can test aggressive bear markets to see exactly where and when your cash flow policies break down.

### Strategy & Optimization

- **How does my asset allocation impact my long-term security?** By comparing simulations, you can determine which portfolio mix provides the best risk-adjusted net worth over decades.
- **What is the optimal withdrawal order for my accounts (Roth, Taxable, 401k)?** The sophisticated tax engine provides auditable insight into the tax drag of various withdrawal policies, guiding you to a strategy that maximizes purchasing power.
- **When should I liquidate specific assets (like a home or business) to ensure financial stability?** You can model specific liquidation triggers to see the exact conditions and scenarios that necessitate the sale of a major asset.

### Control & Transparency

- **Where is every dollar going in every possible future?** The auditable bucket model provides unparalleled transparency, allowing you to trace simulated cash flow and account balances to verify and trust every projection.
- **Are my stated financial _policies_ fully documented and understood?** It forces you to explicitly define every financial decision in declarative JSON, ensuring your strategy is transparent, repeatable, and easily shared with an advisor.

---

## 🏛️ Framework Pillars (Technical Detail)

### Move Beyond Simple Averages for True Financial Resilience

Traditional forecasting relies on single-point estimates or historical averages that gloss over real-world volatility and uncertainty. This framework embraces the inherent stochastic nature of markets and cash flows through Monte Carlo simulation, providing you with a full distribution of possible outcomes. You gain confidence in your plan's ability to withstand worst-case scenarios, not just the best or average.

### Financial Planning Driven by Your Rules, Not Only Assumptions

Its policy-first architecture is a game-changer. Instead of hardcoding generic rules, you explicitly define all critical financial decisions—from monthly cash-flow triggers and bucket refill strategies to withdrawal order and liquidation thresholds—in declarative JSON. This makes your plan fully transparent, repeatable, and adaptable as your life circumstances or tax laws change.

### Accurate Projections through Inflation and Tax Reality

By incorporating inflation-adjusted gain sampling and a sophisticated tax engine that models capital gains, income tax, and specific withdrawal penalties, the framework paints a far more realistic picture of future net worth and sustainable withdrawal rates. You get projections based on real purchasing power, avoiding the pitfalls of over-optimistic nominal returns.

### Gain Deep, Auditable Insight into Every Future Dollar

The core auditable, bucket-level transaction engine provides unparalleled transparency. You can trace every simulated dollar in and out of specific accounts (e.g., Taxable, Roth, 401k), offering a clear, scientific basis for optimizing asset location and withdrawal strategies. This moves your planning from a black box to a fully verifiable, strategic model.

---

## 🔧 Features

- Fixed and recurring transaction ingestion from CSV
- Inflation-aware market return simulation via user-defined gain tables
- Threshold-driven refill policies with retirement-age gating to avoid penalties
- Configurable emergency liquidation hierarchy across buckets
- Automated recurring rental transactions after property liquidation event
- Tax-aware withdrawals distinguishing ordinary income, capital gains, and penalties
- Independent Roth conversion scheduling
- Monte Carlo sampling with percentile bands and probability metrics
- Interactive Plotly visualizations and CSV exports

### Historical Net Worth and Annual/Monthly Gain %

Chart your historical net worth and gain/loss % over time. Both annual and monthly gain/loss % are included to help identify the specific months where the net worth increased or decreased relative to the previous month and the previous year.

![Historical Net Worth](assets/historical.png)

### Simulation Transactions

See the simulated transactions for a given year to better understand the details of your plan. In this example, $20K will need to be moved from Fixed-Income to Cash to help pay for the monthly expenses during 2026.

![Sim Transactions](assets/transactions.png)

### Simulation Transactions in Context

See the simulated transactions for a given year in context to the bucket balances to determine the impact of annual transactions. In this example, $20K will need to be moved from Fixed-Income to Cash to help pay for the monthly expenses during 2026. The chart helps you see these types of transactions in context to the overall bucket balances, to determine if the transactions pose a risk to your plan.

![Sim Transactions in Context](assets/transactions_in_context.png)

### Simulation Forecast by Bucket

See the simulated forecasted balances per bucket across all years to better understand the details of your plan. In this example the Property had to be liquidated in 2042 and the proceeds moved to the Taxable bucket.

![Sim Forecast by Bucket](assets/forecast_by_bucket.png)

### Monte Carlo Net Worth Forecast

See the Monte Carlo simulation net worth trajectories. Included:

- Probablity of positive net worth at 20 and 10 years to the end date, and the final end date
- The end date net worth at the 15th, median, average, and 85th percentile
- The probability of property liquidation and the minimum, average and maximum age of liquidation

![Monte Carlo Net Worth Forecast](assets/mc_networth.png)

---

## 🚀 Quick Start

1. Clone repo:

   ```bash
   git clone https://github.com/emb417/nomad-wealth
   ```

2. Install the dependencies:

   - Use a virtual environment to install dependencies.
   - Or install dependencies manually:

   ```bash
   cd nomad-wealth
   pip install -r requirements.txt
   ```

3. Run the simulation:

   ```bash
   python src/app.py
   ```

---

## 📁 Folder Structure

| Folder    | Description                                                            |
| --------- | ---------------------------------------------------------------------- |
| `config/` | JSON definitions for buckets, thresholds, gain tables, inflation rules |
| `data/`   | CSVs for historical balances and transactions                          |
| `src/`    | Application code (see [`src/README.md`](src/README.md))                |
| `export/` | Outputs: Monte Carlo charts, sample forecasts, tax records             |

---

## 📈 Outputs

- `mc_networth_<timestamp>.html`: Monte Carlo net worth chart with percentile lines and probability metrics
- `####_buckets_forecast_<timestamp>.csv`: Bucket balance trajectories for sampled simulations
- `####_taxes_forecast_<timestamp>.csv`: Year-end tax breakdowns
- `####_buckets_forecast_<timestamp>.html`: Interactive bucket balance visualizations
- `historical_nw_<timestamp>.html`: Historical net worth and gain/loss chart

See [`export/README.md`](export/README.md) for details.

---

## 🧠 Simulation Logic

Each month the engine sequentially applies:

1. Core transactions (fixed, recurring, rental, salary, SS, Roth)
2. Threshold-based refills (age-gated for tax-deferred sources)
3. Market returns via inflation-aware gain sampling
4. Emergency liquidation when cash falls below threshold, bypassing age-gating if needed (i.e. tax-penalized)
5. Monthly tax drip and tax collection
6. Balance snapshot and tax aggregation
7. January year-end tax payment and penalty integration

---

## 🛣️ Roadmap

- UI to enter balances and manage individual accounts and assign them to buckets
- UI for tuning configurations: profile, holdings, gains, inflation, policies
- UI for managing future transactions: fixed and recurring
- UI for managing income sources: unemployement, salary, bonuses, social security
- Handle Required Minimium Distributions programatically instead of using date-based policy with static amounts
- Handle Health Savings Account spending programatically, instead of using date-based recurring transactions
- Handle unemployment and delayed salary expectations
- Handle self-employment taxes
- Handle self and spousal IRA contributions
- Handle specified equities with current market values and forecasted gains
- Support various vesting schedules and maturity dates
- Scenario tagging and multi-profile support
- Interactive forecast comparison across scenarios
- Support "smile" expenses curve
- Category-specific inflation for expenses

---
