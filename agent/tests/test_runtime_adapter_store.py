import sqlite3

import pytest

from runtime_adapter import contract
from runtime_adapter.store import ReportStore, fnv1a_32

RUN_A = "11111111-1111-4111-8111-111111111111"
RUN_B = "22222222-2222-4222-8222-222222222222"


def frozen(**config):
    fields = {"model": "openrouter/example/model", "max_tokens": 16000, "focus_areas": []}
    fields.update(config)
    return contract.freeze(
        contract.build_submission(
            feed_url="https://feeds.synthetic.test/grc/feed.xml",
            config=fields,
            fixture_id="model-plan",
            fixture_sha256="a" * 64,
            max_attempts=3,
        )
    )


def report_payload():
    return {
        "title": "GRC Intelligence Report - 2026-11-01",
        "content": "## Executive Summary\nSynthetic.",
        "status": "completed",
        "source_url": "https://feeds.synthetic.test/grc/feed.xml",
        "generated_at": "2026-11-01T12:00:00Z",
        "metadata": {"analysis_mode": "model", "article_count": 2},
    }


def article_payloads():
    return [
        {
            "title": f"Synthetic article {index}",
            "url": f"https://news.synthetic.test/a/{index}",
            "content": "c",
            "summary": "s",
            "source": "Synthetic GRC Digest",
            "digest_url": f"https://digest.synthetic.test/archive/2026-11-01/#reporting-{index}",
            "published": "2026-11-01T10:00:00Z",
            "has_grc_content": True,
            "regulations": [],
            "frameworks": [],
            "industries": [],
            "regulatory_bodies": [],
        }
        for index in (1, 2)
    ]


@pytest.fixture
def store(tmp_path):
    opened = ReportStore(tmp_path / "product.sqlite3")
    yield opened
    opened.close()


def admitted(store, report_id="weekly-2026-11-01", run_id=RUN_A):
    assert store.freeze(report_id, frozen()).outcome == "created"
    assert store.begin_admission(report_id) == "admit"
    assert store.bind_run(report_id, run_id) == "bound"
    return report_id


def commit(store, report_id, lease_version, owner, run_id=RUN_A):
    return store.commit_completed(
        report_id,
        run_id=run_id,
        attempt=lease_version,
        lease_version=lease_version,
        lease_owner=owner,
        report=report_payload(),
        articles=article_payloads(),
    )


def test_freeze_is_idempotent_and_reports_changed_identity_as_conflict(store):
    first = frozen()
    assert store.freeze("weekly-2026-11-01", first).outcome == "created"
    assert store.freeze("weekly-2026-11-01", first).outcome == "existing"
    changed = store.freeze("weekly-2026-11-01", frozen(max_tokens=8000))
    assert changed.outcome == "conflict"
    record = store.get("weekly-2026-11-01")
    assert record.input_digest == first.input_digest
    assert record.status == "pending" and record.run_id is None
    conflicts = store.conflicts("weekly-2026-11-01")
    assert [(item["source"], item["requested_input_digest"]) for item in conflicts] == [
        ("product", frozen(max_tokens=8000).input_digest)
    ]


def test_late_bind_never_reopens_a_cancelled_report(store):
    store.freeze("weekly-2026-11-01", frozen())
    assert store.begin_admission("weekly-2026-11-01") == "admit"
    assert store.cancel("weekly-2026-11-01") == "cancelled_during_admission"
    assert store.bind_run("weekly-2026-11-01", RUN_A) == "bound"
    record = store.get("weekly-2026-11-01")
    assert (record.status, record.terminal_outcome, record.run_id) == (
        "cancelled",
        "cancelled",
        RUN_A,
    )
    assert store.begin_admission("weekly-2026-11-01") == "cancelled"


def test_cancel_before_admission_prevents_admission(store):
    store.freeze("weekly-2026-11-01", frozen())
    assert store.cancel("weekly-2026-11-01") == "cancelled_before_admission"
    assert store.begin_admission("weekly-2026-11-01") == "cancelled"
    assert store.cancel("weekly-2026-11-01") == "already_cancelled"


def test_bind_is_compare_and_set_on_one_run(store):
    report_id = admitted(store)
    assert store.bind_run(report_id, RUN_A) == "already_bound"
    assert store.bind_run(report_id, RUN_B) == "conflict"
    assert store.get(report_id).run_id == RUN_A


def test_newer_ownership_fences_an_older_attempt_before_it_commits(store):
    report_id = admitted(store)
    assert (
        store.register_owner(report_id, run_id=RUN_A, attempt=1, lease_version=1, lease_owner="a")
        == "registered"
    )
    assert (
        store.register_owner(report_id, run_id=RUN_A, attempt=2, lease_version=2, lease_owner="b")
        == "registered"
    )
    assert commit(store, report_id, 1, "a").outcome == "superseded"
    assert store.articles(report_id) == []
    result = commit(store, report_id, 2, "b")
    assert result.outcome == "committed"
    record = store.get(report_id)
    assert (record.committed_lease_version, record.committed_lease_owner) == (2, "b")
    assert record.result_digest == result.result_digest
    assert (
        store.register_owner(report_id, run_id=RUN_A, attempt=3, lease_version=3, lease_owner="c")
        == "terminal"
    )


