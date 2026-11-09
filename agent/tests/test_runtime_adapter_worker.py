import json
from pathlib import Path
import sqlite3
import threading
import time
from types import SimpleNamespace

import httpx
import pytest

from runtime_adapter import contract
from runtime_adapter.contract import SubmissionError
from runtime_adapter.producer import ProducerHooks, cancel_report, submit_report
from runtime_adapter.reader import read_report, reconcile_report
from runtime_adapter.store import ReportStore
from runtime_adapter.synthetic import EgressRefused, FixtureError, install_boundaries, load_fixture
from runtime_adapter.worker import (
    GRCWorker,
    SimulatedCrash,
    WorkerConfigurationError,
    WorkerHooks,
    WorkerSettings,
)
from runtime_adapter_support import (
    DELETE,
    EVIDENCE_TEXT,
    FEED_URL,
    FakeRuntime,
    model_plan_fixture,
    variant,
    write_fixture,
)

CONFIG = {
    "model": "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    "max_tokens": 16000,
    "focus_areas": [],
}
FAST = WorkerSettings(lease_seconds=30, heartbeat_seconds=3600, attempt_timeout_seconds=20)
SITE_DIR = Path(__file__).resolve().parents[2] / "site"


@pytest.fixture
def env(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "model-plan", model_plan_fixture())
    runtime = FakeRuntime()
    store = ReportStore(tmp_path / "product.sqlite3")
    yield SimpleNamespace(
        tmp=tmp_path,
        fixtures=fixtures,
        runtime=runtime,
        store=store,
        store_path=tmp_path / "product.sqlite3",
    )
    store.close()


def submit(env, fixture_id="model-plan", **kwargs):
    return submit_report(
        env.store,
        env.runtime,
        feed_url=FEED_URL,
        config=CONFIG,
        fixture_dir=env.fixtures,
        fixture_id=fixture_id,
        **kwargs,
    )


def worker(env, *, store=None, hooks=None, settings=FAST, owner=None):
    return GRCWorker(
        store or env.store,
        env.runtime,
        fixture_dir=env.fixtures,
        settings=settings,
        hooks=hooks or WorkerHooks(),
        lease_owner=owner,
    )


def counts(env, report_id):
    return dict(env.store.boundary_counts(report_id))


def steps(receipt, name):
    return [step["result"] for step in receipt["steps"] if step["step"] == name]


def test_model_mode_report_completes_with_exact_output_binding_and_is_publishable(env):
    site_before = sorted((path.name, path.stat().st_mtime_ns) for path in SITE_DIR.iterdir())
    submitted = submit(env)
    assert submitted["outcome"] == "admitted" and submitted["runtime_status"] == 201
    report_id, run_id = submitted["report_id"], submitted["run_id"]

    receipt = worker(env, owner="worker-a").execute_one()
    assert receipt["outcome"] == "completed"

    run = env.runtime.get_run(run_id)
    assert (run["state"], run["attempt"], run["lease_version"]) == ("succeeded", 1, 1)
    assert run["input_ref"] == contract.input_ref(report_id, submitted["input_digest"])
    record = env.store.get(report_id)
    assert (record.status, record.terminal_outcome) == ("completed", "completed")
    assert run["output_ref"] == env.store.output_ref(report_id)
    assert run["output_ref"]["result_digest"] == record.result_digest
    assert env.store.recompute_result_digest(report_id) == record.result_digest
    assert run["output_ref"]["run_id"] == run_id
    assert run["output_ref"]["input_digest"] == submitted["input_digest"]
    assert env.runtime.event_types(run_id) == ["submitted", "lease_acquired", "succeeded"]

    metadata = record.metadata
    assert metadata["analysis_mode"] == "model"
    assert metadata["fallback_reason"] is None
    assert metadata["source_url"] == FEED_URL
    assert metadata["source_home_url"] == "https://digest.synthetic.test/"
    assert metadata["source_issue_date"] == "2026-11-01"
    assert metadata["source_issue_url"] == "https://digest.synthetic.test/archive/2026-11-01/"
    assert metadata["requested_model"] == CONFIG["model"]
    assert metadata["resolved_model"] == "synthetic/grc-plan-model-v1"
    assert metadata["report_plan"] == model_plan_fixture()["model"]["plan"]
    assert metadata["source_articles"][0]["article_evidence"][-1]["text"] == EVIDENCE_TEXT
    articles = env.store.articles(report_id)
    assert [article["url"] for article in articles] == [
        "https://news.synthetic.test/a/gateway-advisory",
        "https://news.synthetic.test/a/supplier-bulletin",
    ]
    assert all(
        article["digest_url"].startswith(metadata["source_issue_url"]) for article in articles
    )
    assert metadata["article_count"] == len(articles) == int(run["output_ref"]["article_count"])

    view = read_report(env.store, env.runtime, report_id)
    assert view["reconciliation"]["state"] == "consistent"
    assert view["binding"]["matches"] is True
    assert view["publication"]["eligible"] is True
    assert view["publication"]["composed_sha256"]
    assert view["runtime"]["events_filtered"] == ["submitted", "lease_acquired", "succeeded"]
    assert counts(env, report_id) == {
        "feed": 1,
        "enrichment": 1,
        "model_init": 1,
        "model_analysis": 1,
        "model_report": 1,
    }
    assert (
        sorted((path.name, path.stat().st_mtime_ns) for path in SITE_DIR.iterdir()) == site_before
    )


def test_fallback_report_completes_but_the_real_oracle_refuses_publication(env):
    write_fixture(env.fixtures, "fallback", variant(model__mode="unavailable"))
    submitted = submit(env, "fallback")
    assert worker(env).execute_one()["outcome"] == "completed"
    record = env.store.get(submitted["report_id"])
    assert record.metadata["analysis_mode"] == "fallback"
    assert (
        record.metadata["fallback_reason"]
        == "OPENROUTER_API_KEY is required for model-backed analysis"
    )
    assert record.metadata["report_plan"] is None
    run = env.runtime.get_run(submitted["run_id"])
    assert run["state"] == "succeeded"
    assert run["output_ref"]["analysis_mode"] == "fallback"
    view = read_report(env.store, env.runtime, submitted["report_id"])
    assert view["reconciliation"]["state"] == "consistent"
    assert view["publication"]["eligible"] is False
    assert "stored report is not model-backed" in view["publication"]["reason"]
    evidence = env.store.publication_evidence(submitted["report_id"])
    assert [(item["eligible"], item["result_digest"]) for item in evidence] == [
        (False, record.result_digest)
    ]
    assert counts(env, submitted["report_id"])["model_init"] == 1


