"""Stage 3 — Robust rolling-IQR anomaly detection per (cloud, service)."""
import pandas as pd


def detect_anomalies(
    df: pd.DataFrame,
    window: int = 14,
    k: float = 1.5,
) -> pd.DataFrame:
    """Flag daily spend that exceeds a robust rolling upper bound.

    Adds columns: rolling_median, rolling_iqr, upper_bound, score, is_anomaly.

    The detector groups by (cloud, service) so each series gets its own
    independent baseline — mixing AWS Compute into GCP Networking's
    baseline would be meaningless.
    """
    df = df.sort_values(["cloud", "service", "date"]).copy()
    out_frames = []

    for (_cloud, _service), grp in df.groupby(["cloud", "service"], sort=False):
        grp = grp.copy()
        cost = grp["cost"]

        roll = cost.rolling(window=window, min_periods=max(3, window // 2))
        med = roll.median()
        q1 = roll.quantile(0.25)
        q3 = roll.quantile(0.75)
        iqr = q3 - q1

        upper = med + k * iqr
        grp["rolling_median"] = med
        grp["rolling_iqr"] = iqr
        grp["upper_bound"] = upper
        safe_iqr = iqr.where(iqr > 0)
        grp["score"] = ((cost - med) / safe_iqr).fillna(0.0).astype(float)
        grp["is_anomaly"] = (cost > upper).fillna(False).astype(bool)
        out_frames.append(grp)

    result = pd.concat(out_frames, ignore_index=True)
    return result.sort_values(["date", "cloud", "service"]).reset_index(drop=True)
