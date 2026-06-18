"""Generate realistic synthetic billing data for AWS, GCP, and Azure.

Produces 90 days of daily spend for a handful of services with weekday
seasonality and noise, then injects three sharp spikes so the detector
has something to catch.

Run:
    python generate_sample_data.py
"""
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
DAYS = 90
START = pd.Timestamp("2026-03-01")
DATES = pd.date_range(START, periods=DAYS, freq="D")
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def seasonal_series(base: float, weekend_drop: float = 0.4, noise: float = 0.08) -> np.ndarray:
    """Daily costs with a weekend dip and mild gaussian noise."""
    vals = []
    for d in DATES:
        factor = (1 - weekend_drop) if d.weekday() >= 5 else 1.0
        jitter = 1 + rng.normal(0, noise)
        vals.append(round(base * factor * jitter, 2))
    return np.array(vals)


def inject_spike(arr: np.ndarray, day_index: int, multiplier: float) -> np.ndarray:
    arr = arr.copy()
    arr[day_index] = round(arr[day_index] * multiplier, 2)
    return arr


def main() -> None:
    # ---- AWS (native CUR-like columns) ----
    aws_compute = inject_spike(seasonal_series(420), 61, 3.4)
    aws_storage = seasonal_series(90)
    aws = pd.concat([
        pd.DataFrame({
            "lineItem/UsageStartDate": DATES,
            "product/ProductName": "Amazon EC2",
            "lineItem/UnblendedCost": aws_compute,
        }),
        pd.DataFrame({
            "lineItem/UsageStartDate": DATES,
            "product/ProductName": "Amazon S3",
            "lineItem/UnblendedCost": aws_storage,
        }),
    ])
    aws.to_csv(RAW_DIR / "aws_cur.csv", index=False)

    # ---- GCP (native export-like columns) ----
    gcp_net = inject_spike(seasonal_series(150), 74, 3.0)
    gcp = pd.DataFrame({
        "usage_start_time": DATES,
        "service_description": "Networking",
        "cost": gcp_net,
    })
    gcp.to_csv(RAW_DIR / "gcp_billing.csv", index=False)

    # ---- Azure (native export-like columns) ----
    az_db = inject_spike(seasonal_series(260), 80, 2.6)
    azure = pd.DataFrame({
        "Date": DATES,
        "MeterCategory": "Azure SQL Database",
        "PreTaxCost": az_db,
    })
    azure.to_csv(RAW_DIR / "azure_costs.csv", index=False)

    print(
        "Wrote 3 sample files to data/raw/ with 3 injected spikes "
        "(AWS EC2 day 61, GCP Networking day 74, Azure SQL day 80)."
    )


if __name__ == "__main__":
    main()
