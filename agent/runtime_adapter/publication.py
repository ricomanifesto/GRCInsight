"""Publication eligibility from the existing site-report composer, unchanged.

``scripts/compose_site_report.py: compose_report`` is the oracle. It is applied
to the retained report record and either returns the composed Markdown or exits
with its refusal reason. Only a digest of the composed text is kept; nothing is
written under ``site/`` or anywhere else.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import runpy
from typing import Any, Callable

from runtime_adapter import contract
from runtime_adapter.store import ReportRecord

COMPOSER = Path(__file__).resolve().parents[2] / "scripts" / "compose_site_report.py"


@dataclass(frozen=True)
class PublicationResult:
    eligible: bool
    reason: str
    composed_sha256: str | None


@lru_cache(maxsize=1)
def _compose_report() -> Callable[[dict, str, str], str]:
    # Importing the composer defines functions only; ``main()`` (which writes
    # site files) is never called.
    return runpy.run_path(str(COMPOSER))["compose_report"]


def evaluate_publication(
    record: ReportRecord, submission: dict[str, Any] | None = None
) -> PublicationResult:
    if submission is None:
        try:
            submission = contract.load_frozen(record.frozen_input, record.input_digest)
        except contract.SubmissionError as error:
            return PublicationResult(
                False, f"committed evidence integrity violation: {error}", None
            )
    try:
        composed = _compose_report()(
            record.publication_document(), submission["feed_url"], submission["config"]["model"]
        )
    except SystemExit as refusal:
        return PublicationResult(False, str(refusal.code), None)
    return PublicationResult(True, "composed", contract.sha256_hex(composed.encode("utf-8")))


def publication_facts(result: PublicationResult) -> dict[str, Any]:
    return {
        "eligible": result.eligible,
        "reason": result.reason,
        "composed_sha256": result.composed_sha256,
    }
