# Cloud Cost Intelligence &amp; Anomaly Detection Platform

A multi-cloud **FinOps** pipeline that ingests AWS, GCP, and Azure billing
exports, normalizes them into one canonical schema, flags anomalous spend
with rolling-IQR detection, and visualizes the result in **Grafana** with
alerting — all wired together by **Docker Compose** so anyone can run the
whole stack with a single command.

```
┌──────────────────┐    ┌─────────────────┐    ┌──────────────┐    ┌───────────┐
│  AWS / GCP /     │ →  │  Python pipeline│ →  │  PostgreSQL  │ →  │  Grafana  │
│  Azure CSVs      │    │  (pandas, IQR)  │    │  cost_daily  │    │ + alerts  │
└──────────────────┘    └─────────────────┘    └──────────────┘    └───────────┘
```

## What it does

- **Ingest**: reads each cloud's native billing export (AWS CUR, GCP
  BigQuery-style export, Azure Cost Management export).
- **Normalize**: maps three vendor-specific schemas into one canonical
  `(date, cloud, service, cost)` table.
- **Detect**: per `(cloud, service)` rolling-IQR baseline; flags days whose
  spend exceeds `median + k × IQR`.
- **Persist**: writes labelled rows to PostgreSQL with an index on `date`.
- **Visualize &amp; alert**: provisioned Grafana dashboard with anomaly table,
  spend-by-cloud and spend-by-service trends, plus an alert rule.
<img width="1469" height="801" alt="image" src="https://github.com/user-attachments/assets/a8fe5cd7-32c1-4456-a1f3-74e360c03f67" />

See [`docs/architecture.md`](docs/architecture.md) for the full data-flow
diagram, schema, and design rationale.

## Quick start (Docker — recommended)

```bash
git clone https://github.com/<your-user>/cloud-cost-intelligence.git
cd cloud-cost-intelligence

cp .env.example .env   # then edit POSTGRES_PASSWORD to anything you like

docker compose up --build
```

Then open <http://localhost:3000> and log in with **admin / admin**.

What happens, in order:

1. `postgres` boots and passes its `pg_isready` healthcheck.
2. `pipeline` builds, generates 90 days of synthetic billing data (with
   three injected spikes), runs ingest → normalize → detect → persist,
   prints `Pipeline complete: wrote N rows, flagged 3 anomalies.`, and
   exits cleanly.
3. `grafana` loads the provisioned `CostIntDB` datasource, the
   **Cloud Cost Intelligence** dashboard, and the **Cost Anomaly Detected**
   alert rule.

The dashboard's default time range is `2026-03-01 → 2026-06-01` — the same
window the sample data lives in. If you change the data range, change this
too.

## Quick start (local Python, no Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

python generate_sample_data.py       # writes data/raw/*.csv
python -m src.costint.pipeline       # writes ./costint.db (SQLite fallback)
pytest -v                            # 6 tests, all should pass
```

With no `POSTGRES_HOST` env var set, `persist.py` automatically falls back
to a local SQLite file (`costint.db`) — so you can run the pipeline and
tests with zero external services.

## Project layout

```
cloud-cost-intelligence/
├── src/costint/                # the importable Python package
│   ├── ingest.py               # Stage 1 — read each cloud's CSV
│   ├── normalize.py            # Stage 2 — unify into canonical schema
│   ├── detect.py               # Stage 3 — rolling-IQR anomaly detection
│   ├── persist.py              # Stage 4 — write to Postgres/SQLite
│   └── pipeline.py             # entrypoint that wires 1–4 together
├── tests/                      # pytest unit tests
│   ├── test_detect.py          # 3 tests covering the detection math
│   └── test_normalize.py       # 3 tests covering the schema unification
├── grafana/provisioning/
│   ├── datasources/postgres.yml          # CostIntDB → postgres:5432
│   ├── dashboards/provider.yml           # tells Grafana where to look
│   ├── dashboards/cost_intelligence.json # the dashboard, as code
│   └── alerting/cost_anomaly_alert.yml   # the anomaly alert rule
├── data/raw/                   # generated sample CSVs (git-ignored)
├── docs/
│   ├── architecture.md         # data flow, schema, design rationale
│   └── runbook-cost-anomaly.md # what to do when the alert fires
├── generate_sample_data.py     # produces realistic synthetic billing
├── docker-compose.yml          # postgres + pipeline + grafana
├── Dockerfile                  # the pipeline image
├── requirements.txt            # pinned Python deps
├── .env.example                # copy to .env and fill in
└── .gitignore
```

## How to verify it works (smoke test)

After `docker compose up --build`:

| Check | How |
| --- | --- |
| Pipeline ran cleanly | `docker logs costint-pipeline` ends with `Pipeline complete: wrote 360 rows, flagged 3 anomalies.` |
| Database has data | `docker exec -it costint-postgres psql -U costint -d costint -c "SELECT cloud, COUNT(*) FROM cost_daily GROUP BY cloud;"` |
| Three injected spikes are flagged | `docker exec -it costint-postgres psql -U costint -d costint -c "SELECT date, cloud, service, cost, score FROM cost_daily WHERE is_anomaly = true ORDER BY date;"` |
| Grafana datasource green | <http://localhost:3000> → ⚙ → Data sources → **CostIntDB** → **Save &amp; test** |
| Dashboard renders | <http://localhost:3000/dashboards> → open **Cloud Cost Intelligence** |
| Anomaly table shows three rows | bottom panel of the dashboard |
| Unit tests pass | `pytest -v` |

To prove the alert path end-to-end, edit
`grafana/provisioning/alerting/cost_anomaly_alert.yml` and change the
threshold from `0` to `-1` (so it fires every evaluation) — restart Grafana
(`docker compose restart grafana`), wait one evaluation interval, and watch
the rule transition through **Pending → Firing**. Revert when done.

## Tuning the detector

Both knobs live in `src/costint/detect.py`:

| Parameter | Default | Effect |
| --- | --- | --- |
| `window` | `14` days | The trailing window for the rolling baseline. Longer → smoother, slower to react. |
| `k` | `1.5` | Sensitivity. Lower → more alerts (higher recall, lower precision). Higher → quieter (higher precision, lower recall). |

## Extending to a real cloud

Because ingest is isolated:

1. Drop the cloud's billing export into `data/raw/`.
2. Add a `read_<cloud>` function in `ingest.py`.
3. Add a `normalize_<cloud>` function in `normalize.py` plus one row in
   the `SERVICE_MAP`.
4. Add the cloud to `read_all()` and `normalize_all()`.

Nothing in `detect.py`, `persist.py`, or the dashboard has to change.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `FileNotFoundError` on a CSV | Sample data not generated | `python generate_sample_data.py` |
| No anomalies flagged | `window` too long or `k` too high | Lower `window` or `k` in `detect_anomalies` |
| Every day flagged | `k` too low / series has near-zero IQR | Raise `k`; check the series has real variation |
| `connection refused` to postgres | DB not ready when pipeline started | `docker compose restart pipeline` (healthcheck retries handle this on cold start) |
| Grafana: *database connection failed* | Wrong host in datasource yml | Must be `postgres`, not `localhost` |
| Panels show "No data" | Dashboard time range excludes the data window | Set range to `2026-03-01 → 2026-06-01` |
| Dashboard didn't auto-load | Provider path not mounted | Confirm the volume mount in `docker-compose.yml` |
| Alert never fires | No anomalies in the last 24h | Lower threshold to test, or seed an obvious spike |

## License

MIT — do what you want with it.
