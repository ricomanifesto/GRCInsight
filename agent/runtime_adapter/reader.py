"""Read distinct product and Runtime facts for one report; reconcile explicitly.

The reader never merges product and Runtime state into one status. It reports
the product record, the Runtime run and events (raw and heartbeat-filtered), the
exact output binding check, publication eligibility from the existing composer,
and a reconciliation state. ``reconcile_report`` is the only writer here: it
records a Runtime-decided terminal failure that no worker observed (for example
lease expiry with the attempt budget exhausted). It never writes ``completed``
and never touches a terminal report.
"""

from __future__ import annotations

from typing import Any

from runtime_adapter import contract
from runtime_adapter.client import RunNotFound, RuntimeClientError
from runtime_adapter.publication import PublicationResult, evaluate_publication, publication_facts
from runtime_adapter.store import ReportStore

RUNTIME_TERMINAL = {"succeeded", "failed"}


def filter_heartbeats(events: list[dict[str, Any]]) -> list[str]:
    return [event["event_type"] for event in events if event["event_type"] != "heartbeat_recorded"]


def _reconciliation(record, run: dict[str, Any] | None, binding: dict[str, Any] | None) -> str:
    if record.run_id is None:
        if record.terminal_outcome == "cancelled":
            return "cancelled_before_admission"
        if record.conflict_existing_run_id:
            return "admission_conflict"
        return "pending_admission"
    if run is None:
        return "runtime_run_missing"
    state = run["state"]
    outcome = record.terminal_outcome
    if binding is not None and not binding["evidence_intact"]:
        return "integrity_violation"
    if outcome is None:
        if state == "failed":
            return "runtime_terminal_product_pending"
        if state == "succeeded":
            return "integrity_violation"
        return "in_progress"
    if outcome == "completed":
        if state == "succeeded":
            return "consistent" if binding and binding["matches"] else "integrity_violation"
        if state == "failed":
            # A committed, verified outcome whose Runtime run ended failed without
            # ever recording an output (for example completion lost on the final
            # attempt, then lease-expiry exhaustion). Neither side is rewritten.
            if not run.get("output_ref"):
                return "product_committed_runtime_failed"
            return "integrity_violation"
        return "product_committed_runtime_pending"
    if outcome == "failed":
        if state == "failed":
            if run.get("error_code") == record.runtime_error_code:
                return "consistent"
            return "failure_code_mismatch"
        if state == "succeeded":
            return "integrity_violation"
        return "product_terminal_runtime_pending"
    # cancelled
    if state == "failed":
        if run.get("error_code") == "side_effect_conflict":
            return "consistent"
        return "cancelled_runtime_failed_otherwise"
    if state == "succeeded":
        return "integrity_violation"
    return "cancel_pending_runtime"


def read_report(
    store: ReportStore, runtime, report_id: str, *, evaluate: bool = True
) -> dict[str, Any]:
    record = store.get(report_id)
    if record is None:
        return {"kind": "grc_report_view", "report_id": report_id, "product": None}
    view: dict[str, Any] = {
        "kind": "grc_report_view",
        "report_id": report_id,
        "product": record.facts(),
        "boundary_counts": dict(store.boundary_counts(report_id)),
        "article_count": store.article_count(report_id),
        "runtime": None,
        "binding": None,
        "publication": None,
    }
    run = None
    # The retained binding is evidence: validate it before using it with Runtime.
    # A corrupt run_id is an integrity failure, not a Runtime availability fact.
    binding_valid = record.run_id is None or contract.is_run_id(record.run_id)
    if not binding_valid:
        view["runtime"] = {
            "error": "retained run_id is not a valid run identity; Runtime was not queried"
        }
    elif record.run_id:
        try:
            run = runtime.get_run(record.run_id)
            events = runtime.list_events(record.run_id)
        except RunNotFound:
            view["runtime"] = {"error": "run_not_found"}
        except RuntimeClientError as error:
            view["runtime"] = {"error": error.code}
            view["reconciliation"] = {"state": "runtime_unavailable"}
            return view
        else:
            view["runtime"] = {
                "run": run,
                "events": events,
                "events_filtered": filter_heartbeats(events),
            }

    binding = None
    check = None
    if record.terminal_outcome == "completed":
        check = store.verify_committed(report_id)
        expected = store.output_ref(report_id) if check.intact else None
        actual = (run or {}).get("output_ref")
        binding = {
            "evidence_intact": check.intact,
            "problems": check.problems,
            "stored_result_digest": record.result_digest,
            "recomputed_result_digest": check.recomputed_result_digest,
            "digest_intact": check.recomputed_result_digest is not None
            and check.recomputed_result_digest == record.result_digest,
            "expected_output_ref": expected,
            "runtime_output_ref": actual,
            "matches": check.intact and actual == expected,
        }
        view["binding"] = binding
    state = _reconciliation(record, run, binding) if binding_valid else "integrity_violation"
    view["reconciliation"] = {"state": state}

    if evaluate and check is not None:
        if not check.intact:
            result = PublicationResult(
                False, "committed evidence integrity violation: " + "; ".join(check.problems), None
            )
        elif state == "integrity_violation":
            result = PublicationResult(
                False,
                "integrity violation: the Runtime output does not bind the committed record",
                None,
            )
        else:
            # The oracle judges the verified product record. A Runtime disagreement
            # (product_committed_runtime_failed) is reported separately above.
            result = evaluate_publication(record, check.submission)
        store.record_publication(
            report_id,
            result_digest=record.result_digest,
            eligible=result.eligible,
            reason=result.reason,
            composed_sha256=result.composed_sha256,
        )
        view["publication"] = publication_facts(result)
    return view


def reconcile_report(store: ReportStore, runtime, report_id: str) -> dict[str, Any]:
    view = read_report(store, runtime, report_id, evaluate=False)
    state = (view.get("reconciliation") or {}).get("state")
    receipt = {"kind": "grc_reconcile_receipt", "report_id": report_id, "state_before": state}
    if state != "runtime_terminal_product_pending":
        return {**receipt, "outcome": "noop"}
    run = view["runtime"]["run"]
    result = store.commit_failed(
        report_id,
        run_id=run["run_id"],
        error_code=run.get("error_code") or "unknown",
        reason=f"reconciled from runtime: {run.get('error_summary') or run.get('error_code')}",
    )
    after = read_report(store, runtime, report_id, evaluate=False)["reconciliation"]["state"]
    return {
        **receipt,
        "outcome": "reconciled" if result == "committed" else "noop",
        "state_after": after,
    }
