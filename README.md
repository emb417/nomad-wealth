# 🕊️ Nomad Wealth: Transparent Forecasting for Financial Freedom  

If you’ve ever tried a financial planning tool and felt like you couldn’t see the assumptions behind the numbers, you know how frustrating that can be. Nomad Wealth is built to solve that challenge.  

It’s a Python framework that runs **Monte Carlo simulations** anchored in **explicit, policy‑driven rules** and **IRS‑aligned tax logic**. Instead of opaque forecasts, you get a system where every projection is **transparent, reproducible, and trustworthy**.  

Nomad Wealth gives finance professionals, planners, and curious retirees the confidence to **define scenarios, test “what‑ifs,” and make decisions** with clarity about how the numbers were calculated and why they matter.  

---

## 🚀 Quick Start  

```bash
git clone https://github.com/emb417/nomad-wealth
cd nomad-wealth
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/app.py
```  

The script runs 100 Monte Carlo trials in about 15 seconds and automatically opens your browser to display:

- **5 charts** from a randomly selected trial, showing detailed flows.  
- **2 aggregate charts** summarizing all simulations.  

For best interpretability, review the charts from right to left — start with high‑level outcomes, then dive into detailed breakdowns.  

The chart below shows the distribution of net worth outcomes across all trials, month by month. It highlights the median and 15th/85th percentile bounds in green and blue, with individual example trials shown in purple. The chart title includes key summary statistics: number of trials, the percentage of simulations maintaining positive net worth at age milestones, and property liquidation rates (forced sale of the primary residence).  

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
