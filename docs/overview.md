# 🌐 Framework Overview

Nomad Wealth is a **policy‑driven financial simulation framework** built for transparency, clarity, and confidence. It models retirement scenarios, withdrawal strategies, and tax implications using **Monte Carlo simulations** and **IRS‑aligned rules**.

---

## 🎯 Purpose

Nomad Wealth helps you plan retirement with confidence by:  

- Showing whether your savings are sufficient under uncertainty.  
- Comparing scenarios with clear percentile overlays and reference lines.  
- Tracing every dollar across accounts, transactions, and policies.  
- Ensuring forecasts align with IRS rules and historical data.  
- Exporting reproducible charts and CSVs you can review or share.  

---

## 🧩 Core Components

Nomad Wealth is organized into modular layers:

- **Configuration** → Define your accounts, policies, and balances.  
- **Architecture** → Behind‑the‑scenes system design (for advanced users).  
- **Simulation Logic (`forecast_engine.py`)** → How monthly forecasts and Monte Carlo trials are calculated.  
- **Visualization (`visualizations.py`)** → Charts and exports that make your plan easy to understand.  
- **Usage** → Options to control forecast size, charts, and exports.  

---

## 📂 Workflow

1. **Configure**  
    - Set up accounts, balances, and tax rules.  
2. **Simulate**  
    - Run Monte Carlo trials that apply monthly transactions, policies, market returns, and taxes.  
    - Results are aggregated into net worth, taxes, balances, and flow logs.  
    - Every debit and credit is tracked for reproducibility.  
3. **Visualize**  
    - Generate charts and reports that show whether you’re on track.  
    - Export HTML and CSV outputs with consistent color palettes, percentile overlays, and hover text for clarity.  

---

## 🧾 IRS Alignment

Nomad Wealth enforces IRS rules so your forecasts reflect reality:  

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

- **Historical Charts** → See how your accounts have grown and changed.  
- **Per‑Trial Charts** → Explore detailed monthly forecasts.  
- **Aggregate Monte Carlo Charts** → Understand probabilities and ranges for your retirement outlook.  
- **CSV/HTML Exports** → Download reports for deeper review or sharing.  

---

## 🎯 Design Principles

- **Policy‑First** → Your plan follows clear, rule‑based logic.  
- **Audit Clarity** → Every forecast is traceable, so you can trust the numbers.  
- **Resilience** → Monte Carlo simulations show how your plan holds up under uncertainty.  
- **Transparency** → Charts and reports make it easy to see what’s happening.  
- **Extensibility** → Advanced users can customize rules, but you don’t need to for core planning.  

---

## 📚 Related Pages

- [Configuration Reference](configuration.md)  
- [Architecture Overview](architecture.md)  
- [Simulation Logic](simulation_logic.md)  
- [Visualization Guide](visualization.md)  
- [Usage Guide](usage.md)  
