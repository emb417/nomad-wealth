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
    files = {f.stem: json.loads(f.read_text()) for f in CONFIG.glob("*.json")}
    return files
