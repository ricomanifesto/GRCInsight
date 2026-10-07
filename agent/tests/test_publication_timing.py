"""Event clocks must preserve precise chronology rather than mask time skew."""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from test_publication_state import history_for, manifest_bytes, publication_namespace

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/lambda-report-generation.yml"
SCRIPT = Path(__file__).resolve().parents[2] / "scripts/publication_state.py"


def test_event_clock_preserves_same_second_fractional_chronology(monkeypatch):
    namespace = publication_namespace()
    captured = datetime(2026, 10, 7, 12, 32, 15, 900000, tzinfo=timezone.utc)

    class Clock:
        @staticmethod
        def now(tz):
            assert tz is timezone.utc
            return captured

    capture = namespace["capture_event_timestamp"]
    with monkeypatch.context() as patch:
        patch.setitem(capture.__globals__, "datetime", Clock)
        event_at = capture()
    assert event_at == "2026-10-07T12:32:15.900000Z"
    state = namespace["build_published_state"](manifest_bytes("2026-10-07T12:32:15.899999Z"))
    assert namespace["state_event"](state, event_at)["event_at"] == event_at


def test_timestamp_cli_emits_only_precise_canonical_utc():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "timestamp"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z\n", result.stdout)
    assert result.stderr == ""


def test_real_clock_skew_still_fails_with_sanitized_precise_diagnostics():
    namespace = publication_namespace()
    # ISO accepts a newline as the date/time separator. Never echo that raw input.
    generated = "2026-10-07\n12:32:15.900001Z"
    state = namespace["build_published_state"](manifest_bytes(generated))
    with pytest.raises(namespace["PublicationStateError"]) as caught:
        namespace["state_event"](state, "2026-10-07T12:32:15.900000Z")
    diagnostic = str(caught.value)
    assert "publication event predates its report" in diagnostic
    assert "event_at=2026-10-07T12:32:15.900000Z" in diagnostic
    assert "report_generated_at=2026-10-07T12:32:15.900001Z" in diagnostic
    assert "\n" not in diagnostic


def test_fractional_ordering_still_rejects_stale_and_conflicting_events():
    namespace = publication_namespace()
    manifest = manifest_bytes("2026-10-07T12:32:15.100000Z")
    state = namespace["build_published_state"](manifest)
    latest = "2026-10-07T12:32:15.900001Z"
    history = history_for(namespace, state, latest)
    before = json.dumps(history, sort_keys=True)
    with pytest.raises(namespace["StalePublicationEvent"]):
        namespace["append_publication_event"](history, state, "2026-10-07T12:32:15.900000Z")
    assert json.dumps(history, sort_keys=True) == before
    assert namespace["append_publication_event"](history, state, latest) == history
    retained = namespace["build_retained_state"](manifest, latest, "provider_quota")
    with pytest.raises(namespace["PublicationStateError"]):
        namespace["append_publication_event"](history, retained, latest)
    assert json.dumps(history, sort_keys=True) == before


def test_workflow_captures_precise_time_after_composition_and_reuses_it_on_retry():
    workflow = WORKFLOW.read_text()
    retrieve = workflow.split("    - name: Retrieve generated report", 1)[1].split(
        "    - name: Persist retained publication state", 1
    )[0]
    capture = "PUBLISHED_AT=$(python3 scripts/publication_state.py timestamp)"
    assert workflow.count("PUBLISHED_AT=") == 1
    assert retrieve.index("python3 scripts/compose_site_report.py") < retrieve.index(capture)
    assert retrieve.index(capture) < retrieve.index("scripts/publication_state.py record-published")
    assert 'echo "published_at=$PUBLISHED_AT" >> "$GITHUB_OUTPUT"' in retrieve
    retry = workflow.split("    - name: Commit and push report", 1)[1]
    assert '--event-at "${{ steps.get-report.outputs.published_at }}"' in retry
    assert "publication_state.py timestamp" not in retry
