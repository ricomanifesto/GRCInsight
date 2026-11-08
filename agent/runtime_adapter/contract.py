"""Versioned identity contract between GRCInsight reports and leased workflow runs.

Three identities, one binding each:

- input identity: ``input_digest``, SHA-256 of the frozen canonical submission;
- report identity: ``report_id``, a product-owned operation key and the Runtime
  idempotency key (derived from the input digest unless the caller supplies one);
- run identity: Runtime's ``run_id``, bound to the report after admission.

The frozen submission covers every admission-affecting field (product, workflow
name and version, attempt budget, feed URL, model configuration and synthetic
fixture identity). Admission carries product, workflow name and version,
``input_ref`` and ``max_attempts``. The adapter encodes ``input_ref`` values as strings.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping
from urllib.parse import urlsplit
import uuid

PRODUCT = "grcinsight"
WORKFLOW_NAME = "generate_report"
WORKFLOW_VERSION = "grc-report-runtime-v1"
SUPPORTED_WORKFLOW_VERSIONS = (WORKFLOW_VERSION,)

SUBMISSION_SCHEMA = "grcinsight.report-submission.v1"
INPUT_REF_SCHEMA = "grcinsight.report-input-ref.v1"
OUTPUT_REF_SCHEMA = "grcinsight.report-output-ref.v1"
RESULT_SCHEMA = "grcinsight.report-result.v1"

# Keep the frozen submission small; admission sends references to its contents.
MAX_FROZEN_INPUT_BYTES = 16 * 1024
MAX_ATTEMPTS_LIMIT = 10
MAX_TOKENS_LIMIT = 200_000
MAX_FOCUS_AREAS = 16
MAX_FOCUS_AREA_LENGTH = 128
MAX_FEED_URL_LENGTH = 2048
MAX_ERROR_SUMMARY = 512

# The MVP admits synthetic feeds only: RFC 2606 reserved names never resolve to a
# real publisher, so no workflow step can reach a live feed or regulatory API.
RESERVED_HOST_SUFFIXES = (".test", ".example", ".invalid")

OPERATION_KEY = re.compile(r"[a-z0-9][a-z0-9._-]{7,63}")
REPORT_ID = re.compile(r"[a-z0-9][a-z0-9._-]{7,63}")
FIXTURE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
MODEL_IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{1,255}")

RETRYABLE_ERROR_CODES = frozenset(
    {"dependency_unavailable", "dependency_timeout", "worker_error", "unknown"}
)
TERMINAL_ERROR_CODES = frozenset(
    {"invalid_input", "invalid_result", "unsupported_workflow", "side_effect_conflict"}
)

# WorkflowResponse.error.code -> Runtime error taxonomy. A failed response is never
# a Runtime success, even though the FastAPI route answers HTTP 200 for it.
WORKFLOW_ERROR_CODES = {
    "RSS_FETCH_FAILED": "dependency_unavailable",
    "FEED_IDENTITY_INVALID": "invalid_input",
    "NO_LINKED_ARTICLES": "invalid_input",
    "WORKFLOW_EXECUTION_ERROR": "worker_error",
}


class SubmissionError(ValueError):
    """The submission or its frozen bytes cannot be admitted or executed."""


class InputRefError(ValueError):
    """A claimed run's ``input_ref`` does not name a supported report input."""

    def __init__(self, message: str, code: str = "invalid_input"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class FrozenSubmission:
    frozen_input: bytes
    input_digest: str


@dataclass(frozen=True)
class InputRef:
    report_id: str
    input_digest: str


def _reject_floats(value: Any) -> None:
    if isinstance(value, float):
        raise SubmissionError("frozen submissions carry no floating-point values")
    if isinstance(value, Mapping):
        for item in value.values():
            _reject_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_floats(item)


def canonical_json(value: Any, *, allow_floats: bool = False) -> bytes:
    """Serialize deterministically: sorted keys, compact separators, UTF-8."""
    if not allow_floats:
        _reject_floats(value)
    try:
        text = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError) as error:
        raise SubmissionError(f"value is not canonical JSON: {error}") from error
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise SubmissionError(f"{field} must be an integer from {minimum} to {maximum}")
    return value


def reserved_synthetic_host(url: str) -> bool:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return any(host.endswith(suffix) for suffix in RESERVED_HOST_SUFFIXES)


