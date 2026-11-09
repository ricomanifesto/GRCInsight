"""The one product entry point that commits a workflow result for an admitted report.

Both the Lambda handler and the HTTP service call :func:`commit_report`, so
asynchronous and synchronous generation share a single completion contract.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from history.table import DynamoDBTable, HistoryTable
from history.writeback import commit_workflow_result

REFUSED = 409


def history_tables() -> tuple[HistoryTable, HistoryTable]:
    """The existing report and article tables, behind history's conditional-write port."""
    import boto3

    # Same settings the Go service reads (database.endpoint / database.region), so a
    # report admitted into a local DynamoDB is completed in that same store.
    options: dict[str, str] = {}
    if endpoint := os.getenv("DATABASE_ENDPOINT"):
        options["endpoint_url"] = endpoint
    if region := os.getenv("DATABASE_REGION"):
        options["region_name"] = region
    client = boto3.client("dynamodb", **options)
    reports = os.getenv("DDB_TABLE_NAME") or "grcinsight-reports"
    articles = os.getenv("ARTICLES_TABLE_NAME") or "grcinsight-articles"
    return (
        DynamoDBTable(client, reports, "report_id"),
        DynamoDBTable(client, articles, "article_id"),
    )


def commit_report(
    *,
    report_id: str,
    result: Any,
    tables: tuple[HistoryTable, HistoryTable],
    job_id: str | None = None,
    invocation_id: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Commit and describe the decision as an HTTP-style status and a content-free body."""
    reports, articles = tables
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    receipt = commit_workflow_result(
        reports=reports,
        articles=articles,
        report_id=report_id,
        result=result,
        now=now,
        job_id=job_id,
        invocation_id=invocation_id,
    )
    body: dict[str, Any] = {
        "report_id": report_id,
        "job_id": receipt.run_id,
        "decision": receipt.decision,
        "terminal_outcome": receipt.terminal_outcome,
        "outcome_sha256": receipt.outcome_sha256,
        "problems": list(receipt.problems),
    }
    if receipt.accepted:
        body.update(status="completed", message="Report generated and saved to DynamoDB")
        return 200, body
    if receipt.decision == "evidence_failure_recorded":
        return 500, {**body, "status": "failed"}
    if receipt.decision == "integrity_failure":
        return 500, {**body, "status": "failed"}
    return REFUSED, {**body, "status": "refused"}
