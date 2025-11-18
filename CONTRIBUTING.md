# 🤝 Contributing to Nomad Wealth

Thank you for your interest in contributing to **Nomad Wealth**! This framework is built for **transparent, auditable financial forecasting**, so contributions must uphold the same principles of clarity, reproducibility, and IRS alignment.

---

## 📋 Contribution Workflow

1. **Fork & Branch**
   - Fork the repository and create a feature branch:

     ```bash
     git checkout -b feature/my-feature
     ```

2. **Code Standards**
   - Write Python code that is explicit, reproducible, and defensive against edge cases.
   - Favor config‑driven design with overridable parameters.
   - Ensure helper functions are reusable and documented.

3. **Documentation**
   - Update relevant Markdown files (`usage.md`, `overview.md`, `configuration.md`, etc.) whenever code changes affect orchestration, inputs, or outputs.
   - Maintain **audit clarity**: every new function, policy, or chart must be documented with purpose, inputs, and outputs.
   - Use consistent terminology (IRS‑aligned, buckets, policies, flows).

4. **Testing**
   - Add or update unit tests for new logic.
   - Validate simulation outputs against historical distributions when relevant.
   - Confirm reproducibility: outputs should match expectations across runs.

5. **Commit Messages**
   - Use clear, descriptive commit messages, examples:

     ```bash
     added Roth conversion break-even logic
     updated configuration.md with new schema fields
     ```

6. **Pull Requests**
   - Reference related issues.
   - Summarize changes and their impact on audit clarity.
   - Include screenshots or sample outputs if visualization logic is affected.

---

## 🧾 Audit & Compliance Notes

- **IRS Alignment**: Contributions must respect IRS rules (e.g., SEPP gating, Roth conversion ordering, IRMAA premiums).
- **Transparency**: Every projection, chart, and export must be traceable to inputs and policies.
- **Reproducibility**: Ensure outputs can be reproduced with the same inputs/configs.

---

## 📚 Resources

- [Framework Overview](docs/overview.md)
- [Configuration Reference](docs/configuration.md)
- [Architecture Overview](docs/architecture.md)
- [Simulation Logic](docs/simulation_logic.md)
- [Visualization Guide](docs/visualization.md)
- [Usage Guide](docs/usage.md)

---

## 🎯 Philosophy

Nomad Wealth thrives on **policy‑first design, audit clarity, and extensibility**.  
Contributions should make the system more transparent, more reproducible, and easier to validate — never more opaque.
