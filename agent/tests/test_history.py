"""Report and article history on the existing DynamoDB tables."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from history import export as history_export
from history import fixture as fx
from history.export import CursorError, export_all, export_page
from history.identity import MAX_RETAINED_CONTENT
from history.table import ConditionFailed, DynamoDBTable
from history.writeback import commit_workflow_result

NOW = "2026-11-02T09:01:00Z"


def commit(reports, articles, report_id="r1", job_id=None, res=None, now=NOW, invocation=None):
    return commit_workflow_result(
        reports=reports,
        articles=articles,
        report_id=report_id,
        job_id=job_id,
        invocation_id=invocation,
        result=res if res is not None else fx.result([fx.article("alpha")]),
        now=now,
    )


@pytest.fixture
def store():
    reports, articles = fx.tables()
    fx.open_report(reports, "r1")
    return reports, articles


def kinds(articles, kind):
    return [v for v in articles.items.values() if v.get("record_kind") == kind]


def test_first_completion_binds_immutable_evidence(store):
    reports, articles = store
    receipt = commit(reports, articles, res=fx.result([fx.article("alpha"), fx.article("bravo")]))
    assert receipt.decision == "committed" and receipt.terminal_outcome == "model_completed"
    row = reports.items["r1"]
    assert row["status"] == "completed" and row["completion_run_id"] == "job-r1"
    assert row["outcome_sha256"] == receipt.outcome_sha256
    revisions = kinds(articles, "article_revision")
    appearances = kinds(articles, "report_article_appearance")
    assert len(revisions) == 2 and len(appearances) == 2
    assert row["article_revision_ids"] == [a["revision_id"] for a in appearances]
    assert all("report_id" not in r for r in revisions)  # stays out of the by-report-id index
    assert all(a["content"] == "" and a["report_id"] == "r1" for a in appearances)


def test_duplicate_request_is_acknowledged_without_writes(store):
    reports, articles = store
    commit(reports, articles)
    before = copy.deepcopy((reports.items, articles.items))
    again = commit(reports, articles, now="2026-11-02T10:00:00Z")
    assert again.decision == "reused" and again.accepted
    assert (reports.items, articles.items) == before


def test_stale_and_foreign_completions_never_rewrite_the_outcome(store):
    reports, articles = store
    commit(reports, articles)
    before = copy.deepcopy(reports.items["r1"])
    diverged = fx.result([fx.article("alpha")], content="# Diverged retry")
    assert commit(reports, articles, res=diverged).decision == "stale_completion_refused"
    assert commit(reports, articles, job_id="job-other").decision == "foreign_completion_refused"
    assert reports.items["r1"] == before


def test_changed_article_is_a_new_revision_and_unchanged_one_is_reused():
    reports, articles = fx.tables()
    fx.open_report(reports, "r1")
    fx.open_report(reports, "r2")
    commit(reports, articles, "r1", res=fx.result([fx.article("alpha"), fx.article("bravo")]))
    changed = fx.article("alpha", body="<p>Revised synthetic body with a correction.</p>")
    receipt = commit(reports, articles, "r2", res=fx.result([changed, fx.article("bravo")]))
    assert (receipt.revisions_written, receipt.revisions_reused) == (1, 1)
    alpha = [r for r in kinds(articles, "article_revision") if r["url"].endswith("/alpha")]
    assert len(alpha) == 2 and len({r["source_key"] for r in alpha}) == 1
    assert len({r["content_sha256"] for r in alpha}) == 2
    assert {r["first_report_id"] for r in alpha} == {"r1", "r2"}


def test_interrupted_completion_recovers_by_reusing_evidence(store):
    reports, articles = store

    def crash(kind, _item):
        if kind == "complete":
            raise RuntimeError("crash")

    reports.before_write = crash
    with pytest.raises(RuntimeError):
        commit(reports, articles)
    reports.before_write = None
    assert reports.items["r1"]["status"] == "processing"
    assert "outcome_sha256" not in reports.items["r1"]
    retry = commit(reports, articles, now="2026-11-02T09:30:00Z")
    assert retry.decision == "committed"
    assert (retry.revisions_reused, retry.appearances_reused) == (1, 1)
    assert (retry.revisions_written, retry.appearances_written) == (0, 0)


def test_completion_racing_a_cancel_is_refused_by_the_condition(store):
    reports, articles = store

    def cancel(kind, _item):
        if kind == "complete":
            reports.items["r1"]["status"] = "failed"

    reports.before_write = cancel
    assert commit(reports, articles).decision == "already_terminal_refused"
    assert "outcome_sha256" not in reports.items["r1"]


def test_late_completion_of_a_cancelled_or_missing_report_writes_nothing():
    reports, articles = fx.tables()
    fx.open_report(reports, "r1", status="failed")
    assert commit(reports, articles).decision == "already_terminal_refused"
    assert commit(reports, articles, "absent").decision == "report_missing"
    assert articles.items == {}
    assert reports.items["r1"]["status"] == "failed"


def test_legacy_completed_row_is_never_overwritten():
    reports, articles = fx.tables()
    fx.open_report(reports, "r1", status="completed")
    before = copy.deepcopy(reports.items["r1"])
    assert commit(reports, articles).decision == "already_terminal_refused"
    assert reports.items["r1"] == before


def test_fallback_is_recorded_as_refusal_not_intelligence(store):
    reports, articles = store
    receipt = commit(reports, articles, res=fx.result([fx.article("alpha")], mode="fallback"))
    assert receipt.decision == "committed" and receipt.terminal_outcome == "refused_fallback"
    row = reports.items["r1"]
    assert row["status"] == "completed"  # legacy status contract is unchanged
    record = export_page(reports, stream="reports")["records"][0]
    assert record["outcome"] == "refused_fallback"
    assert record["conclusion_status"] == "not_intelligence"
    assert "generated_conclusions" not in record
    assert record["publication"] == {"status": "not_established_by_store"}


def test_missing_mode_metadata_is_not_treated_as_model_output(store):
    reports, articles = store
    res = fx.result([fx.article("alpha")])
    assert res.metadata is not None
    res.metadata.analysis_mode = None
    assert commit(reports, articles, res=res).terminal_outcome == "refused_fallback"


def test_failed_run_is_kept_separately(store):
    reports, articles = store
    receipt = commit(reports, articles, res=fx.result([], status="failed"))
    assert receipt.terminal_outcome == "failed"
    record = export_page(reports, stream="reports")["records"][0]
    assert record["outcome"] == "failed" and record["outcome_reason"] == "synthetic feed timeout"
    assert reports.items["r1"]["status"] == "failed"


def test_corrupted_revision_is_visible_and_blocks_a_new_binding():
    reports, articles = fx.tables()
    fx.open_report(reports, "r1")
    fx.open_report(reports, "r2")
    commit(reports, articles, "r1")
    rev = kinds(articles, "article_revision")[0]
    articles.items[rev["article_id"]]["content"] = "tampered"
    exported = export_page(articles, stream="articles")["records"]
    revision = next(r for r in exported if r["record_type"] == "source_article_revision")
    assert revision["integrity"]["status"] == "corrupt"
    receipt = commit(reports, articles, "r2")
    assert receipt.decision == "evidence_failure_recorded" and not receipt.accepted
    row = reports.items["r2"]
    assert row["status"] == "failed" and row["terminal_outcome"] == "failed"
    assert row["terminal_reason"].startswith("evidence_conflict")
    assert row["article_revision_ids"] == [] and row["content"] == ""
    record = next(
        r
        for r in export_page(reports, stream="reports", limit=200)["records"]
        if r["report_id"] == "r2"
    )
    assert record["outcome"] == "failed" and record["integrity"]["status"] == "intact"
    # The recorded failure is itself final: a later retry cannot overwrite it.
    assert commit(reports, articles, "r2").decision == "stale_completion_refused"


def test_corrupted_outcome_is_not_reacknowledged(store):
    reports, articles = store
    commit(reports, articles)
    reports.items["r1"]["content"] = "# Tampered"
    assert commit(reports, articles).decision == "integrity_failure"
    record = export_page(reports, stream="reports")["records"][0]
    assert record["integrity"]["status"] == "corrupt"
    assert record["conclusion_status"] == "not_intelligence"


@pytest.mark.parametrize("field", ["metadata", "article_revision_ids", "completion_run_id"])
def test_any_bound_field_change_breaks_outcome_integrity(store, field):
    reports, articles = store
    commit(reports, articles)
    reports.items["r1"][field] = {"forged": True}
    record = export_page(reports, stream="reports")["records"][0]
    assert record["integrity"]["status"] == "corrupt"


def test_unknown_publication_time_stays_unknown(store):
    reports, articles = store
    commit(reports, articles, res=fx.result([fx.article("alpha", published=None)]))
    rev = kinds(articles, "article_revision")[0]
    assert rev["published_at_known"] is False and "published_at" not in rev
    record = next(
        r
        for r in export_page(articles, stream="articles")["records"]
        if r["record_type"] == "source_article_revision"
    )
    assert record["timestamps"]["published_at"] is None


def test_truncated_content_is_an_excerpt_with_capture_digest(store):
    reports, articles = store
    long_body = "x" * (MAX_RETAINED_CONTENT + 10)
    commit(reports, articles, res=fx.result([fx.article("alpha", body=long_body)]))
    rev = kinds(articles, "article_revision")[0]
    assert rev["evidence_kind"] == "excerpt" and rev["content_truncated"] is True
    assert len(rev["content"]) == MAX_RETAINED_CONTENT
    assert rev["captured_content_length"] == MAX_RETAINED_CONTENT + 10


def test_float_metadata_round_trips_without_breaking_the_digest(store):
    reports, articles = store
    res = fx.result([fx.article("alpha")])
    assert res.metadata is not None
    res.metadata.relevance_diagnostics = {"share": 0.1, "nested": [1.5, 2]}
    commit(reports, articles, res=res)
    assert export_page(reports, stream="reports")["records"][0]["integrity"]["status"] == "intact"
    assert commit(reports, articles, res=res).decision == "reused"


def test_paged_export_covers_each_record_once_and_replays_identically():
    reports, articles, _ = fx.build_scenarios()
    for table, stream in ((reports, "reports"), (articles, "articles")):
        pages = list(export_all(table, stream=stream, limit=2))
        assert all(len(p["records"]) <= 2 for p in pages)
        ids = [(r["record_id"], r["record_revision"]) for p in pages for r in p["records"]]
        assert len(ids) == len(set(ids))
        unpaged = export_page(table, stream=stream, limit=200)["records"]
        assert [r["record_digest"] for p in pages for r in p["records"]] == [
            r["record_digest"] for r in unpaged
        ]
        assert pages[-1]["coverage"]["stream_complete"] is True
        replay = list(export_all(table, stream=stream, limit=2))
        assert json.dumps(replay, sort_keys=True) == json.dumps(pages, sort_keys=True)


def test_legacy_rows_export_with_unknown_provenance():
    reports, articles, _ = fx.build_scenarios()
    legacy = next(
        r
        for r in export_page(reports, stream="reports", limit=200)["records"]
        if r["report_id"].startswith("report_2025")
    )
    assert legacy["provenance_class"] == "legacy_unknown"
    assert legacy["conclusion_status"] == "legacy_unverified"
    assert legacy["source_revision_basis"] == "computed_at_export"
    snapshot = next(
        r
        for r in export_page(articles, stream="articles", limit=200)["records"]
        if r["record_type"] == "legacy_article_snapshot"
    )
    assert snapshot["timestamps"]["published_reliability"] == "legacy_unverified"
    assert snapshot["evidence"]["kind"] == "legacy_text_unverified"


def test_incremental_export_filters_by_change_time():
    reports, _, _ = fx.build_scenarios()
    page = export_page(reports, stream="reports", limit=200, updated_since="2026-11-09T00:00:00Z")
    ids = {r["report_id"] for r in page["records"]}
    assert "report_s1" not in ids and "report_s2" in ids
    assert page["coverage"]["filtered_out"] >= 1


def test_cursor_is_bound_to_its_schema_and_stream():
    reports, articles, _ = fx.build_scenarios()
    page = export_page(reports, stream="reports", limit=1)
    with pytest.raises(CursorError):
        export_page(articles, stream="articles", cursor=page["next_cursor"])
    with pytest.raises(CursorError):
        export_page(reports, stream="reports", cursor="not-a-cursor")
    with pytest.raises(ValueError):
        export_page(reports, stream="reports", limit=history_export.MAX_PAGE + 1)


def test_fixture_is_byte_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    check = fx.write_fixture(a)
    fx.write_fixture(b)
    assert check["replay_identical"] and check["duplicate_record_revisions"] == 0
    for name in ("export.jsonl", "export-pages.json", "scenario-receipts.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_fixture_scenarios_cover_the_acceptance_cases():
    _, _, receipts = fx.build_scenarios()
    decisions = {r["scenario"]: r["decision"] for r in receipts}
    assert decisions == {
        "first completion": "committed",
        "duplicate request": "reused",
        "stale same-run divergent completion": "stale_completion_refused",
        "foreign completion": "foreign_completion_refused",
        "changed article revision": "committed",
        "fallback refusal": "committed",
        "failed run": "committed",
        "interrupted completion": "crashed_before_commit",
        "recovery after interruption": "committed",
        "late completion after cancel": "already_terminal_refused",
        "conflicting identity": "evidence_failure_recorded",
    }


# ----- DynamoDB request shapes (botocore Stubber; no network) -----


@pytest.fixture
def stubbed():
    import boto3

    client = boto3.client(
        "dynamodb",
        region_name="us-east-1",
        aws_access_key_id="synthetic",
        aws_secret_access_key="synthetic",
    )
    with Stubber(client) as stub:
        yield client, stub
        stub.assert_no_pending_responses()


def test_put_if_absent_request_shape(stubbed):
    client, stub = stubbed
    stub.add_response(
        "put_item",
        {},
        {
            "TableName": "grcinsight-articles",
            "Item": {"article_id": {"S": "arev#a#b"}, "score": {"N": "0.1"}, "ok": {"BOOL": True}},
            "ConditionExpression": "attribute_not_exists(#k)",
            "ExpressionAttributeNames": {"#k": "article_id"},
            "ReturnValuesOnConditionCheckFailure": "ALL_OLD",
        },
    )
    DynamoDBTable(client, "grcinsight-articles", "article_id").put_if_absent(
        {"article_id": "arev#a#b", "score": 0.1, "ok": True}
    )


def test_conditional_failure_returns_the_stored_item(stubbed):
    client, stub = stubbed
    stub.add_client_error(
        "put_item",
        service_error_code="ConditionalCheckFailedException",
        http_status_code=400,
        modeled_fields={"Item": {"article_id": {"S": "k"}, "n": {"N": "2"}}},
    )
    with pytest.raises(ConditionFailed) as info:
        DynamoDBTable(client, "t", "article_id").put_if_absent({"article_id": "k"})
    assert info.value.existing == {"article_id": "k", "n": 2}


def test_other_client_errors_propagate(stubbed):
    client, stub = stubbed
    stub.add_client_error("put_item", service_error_code="ProvisionedThroughputExceededException")
    with pytest.raises(ClientError):
        DynamoDBTable(client, "t", "article_id").put_if_absent({"article_id": "k"})


def test_complete_if_open_request_shape(stubbed):
    client, stub = stubbed
    stub.add_response(
        "update_item",
        {},
        {
            "TableName": "grcinsight-reports",
            "Key": {"report_id": {"S": "r1"}},
            "UpdateExpression": "SET #f0 = :v0, #f1 = :v1",
            "ConditionExpression": (
                "attribute_exists(#k) AND #status IN (:open0, :open1) "
                "AND attribute_not_exists(#g)"
            ),
            "ExpressionAttributeNames": {
                "#k": "report_id",
                "#status": "status",
                "#g": "outcome_sha256",
                "#f0": "outcome_sha256",
                "#f1": "status",
            },
            "ExpressionAttributeValues": {
                ":v0": {"S": "d"},
                ":v1": {"S": "completed"},
                ":open0": {"S": "pending"},
                ":open1": {"S": "processing"},
            },
            "ReturnValuesOnConditionCheckFailure": "ALL_OLD",
        },
    )
    DynamoDBTable(client, "grcinsight-reports", "report_id").complete_if_open(
        "r1",
        {"status": "completed", "outcome_sha256": "d"},
        open_statuses=("pending", "processing"),
        guard_attribute="outcome_sha256",
    )


def test_scan_page_passes_the_cursor_key_and_decodes(stubbed):
    client, stub = stubbed
    stub.add_response(
        "scan",
        {
            "Items": [{"report_id": {"S": "r2"}, "n": {"N": "1.5"}}],
            "LastEvaluatedKey": {"report_id": {"S": "r2"}},
        },
        {"TableName": "t", "Limit": 1, "ExclusiveStartKey": {"report_id": {"S": "r1"}}},
    )
    items, last = DynamoDBTable(client, "t", "report_id").scan_page(1, {"report_id": "r1"})
    assert items == [{"report_id": "r2", "n": 1.5}] and last == {"report_id": "r2"}


def test_get_is_strongly_consistent(stubbed):
    client, stub = stubbed
    stub.add_response(
        "get_item",
        {"Item": {"report_id": {"S": "r1"}, "n": {"N": "3"}}},
        {"TableName": "t", "Key": {"report_id": {"S": "r1"}}, "ConsistentRead": True},
    )
    assert DynamoDBTable(client, "t", "report_id").get("r1") == {"report_id": "r1", "n": 3}


def test_to_dynamo_keeps_floats_exact():
    from history.table import to_dynamo

    assert to_dynamo({"a": [0.1, 1, True, None]}) == {"a": [Decimal("0.1"), 1, True, None]}


# ----- Lambda integration -----


def _run_lambda(
    monkeypatch, reports, articles, res, *, report_id="r1", request_id="req-1", job_id=None
):
    import core.workflow
    import lambda_main

    async def fake_run(*_args, **_kwargs):
        return res

    monkeypatch.setattr(core.workflow, "run_grc_analysis_endpoint", fake_run)
    monkeypatch.setattr(lambda_main, "_history_tables", lambda: (reports, articles))
    context = SimpleNamespace(
        aws_request_id=request_id, get_remaining_time_in_millis=lambda: 900000
    )
    event = {"feed_url": fx.FEED, "report_id": report_id, "config": {}}
    if job_id:
        event["job_id"] = job_id
    return lambda_main.handler(event, context)


def test_lambda_writeback_commits_once_and_acknowledges_replays(monkeypatch, store):
    reports, articles = store
    res = fx.result([fx.article("alpha")])
    first = _run_lambda(monkeypatch, reports, articles, res)
    assert first["statusCode"] == 200 and first["body"]["decision"] == "committed"
    assert first["body"]["status"] == "completed"
    # A redelivery with a new request id is the same admitted job, not a foreign one.
    again = _run_lambda(monkeypatch, reports, articles, res, request_id="req-2")
    assert again["statusCode"] == 200 and again["body"]["decision"] == "reused"
    assert reports.items["r1"]["completion_run_id"] == "job-r1"
    assert reports.items["r1"]["completion_invocation_id"] == "req-1"
    foreign = _run_lambda(monkeypatch, reports, articles, res, job_id="job-other")
    assert foreign["statusCode"] == 409
    assert foreign["body"]["decision"] == "foreign_completion_refused"


def test_lambda_writeback_reports_store_failures(monkeypatch, store):
    reports, articles = store

    def boom(kind, _item):
        raise RuntimeError("synthetic store outage")

    articles.before_write = boom
    out = _run_lambda(monkeypatch, reports, articles, fx.result([fx.article("alpha")]))
    assert out["statusCode"] == 500 and out["body"]["status"] == "failed"
    assert out["body"]["decision"] == "evidence_failure_recorded"
    # Visible and final, so publication keeps the last good report instead of waiting.
    row = reports.items["r1"]
    assert row["status"] == "failed" and row["terminal_reason"] == "evidence_persistence_failed"


def test_lambda_writeback_survives_an_unreachable_report_store(monkeypatch, store):
    reports, articles = store

    def boom(kind, _item):
        raise RuntimeError("synthetic outage")

    articles.before_write = boom
    reports.before_write = boom
    out = _run_lambda(monkeypatch, reports, articles, fx.result([fx.article("alpha")]))
    assert out["statusCode"] == 500 and out["body"]["status"] == "failed"
    assert reports.items["r1"]["status"] == "processing"  # exported as incomplete


def test_event_without_job_id_uses_the_admitted_job_on_the_row(store):
    reports, articles = store
    first = commit(reports, articles, invocation="lambda-a")
    again = commit(reports, articles, invocation="lambda-b")
    assert first.run_id == again.run_id == "job-r1" and again.decision == "reused"


def test_rows_without_a_job_id_bind_to_the_report(store):
    reports, articles = fx.tables()
    fx.open_report(reports, "r1", job_id=None)
    assert commit(reports, articles).run_id == "r1"


def test_http_report_route_commits_through_the_same_contract(monkeypatch, store):
    from fastapi.testclient import TestClient

    import core.workflow
    import history.service
    from api.routes import workflow as workflow_route
    from main import app

    reports, articles = store
    res = fx.result([fx.article("alpha")])

    async def fake_run(*_args, **_kwargs):
        return res

    monkeypatch.setattr(workflow_route, "run_grc_analysis_endpoint", fake_run)
    monkeypatch.setattr(core.workflow, "run_grc_analysis_endpoint", fake_run)
    monkeypatch.setattr(history.service, "history_tables", lambda: (reports, articles))
    client = TestClient(app)
    body = {"feed_url": fx.FEED, "config": {}, "job_id": "job-r1"}
    first = client.post("/api/v1/workflow/reports/r1/run", json=body)
    assert first.status_code == 200 and first.json()["decision"] == "committed"
    again = client.post("/api/v1/workflow/reports/r1/run", json=body)
    assert again.status_code == 200 and again.json()["decision"] == "reused"
    foreign = client.post("/api/v1/workflow/reports/r1/run", json={**body, "job_id": "x"})
    assert foreign.status_code == 409
    assert "content" not in first.json()


def test_go_reader_testdata_matches_the_writer():
    """The Go reader's cross-language fixture is exactly what this writer stores."""
    from pathlib import Path

    reports, articles, _ = fx.build_scenarios()
    testdata = (
        Path(__file__).resolve().parents[2]
        / "internal/database/dynamodb/testdata/history-items.json"
    )
    assert json.loads(testdata.read_text()) == json.loads(
        json.dumps(fx.dynamodb_items(reports, articles))
    )


