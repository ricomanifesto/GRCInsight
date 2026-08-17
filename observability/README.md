# Claude Code Monitoring

A local observability stack for [Claude Code's OpenTelemetry
export](https://code.claude.com/docs/en/monitoring-usage): an OTel Collector
that receives metrics and events from Claude Code, Prometheus to store the
metrics, Loki to store the events, and Grafana to visualize both.

This directory only holds shared infrastructure. Nothing here enables
telemetry by itself — that's a local, per-developer setting (see below).

## 1. Start the stack

```bash
cd observability
docker compose up -d
```

This starts:

| Service        | Port | Purpose                                |
|----------------|------|-----------------------------------------|
| otel-collector | 4317 | Receives OTLP gRPC from Claude Code     |
| otel-collector | 4318 | Receives OTLP HTTP from Claude Code     |
| prometheus     | 9090 | Stores/queries metrics                  |
| loki           | 3100 | Stores/queries logs (events)            |
| grafana        | 3000 | Dashboards — http://localhost:3000      |

Grafana comes pre-provisioned with a "Claude Code Usage" dashboard (Prometheus
+ Loki datasources included), no login required for local use.

## 2. Point Claude Code at the collector

`.claude/` is intentionally excluded from this repo's git history (see
`.gitignore`), so telemetry is opt-in per developer. Create
`.claude/settings.json` in the repo root (it will not be committed) with:

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
    "OTEL_METRIC_EXPORT_INTERVAL": "10000",
    "OTEL_LOGS_EXPORT_INTERVAL": "5000"
  }
}
```

Or, without a settings file, export the same variables in your shell before
running `claude`:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Restart `claude` after setting these — telemetry config is read at startup.

## 3. Verify

- Run a Claude Code session, then check Prometheus has data:
  `curl -s http://localhost:9090/api/v1/query?query=claude_code_session_count_total`
- Or just open Grafana at http://localhost:3000 and view the "Claude Code
  Usage" dashboard under the "Claude Code" folder.
- `claude --debug` prints OTel export errors if nothing shows up.

## Stopping

```bash
docker compose down          # stop, keep data
docker compose down -v       # stop and wipe Prometheus/Loki/Grafana volumes
```

## Notes

- This stack is for local development only — it has no auth on Prometheus
  or Loki, and Grafana runs with anonymous Admin access. Do not expose these
  ports outside localhost.
- To send telemetry to a shared/team backend instead of this local stack,
  point `OTEL_EXPORTER_OTLP_ENDPOINT` at that collector instead, or add
  `OTEL_EXPORTER_OTLP_HEADERS` for auth. See the [official
  docs](https://code.claude.com/docs/en/monitoring-usage) for the full
  variable reference (traces, content logging, cardinality controls, etc.).