def test_router_alias_is_not_accepted_as_model_authorship(env):
    write_fixture(env.fixtures, "alias", variant(model__resolved_model="openrouter/auto"))
    submitted = submit(env, "alias")
    worker(env).execute_one()
    record = env.store.get(submitted["report_id"])
    assert record.metadata["analysis_mode"] == "fallback"
    assert "did not attest" in record.metadata["fallback_reason"]
    assert (
        read_report(env.store, env.runtime, submitted["report_id"])["publication"]["eligible"]
        is False
    )


def test_transient_feed_failure_retries_then_succeeds_once(env):
    write_fixture(env.fixtures, "flaky", variant(feed_behaviour__transient_failures=1))
    submitted = submit(env, "flaky", max_attempts=3)
    first = worker(env).execute_one()
    assert first["outcome"] == "retry_scheduled"
    run = env.runtime.get_run(submitted["run_id"])
    assert (run["state"], run["error_code"]) == ("retry_wait", "dependency_unavailable")
    assert env.store.get(submitted["report_id"]).status == "processing"

    assert worker(env).execute_one()["outcome"] == "completed"
    assert env.runtime.event_types(submitted["run_id"]) == [
        "submitted",
        "lease_acquired",
        "retry_scheduled",
        "lease_acquired",
        "succeeded",
    ]
    assert [call["error_code"] for call in env.runtime.calls_named("fail")] == [
        "dependency_unavailable"
    ]
    assert counts(env, submitted["report_id"])["feed"] == 2
    assert counts(env, submitted["report_id"])["model_init"] == 1
    assert len(env.store.attempts(submitted["report_id"])) == 2


@pytest.mark.parametrize(
    ("fixture", "domain_code"),
    [
        (variant(feed__last_updated=DELETE), "FEED_IDENTITY_INVALID"),
        (variant(feed__entries=[{"title": "No link", "content": "x"}]), "NO_LINKED_ARTICLES"),
    ],
)
def test_domain_failure_is_never_reported_as_success(env, fixture, domain_code):
    write_fixture(env.fixtures, "broken", fixture)
    submitted = submit(env, "broken")
    receipt = worker(env).execute_one()
    assert receipt["outcome"] == "failed"
    assert receipt["domain_code"] == domain_code
    assert env.runtime.calls_named("complete") == []
    run = env.runtime.get_run(submitted["run_id"])
    assert (run["state"], run["error_code"]) == ("failed", "invalid_input")
    assert domain_code in run["error_summary"] and "https://" not in run["error_summary"]
    record = env.store.get(submitted["report_id"])
    assert (record.status, record.runtime_error_code) == ("failed", "invalid_input")
    assert env.store.articles(submitted["report_id"]) == []


def test_retry_budget_exhaustion_fails_the_product_from_runtime_truth(env):
    write_fixture(env.fixtures, "down", variant(feed_behaviour__permanent_failure=True))
    submitted = submit(env, "down", max_attempts=2)
    assert worker(env).execute_one()["outcome"] == "retry_scheduled"
    assert worker(env).execute_one()["outcome"] == "failed"
    run = env.runtime.get_run(submitted["run_id"])
    assert (run["state"], run["error_code"], run["attempt"]) == (
        "failed",
        "dependency_unavailable",
        2,
    )
    record = env.store.get(submitted["report_id"])
    assert (record.terminal_outcome, record.runtime_error_code) == (
        "failed",
        "dependency_unavailable",
    )
    assert counts(env, submitted["report_id"]).get("model_init", 0) == 0


def test_crash_after_commit_reuses_the_committed_result_without_new_work(env):
    submitted = submit(env)

    def crash(ctx):
        raise SimulatedCrash("after product commit")

    with pytest.raises(SimulatedCrash):
        worker(env, hooks=WorkerHooks(after_commit=crash)).execute_one()
    record = env.store.get(submitted["report_id"])
    assert record.terminal_outcome == "completed"
    assert env.runtime.get_run(submitted["run_id"])["state"] == "running"
    before = counts(env, submitted["report_id"])

    env.runtime.expire_lease(submitted["run_id"])
    receipt = worker(env).execute_one()
    assert receipt["outcome"] == "reused_completed"
    run = env.runtime.get_run(submitted["run_id"])
    assert (run["state"], run["attempt"], run["lease_version"]) == ("succeeded", 2, 2)
    assert run["output_ref"]["result_digest"] == record.result_digest
    assert run["output_ref"]["committed_lease_version"] == "1"
    assert counts(env, submitted["report_id"]) == before
    assert len(env.store.articles(submitted["report_id"])) == 2
    assert env.runtime.event_types(submitted["run_id"]) == [
        "submitted",
        "lease_acquired",
        "lease_expired",
        "retry_scheduled",
        "lease_acquired",
        "succeeded",
    ]


def run_in_thread(env, hooks, owner):
    """Run a second worker with its own store connection, as a separate process would."""
    result = {}

    def target():
        store = ReportStore(env.store_path)
        try:
            result["receipt"] = worker(env, store=store, hooks=hooks, owner=owner).execute_one()
        except BaseException as error:  # surfaced by the test
            result["error"] = error
        finally:
            store.close()

    thread = threading.Thread(target=target)
    thread.start()
    return thread, result


def test_stale_worker_resuming_before_the_newer_commit_is_fenced_by_product_ownership(env):
    submitted = submit(env)
    run_id = submitted["run_id"]
    b_paused, release_b = threading.Event(), threading.Event()
    state = {}

    def b_before_commit(ctx):
        b_paused.set()
        assert release_b.wait(10)

    def a_before_commit(ctx):
        env.runtime.expire_lease(run_id)
        state["thread"], state["result"] = run_in_thread(
            env, WorkerHooks(before_commit=b_before_commit), "worker-b"
        )
        assert b_paused.wait(10)

    a = worker(
        env, hooks=WorkerHooks(before_commit=a_before_commit), owner="worker-a"
    ).execute_one()
    assert a["outcome"] == "stale_superseded"
    assert steps(a, "commit") == ["superseded"]
    assert steps(a, "heartbeat") == ["lease_fenced"]
    assert env.store.get(submitted["report_id"]).terminal_outcome is None

    release_b.set()
    state["thread"].join(10)
    assert state["result"]["receipt"]["outcome"] == "completed"
    record = env.store.get(submitted["report_id"])
    assert (record.committed_lease_version, record.committed_lease_owner) == (2, "worker-b")
    run = env.runtime.get_run(run_id)
    assert run["output_ref"] == env.store.output_ref(submitted["report_id"])
    assert run["output_ref"]["committed_lease_version"] == "2"
    # Both attempts invoked the synthetic model: execution is at least once.
    assert counts(env, submitted["report_id"])["model_init"] == 2
    assert len(env.store.articles(submitted["report_id"])) == 2