def test_older_attempt_resuming_after_newer_commit_cannot_overwrite(store):
    report_id = admitted(store)
    store.register_owner(report_id, run_id=RUN_A, attempt=1, lease_version=1, lease_owner="a")
    store.register_owner(report_id, run_id=RUN_A, attempt=2, lease_version=2, lease_owner="b")
    committed = commit(store, report_id, 2, "b")
    assert commit(store, report_id, 1, "a").outcome == "terminal"
    assert store.get(report_id).result_digest == committed.result_digest
    assert len(store.articles(report_id)) == 2


def test_registration_cannot_move_ownership_backwards(store):
    report_id = admitted(store)
    store.register_owner(report_id, run_id=RUN_A, attempt=2, lease_version=2, lease_owner="b")
    assert (
        store.register_owner(report_id, run_id=RUN_A, attempt=1, lease_version=1, lease_owner="a")
        == "superseded"
    )
    assert (
        store.register_owner(report_id, run_id=RUN_B, attempt=3, lease_version=3, lease_owner="c")
        == "unbound"
    )


def test_commit_and_cancel_serialize_with_exactly_one_winner(store):
    first = admitted(store, "report-commit-first")
    store.register_owner(first, run_id=RUN_A, attempt=1, lease_version=1, lease_owner="a")
    assert commit(store, first, 1, "a").outcome == "committed"
    assert store.cancel(first) == "rejected_already_committed"
    assert store.get(first).terminal_outcome == "completed"

    second = admitted(store, "report-cancel-first", RUN_B)
    store.register_owner(second, run_id=RUN_B, attempt=1, lease_version=1, lease_owner="a")
    assert store.cancel(second) == "cancelled_during_execution"
    assert commit(store, second, 1, "a", run_id=RUN_B).outcome == "cancelled"
    assert store.articles(second) == []
    assert store.get(second).result_digest is None


def test_queued_cancel_is_distinguished_from_execution_cancel(store):
    report_id = admitted(store)
    assert store.cancel(report_id) == "cancelled_pending_runtime"


def test_failure_from_runtime_never_overwrites_a_terminal_outcome(store):
    report_id = admitted(store)
    store.register_owner(report_id, run_id=RUN_A, attempt=1, lease_version=1, lease_owner="a")
    commit(store, report_id, 1, "a")
    assert (
        store.commit_failed(report_id, run_id=RUN_A, error_code="worker_error", reason="late")
        == "terminal"
    )
    assert store.get(report_id).terminal_outcome == "completed"

    other = admitted(store, "report-failure", RUN_B)
    assert (
        store.commit_failed(other, run_id=RUN_A, error_code="invalid_input", reason="x")
        == "unbound"
    )
    assert (
        store.commit_failed(other, run_id=RUN_B, error_code="invalid_input", reason="x")
        == "committed"
    )
    record = store.get(other)
    assert (record.status, record.terminal_outcome, record.runtime_error_code) == (
        "failed",
        "failed",
        "invalid_input",
    )
    assert store.cancel(other) == "rejected_already_terminal"


def test_result_digest_is_recomputed_from_persisted_rows(store, tmp_path):
    report_id = admitted(store)
    store.register_owner(report_id, run_id=RUN_A, attempt=1, lease_version=1, lease_owner="a")
    result = commit(store, report_id, 1, "a")
    assert store.recompute_result_digest(report_id) == result.result_digest

    raw = sqlite3.connect(tmp_path / "product.sqlite3")
    raw.execute("DROP TRIGGER reports_terminal_immutable")
    raw.execute("UPDATE reports SET content = 'tampered' WHERE report_id = ?", (report_id,))
    raw.commit()
    raw.close()
    assert store.recompute_result_digest(report_id) != result.result_digest


def test_committed_rows_are_immutable_in_the_database(store, tmp_path):
    report_id = admitted(store)
    store.register_owner(report_id, run_id=RUN_A, attempt=1, lease_version=1, lease_owner="a")
    commit(store, report_id, 1, "a")
    raw = sqlite3.connect(tmp_path / "product.sqlite3")
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute("UPDATE reports SET content = 'x' WHERE report_id = ?", (report_id,))
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute("UPDATE articles SET title = 'x' WHERE report_id = ?", (report_id,))
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute("DELETE FROM articles WHERE report_id = ?", (report_id,))
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute(
            "INSERT INTO articles (article_id, numeric_id, report_id, position, title, url, content,"
            " summary, source, digest_url, published, created_at, updated_at, has_grc_content,"
            " regulations, frameworks, industries, regulatory_bodies) VALUES"
            " ('a_x', 1, ?, 9, 't', 'https://news.synthetic.test/x', '', '', '', '', '', '', '', 0,"
            " '[]', '[]', '[]', '[]')",
            (report_id,),
        )
    raw.close()


def test_article_identity_is_report_scoped_and_keeps_existing_numeric_id(store):
    report_id = admitted(store)
    store.register_owner(report_id, run_id=RUN_A, attempt=1, lease_version=1, lease_owner="a")
    commit(store, report_id, 1, "a")
    articles = store.articles(report_id)
    assert [article["position"] for article in articles] == [0, 1]
    first = articles[0]
    assert first["numeric_id"] == fnv1a_32(first["url"])
    assert first["article_id"].startswith("a_") and report_id not in first["article_id"]
    assert len({article["article_id"] for article in articles}) == 2
    # Published FNV-1a 32-bit vectors, matching the Lambda writeback's inline hash.
    assert (fnv1a_32(""), fnv1a_32("a"), fnv1a_32("foobar")) == (0x811C9DC5, 0xE40C292C, 0xBF9CF968)
