# Architecture

A four-stage **extract → transform → load → serve** pipeline. Each stage has
one job and hands a clean result to the next stage; when something breaks,
the single-responsibility boundary tells you exactly where the failure is.

## Data flow

```
  AWS CUR csv ─┐
  GCP export ──┼──▶ [ INGEST ]──▶ raw DataFrames (one per cloud)
  Azure export ┘                        │
                                        ▼
                              [ NORMALIZE ]──▶ unified DataFrame
                                        │        (date, cloud, service, cost)
                                        ▼
                               [ DETECT ]──▶ labelled DataFrame
                                        │      (+ rolling_median, rolling_iqr,
                                        │         upper_bound, score, is_anomaly)
                                        ▼
                           [ PERSIST  (SQLAlchemy) ]
                                        │
                                        ▼
                           ┌──────  PostgreSQL  ──────┐
                           │   table: cost_daily       │
                           └─────────────┬─────────────┘
                                         ▼
                                   [ GRAFANA ]
                              panels  +  alert rules
                                         │
                                         ▼
                            email / Slack / PagerDuty
```

## The four stages

| Stage | Module | Responsibility |
| --- | --- | --- |
| Ingest | `src/costint/ingest.py` | Read each cloud's CSV faithfully, in its native column names. |
| Normalize | `src/costint/normalize.py` | Rename, type-coerce, and stack the three sources into one canonical table. |
| Detect | `src/costint/detect.py` | Per `(cloud, service)` rolling-IQR baseline; emit `is_anomaly`, `score`, `upper_bound`. |
| Persist | `src/costint/persist.py` | Write the labelled frame to Postgres (or SQLite); index on `date`. |

`src/costint/pipeline.py` wires the four stages together and is the script
the Docker container runs.

## Canonical schema

| Column | Type | Meaning |
| --- | --- | --- |
| `date` | `date` | The calendar day the cost was incurred. |
| `cloud` | `string` | `aws`, `gcp`, or `azure`. |
| `service` | `string` | Normalized service family (`Compute`, `Storage`, `Networking`, `Database`). |
| `cost` | `float` | USD cost for that `(date, cloud, service)`. |
| `rolling_median` | `float` | Trailing median of `cost` over `window` days within the series. |
| `rolling_iqr` | `float` | Trailing Q3 − Q1 over the same window. |
| `upper_bound` | `float` | `rolling_median + k × rolling_iqr`. |
| `score` | `float` | `(cost − rolling_median) / rolling_iqr` — IQRs above the median. |
| `is_anomaly` | `bool` | `cost > upper_bound`. |

## Column mapping (provider → canonical)

| Canonical | AWS column | GCP column | Azure column |
| --- | --- | --- | --- |
| `date` | `lineItem/UsageStartDate` | `usage_start_time` | `Date` |
| `service` | `product/ProductName` | `service_description` | `MeterCategory` |
| `cost` | `lineItem/UnblendedCost` | `cost` | `PreTaxCost` |

## Component lifecycle

| Component | Container | Lifecycle |
| --- | --- | --- |
| Pipeline (ingest + normalize + detect + persist) | `pipeline` | Short-lived; runs once and exits. |
| Storage | `postgres` | Long-running; state on the `pgdata` volume. |
| Dashboards & alerts | `grafana` | Long-running; config provisioned from files. |

## Why these boundaries matter

- **Replaceability.** Adding a fourth cloud (e.g. Oracle) is one new reader
  plus one row in the column-mapping table — nothing in detect or persist
  has to change.
- **Testability.** Detection is a pure DataFrame-in, DataFrame-out function,
  so it is unit-tested with tiny synthetic inputs and known answers.
- **Operability.** Storage and presentation are separate processes, so
  Grafana can restart without losing data and Postgres can be backed up
  independently of the pipeline.

## Detection algorithm

For each `(cloud, service)` series, ordered by date:

1. `rolling_median` = trailing median over `window` days (default 14).
2. `rolling_iqr` = `quantile(0.75) − quantile(0.25)` over the same window.
3. `upper_bound = rolling_median + k × rolling_iqr` (default `k = 1.5`).
4. `is_anomaly = cost > upper_bound`.

Median and IQR are rank-based and therefore robust to the very outliers the
detector is trying to catch — a single huge spike does not poison the
baseline the way the mean and standard deviation would.

`k` is the sensitivity knob: smaller `k` → higher recall, lower precision;
larger `k` → quieter, may miss subtle drifts. Tune against historical data
and your tolerance for alert fatigue.
