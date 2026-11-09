"""Test-only doubles and synthetic fixtures for the Runtime adapter tests.

``FakeRuntime`` models the adapter's HTTP expectations to drive deterministic
interleavings (lease expiry, fencing, retry budget) in unit tests. It is a finite
test double, not evidence about a deployed service.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
import uuid

import httpx

from runtime_adapter.client import (
    IdempotencyConflict,
    InvalidRuntimeRequest,
    LeaseFenced,
    RunNotFound,
    SubmitOutcome,
)
from narrative_fixture import narrated

RETRYABLE = {"dependency_unavailable", "dependency_timeout", "worker_error", "unknown"}
TERMINAL = {"invalid_input", "invalid_result", "unsupported_workflow", "side_effect_conflict"}


class FakeRuntime:
    """In-memory model of the Runtime run/lease/event contract with a manual clock."""

    def __init__(self, *, retry_delay: float = 0.0):
        self.lock = threading.RLock()
        self.now = 1_800_000_000.0
        self.retry_delay = retry_delay
        self.runs: dict[str, dict] = {}
        self.events: dict[str, list[dict]] = {}
        self.keys: dict[tuple[str, str, str], tuple[str, str]] = {}
        self.calls: list[tuple[str, dict]] = []
        self.closed = False

    # Test controls -----------------------------------------------------
    def advance(self, seconds: float) -> None:
        with self.lock:
            self.now += seconds

    def expire_lease(self, run_id: str) -> None:
        with self.lock:
            run = self.runs[run_id]
            assert run["state"] == "running"
            run["_lease_expires"] = self.now - 0.001

    def calls_named(self, name: str) -> list[dict]:
        return [args for call, args in self.calls if call == name]

    def event_types(self, run_id: str, *, include_heartbeats: bool = False) -> list[str]:
        return [
            event["event_type"]
            for event in self.events[run_id]
            if include_heartbeats or event["event_type"] != "heartbeat_recorded"
        ]

    # Contract ----------------------------------------------------------
    def _iso(self, value: float | None) -> str | None:
        if value is None:
            return None
        return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")

    def _view(self, run: dict) -> dict:
        view = {key: copy.deepcopy(value) for key, value in run.items() if not key.startswith("_")}
        view["lease_expires_at"] = self._iso(run["_lease_expires"])
        view["next_available_at"] = self._iso(run["_next_available"])
        if not view.get("lease_owner"):
            view.pop("lease_owner", None)
        if view.get("output_ref") is None:
            view.pop("output_ref", None)
        return view

    def _event(self, run: dict, event_type: str, actor_type: str, actor_id: str = "", **fields):
        events = self.events.setdefault(run["run_id"], [])
        events.append(
            {
                "run_id": run["run_id"],
                "sequence": len(events) + 1,
                "event_type": event_type,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "from_state": fields.get("from_state"),
                "to_state": fields.get("to_state"),
                "attempt": run["attempt"],
                "lease_version": run["lease_version"],
                "error_code": fields.get("error_code", ""),
                "metadata": {},
                "occurred_at": self._iso(self.now),
            }
        )

    def ready(self) -> bool:
        return True

    def submit(
        self,
        *,
        product,
        workflow_name,
        workflow_version,
        idempotency_key,
        input_ref,
        max_attempts,
    ):
        with self.lock:
            # Advance the manual clock to keep submissions deterministically ordered.
            self.now += 0.001
            self.calls.append(("submit", {"idempotency_key": idempotency_key}))
            if not all((product, workflow_name, workflow_version, idempotency_key)) or (
                not isinstance(input_ref, dict) or max_attempts < 1
            ):
                raise InvalidRuntimeRequest("invalid_request", 400)
            request_hash = hashlib.sha256(
                json.dumps(
                    [product, workflow_name, workflow_version, input_ref, max_attempts],
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            key = (product, workflow_name, idempotency_key)
            if key in self.keys:
                run_id, existing_hash = self.keys[key]
                if existing_hash != request_hash:
                    raise IdempotencyConflict("idempotency_conflict", 409, existing_run_id=run_id)
                return SubmitOutcome(created=False, run=self._view(self.runs[run_id]))
            run_id = str(uuid.uuid4())
            run = {
                "run_id": run_id,
                "product": product,
                "workflow_name": workflow_name,
                "workflow_version": workflow_version,
                "state": "queued",
                "attempt": 0,
                "max_attempts": max_attempts,
                "lease_owner": "",
                "lease_version": 0,
                "input_ref": copy.deepcopy(input_ref),
                "output_ref": None,
                "error_code": "",
                "error_summary": "",
                "created_at": self._iso(self.now),
                "updated_at": self._iso(self.now),
                "_lease_expires": None,
                "_next_available": self.now,
                "_created": self.now,
            }
            self.runs[run_id] = run
            self.keys[key] = (run_id, request_hash)
            self._event(run, "submitted", "runtime", to_state="queued")
            return SubmitOutcome(created=True, run=self._view(run))

    def get_run(self, run_id: str) -> dict:
        with self.lock:
            self.calls.append(("get_run", {"run_id": run_id}))
            if run_id not in self.runs:
                raise RunNotFound("run_not_found", 404)
            return self._view(self.runs[run_id])

    def list_events(self, run_id: str) -> list[dict]:
        with self.lock:
            self.calls.append(("list_events", {"run_id": run_id}))
            if run_id not in self.runs:
                raise RunNotFound("run_not_found", 404)
            return copy.deepcopy(self.events[run_id])

    def claim(self, *, product, workflow_name, workflow_version, lease_owner, lease_seconds):
        with self.lock:
            self.calls.append(("claim", {"lease_owner": lease_owner}))
            while True:
                eligible = [
                    run
                    for run in self.runs.values()
                    if (run["product"], run["workflow_name"], run["workflow_version"])
                    == (product, workflow_name, workflow_version)
                    and (
                        run["state"] == "queued"
                        or (run["state"] == "retry_wait" and run["_next_available"] <= self.now)
                        or (run["state"] == "running" and run["_lease_expires"] < self.now)
                    )
                ]
                if not eligible:
                    return None
                eligible.sort(
                    key=lambda run: (
                        (
                            run["_lease_expires"]
                            if run["state"] == "running"
                            else run["_next_available"]
                        ),
                        run["_created"],
                        run["run_id"],
                    )
                )
                run = eligible[0]
                from_state = run["state"]
                if from_state != "running":
                    break
                run.update(state="retry_wait", lease_owner="", _lease_expires=None)
                run["_next_available"] = self.now
                self._event(
                    run, "lease_expired", "runtime", from_state="running", to_state="retry_wait"
                )
                if run["attempt"] >= run["max_attempts"]:
                    run.update(
                        state="failed",
                        _next_available=None,
                        error_code="worker_error",
                        error_summary="lease expired and attempt budget exhausted",
                    )
                    self._event(
                        run,
                        "failed",
                        "runtime",
                        from_state="retry_wait",
                        to_state="failed",
                        error_code="worker_error",
                    )
                    continue
                self._event(
                    run,
                    "retry_scheduled",
                    "runtime",
                    from_state="retry_wait",
                    to_state="retry_wait",
                )
                from_state = "retry_wait"
                break
            run["state"] = "running"
            run["attempt"] += 1
            run["lease_version"] += 1
            run["lease_owner"] = lease_owner
            run["_lease_expires"] = self.now + lease_seconds
            run["_next_available"] = None
            run["error_code"] = ""
            run["error_summary"] = ""
            run["updated_at"] = self._iso(self.now)
            self._event(
                run,
                "lease_acquired",
                "worker",
                lease_owner,
                from_state=from_state,
                to_state="running",
            )
            return self._view(run)

    def _owned(self, run_id, lease_owner, lease_version) -> dict:
        run = self.runs.get(run_id)
        if (
            run is None
            or run["state"] != "running"
            or run["lease_owner"] != lease_owner
            or run["lease_version"] != lease_version
        ):
            raise LeaseFenced("lease_fenced", 409)
        return run

    def heartbeat(self, run_id, *, lease_owner, lease_version, lease_seconds):
        with self.lock:
            self.calls.append(("heartbeat", {"run_id": run_id, "lease_version": lease_version}))
            run = self._owned(run_id, lease_owner, lease_version)
            run["_lease_expires"] = self.now + lease_seconds
            self._event(
                run,
                "heartbeat_recorded",
                "worker",
                lease_owner,
                from_state="running",
                to_state="running",
            )
            return self._view(run)

    def complete(self, run_id, *, lease_owner, lease_version, output_ref):
        with self.lock:
            self.calls.append(("complete", {"run_id": run_id, "lease_version": lease_version}))
            run = self._owned(run_id, lease_owner, lease_version)
            run.update(
                state="succeeded",
                output_ref=copy.deepcopy(output_ref),
                lease_owner="",
                _lease_expires=None,
                _next_available=None,
            )
            self._event(
                run, "succeeded", "worker", lease_owner, from_state="running", to_state="succeeded"
            )
            return self._view(run)

    def fail(self, run_id, *, lease_owner, lease_version, error_code, error_summary):
        with self.lock:
            self.calls.append(
                (
                    "fail",
                    {"run_id": run_id, "lease_version": lease_version, "error_code": error_code},
                )
            )
            if error_code not in RETRYABLE | TERMINAL or len(error_summary) > 512:
                raise InvalidRuntimeRequest("invalid_request", 400)
            run = self._owned(run_id, lease_owner, lease_version)
            if error_code in RETRYABLE and run["attempt"] < run["max_attempts"]:
                run.update(
                    state="retry_wait",
                    lease_owner="",
                    _lease_expires=None,
                    _next_available=self.now + self.retry_delay,
                    error_code=error_code,
                    error_summary=error_summary,
                )
                self._event(
                    run,
                    "retry_scheduled",
                    "worker",
                    lease_owner,
                    from_state="running",
                    to_state="retry_wait",
                    error_code=error_code,
                )
            else:
                run.update(
                    state="failed",
                    lease_owner="",
                    _lease_expires=None,
                    _next_available=None,
                    error_code=error_code,
                    error_summary=error_summary,
                )
                self._event(
                    run,
                    "failed",
                    "worker",
                    lease_owner,
                    from_state="running",
                    to_state="failed",
                    error_code=error_code,
                )
            return self._view(run)

    def close(self) -> None:
        self.closed = True

    def clone(self) -> "FakeRuntimeHandle":
        """A second client (the heartbeat's) for the same in-memory Runtime."""
        return FakeRuntimeHandle(self)


class FakeRuntimeHandle:
    """Another client for one in-memory Runtime, closed independently of its siblings."""

    def __init__(self, runtime: FakeRuntime):
        self._runtime = runtime
        self.closed = False

    def __getattr__(self, name: str):
        if self.closed:
            raise RuntimeError("fake runtime client used after close")
        return getattr(self._runtime, name)

    def clone(self) -> "FakeRuntimeHandle":
        return FakeRuntimeHandle(self._runtime)

    def close(self) -> None:
        self.closed = True


class FakeRuntimeTransport(httpx.BaseTransport):
    """Serve the Runtime HTTP contract from a ``FakeRuntime``.

    It has real close semantics: once closed it refuses every request, so a test
    can tell whether a client closed a transport it did not own.
    """

    RUN_PATH = re.compile(r"^/v1/runs/([0-9a-f-]{36})(/events|/heartbeat|/complete|/fail)?$")

    def __init__(self, runtime: FakeRuntime):
        self.runtime = runtime
        self.closed = False
        self.close_calls = 0
        self.requests = 0

    def close(self) -> None:
        self.close_calls += 1
        self.closed = True

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self.closed:
            raise RuntimeError("transport used after close")
        self.requests += 1
        body = json.loads(request.content) if request.content else {}
        try:
            return self._dispatch(request.method, request.url.path, body)
        except IdempotencyConflict as error:
            return httpx.Response(
                409,
                json={
                    "code": "idempotency_conflict",
                    "message": "x",
                    "existing_run_id": error.existing_run_id,
                },
            )
        except LeaseFenced:
            return httpx.Response(409, json={"code": "lease_fenced", "message": "x"})
        except RunNotFound:
            return httpx.Response(404, json={"code": "run_not_found", "message": "x"})
        except InvalidRuntimeRequest:
            return httpx.Response(400, json={"code": "invalid_request", "message": "x"})

    def _dispatch(self, method: str, path: str, body: dict) -> httpx.Response:
        runtime = self.runtime
        if method == "POST" and path == "/v1/runs":
            outcome = runtime.submit(**body)
            return httpx.Response(201 if outcome.created else 200, json=outcome.run)
        if method == "POST" and path == "/v1/worker/claims":
            run = runtime.claim(
                product=body["product"],
                workflow_name=body["workflow_name"],
                workflow_version=body["workflow_version"],
                lease_owner=body["lease_owner"],
                lease_seconds=body["lease_duration_seconds"],
            )
            return httpx.Response(204) if run is None else httpx.Response(200, json=run)
        match = self.RUN_PATH.match(path)
        if match is None:
            return httpx.Response(404, json={"code": "not_found", "message": "x"})
        run_id, suffix = match.group(1), match.group(2)
        if method == "GET" and suffix is None:
            return httpx.Response(200, json=runtime.get_run(run_id))
        if method == "GET" and suffix == "/events":
            return httpx.Response(200, json=runtime.list_events(run_id))
        lease = {"lease_owner": body.get("lease_owner"), "lease_version": body.get("lease_version")}
        if method == "POST" and suffix == "/heartbeat":
            run = runtime.heartbeat(run_id, **lease, lease_seconds=body["lease_duration_seconds"])
        elif method == "POST" and suffix == "/complete":
            run = runtime.complete(run_id, **lease, output_ref=body["output_ref"])
        elif method == "POST" and suffix == "/fail":
            run = runtime.fail(
                run_id, **lease, error_code=body["error_code"], error_summary=body["error_summary"]
            )
        else:
            return httpx.Response(405, json={"code": "method_not_allowed", "message": "x"})
        return httpx.Response(200, json=run)


EVIDENCE_TEXT = "The synthetic advisory describes exposure in deployed edge gateways operated by regulated teams."
FEED_URL = "https://feeds.synthetic.test/grc/feed.xml"


def model_plan_fixture() -> dict:
    """A synthetic feed plus a model boundary that returns a renderer-valid plan."""
    return {
        "schema": "grcinsight.synthetic-fixture.v1",
        "feed": {
            "title": "Synthetic GRC Digest",
            "link": "https://digest.synthetic.test/",
            "last_updated": "Sun, 01 Nov 2026 12:00:00 GMT",
            "entries": [
                {
                    "title": "Synthetic gateway advisory for regulated teams",
                    "link": "https://news.synthetic.test/a/gateway-advisory",
                    "description": "A synthetic summary of a gateway advisory.",
                    "published": "Sun, 01 Nov 2026 10:00:00 GMT",
                    "content": EVIDENCE_TEXT,
                },
                {
                    "title": "Synthetic supplier oversight bulletin",
                    "link": "https://news.synthetic.test/a/supplier-bulletin",
                    "description": "A synthetic bulletin about supplier monitoring coverage.",
                    "published": "Sun, 01 Nov 2026 09:00:00 GMT",
                    "content": "Synthetic supplier monitoring coverage notes for third-party risk reviews.",
                },
            ],
        },
        "feed_behaviour": {"transient_failures": 0, "permanent_failure": False},
        "model": {
            "mode": "plan",
            "resolved_model": "synthetic/grc-plan-model-v1",
            "delay_seconds": 0,
            # A current-contract plan: narrative paragraphs plus finding headline and
            # significance, so parsing keeps it unchanged.
            "plan": narrated(
                {
                    "executive_brief": {"decision_frame": "exposure", "source_ids": [1]},
                    "regulatory_changes": [],
                    "control_implications": [
                        {
                            "control_id": "vulnerability_management",
                            "priority": "medium",
                            "source_ids": [1],
                            "focus": "deployed edge gateways",
                            "evidence_excerpt": EVIDENCE_TEXT,
                            "evidence_origin": "content",
                        }
                    ],
                    "industry_impacts": [],
                }
            ),
        },
    }


def write_fixture(directory: Path, fixture_id: str, fixture: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{fixture_id}.json"
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def variant(**changes) -> dict:
    """Return the model-plan fixture with nested keys replaced (``feed__link`` style)."""
    fixture = model_plan_fixture()
    for dotted, value in changes.items():
        target = fixture
        parts = dotted.split("__")
        for part in parts[:-1]:
            target = target[part]
        if value is _DELETE:
            target.pop(parts[-1], None)
        else:
            target[parts[-1]] = value
    return fixture


_DELETE = object()
DELETE = _DELETE
