"""Synthetic, deterministic history scenarios driven through the real writeback and export.

Everything here is invented test data on in-memory tables. It exists so the
newsletter import path and reviewers can replay the export contract without
touching a provider.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from history.export import export_all, export_report
from history.table import MemoryTable
from history.writeback import commit_workflow_result
from models.api import ArticleRecord, APIError, Report, ReportMetadata, WorkflowResponse

GENERATED_AT = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
FEED = "https://feeds.example.test/grc-weekly.xml"


def tables() -> tuple[MemoryTable, MemoryTable]:
    return MemoryTable("grcinsight-reports", "report_id"), MemoryTable(
        "grcinsight-articles", "article_id"
    )


def open_report(
    reports: MemoryTable,
    report_id: str,
    *,
    status: str = "processing",
    job_id: str | None = "",
) -> None:
    """The row the Go service creates (with its admitted job id) before invoking Python."""
    job = f"job-{report_id}" if job_id == "" else job_id
    reports.seed(
        {
            "report_id": report_id,
            **({"job_id": job} if job else {}),
            "title": "GRC Intelligence Report - 2026-11-02",
            "content": "",
            "status": status,
            "source_url": FEED,
            "created_at": "2026-11-02T08:59:00Z",
            "updated_at": "2026-11-02T08:59:00Z",
            "metadata": {},
        }
    )


def article(
    slug: str,
    *,
    body: str | None = None,
    published: datetime | None = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc),
    tags: list[str] | None = None,
) -> ArticleRecord:
    return ArticleRecord(
        title=f"Synthetic regulator notice {slug}",
        url=f"https://news.example.test/{slug}",
        content=(
            body
            if body is not None
            else f"<p>Synthetic body for {slug}: the example regulator updated its rule.</p>"
        ),
        summary=f"Synthetic summary for {slug}.",
        source="Example Wire",
        digest_url="",
        published=published or GENERATED_AT,
        published_known=published is not None,
        has_grc_content=True,
        regulations=tags or ["Example Rule 1"],
    )


def result(
    articles: list[ArticleRecord],
    *,
    mode: str = "model",
    content: str = "# GRC Intelligence Report\n\nSynthetic generated conclusion.",
    status: str = "completed",
    generated_at: datetime = GENERATED_AT,
) -> WorkflowResponse:
    if status != "completed":
        return WorkflowResponse(
            status="failed",
            error=APIError(
                code="WORKFLOW_EXECUTION_ERROR",
                message="Workflow execution failed",
                details="synthetic feed timeout",
            ),
        )
    metadata = ReportMetadata(
        article_count=len(articles),
        grc_article_count=len(articles),
        analysis_mode=mode,
        fallback_reason=None if mode == "model" else "synthetic model refusal",
        source_name="Synthetic GRC Weekly",
        source_url=FEED,
        requested_model="example/requested-model",
        resolved_model="example/resolved-model" if mode == "model" else "",
        analysis_period="November 2026",
        source_articles=[
            {
                "title": a.title,
                "url": a.url,
                "digest_url": "",
                "cves": [],
                "snippet": a.summary,
                "article_evidence": [
                    {
                        "origin": "summary",
                        "extraction_version": 1,
                        "raw_text": a.summary,
                        "text": a.summary,
                    }
                ],
                "effective_date_evidence": [],
            }
            for a in articles
        ],
        relevance_diagnostics={"uncertain_share": 0.25},
    )
    return WorkflowResponse(
        status="completed",
        report=Report(
            title="GRC Intelligence Report - 2026-11-02", content=content, generated_at=generated_at
        ),
        metadata=metadata,
        articles=articles,
    )


def build_scenarios() -> tuple[MemoryTable, MemoryTable, list[dict[str, Any]]]:
    """Run every acceptance scenario and return the tables plus decision receipts."""
    reports, articles = tables()
    receipts: list[dict[str, Any]] = []

    def commit(
        name: str,
        report_id: str,
        job_id: str | None,
        res: WorkflowResponse,
        now: str,
        invocation_id: str | None = None,
    ) -> None:
        r = commit_workflow_result(
            reports=reports,
            articles=articles,
            report_id=report_id,
            job_id=job_id,
            invocation_id=invocation_id,
            result=res,
            now=now,
        )
        receipts.append({"scenario": name, **r.__dict__, "problems": list(r.problems)})

    week1 = [article("alpha"), article("bravo", published=None)]
    open_report(reports, "report_s1")
    commit(
        "first completion",
        "report_s1",
        "job-report_s1",
        result(week1),
        "2026-11-02T09:01:00Z",
        "invocation-a",
    )
    # A retried or duplicated delivery may carry a different invocation id.
    commit(
        "duplicate request",
        "report_s1",
        "job-report_s1",
        result(week1),
        "2026-11-02T09:05:00Z",
        "invocation-b",
    )
    commit(
        "stale same-run divergent completion",
        "report_s1",
        "job-report_s1",
        result(week1, content="# Diverged retry"),
        "2026-11-02T09:06:00Z",
    )
    commit("foreign completion", "report_s1", "job-foreign", result(week1), "2026-11-02T09:07:00Z")

    week2 = [
        article("alpha", body="<p>Synthetic body for alpha, revised with a correction.</p>"),
        article("bravo", published=None),
    ]
    open_report(reports, "report_s2")
    commit(
        "changed article revision",
        "report_s2",
        "job-report_s2",
        result(week2),
        "2026-11-09T09:01:00Z",
    )

    open_report(reports, "report_s3")
    commit(
        "fallback refusal",
        "report_s3",
        "job-report_s3",
        result(
            week1, mode="fallback", content="# GRC Intelligence Report\n\nModel output unavailable."
        ),
        "2026-11-09T10:00:00Z",
    )

    open_report(reports, "report_s4")
    commit(
        "failed run",
        "report_s4",
        "job-report_s4",
        result([], status="failed"),
        "2026-11-09T11:00:00Z",
    )

    # Interrupted completion: evidence lands, the completion write never does.
    open_report(reports, "report_s5")

    def crash(kind: str, _item: dict[str, Any]) -> None:
        if kind == "complete":
            raise RuntimeError("synthetic crash before completion")

    articles_before = set(articles.items)
    reports.before_write = crash
    try:
        commit(
            "interrupted completion",
            "report_s5",
            "job-report_s5",
            result([article("charlie")]),
            "2026-11-09T12:00:00Z",
        )
    except RuntimeError:
        receipts.append(
            {
                "scenario": "interrupted completion",
                "decision": "crashed_before_commit",
                "evidence_items_left": len(set(articles.items) - articles_before),
            }
        )
    finally:
        reports.before_write = None
    commit(
        "recovery after interruption",
        "report_s5",
        "job-report_s5",
        result([article("charlie")]),
        "2026-11-09T12:10:00Z",
    )

    # Cancelled by the lifecycle owner; a late completion must not resurrect it.
    open_report(reports, "report_s6", status="failed")
    commit(
        "late completion after cancel",
        "report_s6",
        "job-report_s6",
        result(week1),
        "2026-11-09T13:00:00Z",
    )

    # Legacy rows written before history existed.
    reports.seed(
        {
            "report_id": "report_20251001_090000_123",
            "title": "GRC Intelligence Report - 2025-10-01",
            "content": "# Legacy report",
            "status": "completed",
            "source_url": FEED,
            "created_at": "2025-10-01T09:00:00Z",
            "updated_at": "2025-10-01T09:20:00Z",
            "generated_at": "2025-10-01T09:20:00Z",
            "metadata": {"analysis_mode": "model", "source_url": FEED, "source_articles": []},
        }
    )
    articles.seed(
        {
            "article_id": "a_20251001_0badc0de",
            "numeric_id": 195936478,
            "report_id": "report_20251001_090000_123",
            "title": "Legacy synthetic article",
            "url": "https://news.example.test/legacy",
            "content": "Legacy synthetic body.",
            "summary": "",
            "source": "Example Wire",
            "digest_url": "",
            "published": "2025-10-01T09:20:00Z",
            "created_at": "2025-10-01T09:20:00Z",
            "updated_at": "2025-10-01T09:20:00Z",
            "has_grc_content": True,
            "regulations": [],
            "frameworks": [],
            "industries": [],
            "regulatory_bodies": [],
        }
    )

    # Evidence corruption: a retained revision is edited behind history's back, then the
    # same source is captured again. The conflict must be visible and block completion.
    corrupted = next(
        k
        for k, v in articles.items.items()
        if v.get("url") == "https://news.example.test/bravo"
        and v.get("record_kind") == "article_revision"
    )
    articles.items[corrupted]["content"] = "<p>Tampered text.</p>"
    open_report(reports, "report_s7")
    commit(
        "conflicting identity",
        "report_s7",
        "job-report_s7",
        result([article("bravo", published=None)]),
        "2026-11-09T14:00:00Z",
    )
    return reports, articles, receipts


def dynamodb_items(reports: MemoryTable, articles: MemoryTable) -> dict[str, Any]:
    """Every stored item in DynamoDB's typed JSON, for readers in other languages."""
    from boto3.dynamodb.types import TypeSerializer

    from history.table import to_dynamo

    ser = TypeSerializer()

    def typed(item: dict[str, Any]) -> dict[str, Any]:
        out = {}
        for k, v in to_dynamo(item).items():
            out[k] = json.loads(json.dumps(ser.serialize(v), default=str))
        return out

    return {
        table.name: [typed(table.items[k]) for k in sorted(table.items)]
        for table in (reports, articles)
    }


