# 🌐 Framework Overview

Nomad Wealth is a **policy-driven financial simulation framework** built for transparency, audit clarity, and strategic insight. It models retirement scenarios, withdrawal strategies, and tax implications using **Monte Carlo simulations** and **IRS-aligned rules**.

---

## 🎯 Purpose

The framework helps users and auditors:

- Quantify financial sufficiency under uncertainty.
- Compare scenarios with percentile overlays and reference lines.
- Trace every dollar across buckets, transactions, and policies.
- Validate outputs against IRS rules and historical distributions.
- Export reproducible charts and CSVs for audit and review.

---

## 🧩 Core Components

Nomad Wealth is organized into modular layers:

- **Configuration** → JSON and CSV inputs define buckets, policies, tax brackets, and seed balances.
- **Architecture** → Modular design separates buckets, policies, transactions, economic factors, taxes, and visualization.
- **Simulation Logic (`forecast_engine.py`)** → Monthly forecast loop applies transactions, policies, market returns, and taxes.
- **Visualization (`visualizations.py`)** → Interactive charts (historical, per‑trial, Monte Carlo) and CSV/HTML exports provide audit clarity and interpretability.
- **Usage** → Flags in `app.py` control simulation size, chart generation, and export behavior.

---

## 📂 Workflow

1. Configure
    - Define buckets, policies, and tax rules in JSON.
    - Seed balances and transactions in CSV.
2. Simulate
    - Run Monte Carlo trials in parallel.
    - Apply monthly transactions, refill policies, market returns, and taxes.
    - Aggregate results into DataFrames for net worth, taxes, returns, balances, and flow logs.
    - FlowTracker ensures every debit/credit is logged for audit reproducibility.
3. Visualize
    - Generate historical charts, per‑trial examples, and aggregate Monte Carlo distributions.
    - Export HTML and CSV outputs with consistent color palettes, percentile overlays, and hover text for interpretability.

---

## 🧾 IRS Alignment

The framework enforces IRS rules with explicit, layered logic:

- Ordinary income brackets (married filing jointly).
- Capital gains layered above ordinary income.
- Social Security taxation capped at 85%.
- Penalty taxes applied to early withdrawals.
- Roth conversions modeled independently.
- IRMAA premiums applied based on prior MAGI, doubled for MFJ.
- Marketplace premiums capped at 8.5% of prior MAGI.

---

## 📊 Outputs

Nomad Wealth produces:

- **Historical Charts** → bucket gains, net worth trajectory.
- **Per-Trial Charts** → monthly expenses, transactions, taxes, forecasts.
- **Aggregate Monte Carlo Charts** → monthly returns, taxable balances, totals/rates, net worth distribution.
- **CSV/HTML Exports** → balances, taxes, returns, flows, and interactive charts for audit clarity.

---

## 🎯 Design Principles

- **Policy-First** → declarative JSON rules drive all behavior.
- **Audit Clarity** → every projection is traceable and reproducible.
- **Extensibility** → modular design supports new transaction types, policies, and tax rules.
- **Resilience** → Monte Carlo sampling embraces volatility and quantifies sufficiency.
- **Transparency** → charts and exports provide clear evidence for auditors and users alike.

---

## 📚 Related Pages

- [Configuration Reference](configuration.md)
- [Architecture Overview](architecture.md)
- [Simulation Logic](simulation_logic.md)
- [Visualization Guide](visualization.md)
- [Usage Guide](usage.md)