def _feed_url(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_FEED_URL_LENGTH:
        raise SubmissionError("feed_url must be a bounded string")
    if re.search(r"[\s\x00-\x1f\x7f]", value):
        raise SubmissionError("feed_url must not contain whitespace or control characters")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError as error:
        raise SubmissionError("feed_url is not a valid URL") from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SubmissionError("feed_url must be an http(s) URL with a host")
    if parsed.username is not None or parsed.password is not None:
        raise SubmissionError("feed_url must be credential-free")
    if not reserved_synthetic_host(value):
        raise SubmissionError("feed_url must use a reserved synthetic host in this MVP")
    return value


def _config(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"model", "max_tokens", "focus_areas"}:
        raise SubmissionError("config must contain exactly model, max_tokens and focus_areas")
    model = value["model"]
    if not isinstance(model, str) or not MODEL_IDENTITY.fullmatch(model):
        raise SubmissionError("config.model is not a usable model identity")
    focus_areas = value["focus_areas"]
    if (
        not isinstance(focus_areas, (list, tuple))
        or len(focus_areas) > MAX_FOCUS_AREAS
        or any(
            not isinstance(area, str) or not area or len(area) > MAX_FOCUS_AREA_LENGTH
            for area in focus_areas
        )
    ):
        raise SubmissionError("config.focus_areas must be a short list of short strings")
    return {
        "model": model,
        "max_tokens": _strict_int(value["max_tokens"], "config.max_tokens", 1, MAX_TOKENS_LIMIT),
        "focus_areas": list(focus_areas),
    }


def build_submission(
    *,
    feed_url: Any,
    config: Any,
    fixture_id: Any,
    fixture_sha256: Any,
    max_attempts: Any,
    workflow_version: str = WORKFLOW_VERSION,
) -> dict[str, Any]:
    """Validate and assemble the complete admission identity of one report."""
    if workflow_version not in SUPPORTED_WORKFLOW_VERSIONS:
        raise SubmissionError("unsupported workflow version")
    if not isinstance(fixture_id, str) or not FIXTURE_ID.fullmatch(fixture_id):
        raise SubmissionError("fixture id must be a short lowercase slug")
    if not isinstance(fixture_sha256, str) or not SHA256_HEX.fullmatch(fixture_sha256):
        raise SubmissionError("fixture digest must be lowercase SHA-256 hex")
    submission = {
        "schema": SUBMISSION_SCHEMA,
        "product": PRODUCT,
        "workflow_name": WORKFLOW_NAME,
        "workflow_version": workflow_version,
        "max_attempts": _strict_int(max_attempts, "max_attempts", 1, MAX_ATTEMPTS_LIMIT),
        "feed_url": _feed_url(feed_url),
        "config": _config(config),
        "fixture": {"id": fixture_id, "sha256": fixture_sha256},
    }
    freeze(submission)
    return submission


def freeze(submission: Mapping[str, Any]) -> FrozenSubmission:
    frozen_input = canonical_json(submission)
    if len(frozen_input) > MAX_FROZEN_INPUT_BYTES:
        raise SubmissionError("frozen submission exceeds the size bound")
    return FrozenSubmission(frozen_input=frozen_input, input_digest=sha256_hex(frozen_input))


def load_frozen(frozen_input: bytes, expected_digest: str) -> dict[str, Any]:
    """Re-validate stored submission bytes before execution; never repair them."""
    if (
        not isinstance(frozen_input, (bytes, bytearray))
        or len(frozen_input) > MAX_FROZEN_INPUT_BYTES
    ):
        raise SubmissionError("frozen submission exceeds the size bound")
    if sha256_hex(bytes(frozen_input)) != expected_digest:
        raise SubmissionError("frozen submission does not match its input digest")
    try:
        submission = json.loads(frozen_input)
    except ValueError as error:
        raise SubmissionError("frozen submission is not JSON") from error
    if not isinstance(submission, dict) or submission.get("schema") != SUBMISSION_SCHEMA:
        raise SubmissionError("frozen submission has an unsupported schema")
    fixture = submission.get("fixture")
    rebuilt = build_submission(
        feed_url=submission.get("feed_url"),
        config=submission.get("config"),
        fixture_id=fixture.get("id") if isinstance(fixture, dict) else None,
        fixture_sha256=fixture.get("sha256") if isinstance(fixture, dict) else None,
        max_attempts=submission.get("max_attempts"),
        workflow_version=submission.get("workflow_version"),
    )
    if canonical_json(rebuilt) != bytes(frozen_input):
        raise SubmissionError("frozen submission is not in canonical form")
    return rebuilt


def derive_report_id(input_digest: str, operation_key: str | None = None) -> str:
    """MVP-local report identity; distinct from production ``GenerateReportID``."""
    if operation_key is None:
        return f"grc_{input_digest[:32]}"
    if not isinstance(operation_key, str) or not OPERATION_KEY.fullmatch(operation_key):
        raise SubmissionError(
            "operation key must be 8-64 lowercase letters, digits, '.', '_' or '-'"
        )
    return operation_key


def input_ref(report_id: str, input_digest: str) -> dict[str, str]:
    return {"schema": INPUT_REF_SCHEMA, "report_id": report_id, "input_digest": input_digest}


def parse_input_ref(value: Any) -> InputRef:
    if not isinstance(value, dict):
        raise InputRefError("input_ref must be an object")
    if value.get("schema") != INPUT_REF_SCHEMA and isinstance(value.get("schema"), str):
        if value["schema"].startswith("grcinsight.report-input-ref."):
            raise InputRefError("unsupported input_ref schema version", "unsupported_workflow")
    if set(value) != {"schema", "report_id", "input_digest"} or value["schema"] != INPUT_REF_SCHEMA:
        raise InputRefError("input_ref must contain exactly schema, report_id and input_digest")
    report_id, digest = value["report_id"], value["input_digest"]
    if not isinstance(report_id, str) or not REPORT_ID.fullmatch(report_id):
        raise InputRefError("input_ref.report_id is malformed")
    if not isinstance(digest, str) or not SHA256_HEX.fullmatch(digest):
        raise InputRefError("input_ref.input_digest is malformed")
    return InputRef(report_id=report_id, input_digest=digest)


def is_run_id(value: Any) -> bool:
    """A retained run binding must be Runtime's canonical lowercase UUID text."""
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def map_workflow_error(code: str | None) -> str:
    return WORKFLOW_ERROR_CODES.get(code or "", "worker_error")


def error_summary(report_id: str, domain_code: str, attempt: int) -> str:
    """Bounded failure summary: identifiers only, never URLs, exception text or content."""
    safe_code = re.sub(r"[^A-Za-z0-9_.-]", "_", domain_code)[:64]
    safe_report = re.sub(r"[^A-Za-z0-9_.-]", "_", report_id)[:64]
    return f"report_id={safe_report} code={safe_code} attempt={int(attempt)}"[:MAX_ERROR_SUMMARY]