def test_incremental_export_compares_instants_not_strings():
    reports, _ = fx.tables()
    reports.seed(
        {"report_id": "frac", "status": "failed", "updated_at": "2026-11-09T12:00:00.500000Z"}
    )
    reports.seed({"report_id": "old", "status": "failed", "updated_at": "2026-11-09T11:59:59Z"})
    reports.seed(
        {"report_id": "offset", "status": "failed", "updated_at": "2026-11-09T07:30:00-05:00"}
    )
    reports.seed({"report_id": "unreadable", "status": "failed", "updated_at": "yesterday"})
    page = export_page(reports, stream="reports", limit=10, updated_since="2026-11-09T12:00:00Z")
    ids = {r["report_id"] for r in page["records"]}
    assert ids == {"frac", "offset", "unreadable"}
    assert page["coverage"]["filtered_out"] == 1
    with pytest.raises(ValueError):
        export_page(reports, stream="reports", updated_since="not a time")


def test_deployed_policy_grants_what_history_uses_on_both_tables():
    """A role created from the repository policy can write and read history."""
    from pathlib import Path

    policy = json.loads(
        (
            Path(__file__).resolve().parents[2] / "deployments/lambda-permissions-policy.json"
        ).read_text()
    )
    table = "arn:aws:dynamodb:us-east-1:076542168556:table/"
    granted: dict[str, set[str]] = {}
    for statement in policy["Statement"]:
        if statement.get("Effect") != "Allow":
            continue
        for resource in statement["Resource"]:
            granted.setdefault(resource, set()).update(statement["Action"])
    needed = {"dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Scan"}
    assert needed <= granted[table + "grcinsight-reports"]
    assert needed <= granted[table + "grcinsight-articles"]
    assert "dynamodb:Query" in granted[table + "grcinsight-articles/index/*"]


