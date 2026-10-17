import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest
import httpx

from config.settings import settings
from core.relevance_benchmark import classification_metrics, run_comparison
from services.model_service import GRCModelService
from tests.test_relevance_policy import articles, result, service


def test_missing_predictions_count_against_recall_and_accuracy():
    metrics = classification_metrics(
        ["relevant", "relevant", "irrelevant"], ["relevant", None, "relevant"]
    )
    assert metrics["accuracy"] == 1 / 3
    assert metrics["relevant_recall"] == 0.5
    assert metrics["false_positive_rate"] == 1
    assert metrics["missing_predictions"] == 1


def test_replay_measures_actual_subset_fallback_and_alternates_order(monkeypatch):
    model = service(monkeypatch, "enabled")
    model._analyze_articles_with_model = AsyncMock(
        return_value={"grc_articles": [], "summary": {"grc_relevant_count": 0}}
    )
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("relevant", "insufficient_evidence"))
    )
    summary = asyncio.run(
        run_comparison(articles(), ["relevant", "irrelevant"], lambda: model, repeats=2)
    )
    assert summary["repeats"] == 2
    assert summary["decisions"]["fallback_batch_rate"] == 1
    assert summary["decisions"]["fallback_article_rate"] == 0.5
    assert summary["enabled"]["p50_seconds"] > 0
    # The insufficient-evidence position is kept, so the irrelevant case is selected.
    assert summary["enabled"]["accuracy"] == 0.5
    assert summary["decisions"]["accuracy"] == 0.5
    assert summary["decisions"]["predicted_insufficient_evidence"] == 2
    assert summary["runs"][0]["decision_predictions"] == [
        "relevant",
        "insufficient_evidence",
    ]
    assert summary["enabled"]["cost"] is None
    assert summary["decisions"]["cost"] == 0.0000084
    calls = model._analyze_articles_with_model.await_args_list
    assert [call.args[0] for call in calls] == [
        articles(),
        articles()[1:],
        articles()[1:],
        articles(),
    ]
    assert all(
        call.args == (articles(),) for call in model.relevance_client.classify.await_args_list
    )


def test_replay_counts_failed_subset_as_missing_predictions(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("relevant", "insufficient_evidence"))
    )
    model._analyze_articles_with_model.return_value = {"error": "unavailable"}
    summary = asyncio.run(
        run_comparison(articles(), ["relevant", "irrelevant"], lambda: model, repeats=1)
    )
    assert summary["enabled"]["missing_predictions"] == 2
    assert summary["enabled"]["relevant_recall"] == 0


def test_replay_scores_insufficient_evidence_decisions(monkeypatch):
    model = service(monkeypatch, "enabled")
    model.relevance_client.classify = AsyncMock(
        return_value=result(labels=("relevant", "insufficient_evidence"))
    )
    summary = asyncio.run(
        run_comparison(articles(), ["relevant", "insufficient_evidence"], lambda: model, repeats=1)
    )
    assert summary["decisions"]["accuracy"] == 1
    assert summary["decisions"]["predicted_insufficient_evidence"] == 1


def test_replay_requires_enabled_policy(monkeypatch):
    with pytest.raises(ValueError, match="enabled"):
        asyncio.run(
            run_comparison(
                articles(), ["relevant", "irrelevant"], lambda: service(monkeypatch, "off")
            )
        )


def test_replay_uses_independent_workflow_deadlines(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "grc_relevance_mode", "enabled")
    clock = [0.0]
    created = []
    requests = []

    async def complete(request):
        requests.append(request)
        clock[0] += 2
        return httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [{"message": {"content": "Analysis complete"}}],
            },
        )

    def factory():
        model = GRCModelService()
        model.client.clock = lambda: clock[0]
        model.client.total_timeout = 1
        model.client.transport = httpx.MockTransport(complete)
        assert model.relevance_client is not None
        monkeypatch.setattr(
            model.relevance_client, "classify", AsyncMock(return_value=result(probability=0.6))
        )
        created.append(model)
        return model

    summary = asyncio.run(
        run_comparison(articles(), ["relevant", "irrelevant"], factory, repeats=3)
    )
    assert len(created) == len(requests) == 6
    assert summary["legacy"]["missing_predictions"] == 0
    assert summary["enabled"]["missing_predictions"] == 0


