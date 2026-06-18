import pandas as pd

from costint.detect import detect_anomalies


def _series(costs, cloud="aws", service="Compute"):
    dates = pd.date_range("2026-03-01", periods=len(costs), freq="D")
    return pd.DataFrame({
        "date": dates,
        "cloud": cloud,
        "service": service,
        "cost": costs,
    })


def test_flags_obvious_spike():
    costs = [100] * 20 + [900]
    df = detect_anomalies(_series(costs))
    assert bool(df.iloc[-1]["is_anomaly"]) is True
    assert int(df["is_anomaly"].sum()) == 1


def test_ignores_flat_series():
    costs = [100] * 21
    df = detect_anomalies(_series(costs))
    assert int(df["is_anomaly"].sum()) == 0


def test_series_are_independent():
    a = _series([100] * 20 + [900], service="Compute")
    b = _series([50] * 21, service="Storage")
    df = detect_anomalies(pd.concat([a, b], ignore_index=True))
    flagged = df[df["is_anomaly"]]
    assert set(flagged["service"]) == {"Compute"}
