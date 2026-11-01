"""Runtime worker that executes the real GRC workflow for one leased report run.

Order of one attempt:

1. claim one run in the exact (product, workflow, version) scope;
2. verify the run before touching any product record: ``input_ref`` schema and
   shape, the named report exists, its frozen input digest, workflow version and
   attempt budget match, and it is bound to this run (or unbound, in which case
   the worker binds it: lost-acknowledgement recovery). A foreign or duplicate run
   is failed in Runtime and leaves the named report untouched;
3. reuse: a report that already has a terminal outcome is never executed again;
   its stored outcome is reflected into Runtime (completed -> ``complete`` with
   the stored binding, only after the retained input, binding and rows verify,
   otherwise ``invalid_result``; failed -> its terminal code; cancelled ->
   ``side_effect_conflict``);
4. re-validate the report's own frozen input and fixture (tampering is a terminal
   ``invalid_input`` for that report);
5. register product-side ownership with this lease version. A strictly newer
   registered lease fences this attempt out of the commit;
6. heartbeat on a separate thread and client, run the workflow with a deadline,
   watch for cancellation (durable product flag) and fencing; either aborts the
   workflow by asyncio cancellation, so no boundary starts after it is observed;
7. classify the ``WorkflowResponse``; only a structurally valid completed result
   is committed, once, under the ownership fence; then ``complete`` binds the
   Runtime output to the committed digest.

Failures go to Runtime first. A product failure is written only after Runtime
reports the run ``failed``; a ``retry_wait`` answer leaves the report open.

Fencing is not atomic across Runtime and the product store. Between a newer
Runtime claim and that worker's registration, the older lease is still the
registered owner and can still commit. That commit is then the report's single
outcome: the older worker's ``complete`` is fenced by Runtime, and the newer
worker finds the committed outcome at registration and reuses it. No second
effect and no overwrite can happen; which attempt's work is retained can.
Synthetic boundaries may run more than once (at-least-once execution) whenever
a lease expires before the commit.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any, Callable
import uuid

from loguru import logger

from runtime_adapter import contract
from runtime_adapter.client import (
    LeaseFenced,
    RuntimeClientError,
    RuntimeUnavailable,
)
from runtime_adapter.results import InvalidResult, build_product_record
from runtime_adapter.store import ReportRecord, ReportStore
from runtime_adapter.synthetic import FixtureError, install_boundaries, load_fixture

CANCELLED_SUMMARY = "cancelled by product"


class SimulatedCrash(BaseException):
    """Test and fault-injection stand-in for abrupt process death (no cleanup calls)."""


class WorkerConfigurationError(RuntimeError):
    """The worker refuses to run with live provider configuration."""


@dataclass(frozen=True)
class WorkerSettings:
    lease_seconds: int = 15
    heartbeat_seconds: float | None = None  # default: a third of the lease
    attempt_timeout_seconds: float = 120.0
    cancel_poll_seconds: float = 0.05
    complete_retries: int = 3
    retry_backoff_seconds: float = 0.25

    @property
    def heartbeat_interval(self) -> float:
        return self.heartbeat_seconds or max(0.5, self.lease_seconds / 3)


@dataclass
class WorkerHooks:
    """Fault-injection points; all default off and are named in receipts when used."""

    before_register: Callable[["AttemptContext"], None] | None = None
    before_commit: Callable[["AttemptContext"], None] | None = None
    after_commit: Callable[["AttemptContext"], None] | None = None
    on_boundary: Callable[["AttemptContext", str], None] | None = None
    mutate_response: Callable[[Any], Any] | None = None
    names: tuple[str, ...] = ()


class _Heartbeat(threading.Thread):
    def __init__(
        self, runtime, run_id: str, lease_owner: str, lease_version: int, settings: WorkerSettings
    ):
        super().__init__(name=f"heartbeat-{run_id[:8]}", daemon=True)
        self._runtime = runtime
        self._args = dict(
            lease_owner=lease_owner,
            lease_version=lease_version,
            lease_seconds=settings.lease_seconds,
        )
        self._run_id = run_id
        self._interval = settings.heartbeat_interval
        self._stopping = threading.Event()
        self._resume = threading.Event()
        self._resume.set()
        self._lock = threading.Lock()
        self._closed = False
        self.fenced = threading.Event()
        self.results: list[str] = []

    def beat(self) -> str:
        with self._lock:
            if self.fenced.is_set():
                return "lease_fenced"
            if self._closed:
                return "stopped"
            try:
                self._runtime.heartbeat(self._run_id, **self._args)
                result = "ok"
            except LeaseFenced:
                self.fenced.set()
                result = "lease_fenced"
            except RuntimeClientError as error:
                result = f"error:{error.code}"
            self.results.append(result)
            return result

    def run(self) -> None:
        try:
            while not self._stopping.wait(self._interval):
                self._resume.wait()
                if self._stopping.is_set() or self.beat() == "lease_fenced":
                    return
        finally:
            with self._lock:
                self._closed = True
                close = getattr(self._runtime, "close", None)
                if callable(close):
                    close()

    def suspend(self) -> None:
        self._resume.clear()

    def resume(self) -> None:
        self._resume.set()

    def stop(self) -> None:
        self._stopping.set()
        self._resume.set()
        if self.is_alive():
            self.join(timeout=10)


@dataclass
class AttemptContext:
    run: dict[str, Any]
    report_id: str | None
    lease_owner: str
    receipt: dict[str, Any]
    heartbeat: _Heartbeat | None = None
    fixture_dir: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def run_id(self) -> str:
        return self.run["run_id"]

    @property
    def attempt(self) -> int:
        return int(self.run["attempt"])

    @property
    def lease_version(self) -> int:
        return int(self.run["lease_version"])

    @property
    def report(self) -> str:
        """The verified report id; set once the run is bound to its report."""
        assert self.report_id is not None
        return self.report_id

    def heartbeat_now(self) -> str:
        """Heartbeat synchronously, as the heartbeat thread would on its next tick."""
        if self.heartbeat is None:
            return "not_started"
        return self.heartbeat.beat()

    def suspend_heartbeat(self) -> None:
        if self.heartbeat is not None:
            self.heartbeat.suspend()

    def resume_heartbeat(self) -> None:
        if self.heartbeat is not None:
            self.heartbeat.resume()


def default_lease_owner() -> str:
    return f"grc-worker:{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:12]}"


def ensure_offline_configuration() -> None:
    """Refuse to execute with a live provider key or the relevance pilot enabled."""
    from config.settings import settings

    if settings.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY"):
        raise WorkerConfigurationError("worker refuses to run with an OpenRouter key configured")
    if settings.grc_relevance_mode != "off":
        raise WorkerConfigurationError("worker requires GRC_RELEVANCE_MODE=off")


class GRCWorker:
    def __init__(
        self,
        store: ReportStore,
        runtime,
        *,
        fixture_dir: str | Path,
        settings: WorkerSettings = WorkerSettings(),
        hooks: WorkerHooks | None = None,
        lease_owner: str | None = None,
    ):
        self.store = store
        self.runtime = runtime
        self.fixture_dir = Path(fixture_dir)
        self.settings = settings
        self.hooks = hooks or WorkerHooks()
        self.lease_owner = lease_owner or default_lease_owner()

    def _load(self, report_id: str) -> ReportRecord:
        record = self.store.get(report_id)
        assert record is not None, "verified report record disappeared"
        return record

    # Receipts ------------------------------------------------------------------
    @staticmethod
    def _step(ctx: AttemptContext, step: str, result: str, **detail: Any) -> None:
        ctx.receipt["steps"].append({"step": step, "result": result, "at": time.time(), **detail})

    def _finish(
        self, ctx: AttemptContext, outcome: str, attempt_id: int | None = None, **fields: Any
    ) -> dict[str, Any]:
        ctx.receipt.update(outcome=outcome, **fields)
        if ctx.heartbeat is not None:
            ctx.receipt["heartbeats"] = list(ctx.heartbeat.results)
        if attempt_id is not None:
            self.store.finish_attempt(attempt_id, outcome, fields.get("runtime_error_code"))
        if ctx.report_id is not None:
            ctx.receipt["boundary_counts"] = dict(self.store.boundary_counts(ctx.report_id))
        return ctx.receipt

    # Runtime calls -------------------------------------------------------------
    def _fail(
        self, ctx: AttemptContext, error_code: str, domain_code: str
    ) -> dict[str, Any] | None:
        summary = (
            f"{CANCELLED_SUMMARY}; {contract.error_summary(ctx.report_id or '-', domain_code, ctx.attempt)}"
            if domain_code == "CANCELLED_BY_PRODUCT"
            else contract.error_summary(ctx.report_id or "-", domain_code, ctx.attempt)
        )
        try:
            run = self.runtime.fail(
                ctx.run_id,
                lease_owner=self.lease_owner,
                lease_version=ctx.lease_version,
                error_code=error_code,
                error_summary=summary,
            )
        except LeaseFenced:
            self._step(ctx, "fail", "lease_fenced", error_code=error_code)
            return None
        self._step(ctx, "fail", run["state"], error_code=error_code)
        ctx.receipt["runtime_state"] = run["state"]
        return run

    def _complete(self, ctx: AttemptContext) -> str:
        output_ref = self.store.output_ref(ctx.report)
        ctx.receipt["output_ref"] = output_ref
        for attempt in range(self.settings.complete_retries + 1):
            try:
                run = self.runtime.complete(
                    ctx.run_id,
                    lease_owner=self.lease_owner,
                    lease_version=ctx.lease_version,
                    output_ref=output_ref,
                )
            except LeaseFenced:
                self._step(ctx, "complete", "lease_fenced")
                return "lease_fenced"
            except RuntimeUnavailable as error:
                self._step(ctx, "complete", f"unavailable:{error.code}")
                if attempt < self.settings.complete_retries:
                    time.sleep(self.settings.retry_backoff_seconds * (attempt + 1))
                continue
            self._step(ctx, "complete", run["state"])
            ctx.receipt["runtime_state"] = run["state"]
            return "completed"
        return "unacknowledged"

    def _probe_fence(self, ctx: AttemptContext) -> None:
        """Confirm a product-side fence against Runtime truth for the receipt."""
        if ctx.heartbeat is not None:
            self._step(ctx, "heartbeat", ctx.heartbeat.beat())
            return
        try:
            self.runtime.heartbeat(
                ctx.run_id,
                lease_owner=self.lease_owner,
                lease_version=ctx.lease_version,
                lease_seconds=self.settings.lease_seconds,
            )
            self._step(ctx, "heartbeat", "ok")
        except LeaseFenced:
            self._step(ctx, "heartbeat", "lease_fenced")

    def _record_failure(
        self, ctx: AttemptContext, run: dict[str, Any] | None, domain_code: str
    ) -> None:
        """Write a product failure only from a Runtime-confirmed terminal failure."""
        if run is not None and run["state"] == "failed":
            result = self.store.commit_failed(
                ctx.report,
                run_id=ctx.run_id,
                error_code=run.get("error_code") or "unknown",
                reason=domain_code,
            )
            self._step(ctx, "product_failed", result)

    # Attempt -------------------------------------------------------------------
    def execute_one(self) -> dict[str, Any]:
        ensure_offline_configuration()
        receipt: dict[str, Any] = {
            "kind": "grc_worker_receipt",
            "lease_owner": self.lease_owner,
            "faults": list(self.hooks.names),
            "steps": [],
        }
        run = self.runtime.claim(
            product=contract.PRODUCT,
            workflow_name=contract.WORKFLOW_NAME,
            workflow_version=contract.WORKFLOW_VERSION,
            lease_owner=self.lease_owner,
            lease_seconds=self.settings.lease_seconds,
        )
        if run is None:
            receipt["outcome"] = "idle"
            return receipt
        receipt.update(
            run_id=run["run_id"], attempt=run["attempt"], lease_version=run["lease_version"]
        )
        ctx = AttemptContext(
            run=run,
            report_id=None,
            lease_owner=self.lease_owner,
            receipt=receipt,
            fixture_dir=self.fixture_dir,
        )
        self._step(ctx, "claim", "leased")

        if (run.get("product"), run.get("workflow_name"), run.get("workflow_version")) != (
            contract.PRODUCT,
            contract.WORKFLOW_NAME,
            contract.WORKFLOW_VERSION,
        ):
            self._fail(ctx, "unsupported_workflow", "WORKFLOW_SCOPE_MISMATCH")
            return self._finish(ctx, "rejected_scope", runtime_error_code="unsupported_workflow")
        try:
            ref = contract.parse_input_ref(run.get("input_ref"))
        except contract.InputRefError as error:
            self._fail(ctx, error.code, "INPUT_REF_INVALID")
            return self._finish(ctx, "rejected_input_ref", runtime_error_code=error.code)

        record = self.store.get(ref.report_id)
        if record is None:
            self._fail(ctx, "invalid_input", "REPORT_NOT_FOUND")
            return self._finish(ctx, "orphan", runtime_error_code="invalid_input")
        if (
            record.input_digest != ref.input_digest
            or record.workflow_version != run["workflow_version"]
            or record.max_attempts != run.get("max_attempts")
        ):
            self._fail(ctx, "invalid_input", "RUN_IDENTITY_MISMATCH")
            return self._finish(ctx, "foreign_run", runtime_error_code="invalid_input")
        if record.run_id is not None and record.run_id != run["run_id"]:
            self._fail(ctx, "side_effect_conflict", "REPORT_BOUND_TO_OTHER_RUN")
            return self._finish(ctx, "duplicate_run", runtime_error_code="side_effect_conflict")
        if record.run_id is None:
            bound = self.store.bind_run(ref.report_id, run["run_id"])
            self._step(ctx, "bind", bound)
            if bound == "conflict":
                self._fail(ctx, "side_effect_conflict", "REPORT_BOUND_TO_OTHER_RUN")
                return self._finish(ctx, "duplicate_run", runtime_error_code="side_effect_conflict")

        # The run is now verified as this report's run.
        ctx.report_id = ref.report_id
        receipt["report_id"] = ref.report_id
        attempt_id = self.store.record_attempt(
            ref.report_id,
            run_id=run["run_id"],
            attempt=ctx.attempt,
            lease_version=ctx.lease_version,
            lease_owner=self.lease_owner,
        )
        record = self._load(ref.report_id)
        if record.terminal_outcome is not None:
            return self._reuse(ctx, attempt_id)

        try:
            submission = contract.load_frozen(record.frozen_input, record.input_digest)
            fixture = load_fixture(
                self.fixture_dir, submission["fixture"]["id"], submission["fixture"]["sha256"]
            )
        except (contract.SubmissionError, FixtureError) as error:
            self._step(ctx, "validate_input", "invalid", reason=type(error).__name__)
            run_after = self._fail(ctx, "invalid_input", "STORED_INPUT_INVALID")
            self._record_failure(ctx, run_after, "STORED_INPUT_INVALID")
            return self._finish(
                ctx,
                "failed" if run_after else "stale",
                attempt_id,
                runtime_error_code="invalid_input",
            )

        if self.hooks.before_register:
            self.hooks.before_register(ctx)
        registered = self.store.register_owner(
            ref.report_id,
            run_id=run["run_id"],
            attempt=ctx.attempt,
            lease_version=ctx.lease_version,
            lease_owner=self.lease_owner,
        )
        self._step(ctx, "register", registered)
        if registered == "terminal":
            return self._reuse(ctx, attempt_id)
        if registered != "registered":
            self._probe_fence(ctx)
            return self._finish(ctx, "stale_superseded", attempt_id)

        ctx.heartbeat = _Heartbeat(
            _heartbeat_client(self.runtime),
            run["run_id"],
            self.lease_owner,
            ctx.lease_version,
            self.settings,
        )
        ctx.heartbeat.start()
        try:
            return self._execute(ctx, attempt_id, submission, fixture)
        finally:
            ctx.heartbeat.stop()
            receipt["heartbeats"] = list(ctx.heartbeat.results)

    def _reuse(self, ctx: AttemptContext, attempt_id: int) -> dict[str, Any]:
        record = self._load(ctx.report)
        self._step(ctx, "reuse", record.terminal_outcome or "none")
        if record.terminal_outcome == "completed":
            check = self.store.verify_committed(ctx.report)
            if not check.intact:
                # The retained input, binding or rows no longer verify. Never execute
                # again and never bind Runtime success to it; the record is untouched.
                ctx.receipt["integrity_problems"] = check.problems
                self._fail(ctx, "invalid_result", "COMMITTED_EVIDENCE_INTEGRITY")
                return self._finish(
                    ctx, "integrity_failure", attempt_id, runtime_error_code="invalid_result"
                )
            result = self._complete(ctx)
            outcome = {"completed": "reused_completed", "lease_fenced": "stale_after_terminal"}.get(
                result, "complete_unacknowledged"
            )
            return self._finish(ctx, outcome, attempt_id)
        if record.terminal_outcome == "failed":
            code = (
                record.runtime_error_code
                if record.runtime_error_code in contract.TERMINAL_ERROR_CODES
                else "side_effect_conflict"
            )
            run_after = self._fail(ctx, code, "PRODUCT_ALREADY_FAILED")
            return self._finish(
                ctx, "reused_failed" if run_after else "stale", attempt_id, runtime_error_code=code
            )
        run_after = self._fail(ctx, "side_effect_conflict", "CANCELLED_BY_PRODUCT")
        return self._finish(
            ctx,
            "cancelled" if run_after else "stale",
            attempt_id,
            runtime_error_code="side_effect_conflict",
        )

    def _execute(
        self,
        ctx: AttemptContext,
        attempt_id: int,
        submission: dict[str, Any],
        fixture: dict[str, Any],
    ) -> dict[str, Any]:
        from core.workflow import run_grc_analysis_endpoint
        from models.api import GRCAnalysisConfig

        heartbeat = ctx.heartbeat
        assert heartbeat is not None, "execution requires a started heartbeat"

        def record_boundary(name: str) -> None:
            self.store.record_boundary(
                ctx.report,
                run_id=ctx.run_id,
                attempt=ctx.attempt,
                lease_version=ctx.lease_version,
                lease_owner=self.lease_owner,
                boundary=name,
            )
            if self.hooks.on_boundary:
                self.hooks.on_boundary(ctx, name)

        config = GRCAnalysisConfig(**submission["config"])
        abort: dict[str, str] = {}

        async def attempt() -> Any:
            deadline = time.monotonic() + self.settings.attempt_timeout_seconds
            task = asyncio.ensure_future(
                run_grc_analysis_endpoint(submission["feed_url"], config, model_deadline=deadline)
            )
            while not task.done():
                if heartbeat.fenced.is_set():
                    abort["reason"] = "fenced"
                elif self.store.terminal_outcome(ctx.report) == "cancelled":
                    abort["reason"] = "cancelled"
                if abort:
                    task.cancel()
                    break
                await asyncio.wait({task}, timeout=self.settings.cancel_poll_seconds)
            try:
                return await task
            except asyncio.CancelledError:
                if abort:
                    return None
                raise

        try:
            with install_boundaries(fixture, attempt=ctx.attempt, record=record_boundary):
                response = asyncio.run(
                    asyncio.wait_for(attempt(), timeout=self.settings.attempt_timeout_seconds)
                )
        except asyncio.TimeoutError:
            self._step(ctx, "execute", "timeout")
            run_after = self._fail(ctx, "dependency_timeout", "ATTEMPT_DEADLINE_EXCEEDED")
            self._record_failure(ctx, run_after, "ATTEMPT_DEADLINE_EXCEEDED")
            return self._outcome_from_fail(ctx, attempt_id, run_after, "dependency_timeout")
        except Exception as error:  # adapter failure before any product write
            logger.warning("Adapter failure during execution: {}", type(error).__name__)
            self._step(ctx, "execute", "adapter_error", error=type(error).__name__)
            run_after = self._fail(ctx, "worker_error", "ADAPTER_ERROR")
            self._record_failure(ctx, run_after, "ADAPTER_ERROR")
            return self._outcome_from_fail(ctx, attempt_id, run_after, "worker_error")

        if abort.get("reason") == "fenced":
            self._step(ctx, "execute", "aborted_fenced")
            return self._finish(ctx, "stale_fenced_during_execution", attempt_id)
        if abort.get("reason") == "cancelled":
            self._step(ctx, "execute", "aborted_cancelled")
            run_after = self._fail(ctx, "side_effect_conflict", "CANCELLED_BY_PRODUCT")
            return self._finish(
                ctx,
                "cancelled_during_execution" if run_after else "stale",
                attempt_id,
                runtime_error_code="side_effect_conflict",
            )

        if self.hooks.mutate_response:
            response = self.hooks.mutate_response(response)
        self._step(ctx, "execute", response.status)
        if response.status == "failed":
            domain_code = response.error.code if response.error else "UNKNOWN"
            error_code = contract.map_workflow_error(domain_code)
            run_after = self._fail(ctx, error_code, domain_code)
            self._record_failure(ctx, run_after, domain_code)
            ctx.receipt["domain_code"] = domain_code
            return self._outcome_from_fail(ctx, attempt_id, run_after, error_code)
        try:
            report, articles = build_product_record(response, submission)
        except InvalidResult as error:
            self._step(ctx, "validate_result", "invalid", reason=str(error))
            run_after = self._fail(ctx, "invalid_result", "RESULT_INVALID")
            self._record_failure(ctx, run_after, "RESULT_INVALID")
            return self._outcome_from_fail(ctx, attempt_id, run_after, "invalid_result")

        if self.hooks.before_commit:
            self.hooks.before_commit(ctx)
        if heartbeat.fenced.is_set():
            # Runtime already told this attempt it lost the lease: it cannot commit.
            return self._finish(ctx, "stale_known_fenced", attempt_id)
        committed = self.store.commit_completed(
            ctx.report,
            run_id=ctx.run_id,
            attempt=ctx.attempt,
            lease_version=ctx.lease_version,
            lease_owner=self.lease_owner,
            report=report,
            articles=articles,
        )
        self._step(ctx, "commit", committed.outcome, result_digest=committed.result_digest)
        ctx.resume_heartbeat()
        if committed.outcome == "committed":
            ctx.receipt["result_digest"] = committed.result_digest
            if self.hooks.after_commit:
                self.hooks.after_commit(ctx)
            heartbeat.stop()
            result = self._complete(ctx)
            outcome = {"completed": "completed", "lease_fenced": "stale_after_commit"}.get(
                result, "complete_unacknowledged"
            )
            return self._finish(ctx, outcome, attempt_id)
        if committed.outcome == "terminal":
            # Another attempt committed first: reflect its verified outcome, never ours.
            heartbeat.stop()
            return self._reuse(ctx, attempt_id)
        if committed.outcome == "cancelled":
            run_after = self._fail(ctx, "side_effect_conflict", "CANCELLED_BY_PRODUCT")
            return self._finish(
                ctx,
                "cancelled_during_execution" if run_after else "stale",
                attempt_id,
                runtime_error_code="side_effect_conflict",
            )
        self._probe_fence(ctx)
        return self._finish(ctx, "stale_superseded", attempt_id)

    def _outcome_from_fail(
        self,
        ctx: AttemptContext,
        attempt_id: int,
        run_after: dict[str, Any] | None,
        error_code: str,
    ) -> dict[str, Any]:
        if run_after is None:
            return self._finish(ctx, "stale", attempt_id, runtime_error_code=error_code)
        outcome = "retry_scheduled" if run_after["state"] == "retry_wait" else "failed"
        return self._finish(ctx, outcome, attempt_id, runtime_error_code=error_code)


def _heartbeat_client(runtime):
    clone = getattr(runtime, "clone", None)
    return clone() if callable(clone) else runtime