def test_incremental_export_uses_update_time_for_mutable_legacy_articles():
    _, articles = fx.tables()
    articles.seed(
        {
            "article_id": "a_20261101_00000001",
            "url": "https://news.example.test/legacy-updated",
            "created_at": "2026-11-01T00:00:00Z",
            "updated_at": "2026-11-09T00:00:00Z",
        }
    )
    page = export_page(articles, stream="articles", updated_since="2026-11-08T00:00:00Z")
    assert [r["article_id"] for r in page["records"]] == ["a_20261101_00000001"]


def test_export_keeps_failure_reasons_the_go_service_records():
    reports, _ = fx.tables()
    reports.seed(
        {
            "report_id": "go_failed",
            "job_id": "job_x",
            "status": "failed",
            "terminal_outcome": "failed",
            "terminal_reason": "invocation_failed",
            "updated_at": "2026-11-09T00:00:00Z",
        }
    )
    record = export_page(reports, stream="reports")["records"][0]
    assert record["outcome"] == "failed" and record["outcome_reason"] == "invocation_failed"
    assert record["integrity"]["status"] == "unverifiable_legacy"
    assert record["conclusion_status"] == "not_intelligence"


def test_writer_uses_the_same_dynamodb_settings_as_the_go_service(monkeypatch):
    import boto3

    import history.service

    seen = {}

    def fake_client(service, **kwargs):
        seen.update(service=service, **kwargs)
        return object()

    monkeypatch.setattr(boto3, "client", fake_client)
    monkeypatch.setenv("DATABASE_ENDPOINT", "http://localhost:8000")
    monkeypatch.setenv("DATABASE_REGION", "us-west-2")
    reports, articles = history.service.history_tables()
    assert seen == {
        "service": "dynamodb",
        "endpoint_url": "http://localhost:8000",
        "region_name": "us-west-2",
    }
    assert (reports.name, articles.name) == ("grcinsight-reports", "grcinsight-articles")
    monkeypatch.delenv("DATABASE_ENDPOINT")
    monkeypatch.delenv("DATABASE_REGION")
    seen.clear()
    history.service.history_tables()
    assert seen == {"service": "dynamodb"}


