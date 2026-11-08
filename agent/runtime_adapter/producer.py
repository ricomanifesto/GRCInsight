"""Product-side admission and cancellation for Runtime-executed GRC reports.

Submission is idempotent in steps: freeze the complete admission identity, insert
the product record (same report and digest continues; a changed digest is a
visible conflict before any Runtime call), stop if cancelled, mark the admission
in flight, ``POST /v1/runs`` with ``idempotency_key=report_id``, then bind the
returned run with a compare-and-set. A lost acknowledgement is recovered by
resubmitting (Runtime returns the existing run) or by the first claiming worker.

Cancellation is a durable product fact linearized against the product commit.
Runtime has no cancellation state; a cancelled report's run is failed with
``side_effect_conflict`` by whichever worker next holds its lease.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from runtime_adapter import contract
from runtime_adapter.client import IdempotencyConflict, RuntimeClientError
from runtime_adapter.store import ReportStore
from runtime_adapter.synthetic import FixtureError, fixture_sha256

RUNTIME_TERMINAL_STATES = {"succeeded", "failed"}


@dataclass
class ProducerHooks:
    """Fault-injection points around the Runtime submission; default off."""

    before_runtime_submit: Callable[[str], None] | None = None
    after_runtime_submit: Callable[[dict[str, Any]], None] | None = None
    names: tuple[str, ...] = ()


def submit_report(
    store: ReportStore,
    runtime,
    *,
    feed_url: str,
    config: dict[str, Any],
    fixture_dir: str | Path,
    fixture_id: str,
    max_attempts: int = 3,
    operation_key: str | None = None,
    prepare_only: bool = False,
    hooks: ProducerHooks | None = None,
) -> dict[str, Any]:
    hooks = hooks or ProducerHooks()
    try:
        digest = fixture_sha256(fixture_dir, fixture_id)
    except FixtureError as error:
        raise contract.SubmissionError(str(error)) from error
    submission = contract.build_submission(
        feed_url=feed_url,
        config=config,
        fixture_id=fixture_id,
        fixture_sha256=digest,
        max_attempts=max_attempts,
    )
    frozen = contract.freeze(submission)
    report_id = contract.derive_report_id(frozen.input_digest, operation_key)
    receipt: dict[str, Any] = {
        "kind": "grc_submit_receipt",
        "report_id": report_id,
        "input_digest": frozen.input_digest,
        "run_id": None,
        "runtime_status": None,
        "faults": list(hooks.names),
    }

    frozen_result = store.freeze(report_id, frozen)
    receipt["product_record"] = frozen_result.outcome
    if frozen_result.outcome == "conflict":
        return {
            **receipt,
            "outcome": "conflict",
            "existing_input_digest": frozen_result.record.input_digest,
            "run_id": frozen_result.record.run_id,
        }
    if prepare_only:
        return {**receipt, "outcome": "prepared"}

    decision = store.begin_admission(report_id)
    if decision == "cancelled":
        cancelled = store.get(report_id)
        return {
            **receipt,
            "outcome": "cancelled",
            "run_id": cancelled.run_id if cancelled else None,
        }
    if decision == "terminal":
        return {**receipt, "outcome": "terminal"}

    if hooks.before_runtime_submit:
        hooks.before_runtime_submit(report_id)
    try:
        submitted = runtime.submit(
            product=contract.PRODUCT,
            workflow_name=contract.WORKFLOW_NAME,
            workflow_version=submission["workflow_version"],
            idempotency_key=report_id,
            input_ref=contract.input_ref(report_id, frozen.input_digest),
            max_attempts=submission["max_attempts"],
        )
    except IdempotencyConflict as error:
        store.record_runtime_conflict(report_id, frozen.input_digest, error.existing_run_id)
        return {
            **receipt,
            "outcome": "runtime_conflict",
            "runtime_status": 409,
            "existing_run_id": error.existing_run_id,
        }
    except RuntimeClientError as error:
        return {**receipt, "outcome": "unavailable", "runtime_error": error.code}

    run = submitted.run
    receipt.update(run_id=run["run_id"], runtime_status=201 if submitted.created else 200)
    if hooks.after_runtime_submit:
        hooks.after_runtime_submit(run)
    bound = store.bind_run(report_id, run["run_id"])
    receipt["bind"] = bound
    if bound == "conflict":
        return {**receipt, "outcome": "bind_conflict"}
    record = store.get(report_id)
    if record is not None and record.terminal_outcome == "cancelled":
        return {**receipt, "outcome": "admitted_after_cancel"}
    if decision == "bound":
        return {**receipt, "outcome": "already_bound"}
    return {**receipt, "outcome": "admitted" if submitted.created else "admitted_existing"}


def cancel_report(store: ReportStore, report_id: str, runtime=None) -> dict[str, Any]:
    """Request cancellation; with a Runtime client, refuse when Runtime is already terminal."""
    receipt: dict[str, Any] = {"kind": "grc_cancel_receipt", "report_id": report_id}
    record = store.get(report_id)
    if (
        runtime is not None
        and record is not None
        and record.run_id
        and record.terminal_outcome is None
    ):
        if not contract.is_run_id(record.run_id):
            # A corrupt retained binding cannot be looked up; the product-side
            # cancel still applies and the reader reports the integrity problem.
            receipt["runtime_lookup"] = (
                "retained run_id is not a valid run identity; Runtime was not queried"
            )
            return {**receipt, "outcome": store.cancel(report_id)}
        try:
            run = runtime.get_run(record.run_id)
        except RuntimeClientError as error:
            receipt["runtime_lookup"] = error.code
        else:
            receipt["runtime_state"] = run["state"]
            if run["state"] in RUNTIME_TERMINAL_STATES:
                # Runtime decided the outcome without the product: reconcile, do not cancel.
                return {**receipt, "outcome": "rejected_runtime_terminal"}
    return {**receipt, "outcome": store.cancel(report_id)}