def test_replay_defaults_to_validation_without_credentials_or_network(tmp_path):
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            [
                {"article": item.model_dump(mode="json"), "expected": label}
                for item, label in zip(articles(), ["relevant", "irrelevant"])
            ]
        )
    )
    script = Path(__file__).resolve().parents[2] / "scripts" / "benchmark_relevance.py"
    process = subprocess.run(
        [sys.executable, str(script), str(cases)], text=True, capture_output=True, check=True
    )
    report = json.loads(process.stdout)
    assert report == {"cases": 2, "status": "validated_only", "network_calls": 0}


# Offline corpus replay ----------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = REPO_ROOT / "docs" / "relevance-gate-spec.template.json"


def replay_inputs(cases=None):
    from core.relevance_benchmark import RecordedResponses, load_recordings
    from core.relevance_corpus import validate_corpus
    from tests.relevance_fixtures import corpus_lines, recordings_lines

    validation = validate_corpus(corpus_lines(cases))
    responses = RecordedResponses(load_recordings(recordings_lines(cases)))
    return validation, responses


def replay(validation, responses, **options):
    from core.relevance_benchmark import load_gate_spec, replay_corpus
    from tests.relevance_fixtures import BATCH_SIZE, FOCUS_AREAS

    options.setdefault("split", "development")
    options.setdefault("thresholds", [0.95])
    options.setdefault("gate_spec", load_gate_spec(TEMPLATE))
    return asyncio.run(
        replay_corpus(
            validation, responses, focus_areas=FOCUS_AREAS, batch_size=BATCH_SIZE, **options
        )
    )


def spec(**changes):
    value = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    for gate in value["gates"].values():
        for key in ("min_cases", "min_batches"):
            if key in gate:
                gate[key] = 1
    value.update(changes)
    return value


def test_committed_recordings_are_generated_from_code():
    from tests.relevance_fixtures import RECORDINGS, recordings_lines

    assert RECORDINGS.read_text(encoding="utf-8").splitlines() == recordings_lines()


def test_wilson_interval_bounds():
    from core.relevance_benchmark import wilson_interval

    assert wilson_interval(0, 0) is None

    def lower(successes, total):
        interval = wilson_interval(successes, total)
        assert interval is not None and interval[1] <= 1
        return interval[0]

    # At a 0.90 bound, 50 cases allow no miss and 60 allow one.
    assert lower(49, 50) == pytest.approx(0.8950, abs=1e-4)
    assert lower(50, 50) == pytest.approx(0.9287, abs=1e-4)
    assert lower(59, 60) == pytest.approx(0.9115, abs=1e-4)
    assert lower(0, 10) == 0


def test_replay_runs_the_enabled_route_offline_and_reports_denominators():
    validation, responses = replay_inputs()
    rows, summary = replay(validation, responses)
    assert summary["network_calls"] == 0
    assert len(responses.requests) == 2 and responses.missing == []
    assert [row["case_id"] for row in rows] == [f"dev-0{number}" for number in range(1, 9)]
    result = summary["results"][0]
    assert result["route_mix"]["dispositions"] == {
        "accepted_relevant": 3,
        "accepted_irrelevant": 2,
        "uncertain_kept": 2,
        "insufficient_evidence_kept": 1,
    }
    workflow = result["all_cases"]["selections"]["workflow_selected"]
    # Insufficient-evidence references are reported apart from recall and false positives.
    assert workflow["insufficient_evidence"] == {
        "total": 1,
        "selected": 1,
        "not_selected": 0,
        "unknown": 0,
    }
    assert workflow["recall"]["total"] == 3
    assert result["gate_eligible"]["cases"] == 6
    # One request has no cost receipt, so the total stays unknown.
    assert result["requests"]["missing_usage"] == 1
    assert result["requests"]["cost"] is None
    assert result["gates"]["overall"] == "remain_off"
    assert result["gates"]["gates"]["G1"]["verdict"] == "insufficient_evidence"
    assert result["gates"]["gates"]["G5"]["verdict"] == "pass"
    for row in rows:
        assert "rationale" not in json.dumps(row)


