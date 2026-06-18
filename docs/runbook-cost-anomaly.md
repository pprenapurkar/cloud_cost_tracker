# Runbook: Cost Anomaly Alert

## Trigger

Grafana alert **"Cost Anomaly Detected"** is `Firing`: one or more rows in
`cost_daily` have `is_anomaly = true` within the last 24 hours.

## Severity

`warning` — financial impact, not a customer-facing outage. Investigate
during business hours unless the run-rate impact is large enough to warrant
overnight action.

## Likely causes

- A misconfigured resource (oversized VM, runaway autoscaler, forgotten
  test cluster).
- A new deployment that legitimately increased usage.
- A cross-region data-transfer or egress loop.
- A pricing/tagging change in the billing export that shifted costs into a
  category that previously had little spend.

## Diagnose

1. Open the **Spend by service** panel and identify which
   `(cloud, service)` is driving the spike.
2. Note the date and the `score` column (= how many IQRs above the rolling
   median).
3. Correlate with deploy/change logs for that service on that day.
4. If multiple services on the same cloud spike at once, suspect a billing
   export anomaly before suspecting a real workload issue.

## Remediate

- **Misconfiguration:** right-size or terminate the resource; confirm with
  the owning team.
- **Legitimate increase:** acknowledge the alert. If the new level is the
  new normal, the rolling baseline will absorb it within the detection
  window (default 14 days) and the alert will self-resolve.
- **Data/pricing artifact:** fix the export pipeline or exclude the meter
  from the dataset.

## Confirm recovery

1. Re-run the pipeline (or wait for the next scheduled run).
2. The flagged `(cloud, service)` should fall back under `upper_bound`.
3. The alert should return to `Normal` at the next evaluation interval.

## Escalate

If spend continues climbing after remediation, page the cloud-platform
owner for that provider and open an incident in your tracker.

## Tuning

- If alerts fire too often: raise `k` in `detect_anomalies` (try `2.0`) or
  lengthen the detection `window`.
- If real spikes slip through: lower `k` (try `1.2`) or shorten the window
  so the baseline reacts faster.
- Re-evaluate at least once a quarter against recent alert history.