# model_completed with a corrupt revision, a changed revision, fallback, failed and legacy.
KEYED_FIXTURE_REPORTS = (
    "report_s1",
    "report_s2",
    "report_s3",
    "report_s4",
    "report_20251001_090000_123",
)


def write_fixture(out_dir: Path, *, limit: int = 3) -> dict[str, Any]:
    """Write receipts, paged export and a replay check; output is byte-stable."""
    out_dir.mkdir(parents=True, exist_ok=True)
    reports, articles, receipts = build_scenarios()
    lines: list[str] = []
    pages: dict[str, list[dict[str, Any]]] = {}
    for stream, table in (("reports", reports), ("articles", articles)):
        pages[stream] = list(export_all(table, stream=stream, limit=limit))
        for page in pages[stream]:
            lines.extend(json.dumps(r, sort_keys=True) for r in page["records"])
    replay = []
    for stream, table in (("reports", reports), ("articles", articles)):
        replay.extend(
            json.dumps(r, sort_keys=True)
            for page in export_all(table, stream=stream, limit=limit)
            for r in page["records"]
        )
    keys = [(json.loads(x)["record_id"], json.loads(x)["record_revision"]) for x in lines]
    check = {
        "records": len(lines),
        "replay_identical": replay == lines,
        "unique_record_revisions": len(set(keys)),
        "duplicate_record_revisions": len(keys) - len(set(keys)),
    }
    files = {
        "dynamodb-items.json": dynamodb_items(reports, articles),
        "scenario-receipts.json": receipts,
        "export-pages.json": pages,
        "replay-check.json": check,
    }
    # One keyed export per kind of outcome, as a consumer reading by report id sees it.
    for report_id in KEYED_FIXTURE_REPORTS:
        files[f"keyed/{report_id}.json"] = export_report(reports, articles, report_id)
    (out_dir / "keyed").mkdir(exist_ok=True)
    for name, data in files.items():
        (out_dir / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    (out_dir / "export.jsonl").write_text("\n".join(lines) + "\n")
    return check
