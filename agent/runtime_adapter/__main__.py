"""Command line for the Runtime MVP: submit, cancel, work, read, reconcile, dump.

Every command prints one JSON receipt on stdout. Fault flags are for local
recovery demonstrations only, default off, and are listed in the receipt:

- ``--fault crash-after-runtime-submit`` (submit): exit before binding the run;
- ``--pause-before-runtime-submit PATH`` (submit): wait for PATH before POST;
- ``--fault crash-after-commit`` (work): exit after the product commit, before
  Runtime ``complete``;
- ``--pause-before-register PATH`` / ``--pause-before-commit PATH`` (work):
  write ``PATH.reached`` and wait for PATH. The before-commit pause stands in
  for a stalled worker: its heartbeat is suspended until the commit attempt;
- ``--fault mutate-response=<kind>`` (work): alter the completed response
  before validation (``source-url``, ``requested-model``, ``analysis-mode``).

A simulated crash exits with status 86 without any cleanup call.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

from runtime_adapter.client import RuntimeClient, RuntimeClientError
from runtime_adapter.contract import SubmissionError
from runtime_adapter.producer import ProducerHooks, cancel_report, submit_report
from runtime_adapter.reader import read_report, reconcile_report
from runtime_adapter.store import ReportStore
from runtime_adapter.worker import (
    GRCWorker,
    WorkerConfigurationError,
    WorkerHooks,
    WorkerSettings,
)

CRASH_EXIT = 86
DEFAULT_MODEL = "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
MUTATIONS = {
    "source-url": lambda response: setattr(
        response.metadata, "source_url", "https://feeds.synthetic.test/mutated"
    ),
    "requested-model": lambda response: setattr(
        response.metadata, "requested_model", "openrouter/mutated/model"
    ),
    "analysis-mode": lambda response: setattr(response.metadata, "analysis_mode", None),
}


def _emit(receipt: Any) -> None:
    sys.stdout.write(json.dumps(receipt, sort_keys=True, default=str) + "\n")
    sys.stdout.flush()


def _crash(name: str):
    def crash(*_args: Any) -> None:
        sys.stdout.write(json.dumps({"kind": "simulated_crash", "fault": name}) + "\n")
        sys.stdout.flush()
        os._exit(CRASH_EXIT)

    return crash


def _wait_for_barrier(barrier: Path, timeout: float) -> bool:
    Path(f"{barrier}.reached").write_text(str(os.getpid()), encoding="utf-8")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if barrier.exists():
            return True
        time.sleep(0.02)
    return False


def _pause(barrier: Path, timeout: float, *, stall_heartbeat: bool):
    def pause(ctx) -> None:
        if stall_heartbeat:
            ctx.suspend_heartbeat()
        released = _wait_for_barrier(barrier, timeout)
        ctx.receipt.setdefault("pauses", []).append({"barrier": barrier.name, "released": released})

    return pause


def _worker_hooks(args: argparse.Namespace) -> WorkerHooks:
    hooks = WorkerHooks()
    names: list[str] = []
    for fault in args.fault or []:
        if fault == "crash-after-commit":
            hooks.after_commit = _crash(fault)
        elif fault.startswith("mutate-response="):
            kind = fault.split("=", 1)[1]
            mutate = MUTATIONS[kind]

            def apply(response, mutate=mutate):
                mutate(response)
                return response

            hooks.mutate_response = apply
        else:
            raise SystemExit(f"unknown worker fault: {fault}")
        names.append(fault)
    if args.pause_before_register:
        hooks.before_register = _pause(
            Path(args.pause_before_register), args.barrier_timeout, stall_heartbeat=False
        )
        names.append("pause-before-register")
    if args.pause_before_commit:
        hooks.before_commit = _pause(
            Path(args.pause_before_commit), args.barrier_timeout, stall_heartbeat=True
        )
        names.append("pause-before-commit")
    hooks.names = tuple(names)
    return hooks


def _producer_hooks(args: argparse.Namespace) -> ProducerHooks:
    hooks = ProducerHooks()
    names: list[str] = []
    for fault in args.fault or []:
        if fault != "crash-after-runtime-submit":
            raise SystemExit(f"unknown submit fault: {fault}")
        hooks.after_runtime_submit = _crash(fault)
        names.append(fault)
    if args.pause_before_runtime_submit:
        barrier = Path(args.pause_before_runtime_submit)

        def pause_submit(report_id: str) -> None:
            _wait_for_barrier(barrier, args.barrier_timeout)

        hooks.before_runtime_submit = pause_submit
        names.append("pause-before-runtime-submit")
    hooks.names = tuple(names)
    return hooks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m runtime_adapter")
    commands = parser.add_subparsers(dest="command", required=True)

    def common(command: argparse.ArgumentParser, *, runtime: bool = True) -> None:
        command.add_argument("--store", required=True, type=Path)
        if runtime:
            command.add_argument("--runtime-url", required=True)
        command.add_argument("--barrier-timeout", type=float, default=60.0)

    submit = commands.add_parser("submit")
    common(submit)
    submit.add_argument("--feed-url", required=True)
    submit.add_argument("--fixture-dir", required=True, type=Path)
    submit.add_argument("--fixture-id", required=True)
    submit.add_argument("--model", default=DEFAULT_MODEL)
    submit.add_argument("--max-tokens", type=int, default=16000)
    submit.add_argument("--focus-area", action="append", default=[])
    submit.add_argument("--max-attempts", type=int, default=3)
    submit.add_argument("--operation-key")
    submit.add_argument("--prepare-only", action="store_true")
    submit.add_argument("--fault", action="append")
    submit.add_argument("--pause-before-runtime-submit")

    cancel = commands.add_parser("cancel")
    common(cancel, runtime=False)
    cancel.add_argument("--runtime-url")
    cancel.add_argument("--report-id", required=True)

    work = commands.add_parser("work")
    common(work)
    work.add_argument("--fixture-dir", required=True, type=Path)
    work.add_argument("--lease-seconds", type=int, default=15)
    work.add_argument("--heartbeat-seconds", type=float)
    work.add_argument("--attempt-timeout", type=float, default=120.0)
    work.add_argument("--max-claims", type=int, default=1)
    work.add_argument("--lease-owner")
    work.add_argument("--fault", action="append")
    work.add_argument("--pause-before-register")
    work.add_argument("--pause-before-commit")

    for name in ("read", "reconcile"):
        command = commands.add_parser(name)
        common(command)
        command.add_argument("--report-id", required=True)
        if name == "read":
            command.add_argument("--no-publication", action="store_true")

    dump = commands.add_parser("dump")
    common(dump, runtime=False)
    dump.add_argument("--report-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    store = ReportStore(args.store, read_only=args.command == "dump")
    runtime = RuntimeClient(args.runtime_url) if getattr(args, "runtime_url", None) else None
    try:
        if args.command == "submit":
            try:
                receipt = submit_report(
                    store,
                    runtime,
                    feed_url=args.feed_url,
                    config={
                        "model": args.model,
                        "max_tokens": args.max_tokens,
                        "focus_areas": args.focus_area,
                    },
                    fixture_dir=args.fixture_dir,
                    fixture_id=args.fixture_id,
                    max_attempts=args.max_attempts,
                    operation_key=args.operation_key,
                    prepare_only=args.prepare_only,
                    hooks=_producer_hooks(args),
                )
            except SubmissionError as error:
                _emit({"kind": "grc_submit_receipt", "outcome": "rejected", "reason": str(error)})
                return 2
            _emit(receipt)
            return 0
        if args.command == "cancel":
            _emit(cancel_report(store, args.report_id, runtime))
            return 0
        if args.command == "work":
            worker = GRCWorker(
                store,
                runtime,
                fixture_dir=args.fixture_dir,
                settings=WorkerSettings(
                    lease_seconds=args.lease_seconds,
                    heartbeat_seconds=args.heartbeat_seconds,
                    attempt_timeout_seconds=args.attempt_timeout,
                ),
                hooks=_worker_hooks(args),
                lease_owner=args.lease_owner,
            )
            receipts = []
            try:
                for _ in range(max(1, args.max_claims)):
                    receipt = worker.execute_one()
                    receipts.append(receipt)
                    if receipt["outcome"] == "idle":
                        break
            except WorkerConfigurationError as error:
                _emit({"kind": "grc_worker_receipt", "outcome": "refused", "reason": str(error)})
                return 2
            _emit(
                {
                    "kind": "grc_worker_session",
                    "lease_owner": worker.lease_owner,
                    "receipts": receipts,
                }
            )
            return 0
        if args.command == "read":
            _emit(read_report(store, runtime, args.report_id, evaluate=not args.no_publication))
            return 0
        if args.command == "dump":
            _emit(
                {
                    "kind": "grc_product_dump",
                    "report_id": args.report_id,
                    **store.dump(args.report_id),
                }
            )
            return 0
        _emit(reconcile_report(store, runtime, args.report_id))
        return 0
    except RuntimeClientError as error:
        _emit({"kind": "runtime_unavailable", "command": args.command, "code": error.code})
        return 3
    finally:
        if runtime is not None:
            runtime.close()
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