def test_stale_worker_resuming_after_the_newer_commit_cannot_overwrite_it(env):
    submitted = submit(env)
    run_id = submitted["run_id"]

    def a_before_commit(ctx):
        env.runtime.expire_lease(run_id)
        thread, result = run_in_thread(env, WorkerHooks(), "worker-b")
        thread.join(10)
        assert result["receipt"]["outcome"] == "completed"

    committed_by_b = {}
    a = worker(
        env, hooks=WorkerHooks(before_commit=a_before_commit), owner="worker-a"
    ).execute_one()
    committed_by_b["digest"] = env.store.get(submitted["report_id"]).result_digest
    assert a["outcome"] == "stale_after_terminal"
    assert steps(a, "commit") == ["terminal"]
    assert steps(a, "complete") == ["lease_fenced"]
    record = env.store.get(submitted["report_id"])
    assert record.committed_lease_owner == "worker-b"
    assert env.runtime.get_run(run_id)["output_ref"]["result_digest"] == committed_by_b["digest"]
    assert len(env.store.articles(submitted["report_id"])) == 2


def test_old_attempt_committing_in_the_registration_gap_is_reused_by_the_newer_lease(env):
    submitted = submit(env)
    run_id = submitted["run_id"]
    b_paused, release_b = threading.Event(), threading.Event()
    state = {}

    def b_before_register(ctx):
        b_paused.set()
        assert release_b.wait(10)

    def a_before_commit(ctx):
        env.runtime.expire_lease(run_id)
        state["thread"], state["result"] = run_in_thread(
            env, WorkerHooks(before_register=b_before_register), "worker-b"
        )
        assert b_paused.wait(10)

    a = worker(
        env, hooks=WorkerHooks(before_commit=a_before_commit), owner="worker-a"
    ).execute_one()
    assert a["outcome"] == "stale_after_commit"
    assert steps(a, "commit") == ["committed"]
    assert steps(a, "complete") == ["lease_fenced"]

    release_b.set()
    state["thread"].join(10)
    b = state["result"]["receipt"]
    assert b["outcome"] == "reused_completed"
    assert steps(b, "register") == ["terminal"]
    run = env.runtime.get_run(run_id)
    assert (run["state"], run["lease_version"]) == ("succeeded", 2)
    assert run["output_ref"]["committed_lease_version"] == "1"
    assert run["output_ref"] == env.store.output_ref(submitted["report_id"])
    assert counts(env, submitted["report_id"])["model_init"] == 1


def test_attempt_already_known_to_be_fenced_never_commits(env):
    submitted = submit(env)
    run_id = submitted["run_id"]

    def a_before_commit(ctx):
        env.runtime.expire_lease(run_id)
        env.runtime.claim(
            product=contract.PRODUCT,
            workflow_name=contract.WORKFLOW_NAME,
            workflow_version=contract.WORKFLOW_VERSION,
            lease_owner="raw-claimant",
            lease_seconds=30,
        )
        assert ctx.heartbeat_now() == "lease_fenced"

    a = worker(env, hooks=WorkerHooks(before_commit=a_before_commit)).execute_one()
    assert a["outcome"] == "stale_known_fenced"
    assert steps(a, "commit") == []
    assert env.store.get(submitted["report_id"]).terminal_outcome is None
    assert env.store.articles(submitted["report_id"]) == []


def test_cancel_while_queued_is_reflected_without_synthetic_work(env):
    submitted = submit(env)
    assert (
        cancel_report(env.store, submitted["report_id"])["outcome"] == "cancelled_pending_runtime"
    )
    assert env.runtime.get_run(submitted["run_id"])["state"] == "queued"
    receipt = worker(env).execute_one()
    assert receipt["outcome"] == "cancelled"
    run = env.runtime.get_run(submitted["run_id"])
    assert (run["state"], run["error_code"]) == ("failed", "side_effect_conflict")
    assert "cancelled by product" in run["error_summary"]
    assert counts(env, submitted["report_id"]) == {}
    view = read_report(env.store, env.runtime, submitted["report_id"])
    assert view["product"]["status"] == "cancelled"
    assert view["runtime"]["run"]["state"] == "failed"
    assert view["reconciliation"]["state"] == "consistent"


def test_cancel_during_execution_aborts_new_work_and_rejects_the_commit(env):
    write_fixture(env.fixtures, "slow", variant(model__delay_seconds=5))
    submitted = submit(env, "slow")
    cancelled = {}

    def on_boundary(ctx, name):
        if name == "model_analysis":
            cancelled["outcome"] = cancel_report(env.store, submitted["report_id"])["outcome"]

    started = time.monotonic()
    receipt = worker(env, hooks=WorkerHooks(on_boundary=on_boundary)).execute_one()
    assert time.monotonic() - started < 4
    assert cancelled["outcome"] == "cancelled_during_execution"
    assert receipt["outcome"] == "cancelled_during_execution"
    run = env.runtime.get_run(submitted["run_id"])
    assert (run["state"], run["error_code"]) == ("failed", "side_effect_conflict")
    boundary = counts(env, submitted["report_id"])
    assert boundary["model_analysis"] == 1 and "model_report" not in boundary
    assert env.store.articles(submitted["report_id"]) == []
    assert env.store.get(submitted["report_id"]).status == "cancelled"


def test_cancel_after_product_commit_is_rejected_and_reuse_completes_runtime(env):
    submitted = submit(env)
    outcomes = []

    def after_commit(ctx):
        outcomes.append(cancel_report(env.store, submitted["report_id"])["outcome"])
        raise SimulatedCrash("before runtime completion")

    with pytest.raises(SimulatedCrash):
        worker(env, hooks=WorkerHooks(after_commit=after_commit)).execute_one()
    assert outcomes == ["rejected_already_committed"]
    env.runtime.expire_lease(submitted["run_id"])
    assert worker(env).execute_one()["outcome"] == "reused_completed"
    assert env.runtime.get_run(submitted["run_id"])["state"] == "succeeded"
    assert env.store.get(submitted["report_id"]).status == "completed"


