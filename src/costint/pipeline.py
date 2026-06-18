"""End-to-end pipeline entrypoint: ingest -> normalize -> detect -> persist."""
from .detect import detect_anomalies
from .ingest import read_all
from .normalize import normalize_all
from .persist import persist


def run() -> None:
    raw = read_all()
    unified = normalize_all(raw)
    labelled = detect_anomalies(unified)
    n = persist(labelled)
    anomalies = int(labelled["is_anomaly"].sum())
    print(f"Pipeline complete: wrote {n} rows, flagged {anomalies} anomalies.")


if __name__ == "__main__":
    run()
