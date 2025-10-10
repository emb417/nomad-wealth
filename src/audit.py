import pandas as pd


class FlowTracker:
    def __init__(self):
        self.records = []

    def record(
        self,
        source: str,
        target: str,
        amount: int,
        tx_month: pd.Period,
        flow_type: str,
    ):
        self.records.append(
            {
                "date": tx_month,
                "source": source,
                "target": target,
                "amount": amount,
                "type": flow_type,
            }
        )

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.records)
