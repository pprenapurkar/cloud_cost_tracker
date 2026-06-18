"""Stage 2 — Normalize each cloud's raw frame into one canonical schema.

Canonical columns: date (datetime64), cloud (str), service (str), cost (float).
"""
import pandas as pd

# Optional: collapse provider-specific names into shared service families.
SERVICE_MAP = {
    "Amazon EC2": "Compute",
    "Amazon S3": "Storage",
    "Networking": "Networking",
    "Azure SQL Database": "Database",
}


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["service"] = df["service"].map(lambda s: SERVICE_MAP.get(s, s))
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
    return df[["date", "cloud", "service", "cost"]].dropna(subset=["cost"])


def normalize_aws(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={
        "lineItem/UsageStartDate": "date",
        "product/ProductName": "service",
        "lineItem/UnblendedCost": "cost",
    })
    out["cloud"] = "aws"
    return _finalize(out)


def normalize_gcp(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={
        "usage_start_time": "date",
        "service_description": "service",
    })
    out["cloud"] = "gcp"
    return _finalize(out)


def normalize_azure(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={
        "Date": "date",
        "MeterCategory": "service",
        "PreTaxCost": "cost",
    })
    out["cloud"] = "azure"
    return _finalize(out)


def normalize_all(raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = [
        normalize_aws(raw["aws"]),
        normalize_gcp(raw["gcp"]),
        normalize_azure(raw["azure"]),
    ]
    unified = pd.concat(frames, ignore_index=True)
    return (
        unified.groupby(["date", "cloud", "service"], as_index=False)["cost"]
        .sum()
        .sort_values(["date", "cloud", "service"])
        .reset_index(drop=True)
    )
