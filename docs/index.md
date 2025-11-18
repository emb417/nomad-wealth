# 🕊️ Nomad Wealth Documentation

Welcome to the documentation for **Nomad Wealth**, the Python framework for **transparent financial forecasting**. Where traditional models can be opaque and unauditable, Nomad Wealth is built to deliver **clarity, reproducibility, and confidence**.  

This site is more than a technical manual — it’s a guide to understanding how policy‑driven rules, IRS‑aligned tax logic, and Monte Carlo simulations come together to create a **trustworthy system for financial planning**. Whether you’re an auditor validating compliance or a planner exploring retirement scenarios, these pages will help you **define, test, and execute** strategies with confidence.

---

## 🚀 Getting Started

The best place to begin is the [Framework Overview](overview.md). It explains the purpose of Nomad Wealth, its design principles, and how the system fits together.

---

## 📚 Documentation Structure

- **Framework Overview** → Conceptual landing page, purpose, workflow, design principles.
- **Configuration Reference** → JSON and CSV schemas for buckets, policies, and seed balances.
- **Architecture Overview** → Modular system design and data flow.
- **Simulation Logic (`forecast_engine.py`)** → Step‑by‑step execution of the monthly forecast loop and Monte Carlo trials.
- **Visualization Guide (`visualizations.py`)** → Interactive charts (historical, per‑trial, Monte Carlo) and CSV/HTML exports for audit clarity.
- **Usage Guide** → How to run simulations, control flags, and interpret outputs.

> Each section includes **audit notes** to ensure reproducibility and IRS‑aligned transparency.

---

## 🎯 Design Philosophy

Nomad Wealth is built around:

- **Policy‑First** → declarative JSON rules drive all behavior.
- **Audit Clarity** → every projection is traceable and reproducible.
- **IRS Alignment** → tax rules, penalties, and premiums modeled explicitly.
- **Extensibility** → modular design supports new transaction types, policies, and tax rules.
- **Resilience** → Monte Carlo sampling embraces volatility and quantifies sufficiency.
- **Transparency & Reproducibility** → charts, CSV/HTML exports, and logging provide clear evidence for auditors and users alike.

---

## 📚 Next Steps

👉 Start with the [Framework Overview](overview.md) to understand the system’s purpose and design.  
From there, follow the flow: **Configuration → Architecture → Simulation → Visualization → Usage**.