def test_cancel_racing_admission_never_reopens_the_report(env):
    outcomes = []

    def before_runtime_submit(report_id):
        outcomes.append(cancel_report(env.store, report_id)["outcome"])

    submitted = submit(env, hooks=ProducerHooks(before_runtime_submit=before_runtime_submit))
    assert outcomes == ["cancelled_during_admission"]
    assert submitted["outcome"] == "admitted_after_cancel"
    record = env.store.get(submitted["report_id"])
    assert (record.status, record.terminal_outcome, record.run_id) == (
        "cancelled",
        "cancelled",
        submitted["run_id"],
    )
    assert worker(env).execute_one()["outcome"] == "cancelled"
    assert env.runtime.get_run(submitted["run_id"])["error_code"] == "side_effect_conflict"
    assert counts(env, submitted["report_id"]) == {}


def test_cancel_before_admission_never_reaches_runtime(env):
    prepared = submit(env, prepare_only=True)
    assert prepared["outcome"] == "prepared"
    assert (
        cancel_report(env.store, prepared["report_id"])["outcome"] == "cancelled_before_admission"
    )
    again = submit(env)
    assert again["outcome"] == "cancelled" and again["run_id"] is None
    assert env.runtime.calls_named("submit") == []


def test_orphan_run_fails_invalid_input_without_a_product_write(env):
    orphan = env.runtime.submit(
        product=contract.PRODUCT,
        workflow_name=contract.WORKFLOW_NAME,
        workflow_version=contract.WORKFLOW_VERSION,
        idempotency_key="orphan-key-0001",
        input_ref=contract.input_ref("missing-report-0001", "d" * 64),
        max_attempts=3,
    ).run
    receipt = worker(env).execute_one()
    assert receipt["outcome"] == "orphan"
    run = env.runtime.get_run(orphan["run_id"])
    assert (run["state"], run["error_code"]) == ("failed", "invalid_input")
    assert env.store.get("missing-report-0001") is None


def test_malformed_input_ref_is_rejected_without_touching_a_named_report(env):
    prepared = submit(env, prepare_only=True)
    env.runtime.submit(
        product=contract.PRODUCT,
        workflow_name=contract.WORKFLOW_NAME,
        workflow_version=contract.WORKFLOW_VERSION,
        idempotency_key="malformed-key-0001",
        input_ref={"schema": contract.INPUT_REF_SCHEMA, "report_id": prepared["report_id"]},
        max_attempts=1,
    )
    receipt = worker(env).execute_one()
    assert receipt["outcome"] == "rejected_input_ref"
    assert env.runtime.calls_named("fail")[-1]["error_code"] == "invalid_input"
    record = env.store.get(prepared["report_id"])
    assert (record.status, record.run_id, record.terminal_outcome) == ("pending", None, None)


def test_foreign_run_cannot_poison_an_unrelated_report(env):
    prepared = submit(env, prepare_only=True)
    report_id = prepared["report_id"]
    foreign = env.runtime.submit(
        product=contract.PRODUCT,
        workflow_name=contract.WORKFLOW_NAME,
        workflow_version=contract.WORKFLOW_VERSION,
        idempotency_key="foreign-key-0001",
        input_ref=contract.input_ref(report_id, "e" * 64),
        max_attempts=3,
    ).run
    receipt = worker(env).execute_one()
    assert receipt["outcome"] == "foreign_run"
    assert env.runtime.get_run(foreign["run_id"])["error_code"] == "invalid_input"
    record = env.store.get(report_id)
    assert (record.status, record.run_id, record.terminal_outcome) == ("pending", None, None)

    admitted = submit(env)
    assert admitted["outcome"] == "admitted"
    assert worker(env).execute_one()["outcome"] == "completed"
    assert env.store.get(report_id).run_id == admitted["run_id"] != foreign["run_id"]


def test_duplicate_run_for_a_bound_report_is_refused_without_changing_it(env):
    prepared = submit(env, prepare_only=True)
    duplicate = env.runtime.submit(
        product=contract.PRODUCT,
        workflow_name=contract.WORKFLOW_NAME,
        workflow_version=contract.WORKFLOW_VERSION,
        idempotency_key="duplicate-key-0001",
        input_ref=contract.input_ref(prepared["report_id"], prepared["input_digest"]),
        max_attempts=3,
    ).run
    admitted = submit(env)
    assert admitted["run_id"] != duplicate["run_id"]
    receipt = worker(env).execute_one()
    assert receipt["outcome"] == "duplicate_run"
    assert env.runtime.get_run(duplicate["run_id"])["error_code"] == "side_effect_conflict"
    assert env.store.get(prepared["report_id"]).terminal_outcome is None
    assert worker(env).execute_one()["outcome"] == "completed"


def test_tampered_stored_input_fails_the_report_as_invalid_input(env):
    submitted = submit(env)
    raw = sqlite3.connect(env.store_path)
    raw.execute(
        "UPDATE reports SET frozen_input = frozen_input || ' ' WHERE report_id = ?",
        (submitted["report_id"],),
    )
    raw.commit()
    raw.close()
    receipt = worker(env).execute_one()
    assert (receipt["outcome"], receipt["runtime_error_code"]) == ("failed", "invalid_input")
    record = env.store.get(submitted["report_id"])
    assert (record.status, record.runtime_error_code) == ("failed", "invalid_input")
    assert counts(env, submitted["report_id"]) == {}


def test_fixture_changed_after_submission_is_invalid_input(env):
    submitted = submit(env)
    write_fixture(env.fixtures, "model-plan", variant(model__mode="unavailable"))
    receipt = worker(env).execute_one()
    assert (receipt["outcome"], receipt["runtime_error_code"]) == ("failed", "invalid_input")
    assert env.store.get(submitted["report_id"]).runtime_error_code == "invalid_input"