def test_missing_recordings_count_as_unknown_in_denominators():
    from core.relevance_benchmark import RecordedResponses

    validation, responses = replay_inputs()
    first = next(iter(responses.recordings))
    trimmed = {key: value for key, value in responses.recordings.items() if key != first}
    rows, summary = replay(validation, RecordedResponses(trimmed))
    result = summary["results"][0]
    assert result["requests"]["missing_recordings"] == 1
    assert result["route_mix"]["legacy_full_reasons"] == {"jev_http_error": 1}
    missing = [row for row in rows if row["batch"] == 0]
    assert all(row["model_selected"] is None for row in missing)
    assert all(row["workflow_selected"] is not False for row in missing)
    recall = result["all_cases"]["selections"]["model_selected"]["recall"]
    assert recall["total"] == 3 and recall["successes"] == 1
    assert result["gates"]["gates"]["G8"]["verdict"] == "insufficient_evidence"
    # A request with no recording has no cost receipt either.
    assert result["requests"]["missing_usage"] == 2
    assert result["batches"][0]["missing_usage"] == 1
    assert result["requests"]["cost"] is None


def test_missing_receipts_from_unrecorded_requests_fail_the_cost_gate():
    from core.relevance_benchmark import RecordedResponses

    # Only the holdout batch has full cost receipts; drop its recording.
    validation, responses = replay_inputs()
    holdout_request = list(responses.recordings)[-1]
    trimmed = {key: value for key, value in responses.recordings.items() if key != holdout_request}
    frozen = accepted_spec(validation)
    _, summary = replay(validation, RecordedResponses(trimmed), split="holdout", gate_spec=frozen)
    result = summary["results"][0]
    assert result["requests"] == {
        "replayed": 1,
        "missing_recordings": 1,
        "missing_usage": 1,
        "cost": None,
    }
    assert result["gates"]["gates"]["G10"]["verdict"] == "fail"


def test_cases_without_records_stay_in_denominators(monkeypatch):
    from core import relevance_benchmark

    async def lose_records(self, articles):
        await relevance_benchmark.GRCModelService.analyze_articles_for_grc(self, articles)
        self.last_selection_records = None
        return {}

    monkeypatch.setattr(relevance_benchmark._ReplayService, "replay", lose_records)
    validation, responses = replay_inputs()
    rows, summary = replay(validation, responses)
    assert [row["case_id"] for row in rows] == [f"dev-0{number}" for number in range(1, 9)]
    assert all(row["model_selected"] is None for row in rows)
    assert all(row["reason"] == "missing_record" for row in rows)
    assert all(row["workflow_selected"] is not False for row in rows)
    result = summary["results"][0]
    assert result["all_cases"]["selections"]["model_selected"]["recall"]["total"] == 3
    assert result["gates"]["gates"]["G5"]["verdict"] == "fail"


def test_threshold_sweeps_are_development_only():
    validation, responses = replay_inputs()
    _, summary = replay(validation, responses, thresholds=[0.75, 0.95])
    by_threshold = {item["threshold"]: item for item in summary["results"]}
    assert by_threshold[0.75]["route_mix"]["dispositions"]["accepted_irrelevant"] == 3
    assert (
        by_threshold[0.75]["candidate_fingerprint"] != by_threshold[0.95]["candidate_fingerprint"]
    )
    frozen = spec(status="accepted")
    with pytest.raises(ValueError, match="only the frozen threshold"):
        replay(validation, responses, split="holdout", thresholds=[0.75, 0.95], gate_spec=frozen)


