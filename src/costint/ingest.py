"""Stage 1 — Ingest raw billing exports into pandas DataFrames.

Each reader knows only how to load one cloud's native CSV. No reshaping
happens here; that is normalize.py's job.
"""
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")


def _read(path: Path, cloud: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{cloud} export not found at {path}. "
            f"Run 'python generate_sample_data.py' first."
        )
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"{cloud} export at {path} is empty.")
    return df


def read_aws(path: Path = RAW / "aws_cur.csv") -> pd.DataFrame:
    """Read an AWS CUR-style export in its native columns."""
    return _read(path, "AWS")


def read_gcp(path: Path = RAW / "gcp_billing.csv") -> pd.DataFrame:
    """Read a GCP billing-export-style file in its native columns."""
    return _read(path, "GCP")


def read_azure(path: Path = RAW / "azure_costs.csv") -> pd.DataFrame:
    """Read an Azure Cost-Management-style export in its native columns."""
    return _read(path, "Azure")


def read_all() -> dict[str, pd.DataFrame]:
    """Return every cloud's raw frame keyed by cloud name."""
    return {"aws": read_aws(), "gcp": read_gcp(), "azure": read_azure()}