def test_truncated_publisher_page_is_an_excerpt_with_its_own_scope(store):
    reports, articles = store
    page = fx.article("alpha", body="<html>" + "x" * 4994)
    page.content_origin = "publisher_page"
    page.content_truncated = True
    commit(reports, articles, res=fx.result([page]))
    rev = kinds(articles, "article_revision")[0]
    assert rev["evidence_kind"] == "excerpt" and rev["content_truncated"] is True
    assert rev["full_text_scope"] == "publisher_page_html"
    assert rev["content_origin"] == "publisher_page"


def test_publisher_page_enrichment_records_origin_and_truncation(monkeypatch):
    import asyncio

    import httpx

    from models.api import ArticleInput
    from services import rss_service as rss_module

    real_client = httpx.AsyncClient

    def handler(request):
        return httpx.Response(200, text="<html>" + "y" * 6000 + "</html>")

    monkeypatch.setattr(
        rss_module.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    service = rss_module.RSSService()
    empty = ArticleInput(
        title="t", url="https://news.example.test/p", content="", published=fx.GENERATED_AT
    )
    feed = ArticleInput(
        title="t", url="https://news.example.test/f", content="feed body", published=fx.GENERATED_AT
    )
    enriched = asyncio.run(service.enrich_articles([empty, feed]))
    assert enriched[0].content_origin == "publisher_page"
    assert enriched[0].content_truncated is True and len(enriched[0].content) == 5000
    assert enriched[1].content_origin == "feed_item" and enriched[1].content_truncated is False


def test_any_exported_change_is_a_new_record_revision():
    _, articles = fx.tables()
    row = {
        "article_id": "a_20261101_00000002",
        "url": "https://news.example.test/legacy",
        "content": "same",
        "created_at": "2026-11-01T00:00:00Z",
        "updated_at": "2026-11-01T00:00:00Z",
    }
    articles.seed(row)
    first = export_page(articles, stream="articles")["records"][0]
    articles.seed({**row, "updated_at": "2026-11-09T00:00:00Z"})
    second = export_page(articles, stream="articles")["records"][0]
    assert first["record_id"] == second["record_id"]
    assert first["record_revision"] != second["record_revision"]
    unchanged = export_page(articles, stream="articles")["records"][0]
    assert unchanged == second


def test_capture_completeness_is_part_of_revision_identity():
    reports, articles = fx.tables()
    fx.open_report(reports, "r1")
    fx.open_report(reports, "r2")
    exact = "z" * MAX_RETAINED_CONTENT
    commit(reports, articles, "r1", res=fx.result([fx.article("alpha", body=exact)]))
    longer = fx.article("alpha", body=exact + "appended later")
    receipt = commit(reports, articles, "r2", res=fx.result([longer]))
    assert receipt.decision == "committed" and receipt.revisions_written == 1
    revisions = sorted(
        kinds(articles, "article_revision"), key=lambda r: r["captured_content_length"]
    )
    assert [r["content_truncated"] for r in revisions] == [False, True]
    assert revisions[0]["content_sha256"] == revisions[1]["content_sha256"]
    assert revisions[0]["article_id"] != revisions[1]["article_id"]
    assert reports.items["r2"]["article_revision_ids"] == [revisions[1]["article_id"]]
    assert revisions[1]["evidence_kind"] == "excerpt"


def test_tampered_capture_provenance_is_detected():
    reports, articles = fx.tables()
    fx.open_report(reports, "r1")
    commit(reports, articles, "r1")
    rev = kinds(articles, "article_revision")[0]
    articles.items[rev["article_id"]]["content_truncated"] = True
    record = next(
        r
        for r in export_page(articles, stream="articles")["records"]
        if r["record_type"] == "source_article_revision"
    )
    assert record["integrity"]["status"] == "corrupt"