def test_oversized_fixture_is_refused_at_submission(env):
    oversized = model_plan_fixture()
    oversized["padding"] = "x" * (70 * 1024)
    write_fixture(env.fixtures, "huge", oversized)
    with pytest.raises(SubmissionError):
        submit(env, "huge")
    assert env.runtime.calls_named("submit") == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda response: setattr(
            response.metadata, "source_url", "https://feeds.synthetic.test/other"
        ),
        lambda response: setattr(response.metadata, "requested_model", "openrouter/other/model"),
        lambda response: setattr(response.metadata, "analysis_mode", None),
        lambda response: setattr(response, "metadata", None),
        lambda response: setattr(response, "articles", response.articles[:1]),
        lambda response: setattr(
            response.articles[0], "digest_url", "https://digest.synthetic.test/x"
        ),
        lambda response: setattr(
            response.metadata, "source_issue_url", "https://digest.synthetic.test/"
        ),
        lambda response: setattr(response.metadata, "resolved_model", ""),
    ],
)
def test_structurally_invalid_completed_response_is_invalid_result(env, mutation):
    submitted = submit(env)

    def mutate(response):
        mutation(response)
        return response

    receipt = worker(env, hooks=WorkerHooks(mutate_response=mutate)).execute_one()
    assert (receipt["outcome"], receipt["runtime_error_code"]) == ("failed", "invalid_result")
    run = env.runtime.get_run(submitted["run_id"])
    assert (run["state"], run["error_code"]) == ("failed", "invalid_result")
    assert env.store.get(submitted["report_id"]).runtime_error_code == "invalid_result"
    assert env.store.articles(submitted["report_id"]) == []


def test_attempt_deadline_maps_to_dependency_timeout(env):
    write_fixture(env.fixtures, "slow", variant(model__delay_seconds=5))
    submitted = submit(env, "slow", max_attempts=1)
    settings = WorkerSettings(lease_seconds=30, heartbeat_seconds=3600, attempt_timeout_seconds=0.3)
    receipt = worker(env, settings=settings).execute_one()
    assert (receipt["outcome"], receipt["runtime_error_code"]) == ("failed", "dependency_timeout")
    assert env.store.get(submitted["report_id"]).runtime_error_code == "dependency_timeout"


def test_runtime_decided_failure_is_exposed_then_reconciled_explicitly(env):
    submitted = submit(env, max_attempts=2)
    report_id, run_id = submitted["report_id"], submitted["run_id"]

    def crash(ctx, name):
        if name == "model_analysis":
            raise SimulatedCrash("worker killed mid-execution")

    for _ in range(2):
        with pytest.raises(SimulatedCrash):
            worker(env, hooks=WorkerHooks(on_boundary=crash)).execute_one()
        env.runtime.expire_lease(run_id)
    assert worker(env).execute_one()["outcome"] == "idle"
    run = env.runtime.get_run(run_id)
    assert (run["state"], run["error_code"]) == ("failed", "worker_error")

    view = read_report(env.store, env.runtime, report_id)
    assert view["reconciliation"]["state"] == "runtime_terminal_product_pending"
    assert (
        cancel_report(env.store, report_id, env.runtime)["outcome"] == "rejected_runtime_terminal"
    )
    assert reconcile_report(env.store, env.runtime, report_id)["outcome"] == "reconciled"
    record = env.store.get(report_id)
    assert (record.status, record.runtime_error_code) == ("failed", "worker_error")
    assert reconcile_report(env.store, env.runtime, report_id)["outcome"] == "noop"
    assert read_report(env.store, env.runtime, report_id)["reconciliation"]["state"] == "consistent"


def test_reader_reports_integrity_violation_for_corrupt_committed_evidence(env):
    submitted = submit(env)
    worker(env).execute_one()
    raw = sqlite3.connect(env.store_path)
    raw.execute("DROP TRIGGER reports_terminal_immutable")
    raw.execute(
        "UPDATE reports SET content = 'tampered' WHERE report_id = ?", (submitted["report_id"],)
    )
    raw.commit()
    raw.close()
    view = read_report(env.store, env.runtime, submitted["report_id"])
    assert view["reconciliation"]["state"] == "integrity_violation"
    assert view["binding"]["matches"] is False
    assert view["publication"]["eligible"] is False
    assert reconcile_report(env.store, env.runtime, submitted["report_id"])["outcome"] == "noop"


def test_resubmitting_the_same_input_reads_the_existing_run(env):
    first = submit(env)
    second = submit(env)
    assert (first["runtime_status"], second["runtime_status"]) == (201, 200)
    assert second["outcome"] == "already_bound"
    assert (second["report_id"], second["run_id"]) == (first["report_id"], first["run_id"])
    assert len(env.runtime.runs) == 1


def test_lost_submit_acknowledgement_is_recovered_by_resubmission(env):
    def crash(run):
        raise SimulatedCrash("after runtime submit")

    with pytest.raises(SimulatedCrash):
        submit(env, hooks=ProducerHooks(after_runtime_submit=crash))
    report_id = contract.derive_report_id(
        next(iter(env.runtime.runs.values()))["input_ref"]["input_digest"]
    )
    assert env.store.get(report_id).run_id is None
    again = submit(env)
    assert (again["outcome"], again["runtime_status"]) == ("admitted_existing", 200)
    assert env.store.get(report_id).run_id == again["run_id"]
    assert len(env.runtime.runs) == 1


def test_lost_submit_acknowledgement_is_recovered_by_the_first_worker(env):
    def crash(run):
        raise SimulatedCrash("after runtime submit")

    with pytest.raises(SimulatedCrash):
        submit(env, hooks=ProducerHooks(after_runtime_submit=crash))
    receipt = worker(env).execute_one()
    assert steps(receipt, "bind") == ["bound"]
    assert receipt["outcome"] == "completed"
    assert len(env.runtime.runs) == 1


def test_operation_key_reuse_with_changed_input_is_a_visible_conflict(env):
    first = submit(env, operation_key="weekly-2026-11-01")
    calls = len(env.runtime.calls_named("submit"))
    changed = submit_report(
        env.store,
        env.runtime,
        feed_url=FEED_URL,
        config={**CONFIG, "max_tokens": 8000},
        fixture_dir=env.fixtures,
        fixture_id="model-plan",
        operation_key="weekly-2026-11-01",
    )
    assert changed["outcome"] == "conflict"
    assert changed["existing_input_digest"] == first["input_digest"]
    assert len(env.runtime.calls_named("submit")) == calls
    assert env.store.get("weekly-2026-11-01").input_digest == first["input_digest"]
    assert env.store.conflicts("weekly-2026-11-01")[0]["source"] == "product"

    changed_attempts = submit(env, operation_key="weekly-2026-11-01", max_attempts=2)
    assert changed_attempts["outcome"] == "conflict"


