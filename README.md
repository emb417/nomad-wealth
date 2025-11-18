# 🕊️ Nomad Wealth: Transparent Forecasting for Financial Freedom

Traditional financial models can be **opaque** and **unauditable**. Nomad Wealth is the Python framework built to solve this challenge. It provides a robust engine for **Monte Carlo simulations** that anchors every projection in **explicit, policy-driven** rules and **IRS-aligned** tax logic. The result is a **transparent and trustworthy** system that gives finance professionals and planners the confidence to **define, test, and execute** their path to financial freedom.

---

## 🚀 Quick Start

```bash
git clone https://github.com/emb417/nomad-wealth
cd nomad-wealth
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/app.py
```

The script runs 100 Monte Carlo trials in approximately 15 seconds and automatically opens your web browser to display 5 charts from a randomly selected trial, along with 2 aggregate charts summarizing all simulations. For best interpretability, we recommend reviewing the charts from right to left — starting with high‑level outcomes and progressively diving into detailed breakdowns.

The chart below visualizes the distribution of net worth outcomes across all trials, month by month. It highlights the median and 15th/85th percentile bounds in green and blue, with individual example trials shown in purple. The chart title includes key summary statistics: total number of trials, the percentage of simulations maintaining positive net worth at various age milestones, and the rate of property liquidations and when (forced sale of the primary residence).

![Monte Carlo Net Worth Chart](/docs/images/mc_networth.png)

---

## 📚 Documentation

Full documentation 👉 [Nomad Wealth Docs](https://emb417.github.io/nomad-wealth/)

---

## 🗺️ Roadmap

- ✅ Current
  - Monte Carlo engine, IRS-compliant tax logic, visualization suite
- 🔜 Next
  - Configurable scenario overlays and multi-profile support
  - Enhanced audit exports and interactive forecast comparisons
  - Expanded account types (HSA, IRA contributions, vesting schedules)
  - Policy-driven UI for balances, transactions, and income sources
- 🎯 Future
  - Advisor collaboration tools and policy comparison dashboards
  - Advanced expense modeling (e.g., “smile” curve for retirement spending)
  - Equity-specific forecasting with market value integration
  - Self-employment and unemployment income/tax handling

---

## 🤝 Contributing

Pull requests welcome. Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

---

## 📄 License

Nomad Wealth is proprietary software. Contact for licensing. See [`LICENSE`](LICENSE) for details.

---