def accepted_spec(validation):
    from services.relevance_selection import candidate_fingerprint
    from tests.relevance_fixtures import BATCH_SIZE, FOCUS_AREAS

    from core.relevance_benchmark import evaluator_sha256

    return spec(
        status="accepted",
        batch_size=BATCH_SIZE,
        evaluator_sha256=evaluator_sha256(),
        candidate_fingerprint=candidate_fingerprint(0.95, FOCUS_AREAS, batch_size=BATCH_SIZE),
        holdout_sha256=validation.holdout_sha256,
    )


def test_holdout_replay_requires_a_frozen_matching_spec():
    validation, responses = replay_inputs()
    frozen = accepted_spec(validation)
    rows, summary = replay(validation, responses, split="holdout", gate_spec=frozen)
    assert summary["verdict_scope"] == "frozen holdout"
    assert {row["split"] for row in rows} == {"holdout"}
    refusals = [
        (None, "accepted gate spec"),
        (spec(), "accepted gate spec"),
        ({**frozen, "candidate_fingerprint": "0" * 64}, "fingerprint"),
        ({**frozen, "holdout_sha256": "0" * 64}, "holdout hash"),
        ({**frozen, "batch_size": 12}, "batch size"),
        # Changed corpus or scoring code cannot re-judge a frozen holdout.
        ({**frozen, "evaluator_sha256": "0" * 64}, "evaluator"),
    ]
    for gate_spec, message in refusals:
        with pytest.raises(ValueError, match=message):
            replay(validation, responses, split="holdout", gate_spec=gate_spec)
    # The template is a proposal; it can never authorize a holdout replay.
    with pytest.raises(ValueError, match="accepted gate spec"):
        replay(validation, responses, split="holdout")


def test_changed_holdout_labels_are_refused_after_freezing():
    from tests.relevance_fixtures import case_dicts

    validation, responses = replay_inputs()
    frozen = accepted_spec(validation)
    cases = case_dicts()
    next(case for case in cases if case["case_id"] == "hold-02")["labels"][0]["label"] = "relevant"
    changed, changed_responses = replay_inputs(cases)
    with pytest.raises(ValueError, match="holdout hash"):
        replay(changed, changed_responses, split="holdout", gate_spec=frozen)


def test_replayed_requests_never_contain_labels_or_adjudication():
    from tests.relevance_fixtures import case_dicts

    cases = case_dicts()
    for case in cases:
        for label in case["labels"]:
            label["rationale"] = "SENTINEL-RATIONALE-7f3a"
            label["labeler"] = "sentinel-labeler-7f3a"
        if case["adjudication"]:
            case["adjudication"]["rationale"] = "SENTINEL-ADJUDICATION-7f3a"
    validation, responses = replay_inputs(cases)
    replay(validation, responses)
    replay(validation, responses, split="holdout", gate_spec=accepted_spec(validation))
    assert len(responses.requests) == 3
    for raw in responses.requests:
        for sentinel in (b"7f3a", b"dev-0", b"hold-0", b"evt-", b"single_reviewed"):
            assert sentinel not in raw