def test_runtime_conflict_is_recorded_when_the_product_record_was_lost(env):
    first = submit(env, operation_key="weekly-2026-11-01")
    raw = sqlite3.connect(env.store_path)
    raw.execute("DELETE FROM attempts")
    raw.execute("DELETE FROM reports WHERE report_id = 'weekly-2026-11-01'")
    raw.commit()
    raw.close()
    changed = submit_report(
        env.store,
        env.runtime,
        feed_url=FEED_URL,
        config={**CONFIG, "max_tokens": 8000},
        fixture_dir=env.fixtures,
        fixture_id="model-plan",
        operation_key="weekly-2026-11-01",
    )
    assert changed["outcome"] == "runtime_conflict"
    assert changed["existing_run_id"] == first["run_id"]
    record = env.store.get("weekly-2026-11-01")
    assert (record.run_id, record.conflict_existing_run_id) == (None, first["run_id"])
    assert env.store.conflicts("weekly-2026-11-01")[-1]["source"] == "runtime"
    assert len(env.runtime.runs) == 1


def test_egress_guard_refuses_real_http_clients_inside_boundaries(env):
    import services.openrouter_client as openrouter_client
    import services.regulatory_sources as regulatory_sources
    import services.relevance_decisions as relevance_decisions
    import services.rss_service as rss_service

    fixture = load_fixture(
        env.fixtures,
        "model-plan",
        contract.sha256_hex((env.fixtures / "model-plan.json").read_bytes()),
    )
    modules = (rss_service, openrouter_client, regulatory_sources, relevance_decisions)
    with install_boundaries(fixture, attempt=1, record=lambda name: None):
        for module in modules:
            with pytest.raises(EgressRefused):
                module.httpx.AsyncClient()
            assert module.httpx.HTTPError is httpx.HTTPError
    assert all(module.httpx is httpx for module in modules)


@pytest.mark.parametrize(
    "fixture",
    [
        variant(feed__link="https://digest.example.com/"),
        variant(
            feed__entries=[{"title": "Rule", "link": "https://www.sec.gov/rules/x", "content": "x"}]
        ),
        variant(schema="grcinsight.synthetic-fixture.v0"),
        variant(model__mode="live"),
    ],
)
def test_fixtures_must_stay_synthetic(env, fixture):
    path = write_fixture(env.fixtures, "bad", fixture)
    with pytest.raises(FixtureError):
        load_fixture(env.fixtures, "bad", contract.sha256_hex(path.read_bytes()))


def test_worker_refuses_to_run_with_provider_credentials(env, monkeypatch):
    from config.settings import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "configured-for-test")
    submit(env)
    with pytest.raises(WorkerConfigurationError):
        worker(env).execute_one()
    assert env.runtime.calls_named("claim") == []


def test_worker_receipts_are_json_serializable(env):
    submit(env)
    receipt = worker(env).execute_one()
    assert json.loads(json.dumps(receipt))["outcome"] == "completed"
    assert receipt["lease_owner"]


def fence_out(env, run_id):
    """Expire the current lease and let another claimant take the run."""
    env.runtime.expire_lease(run_id)
    env.runtime.claim(
        product=contract.PRODUCT,
        workflow_name=contract.WORKFLOW_NAME,
        workflow_version=contract.WORKFLOW_VERSION,
        lease_owner="newer-claimant",
        lease_seconds=30,
    )


def test_stale_retryable_failure_changes_nothing(env):
    write_fixture(env.fixtures, "down", variant(feed_behaviour__permanent_failure=True))
    submitted = submit(env, "down", max_attempts=3)

    def on_boundary(ctx, name):
        if name == "feed":
            fence_out(env, submitted["run_id"])

    receipt = worker(env, hooks=WorkerHooks(on_boundary=on_boundary)).execute_one()
    assert receipt["outcome"] == "stale"
    assert steps(receipt, "fail") == ["lease_fenced"]
    run = env.runtime.get_run(submitted["run_id"])
    assert (run["state"], run["lease_owner"], run["lease_version"]) == (
        "running",
        "newer-claimant",
        2,
    )
    record = env.store.get(submitted["report_id"])
    assert (record.status, record.terminal_outcome) == ("processing", None)


def test_stale_terminal_failure_is_not_written_to_the_product(env):
    submitted = submit(env)

    def mutate(response):
        fence_out(env, submitted["run_id"])
        response.metadata = None
        return response

    receipt = worker(env, hooks=WorkerHooks(mutate_response=mutate)).execute_one()
    assert receipt["outcome"] == "stale"
    assert steps(receipt, "fail") == ["lease_fenced"]
    assert steps(receipt, "product_failed") == []
    record = env.store.get(submitted["report_id"])
    assert (record.terminal_outcome, record.runtime_error_code) == (None, None)
    assert env.runtime.get_run(submitted["run_id"])["state"] == "running"


def test_reader_detects_runtime_output_not_bound_to_the_product_record(env):
    submitted = submit(env)
    worker(env).execute_one()
    assert read_report(env.store, env.runtime, submitted["report_id"])["binding"]["matches"] is True
    env.runtime.runs[submitted["run_id"]]["output_ref"]["result_digest"] = "0" * 64
    view = read_report(env.store, env.runtime, submitted["report_id"])
    assert view["binding"]["digest_intact"] is True
    assert view["binding"]["matches"] is False
    assert view["reconciliation"]["state"] == "integrity_violation"


def test_heartbeat_client_close_never_closes_the_workers_borrowed_transport(env):
    from runtime_adapter.client import RuntimeClient
    from runtime_adapter_support import FakeRuntimeTransport

    transport = FakeRuntimeTransport(env.runtime)
    client = RuntimeClient("http://127.0.0.1:18999", transport=transport)
    submitted = submit_report(
        env.store,
        client,
        feed_url=FEED_URL,
        config=CONFIG,
        fixture_dir=env.fixtures,
        fixture_id="model-plan",
    )
    receipt = GRCWorker(env.store, client, fixture_dir=env.fixtures, settings=FAST).execute_one()
    assert receipt["outcome"] == "completed"
    assert client.get_run(submitted["run_id"])["state"] == "succeeded"
    client.close()
    assert (transport.closed, transport.close_calls) == (False, 0)


def corrupt(env, *statements):
    """Test-only corruption of committed rows, bypassing the immutability triggers."""
    raw = sqlite3.connect(env.store_path)
    raw.execute("DROP TRIGGER IF EXISTS reports_terminal_immutable")
    raw.execute("DROP TRIGGER IF EXISTS articles_no_update")
    for statement in statements:
        raw.execute(statement)
    raw.commit()
    raw.close()


