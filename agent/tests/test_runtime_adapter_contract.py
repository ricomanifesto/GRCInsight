import json
from typing import Any

import pytest

from runtime_adapter import contract
from runtime_adapter.contract import SubmissionError


def submission(**overrides):
    fields: dict[str, Any] = {
        "feed_url": "https://feeds.synthetic.test/grc/feed.xml",
        "config": {"model": "openrouter/example/model", "max_tokens": 16000, "focus_areas": []},
        "fixture_id": "model-plan",
        "fixture_sha256": "a" * 64,
        "max_attempts": 3,
    }
    fields.update(overrides)
    return contract.build_submission(**fields)


def test_canonical_json_is_key_order_independent_and_refuses_floats():
    assert contract.canonical_json({"b": 1, "a": [2, "x"]}) == contract.canonical_json(
        {"a": [2, "x"], "b": 1}
    )
    assert contract.canonical_json({"a": "é"}) == '{"a":"é"}'.encode("utf-8")
    with pytest.raises(SubmissionError):
        contract.canonical_json({"a": 0.5})


def test_submission_freezes_the_complete_admission_identity():
    base = contract.freeze(submission()).input_digest
    changes = [
        {"feed_url": "https://feeds.synthetic.test/grc/other.xml"},
        {"config": {"model": "openrouter/example/other", "max_tokens": 16000, "focus_areas": []}},
        {"config": {"model": "openrouter/example/model", "max_tokens": 8000, "focus_areas": []}},
        {
            "config": {
                "model": "openrouter/example/model",
                "max_tokens": 16000,
                "focus_areas": ["x"],
            }
        },
        {"fixture_id": "model-plan-2"},
        {"fixture_sha256": "b" * 64},
        {"max_attempts": 2},
    ]
    digests = {contract.freeze(submission(**change)).input_digest for change in changes}
    assert base not in digests
    assert len(digests) == len(changes)
    frozen = json.loads(contract.freeze(submission()).frozen_input)
    assert frozen["product"] == contract.PRODUCT
    assert frozen["workflow_name"] == contract.WORKFLOW_NAME
    assert frozen["workflow_version"] == contract.WORKFLOW_VERSION


def test_workflow_version_is_part_of_identity_and_must_be_supported(monkeypatch):
    with pytest.raises(SubmissionError, match="workflow version"):
        submission(workflow_version="grc-report-runtime-v0")
    monkeypatch.setattr(
        contract,
        "SUPPORTED_WORKFLOW_VERSIONS",
        (contract.WORKFLOW_VERSION, "grc-report-runtime-v2"),
    )
    assert (
        contract.freeze(submission()).input_digest
        != contract.freeze(submission(workflow_version="grc-report-runtime-v2")).input_digest
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"feed_url": "https://feeds.example.com/feed.xml"},
        {"feed_url": "https://user:pass@feeds.synthetic.test/feed.xml"},
        {"feed_url": "ftp://feeds.synthetic.test/feed.xml"},
        {"feed_url": "https://feeds.synthetic.test/a b"},
        {"config": {"model": "openrouter/x", "max_tokens": True, "focus_areas": []}},
        {"config": {"model": "openrouter/x", "max_tokens": 10, "focus_areas": [], "extra": 1}},
        {"config": {"model": "bad model", "max_tokens": 10, "focus_areas": []}},
        {"config": {"model": "openrouter/x", "max_tokens": 0, "focus_areas": []}},
        {"config": {"model": "openrouter/x", "max_tokens": 10, "focus_areas": [3]}},
        {"fixture_id": "../escape"},
        {"fixture_sha256": "z" * 64},
        {"max_attempts": 0},
        {"max_attempts": 11},
        {"max_attempts": True},
    ],
)
def test_submission_rejects_malformed_fields_before_admission(overrides):
    with pytest.raises(SubmissionError):
        submission(**overrides)