def test_gate_verdicts_need_minimum_samples_and_stay_off_on_any_failure():
    from core.relevance_benchmark import evaluate_gates

    def row(reference, selected, stratum="local_negative", critical=False):
        return {
            "gate_eligible": True,
            "reference_label": reference,
            "workflow_selected": selected,
            "stratum": stratum,
            "critical": critical,
        }

    batch = {
        "route": "decision",
        "reason": None,
        "missing_recordings": 0,
        "requests": 1,
        "missing_usage": 0,
        "invariant_failures": [],
    }
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    passing = [row("relevant", True, critical=True)] * 120
    result = evaluate_gates(passing, [batch] * 25, template)
    assert result["gates"]["G1"]["verdict"] == "pass"
    assert result["gates"]["G2"]["verdict"] == "pass"
    assert result["gates"]["G3"]["verdict"] == "pass"
    assert result["gates"]["G9"]["verdict"] == "not_evaluated"
    # Latency, deployment and test-owned gates are outside replay: still off.
    assert result["overall"] == "remain_off"

    small = evaluate_gates(passing[:10], [batch], template)
    assert small["gates"]["G2"]["verdict"] == "insufficient_evidence"
    assert small["gates"]["G8"]["verdict"] == "insufficient_evidence"

    # A single critical miss fails regardless of sample size.
    missed = evaluate_gates([row("relevant", None, critical=True)], [batch], template)
    assert missed["gates"]["G1"]["verdict"] == "fail"
    assert missed["overall"] == "remain_off"

    unbilled = {**batch, "missing_usage": 1}
    assert evaluate_gates(passing, [unbilled] * 25, template)["gates"]["G10"]["verdict"] == "fail"
    broken = {**batch, "invariant_failures": ["records are not total and ordered"]}
    failed = evaluate_gates(passing, [broken] * 25, template)
    assert failed["gates"]["G5"]["verdict"] == "fail"
    assert failed["gates"]["G8"]["verdict"] == "fail"


def test_gate_template_is_a_proposal():
    from core.relevance_benchmark import load_gate_spec

    template = load_gate_spec(TEMPLATE)
    assert template["status"] == "proposed, not accepted"
    assert template["candidate_fingerprint"] is None
    assert template["evaluator_sha256"] is None
    assert template["holdout_sha256"] is None
    assert template["gates"]["G2"]["min_lower_bound"] == 0.9


def test_invalid_corpus_or_recordings_are_refused():
    from core.relevance_benchmark import load_recordings
    from core.relevance_corpus import validate_corpus
    from tests.relevance_fixtures import case_dicts, corpus_lines, recordings_lines

    cases = case_dicts()
    cases[0]["split"] = "test"
    _, responses = replay_inputs()
    with pytest.raises(ValueError, match="Corpus is invalid"):
        replay(validate_corpus(corpus_lines(cases)), responses)
    line = json.loads(recordings_lines()[0])
    for bad in (
        {**line, "headers": {}},
        {**line, "status_code": "200"},
        {**line, "request_sha256": "z" * 64},
    ):
        with pytest.raises(ValueError, match="expected"):
            load_recordings([json.dumps(bad)])
    with pytest.raises(ValueError, match="duplicate"):
        load_recordings([json.dumps(line)] * 2)


def test_script_replays_corpus_offline(tmp_path):
    from tests.relevance_fixtures import CORPUS, RECORDINGS

    script = REPO_ROOT / "scripts" / "benchmark_relevance.py"
    env = {key: value for key, value in os.environ.items() if key != "OPENROUTER_API_KEY"}
    validated = subprocess.run(
        [sys.executable, str(script), "--corpus", str(CORPUS)],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    assert json.loads(validated.stdout)["status"] == "validated_only"
    process = subprocess.run(
        [
            sys.executable,
            str(script),
            "--corpus",
            str(CORPUS),
            "--recordings",
            str(RECORDINGS),
            "--batch-size",
            "4",
            "--output-dir",
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    report = json.loads(process.stdout)
    assert report["status"] == "replayed"
    assert report["network_calls"] == 0
    assert report["overall"] == ["remain_off"]
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["gate_spec"]["file"] == "relevance-gate-spec.template.json"
    assert len((tmp_path / "selections.jsonl").read_text(encoding="utf-8").splitlines()) == 8
    refused = subprocess.run(
        [sys.executable, str(script), "--corpus", str(CORPUS), "--run-paid"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert refused.returncode == 2
