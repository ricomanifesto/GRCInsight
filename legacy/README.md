Legacy Monolith
===============

Deprecated single‑process Python implementation (former `main.py` and `src/`). Kept for reference.

Current path:
- Go API/Lambda: `cmd/`, `internal/`
- Python Agent/Lambda: `agent/`
- Serverless flow: API Gateway → Go Lambda → Python Lambda → DynamoDB

Run legacy locally only if needed: `python legacy/main.py`

Use now:
- Local dev: `agent/main.py` and `cmd/server/main.go`
- Serverless: `.github/workflows/lambda-report-generation.yml`