def forge_digest(env, report_id):
    """Make the stored digest agree with corrupted rows, as a consistent forgery would.

    Computed from the raw rows with the store's digest definition, independently of
    the store's own (validating) read path.
    """
    from runtime_adapter.store import ARTICLE_LIST_FIELDS, _digest

    raw = sqlite3.connect(env.store_path)
    raw.row_factory = sqlite3.Row
    row = raw.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    articles = []
    for item in raw.execute(
        "SELECT * FROM articles WHERE report_id = ? ORDER BY position", (report_id,)
    ).fetchall():
        article = dict(item)
        article["has_grc_content"] = bool(article["has_grc_content"])
        for name in ARTICLE_LIST_FIELDS:
            article[name] = json.loads(article[name])
        articles.append(article)
    raw.close()
    report = {
        key: row[key]
        for key in (
            "report_id",
            "title",
            "content",
            "status",
            "source_url",
            "generated_at",
            "created_at",
            "updated_at",
        )
    }
    report["metadata"] = json.loads(row["metadata"])
    digest = _digest(
        report, input_digest=row["input_digest"], run_id=row["run_id"], articles=articles
    )
    corrupt(env, f"UPDATE reports SET result_digest = '{digest}' WHERE report_id = '{report_id}'")


def commit_then_lose_completion(env, fixture_id="model-plan", **kwargs):
    submitted = submit(env, fixture_id, **kwargs)

    def crash(ctx):
        raise SimulatedCrash("after product commit")

    with pytest.raises(SimulatedCrash):
        worker(env, hooks=WorkerHooks(after_commit=crash)).execute_one()
    return submitted


CORRUPTIONS = {
    "frozen-input-bytes": (
        "UPDATE reports SET frozen_input = CAST(frozen_input || ' ' AS BLOB)"
        " WHERE report_id = '{report_id}'",
        False,
    ),
    "frozen-input-recomputed-digest": (
        "UPDATE reports SET frozen_input = CAST(frozen_input || ' ' AS BLOB)"
        " WHERE report_id = '{report_id}'",
        True,
    ),
    "article-list-not-json": (
        "UPDATE articles SET regulations = 'not json' WHERE report_id = '{report_id}'",
        False,
    ),
    "article-list-wrong-shape": (
        "UPDATE articles SET frameworks = '{{\"a\": 1}}' WHERE report_id = '{report_id}'",
        True,
    ),
    "metadata-not-json": (
        "UPDATE reports SET metadata = '{{\"broken' WHERE report_id = '{report_id}'",
        False,
    ),
    "metadata-not-object": (
        "UPDATE reports SET metadata = '[]' WHERE report_id = '{report_id}'",
        True,
    ),
    "metadata-feed-not-frozen-feed": (
        "UPDATE reports SET metadata = json_set(metadata, '$.source_url',"
        " 'https://feeds.synthetic.test/other') WHERE report_id = '{report_id}'",
        True,
    ),
    "article-count-mismatch": (
        "UPDATE reports SET metadata = json_set(metadata, '$.article_count', 7)"
        " WHERE report_id = '{report_id}'",
        True,
    ),
}


@pytest.mark.parametrize("case", sorted(CORRUPTIONS))
def test_reader_reports_corrupt_committed_evidence_without_raising(env, case):
    submitted = submit(env)
    worker(env).execute_one()
    report_id = submitted["report_id"]
    statement, forge = CORRUPTIONS[case]
    corrupt(env, statement.format(report_id=report_id))
    if forge:
        forge_digest(env, report_id)
    view = read_report(env.store, env.runtime, report_id)
    assert view["reconciliation"]["state"] == "integrity_violation"
    assert view["binding"]["matches"] is False and view["binding"]["problems"]
    assert view["publication"]["eligible"] is False
    assert "integrity" in view["publication"]["reason"]
    assert env.store.publication_evidence(report_id)[-1]["eligible"] is False
    assert env.store.dump(report_id)["integrity"]["intact"] is False
    assert reconcile_report(env.store, env.runtime, report_id)["outcome"] == "noop"


@pytest.mark.parametrize("case", sorted(CORRUPTIONS))
def test_reuse_refuses_corrupt_committed_evidence_without_new_work(env, case):
    submitted = commit_then_lose_completion(env)
    report_id = submitted["report_id"]
    before = counts(env, report_id)
    statement, forge = CORRUPTIONS[case]
    corrupt(env, statement.format(report_id=report_id))
    if forge:
        forge_digest(env, report_id)
    raw = sqlite3.connect(env.store_path)
    row_before = raw.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    raw.close()

    env.runtime.expire_lease(submitted["run_id"])
    receipt = worker(env).execute_one()
    assert receipt["outcome"] == "integrity_failure"
    assert env.runtime.calls_named("complete") == []
    run = env.runtime.get_run(submitted["run_id"])
    assert (run["state"], run["error_code"]) == ("failed", "invalid_result")
    assert counts(env, report_id) == before
    raw = sqlite3.connect(env.store_path)
    assert (
        raw.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        == row_before
    )
    raw.close()


def test_final_attempt_commit_with_lost_completion_is_exposed_not_repaired(env):
    write_fixture(env.fixtures, "flaky", variant(feed_behaviour__transient_failures=1))
    submitted = submit(env, "flaky", max_attempts=2)
    report_id, run_id = submitted["report_id"], submitted["run_id"]
    assert worker(env).execute_one()["outcome"] == "retry_scheduled"

    def crash(ctx):
        raise SimulatedCrash("after product commit on the final attempt")

    with pytest.raises(SimulatedCrash):
        worker(env, hooks=WorkerHooks(after_commit=crash)).execute_one()
    committed = env.store.get(report_id)
    assert (committed.terminal_outcome, committed.committed_attempt) == ("completed", 2)
    before = counts(env, report_id)

    env.runtime.expire_lease(run_id)
    assert worker(env).execute_one()["outcome"] == "idle"
    run = env.runtime.get_run(run_id)
    assert (run["state"], run["error_code"], run["attempt"]) == ("failed", "worker_error", 2)
    assert "output_ref" not in run

    view = read_report(env.store, env.runtime, report_id)
    assert view["reconciliation"]["state"] == "product_committed_runtime_failed"
    assert view["binding"]["digest_intact"] is True and view["binding"]["matches"] is False
    assert reconcile_report(env.store, env.runtime, report_id)["outcome"] == "noop"
    assert (
        cancel_report(env.store, report_id, env.runtime)["outcome"] == "rejected_already_committed"
    )
    after = env.store.get(report_id)
    assert (after.result_digest, after.updated_at, after.status) == (
        committed.result_digest,
        committed.updated_at,
        "completed",
    )
    assert counts(env, report_id) == before
    assert worker(env).execute_one()["outcome"] == "idle"