def test_frozen_submission_is_size_bounded():
    huge = {"model": "openrouter/x", "max_tokens": 10, "focus_areas": ["x" * 120] * 16}
    contract.freeze(submission(config=huge))
    oversized = {"model": "openrouter/x", "max_tokens": 10, "focus_areas": ["x" * 128] * 200}
    with pytest.raises(SubmissionError):
        submission(config=oversized)


def test_load_frozen_rejects_tampered_or_oversized_bytes():
    frozen = contract.freeze(submission())
    assert contract.load_frozen(frozen.frozen_input, frozen.input_digest)["max_attempts"] == 3
    tampered = frozen.frozen_input.replace(b'"max_attempts":3', b'"max_attempts":4')
    with pytest.raises(SubmissionError, match="digest"):
        contract.load_frozen(tampered, frozen.input_digest)
    oversized = b" " * (contract.MAX_FROZEN_INPUT_BYTES + 1)
    with pytest.raises(SubmissionError, match="bound"):
        contract.load_frozen(oversized, contract.sha256_hex(oversized))


def test_report_identity_defaults_to_input_digest_and_validates_operation_keys():
    digest = contract.freeze(submission()).input_digest
    assert contract.derive_report_id(digest) == f"grc_{digest[:32]}"
    assert contract.derive_report_id(digest, "weekly-2026-11-01") == "weekly-2026-11-01"
    for key in ("", "short", "UPPER-case-key", "x" * 65, "has space key", "../../escape-key"):
        with pytest.raises(SubmissionError):
            contract.derive_report_id(digest, key)


def test_input_ref_is_string_only_and_strictly_parsed():
    ref = contract.input_ref("weekly-2026-11-01", "c" * 64)
    assert ref == {
        "schema": contract.INPUT_REF_SCHEMA,
        "report_id": "weekly-2026-11-01",
        "input_digest": "c" * 64,
    }
    assert all(isinstance(value, str) for value in ref.values())
    parsed = contract.parse_input_ref(ref)
    assert (parsed.report_id, parsed.input_digest) == ("weekly-2026-11-01", "c" * 64)

    invalid = [
        None,
        [],
        {**ref, "extra": "x"},
        {key: value for key, value in ref.items() if key != "input_digest"},
        {**ref, "input_digest": 7},
        {**ref, "input_digest": "short"},
        {**ref, "report_id": "Bad Id"},
    ]
    for value in invalid:
        with pytest.raises(contract.InputRefError) as error:
            contract.parse_input_ref(value)
        assert error.value.code == "invalid_input"
    with pytest.raises(contract.InputRefError) as error:
        contract.parse_input_ref({**ref, "schema": "grcinsight.report-input-ref.v9"})
    assert error.value.code == "unsupported_workflow"


def test_workflow_failures_map_to_runtime_taxonomy_without_success():
    assert contract.map_workflow_error("RSS_FETCH_FAILED") == "dependency_unavailable"
    assert contract.map_workflow_error("FEED_IDENTITY_INVALID") == "invalid_input"
    assert contract.map_workflow_error("NO_LINKED_ARTICLES") == "invalid_input"
    assert contract.map_workflow_error("WORKFLOW_EXECUTION_ERROR") == "worker_error"
    assert contract.map_workflow_error("SOMETHING_NEW") == "worker_error"
    assert contract.map_workflow_error(None) == "worker_error"
    assert contract.TERMINAL_ERROR_CODES == {
        "invalid_input",
        "invalid_result",
        "unsupported_workflow",
        "side_effect_conflict",
    }


def test_error_summary_is_bounded_and_carries_identifiers_only():
    summary = contract.error_summary("weekly-2026-11-01", "RSS_FETCH_FAILED", 2)
    assert summary == "report_id=weekly-2026-11-01 code=RSS_FETCH_FAILED attempt=2"
    long = contract.error_summary("r" * 64, "https://feeds.synthetic.test/" + "x" * 900, 1)
    assert len(long) <= 512
    assert "https://" not in long
