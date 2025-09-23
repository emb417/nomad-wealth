import json
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA = BASE / "data"
CONFIG = BASE / "config"


def load_csv() -> dict[str, pd.DataFrame]:
    return {
        "balance": pd.read_csv(DATA / "balance.csv", parse_dates=["Date"]),
        "fixed": pd.read_csv(DATA / "fixed.csv", parse_dates=["Date"]),
        "recurring": pd.read_csv(
            DATA / "recurring.csv", parse_dates=["Start Date", "End Date"]
        ),
    }


def load_json() -> dict[str, dict]:
    return {
        "profile": json.loads((CONFIG / "profile.json").read_text()),
        "gain_table": json.loads((CONFIG / "gain_table.json").read_text()),
        "inflation_rate": json.loads((CONFIG / "inflation_rate.json").read_text()),
        "inflation_thresholds": json.loads(
            (CONFIG / "inflation_thresholds.json").read_text()
        ),
        "holdings": json.loads((CONFIG / "holdings.json").read_text()),
        "refill_policy": json.loads((CONFIG / "refill_policy.json").read_text()),
    }
