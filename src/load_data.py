import json
import logging
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA = BASE / "data"
CONFIG = BASE / "config"


def load_csv() -> dict[str, pd.DataFrame]:
    if (
        (DATA / "balance.csv").exists()
        and (DATA / "fixed.csv").exists()
        and (DATA / "recurring.csv").exists()
    ):
        return {
            "balance": pd.read_csv(DATA / "balance.csv", parse_dates=["Date"]),
            "fixed": pd.read_csv(DATA / "fixed.csv", parse_dates=["Date"]),
            "recurring": pd.read_csv(
                DATA / "recurring.csv", parse_dates=["Start Date", "End Date"]
            ),
        }
    else:
        logging.error(
            "Required: `balance.csv`, `fixed.csv`, and `recurring.csv` in the `data` directory."
        )
        exit(1)


def load_json() -> dict[str, dict]:
    files = {f.stem: json.loads(f.read_text()) for f in CONFIG.glob("*.json")}
    if "profile" not in files:
        logging.error("Required: `profile.json` in the `config` directory.")
        exit(1)

    return files