# Retained values of the wrong SQLite storage class. Small, harmless values only:
# an integer frozen input must never be turned into that many bytes.
TYPE_CORRUPTIONS = {
    "frozen-input-small-integer": (
        "UPDATE reports SET frozen_input = 7 WHERE report_id = '{report_id}'",
        "frozen_input",
    ),
    "frozen-input-negative-integer": (
        "UPDATE reports SET frozen_input = -1 WHERE report_id = '{report_id}'",
        "frozen_input",
    ),
    "report-content-blob": (
        "UPDATE reports SET content = X'00ff' WHERE report_id = '{report_id}'",
        "content",
    ),
    "article-title-blob": (
        "UPDATE articles SET title = X'00' WHERE report_id = '{report_id}' AND position = 0",
        "title",
    ),
    "committed-lease-version-blob": (
        "UPDATE reports SET committed_lease_version = X'01' WHERE report_id = '{report_id}'",
        "committed_lease_version",
    ),
    "metadata-blob": (
        "UPDATE reports SET metadata = X'ff' WHERE report_id = '{report_id}'",
        "metadata",
    ),
}


@pytest.mark.parametrize("case", sorted(TYPE_CORRUPTIONS))
def test_reader_and_dump_classify_wrong_retained_types_without_converting(env, case):
    submitted = submit(env)
    worker(env).execute_one()
    report_id = submitted["report_id"]
    statement, column = TYPE_CORRUPTIONS[case]
    corrupt(env, statement.format(report_id=report_id))

    record = env.store.get(report_id)
    assert record.frozen_input not in (b"\x00" * 7,), "an integer must not become zero bytes"
    view = read_report(env.store, env.runtime, report_id)
    assert view["reconciliation"]["state"] == "integrity_violation"
    assert view["publication"]["eligible"] is False
    assert any(column in problem for problem in view["binding"]["problems"]), view["binding"][
        "problems"
    ]
    dumped = env.store.dump(report_id)
    assert dumped["integrity"]["intact"] is False
    json.dumps(dumped, default=str)


@pytest.mark.parametrize("case", sorted(TYPE_CORRUPTIONS))
def test_reuse_refuses_wrong_retained_types_without_new_work(env, case):
    submitted = commit_then_lose_completion(env)
    report_id = submitted["report_id"]
    before = counts(env, report_id)
    statement, column = TYPE_CORRUPTIONS[case]
    corrupt(env, statement.format(report_id=report_id))
    raw = sqlite3.connect(env.store_path)
    row_before = raw.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    raw.close()

    env.runtime.expire_lease(submitted["run_id"])
    receipt = worker(env).execute_one()
    assert receipt["outcome"] == "integrity_failure", receipt
    assert env.runtime.calls_named("complete") == []
    assert env.runtime.get_run(submitted["run_id"])["state"] == "failed"
    assert counts(env, report_id) == before
    raw = sqlite3.connect(env.store_path)
    assert (
        raw.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        == row_before
    )
    raw.close()


def http_client(env):
    """The real RuntimeClient (with its run_id validation) over the HTTP test double."""
    from runtime_adapter.client import RuntimeClient
    from runtime_adapter_support import FakeRuntimeTransport

    transport = FakeRuntimeTransport(env.runtime)
    return RuntimeClient("http://127.0.0.1:18999", transport=transport), transport


@pytest.mark.parametrize("retained_run_id", ["X'01'", "'not-a-run-uuid'"])
def test_reader_refuses_a_corrupt_retained_run_binding_before_querying_runtime(
    env, retained_run_id
):
    client, transport = http_client(env)
    submitted = submit_report(
        env.store,
        client,
        feed_url=FEED_URL,
        config=CONFIG,
        fixture_dir=env.fixtures,
        fixture_id="model-plan",
    )
    GRCWorker(env.store, client, fixture_dir=env.fixtures, settings=FAST).execute_one()
    report_id = submitted["report_id"]
    before = counts(env, report_id)
    corrupt(env, f"UPDATE reports SET run_id = {retained_run_id} WHERE report_id = '{report_id}'")
    raw = sqlite3.connect(env.store_path)
    row_before = raw.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    raw.close()
    requests_before = transport.requests

    view = read_report(env.store, client, report_id)
    assert (
        transport.requests == requests_before
    ), "Runtime must not be queried with a corrupt binding"
    assert view["reconciliation"]["state"] == "integrity_violation"
    assert view["publication"]["eligible"] is False
    assert any("run_id" in problem for problem in view["binding"]["problems"]), view["binding"]
    assert reconcile_report(env.store, client, report_id)["outcome"] == "noop"
    assert counts(env, report_id) == before
    raw = sqlite3.connect(env.store_path)
    assert (
        raw.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        == row_before
    )
    raw.close()
    client.close()


def test_cancel_lookup_skips_runtime_for_a_corrupt_retained_binding(env):
    client, transport = http_client(env)
    submitted = submit_report(
        env.store,
        client,
        feed_url=FEED_URL,
        config=CONFIG,
        fixture_dir=env.fixtures,
        fixture_id="model-plan",
    )
    corrupt(
        env,
        f"UPDATE reports SET run_id = 'not-a-run-uuid' WHERE report_id = '{submitted['report_id']}'",
    )
    requests_before = transport.requests
    receipt = cancel_report(env.store, submitted["report_id"], client)
    assert transport.requests == requests_before
    assert "run_id" in receipt.get("runtime_lookup", "")
    client.close()


def test_valid_binding_keeps_runtime_unavailable_semantics(env):
    from runtime_adapter.client import RuntimeClient

    submitted = submit(env)
    worker(env).execute_one()

    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    client = RuntimeClient("http://127.0.0.1:18999", transport=httpx.MockTransport(refuse))
    view = read_report(env.store, client, submitted["report_id"])
    assert view["reconciliation"]["state"] == "runtime_unavailable"
    assert view["runtime"] == {"error": "ConnectError"}
    client.close()
