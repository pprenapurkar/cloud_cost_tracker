import pandas as pd

from costint.normalize import normalize_all, normalize_aws, normalize_azure, normalize_gcp


def _aws_raw():
    return pd.DataFrame({
        "lineItem/UsageStartDate": pd.date_range("2026-03-01", periods=3, freq="D"),
        "product/ProductName": ["Amazon EC2", "Amazon EC2", "Amazon S3"],
        "lineItem/UnblendedCost": [100.0, 110.0, 5.5],
    })


def _gcp_raw():
    return pd.DataFrame({
        "usage_start_time": pd.date_range("2026-03-01", periods=2, freq="D"),
        "service_description": ["Networking", "Networking"],
        "cost": [50.0, 51.0],
    })


def _azure_raw():
    return pd.DataFrame({
        "Date": pd.date_range("2026-03-01", periods=2, freq="D"),
        "MeterCategory": ["Azure SQL Database", "Azure SQL Database"],
        "PreTaxCost": [200.0, 210.0],
    })


def test_canonical_columns_aws():
    df = normalize_aws(_aws_raw())
    assert list(df.columns) == ["date", "cloud", "service", "cost"]
    assert (df["cloud"] == "aws").all()
    assert "Compute" in df["service"].values


def test_canonical_columns_gcp_and_azure():
    g = normalize_gcp(_gcp_raw())
    a = normalize_azure(_azure_raw())
    assert list(g.columns) == ["date", "cloud", "service", "cost"]
    assert list(a.columns) == ["date", "cloud", "service", "cost"]
    assert (g["cloud"] == "gcp").all() and (a["cloud"] == "azure").all()


def test_unified_concat_and_dedup():
    df = normalize_all({"aws": _aws_raw(), "gcp": _gcp_raw(), "azure": _azure_raw()})
    assert set(df["cloud"].unique()) == {"aws", "gcp", "azure"}
    # one row per (date, cloud, service) — duplicates from raw are summed
    grouped = df.groupby(["date", "cloud", "service"]).size()
    assert (grouped == 1).all()
