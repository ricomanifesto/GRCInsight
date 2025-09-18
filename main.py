"""
Deprecated entrypoint.

The monolithic workflow has moved to `legacy/`. Use the serverless path instead:
- API Gateway → Go Lambda → Python Lambda → DynamoDB
- Or run services locally: `agent/main.py` (FastAPI) and `cmd/server/main.go` (Go)

This script is kept only to avoid breaking references. It does nothing.
"""

import sys
import textwrap

message = textwrap.dedent(
    """
    GRCInsight legacy monolith has been moved to `legacy/` and is no longer maintained.

    Recommended usage:
    - Serverless: trigger the Lambda workflow (see .github/workflows/lambda-report-generation.yml)
    - Local dev: run FastAPI in `agent/` and Go server in `cmd/server/`

    If you still need the old behavior, run: `python legacy/main.py`
    """
)

print(message)
sys.exit(0)

