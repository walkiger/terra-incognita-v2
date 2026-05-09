# Prometheus files for Hub Compose (`deploy/compose/hub.yml`, profile **default**).

| File                      | Role                                                                                               |
| ------------------------- | -------------------------------------------------------------------------------------------------- |
| `prometheus.yml`          | Scrape self, Hub API `/metrics` (Bearer file), node-exporter.                                      |
| `alert_rules.example.yml` | Placeholder rule groups; thresholds documented from MVP §10.                                       |
| `bearer.token`            | Bearer string Prometheus sends to FastAPI `/metrics` (**rotate** in prod; prefer env via decrypt). |

API reads `METRICS_BEARER_TOKEN` (Compose default matches this file for bootstrap).
