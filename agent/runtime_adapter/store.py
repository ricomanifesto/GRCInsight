"""Durable product outcome store for Runtime-executed GRC reports.

One SQLite file (WAL, busy timeout) owned by the product CLIs. Runtime never
reads it and the product never writes Runtime tables. The record shape mirrors
the existing report and article records; identity derivation and the MVP-only
columns (input/run binding, ownership fence, terminal outcome) do not, and this
is not a DynamoDB conformance claim.

Protocol, all single-row compare-and-set updates inside ``BEGIN IMMEDIATE``:

- bind: ``run_id`` moves only from NULL to one run; status leaves ``pending`` only
  while the report is open, so a late bind never reopens a terminal report;
- register: an attempt records its Runtime ``lease_version`` as the product-side
  owner, and only a strictly newer version can replace it;
- commit: report, metadata and articles are written once, by the registered
  owner, while the report is open;
- cancel: marks an open report cancelled.

Commit and cancel serialize on one row, so exactly one wins. Registration happens
after the Runtime claim, so there is a window in which an older lease is still
the registered owner (documented in the worker). Triggers make terminal rows and
committed articles immutable.
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from runtime_adapter import contract

STORE_SCHEMA_VERSION = "grcinsight.runtime-store.v1"
ARTICLE_CONTENT_LIMIT = 50_000  # The existing article record keeps at most 50k characters.

SCHEMA = """
CREATE TABLE IF NOT EXISTS store_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    source_url TEXT NOT NULL DEFAULT '',
    generated_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT,
    input_digest TEXT NOT NULL,
    frozen_input BLOB NOT NULL,
    workflow_version TEXT NOT NULL,
    max_attempts INTEGER NOT NULL,
    admission_started_at TEXT,
    run_id TEXT UNIQUE,
    cancel_requested_at TEXT,
    terminal_outcome TEXT
        CHECK (terminal_outcome IS NULL OR terminal_outcome IN ('completed', 'failed', 'cancelled')),
    result_digest TEXT,
    owner_lease_version INTEGER NOT NULL DEFAULT 0,
    owner_lease_owner TEXT,
    owner_attempt INTEGER,
    committed_attempt INTEGER,
    committed_lease_version INTEGER,
    committed_lease_owner TEXT,
    runtime_error_code TEXT,
    failure_reason TEXT,
    conflict_existing_run_id TEXT,
    CHECK ((terminal_outcome IS 'completed') = (result_digest IS NOT NULL)),
    CHECK ((terminal_outcome IS 'cancelled') = (cancel_requested_at IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS articles (
    article_id TEXT PRIMARY KEY,
    numeric_id INTEGER NOT NULL,
    report_id TEXT NOT NULL REFERENCES reports (report_id),
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    source TEXT NOT NULL,
    digest_url TEXT NOT NULL,
    published TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    has_grc_content INTEGER NOT NULL CHECK (has_grc_content IN (0, 1)),
    regulations TEXT NOT NULL,
    frameworks TEXT NOT NULL,
    industries TEXT NOT NULL,
    regulatory_bodies TEXT NOT NULL,
    UNIQUE (report_id, url),
    UNIQUE (report_id, position)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    lease_version INTEGER NOT NULL,
    lease_owner TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    outcome TEXT,
    runtime_error_code TEXT
);

CREATE TABLE IF NOT EXISTS boundary_invocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    lease_version INTEGER NOT NULL,
    lease_owner TEXT NOT NULL,
    boundary TEXT NOT NULL,
    invoked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publication_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL,
    result_digest TEXT,
    eligible INTEGER NOT NULL CHECK (eligible IN (0, 1)),
    reason TEXT NOT NULL,
    composed_sha256 TEXT,
    evaluated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submission_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('product', 'runtime')),
    existing_input_digest TEXT,
    requested_input_digest TEXT NOT NULL,
    existing_run_id TEXT,
    recorded_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS reports_terminal_immutable
BEFORE UPDATE ON reports
WHEN OLD.terminal_outcome IS NOT NULL AND NOT (
    -- The only change to a terminal row: an admission already in flight when a
    -- cancel won may still bind its run so the reader can show the Runtime side.
    OLD.terminal_outcome = 'cancelled' AND OLD.run_id IS NULL AND NEW.run_id IS NOT NULL
    AND NEW.report_id IS OLD.report_id AND NEW.title IS OLD.title
    AND NEW.content IS OLD.content AND NEW.status IS OLD.status
    AND NEW.source_url IS OLD.source_url AND NEW.generated_at IS OLD.generated_at
    AND NEW.created_at IS OLD.created_at AND NEW.updated_at IS OLD.updated_at
    AND NEW.metadata IS OLD.metadata AND NEW.input_digest IS OLD.input_digest
    AND NEW.frozen_input IS OLD.frozen_input AND NEW.workflow_version IS OLD.workflow_version
    AND NEW.max_attempts IS OLD.max_attempts
    AND NEW.admission_started_at IS OLD.admission_started_at
    AND NEW.cancel_requested_at IS OLD.cancel_requested_at
    AND NEW.terminal_outcome IS OLD.terminal_outcome AND NEW.result_digest IS OLD.result_digest
    AND NEW.owner_lease_version IS OLD.owner_lease_version
    AND NEW.owner_lease_owner IS OLD.owner_lease_owner AND NEW.owner_attempt IS OLD.owner_attempt
    AND NEW.committed_attempt IS OLD.committed_attempt
    AND NEW.committed_lease_version IS OLD.committed_lease_version
    AND NEW.committed_lease_owner IS OLD.committed_lease_owner
    AND NEW.runtime_error_code IS OLD.runtime_error_code
    AND NEW.failure_reason IS OLD.failure_reason
    AND NEW.conflict_existing_run_id IS OLD.conflict_existing_run_id
)
BEGIN
    SELECT RAISE(ABORT, 'terminal report is immutable');
END;

CREATE TRIGGER IF NOT EXISTS articles_require_open_report
BEFORE INSERT ON articles
WHEN (SELECT terminal_outcome FROM reports WHERE report_id = NEW.report_id) IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'articles of a terminal report are immutable');
END;

CREATE TRIGGER IF NOT EXISTS articles_no_update
BEFORE UPDATE ON articles
BEGIN
    SELECT RAISE(ABORT, 'articles are immutable');
END;

CREATE TRIGGER IF NOT EXISTS articles_no_delete
BEFORE DELETE ON articles
BEGIN
    SELECT RAISE(ABORT, 'articles are immutable');
END;
"""

REPORT_FIELDS = ("title", "content", "status", "source_url", "generated_at", "metadata")
ARTICLE_LIST_FIELDS = ("regulations", "frameworks", "industries", "regulatory_bodies")

# SQLite does not enforce declared column types, so a corrupted row can hold any
# storage class. Retained values are checked against these before any conversion
# (``bytes()``), JSON parsing or digest serialization.
REPORT_TEXT = (
    "report_id",
    "title",
    "content",
    "status",
    "source_url",
    "created_at",
    "updated_at",
    "input_digest",
    "workflow_version",
)
REPORT_OPTIONAL_TEXT = (
    "generated_at",
    "metadata",
    "admission_started_at",
    "run_id",
    "cancel_requested_at",
    "terminal_outcome",
    "result_digest",
    "owner_lease_owner",
    "committed_lease_owner",
    "runtime_error_code",
    "failure_reason",
    "conflict_existing_run_id",
)
REPORT_INTEGER = ("max_attempts", "owner_lease_version")
REPORT_OPTIONAL_INTEGER = ("owner_attempt", "committed_attempt", "committed_lease_version")
ARTICLE_TEXT = (
    "article_id",
    "report_id",
    "title",
    "url",
    "content",
    "summary",
    "source",
    "digest_url",
    "published",
    "created_at",
    "updated_at",
    *ARTICLE_LIST_FIELDS,
)
ARTICLE_INTEGER = ("numeric_id", "position", "has_grc_content")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def fnv1a_32(data: str) -> int:
    """The FNV-1a hash used for the existing article ``numeric_id``."""
    value = 2166136261
    for byte in data.encode("utf-8"):
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return value


def retained_type_problems(
    row: Any,
    *,
    text: tuple[str, ...] = (),
    optional_text: tuple[str, ...] = (),
    integer: tuple[str, ...] = (),
    optional_integer: tuple[str, ...] = (),
    label: str = "",
) -> list[str]:
    """Columns whose retained SQLite storage class is not the committed one."""
    problems = []

    def check(name: str, expected: type, optional: bool) -> None:
        value = row[name]
        if value is None and optional:
            return
        if type(value) is not expected:
            kind = "text" if expected is str else "integer"
            problems.append(
                f"{label}{name} has retained type {type(value).__name__}, expected {kind}"
            )

    for name in text:
        check(name, str, False)
    for name in optional_text:
        check(name, str, True)
    for name in integer:
        check(name, int, False)
    for name in optional_integer:
        check(name, int, True)
    return problems


def report_type_problems(row: Any) -> list[str]:
    problems = retained_type_problems(
        row,
        text=REPORT_TEXT,
        optional_text=REPORT_OPTIONAL_TEXT,
        integer=REPORT_INTEGER,
        optional_integer=REPORT_OPTIONAL_INTEGER,
    )
    if not isinstance(row["frozen_input"], (bytes, bytearray, memoryview)):
        problems.append(
            f"frozen_input has retained type {type(row['frozen_input']).__name__}, expected blob"
        )
    return problems


def _evidence_value(value: Any) -> Any:
    """Render retained bytes as a descriptor so evidence is always JSON-safe."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        data = bytes(value)
        return {"retained_type": "bytes", "length": len(data), "sha256": contract.sha256_hex(data)}
    return value


def _text_sha256(value: Any) -> str | None:
    if isinstance(value, str):
        return contract.sha256_hex(value.encode("utf-8"))
    if isinstance(value, (bytes, bytearray, memoryview)):
        return contract.sha256_hex(bytes(value))
    return None


def _digest(
    report: dict[str, Any], *, input_digest: str, run_id: str, articles: list[dict[str, Any]]
) -> str:
    """SHA-256 over the canonical committed report, its binding and its ordered articles."""
    document = {
        "schema": contract.RESULT_SCHEMA,
        "binding": {"input_digest": input_digest, "run_id": run_id},
        "report": report,
        "articles": articles,
    }
    return contract.sha256_hex(contract.canonical_json(document, allow_floats=True))


def article_id(report_id: str, url: str) -> str:
    """Report-scoped article identity; production prefixes a wall-clock date instead."""
    return "a_" + contract.sha256_hex(f"{report_id}\x00{url}".encode("utf-8"))[:24]


@dataclass(frozen=True)
class ReportRecord:
    report_id: str
    title: str
    content: str
    status: str
    source_url: str
    generated_at: str | None
    created_at: str
    updated_at: str
    metadata: dict[str, Any] | None
    input_digest: str
    frozen_input: bytes
    workflow_version: str
    max_attempts: int
    admission_started_at: str | None
    run_id: str | None
    cancel_requested_at: str | None
    terminal_outcome: str | None
    result_digest: str | None
    owner_lease_version: int
    owner_lease_owner: str | None
    owner_attempt: int | None
    committed_attempt: int | None
    committed_lease_version: int | None
    committed_lease_owner: str | None
    runtime_error_code: str | None
    failure_reason: str | None
    conflict_existing_run_id: str | None
    raw_metadata: str | None = field(default=None, repr=False)
    metadata_error: str | None = None
    retained_type_errors: tuple[str, ...] = ()

    def publication_document(self) -> dict[str, Any]:
        """The stored-report shape the existing publication composer reads."""
        return {
            "status": self.status,
            "title": self.title,
            "content": self.content,
            "generated_at": self.generated_at,
            "metadata": self.metadata or {},
        }

    def facts(self) -> dict[str, Any]:
        metadata = self.metadata or {}
        return {
            "report_id": self.report_id,
            "status": self.status,
            "terminal_outcome": self.terminal_outcome,
            "run_id": self.run_id,
            "input_digest": self.input_digest,
            "result_digest": self.result_digest,
            "workflow_version": self.workflow_version,
            "max_attempts": self.max_attempts,
            "cancel_requested_at": self.cancel_requested_at,
            "admission_started_at": self.admission_started_at,
            "owner_lease_version": self.owner_lease_version,
            "owner_lease_owner": self.owner_lease_owner,
            "committed_attempt": self.committed_attempt,
            "committed_lease_version": self.committed_lease_version,
            "committed_lease_owner": self.committed_lease_owner,
            "runtime_error_code": self.runtime_error_code,
            "failure_reason": self.failure_reason,
            "conflict_existing_run_id": self.conflict_existing_run_id,
            "title": self.title,
            "generated_at": self.generated_at,
            "analysis_mode": metadata.get("analysis_mode"),
            "fallback_reason": metadata.get("fallback_reason"),
            "source_name": metadata.get("source_name"),
            "source_url": metadata.get("source_url"),
            "source_home_url": metadata.get("source_home_url"),
            "source_issue_date": metadata.get("source_issue_date"),
            "source_issue_url": metadata.get("source_issue_url"),
            "requested_model": metadata.get("requested_model"),
            "resolved_model": metadata.get("resolved_model"),
            "article_count": metadata.get("article_count"),
        }


class CorruptEvidence(ValueError):
    """A retained row cannot be read back in its committed shape."""


@dataclass(frozen=True)
class EvidenceCheck:
    """Integrity of one committed outcome, checked from the retained rows."""

    intact: bool
    problems: list[str]
    recomputed_result_digest: str | None
    submission: dict[str, Any] | None


@dataclass(frozen=True)
class FreezeResult:
    outcome: str  # created | existing | conflict
    record: ReportRecord


@dataclass(frozen=True)
class CommitResult:
    outcome: str  # committed | terminal | cancelled | superseded | unbound
    result_digest: str | None


class ReportStore:
    def __init__(self, path: str | Path, *, read_only: bool = False):
        self.path = Path(path)
        if read_only:
            # Evidence reads: no schema creation, no writes.
            self._db = sqlite3.connect(
                f"file:{self.path}?mode=ro", uri=True, timeout=10.0, isolation_level=None
            )
            self._db.row_factory = sqlite3.Row
            self._db.execute("PRAGMA busy_timeout=10000")
            return
        self._db = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA busy_timeout=10000")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(SCHEMA)
        self._db.execute(
            "INSERT OR IGNORE INTO store_meta (key, value) VALUES ('schema', ?)",
            (STORE_SCHEMA_VERSION,),
        )
        stored = self._db.execute("SELECT value FROM store_meta WHERE key = 'schema'").fetchone()
        if stored["value"] != STORE_SCHEMA_VERSION:
            raise RuntimeError("product store schema version is not supported")

    def close(self) -> None:
        self._db.close()

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield self._db
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        self._db.execute("COMMIT")

    def _row(self, report_id: str) -> sqlite3.Row | None:
        return self._db.execute(
            "SELECT * FROM reports WHERE report_id = ?", (report_id,)
        ).fetchone()

    @staticmethod
    def _record(row: sqlite3.Row) -> ReportRecord:
        values = dict(row)
        type_errors = report_type_problems(values)
        raw_metadata = values.pop("metadata")
        frozen_input = values["frozen_input"]
        # Never convert a retained value of the wrong class: bytes(7) would allocate
        # zero bytes and bytes(-1) would raise. Text is tampered data and is kept
        # as its encoding; anything else becomes empty bytes, which cannot match
        # the input digest.
        if isinstance(frozen_input, (bytes, bytearray, memoryview)):
            values["frozen_input"] = bytes(frozen_input)
        elif isinstance(frozen_input, str):
            values["frozen_input"] = frozen_input.encode("utf-8")
        else:
            values["frozen_input"] = b""
        metadata, metadata_error = None, None
        if raw_metadata is not None and not isinstance(raw_metadata, str):
            metadata_error = (
                f"metadata has retained type {type(raw_metadata).__name__}, expected text"
            )
        elif raw_metadata is not None:
            try:
                parsed = json.loads(raw_metadata)
            except (TypeError, ValueError):
                metadata_error = "metadata is not JSON"
            else:
                if isinstance(parsed, dict):
                    metadata = parsed
                else:
                    metadata_error = "metadata is not a JSON object"
        return ReportRecord(
            **values,
            metadata=metadata,
            raw_metadata=raw_metadata,
            metadata_error=metadata_error,
            retained_type_errors=tuple(type_errors),
        )

    def get(self, report_id: str) -> ReportRecord | None:
        row = self._row(report_id)
        return self._record(row) if row is not None else None

    def terminal_outcome(self, report_id: str) -> str | None:
        row = self._db.execute(
            "SELECT terminal_outcome FROM reports WHERE report_id = ?", (report_id,)
        ).fetchone()
        return row["terminal_outcome"] if row is not None else None

    # Producer --------------------------------------------------------------
    def freeze(self, report_id: str, frozen: contract.FrozenSubmission) -> FreezeResult:
        submission = json.loads(frozen.frozen_input)
        now = utc_now()
        with self._write() as db:
            row = self._row(report_id)
            if row is None:
                db.execute(
                    "INSERT INTO reports (report_id, status, created_at, updated_at, input_digest,"
                    " frozen_input, workflow_version, max_attempts) VALUES (?, 'pending', ?, ?, ?, ?, ?, ?)",
                    (
                        report_id,
                        now,
                        now,
                        frozen.input_digest,
                        frozen.frozen_input,
                        submission["workflow_version"],
                        submission["max_attempts"],
                    ),
                )
                outcome = "created"
            elif row["input_digest"] == frozen.input_digest:
                outcome = "existing"
            else:
                db.execute(
                    "INSERT INTO submission_conflicts (report_id, source, existing_input_digest,"
                    " requested_input_digest, existing_run_id, recorded_at) VALUES (?, 'product', ?, ?, ?, ?)",
                    (report_id, row["input_digest"], frozen.input_digest, row["run_id"], now),
                )
                outcome = "conflict"
        record = self.get(report_id)
        assert record is not None
        return FreezeResult(outcome, record)

    def begin_admission(self, report_id: str) -> str:
        """Decide whether to call Runtime; record that an admission is in flight."""
        with self._write() as db:
            row = self._row(report_id)
            if row is None:
                raise KeyError(report_id)
            if row["terminal_outcome"] == "cancelled":
                return "cancelled"
            if row["run_id"] is not None:
                return "bound"
            if row["terminal_outcome"] is not None:
                return "terminal"
            db.execute(
                "UPDATE reports SET admission_started_at = COALESCE(admission_started_at, ?)"
                " WHERE report_id = ? AND terminal_outcome IS NULL",
                (utc_now(), report_id),
            )
            return "admit"

    def bind_run(self, report_id: str, run_id: str) -> str:
        with self._write() as db:
            row = self._row(report_id)
            if row is None:
                raise KeyError(report_id)
            if row["run_id"] == run_id:
                return "already_bound"
            if row["run_id"] is not None:
                return "conflict"
            if row["terminal_outcome"] is None:
                updated = db.execute(
                    "UPDATE reports SET run_id = ?, updated_at = ?,"
                    " status = CASE WHEN status = 'pending' THEN 'processing' ELSE status END"
                    " WHERE report_id = ? AND run_id IS NULL AND terminal_outcome IS NULL",
                    (run_id, utc_now(), report_id),
                )
            else:
                updated = db.execute(
                    "UPDATE reports SET run_id = ? WHERE report_id = ? AND run_id IS NULL"
                    " AND terminal_outcome = 'cancelled'",
                    (run_id, report_id),
                )
            return "bound" if updated.rowcount == 1 else "conflict"

    def record_runtime_conflict(
        self, report_id: str, requested_input_digest: str, existing_run_id: str | None
    ) -> None:
        now = utc_now()
        with self._write() as db:
            db.execute(
                "INSERT INTO submission_conflicts (report_id, source, existing_input_digest,"
                " requested_input_digest, existing_run_id, recorded_at) VALUES (?, 'runtime', NULL, ?, ?, ?)",
                (report_id, requested_input_digest, existing_run_id, now),
            )
            db.execute(
                "UPDATE reports SET conflict_existing_run_id = ?, updated_at = ?"
                " WHERE report_id = ? AND terminal_outcome IS NULL",
                (existing_run_id, now, report_id),
            )

    def cancel(self, report_id: str) -> str:
        now = utc_now()
        with self._write() as db:
            row = self._row(report_id)
            if row is None:
                return "unknown_report"
            if row["terminal_outcome"] == "completed":
                return "rejected_already_committed"
            if row["terminal_outcome"] == "failed":
                return "rejected_already_terminal"
            if row["terminal_outcome"] == "cancelled":
                return "already_cancelled"
            updated = db.execute(
                "UPDATE reports SET cancel_requested_at = ?, status = 'cancelled',"
                " terminal_outcome = 'cancelled', updated_at = ?"
                " WHERE report_id = ? AND terminal_outcome IS NULL",
                (now, now, report_id),
            )
            assert updated.rowcount == 1
            if row["run_id"] is None:
                if row["admission_started_at"] is not None:
                    return "cancelled_during_admission"
                return "cancelled_before_admission"
            if row["owner_lease_version"] > 0:
                return "cancelled_during_execution"
            return "cancelled_pending_runtime"

    # Worker ----------------------------------------------------------------
    def register_owner(
        self, report_id: str, *, run_id: str, attempt: int, lease_version: int, lease_owner: str
    ) -> str:
        with self._write() as db:
            row = self._row(report_id)
            if row is None or row["run_id"] != run_id:
                return "unbound"
            if row["terminal_outcome"] is not None:
                return "terminal"
            updated = db.execute(
                "UPDATE reports SET owner_lease_version = ?, owner_lease_owner = ?, owner_attempt = ?,"
                " updated_at = ? WHERE report_id = ? AND run_id = ? AND terminal_outcome IS NULL"
                " AND owner_lease_version < ?",
                (lease_version, lease_owner, attempt, utc_now(), report_id, run_id, lease_version),
            )
            return "registered" if updated.rowcount == 1 else "superseded"

    def commit_completed(
        self,
        report_id: str,
        *,
        run_id: str,
        attempt: int,
        lease_version: int,
        lease_owner: str,
        report: dict[str, Any],
        articles: list[dict[str, Any]],
    ) -> CommitResult:
        """Write the complete report and article set once, as the registered owner."""
        now = utc_now()
        with self._write() as db:
            row = self._row(report_id)
            if row is None or row["run_id"] != run_id:
                return CommitResult("unbound", None)
            if row["terminal_outcome"] == "cancelled":
                return CommitResult("cancelled", None)
            if row["terminal_outcome"] is not None:
                return CommitResult("terminal", row["result_digest"])
            if (
                row["owner_lease_version"] != lease_version
                or row["owner_lease_owner"] != lease_owner
            ):
                return CommitResult("superseded", None)
            for position, article in enumerate(articles):
                url = article["url"]
                db.execute(
                    "INSERT INTO articles (article_id, numeric_id, report_id, position, title, url,"
                    " content, summary, source, digest_url, published, created_at, updated_at,"
                    " has_grc_content, regulations, frameworks, industries, regulatory_bodies)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        article_id(report_id, url),
                        fnv1a_32(url) if url else 0,
                        report_id,
                        position,
                        article["title"],
                        url,
                        article["content"][:ARTICLE_CONTENT_LIMIT],
                        article["summary"],
                        article["source"],
                        article["digest_url"],
                        article["published"],
                        now,
                        now,
                        1 if article["has_grc_content"] else 0,
                        *(
                            contract.canonical_json(list(article[name])).decode("utf-8")
                            for name in ARTICLE_LIST_FIELDS
                        ),
                    ),
                )
            metadata_text = contract.canonical_json(report["metadata"], allow_floats=True).decode(
                "utf-8"
            )
            persisted_articles = db.execute(
                "SELECT * FROM articles WHERE report_id = ? ORDER BY position", (report_id,)
            ).fetchall()
            digest = _digest(
                {
                    "report_id": report_id,
                    "title": report["title"],
                    "content": report["content"],
                    "status": "completed",
                    "source_url": report["source_url"],
                    "generated_at": report["generated_at"],
                    "created_at": row["created_at"],
                    "updated_at": now,
                    "metadata": json.loads(metadata_text),
                },
                input_digest=row["input_digest"],
                run_id=run_id,
                articles=[self._article(article) for article in persisted_articles],
            )
            updated = db.execute(
                "UPDATE reports SET title = ?, content = ?, status = 'completed', source_url = ?,"
                " generated_at = ?, metadata = ?, updated_at = ?, terminal_outcome = 'completed',"
                " result_digest = ?, committed_attempt = ?, committed_lease_version = ?,"
                " committed_lease_owner = ? WHERE report_id = ? AND run_id = ?"
                " AND terminal_outcome IS NULL AND cancel_requested_at IS NULL"
                " AND owner_lease_version = ? AND owner_lease_owner = ?",
                (
                    report["title"],
                    report["content"],
                    report["source_url"],
                    report["generated_at"],
                    metadata_text,
                    now,
                    digest,
                    attempt,
                    lease_version,
                    lease_owner,
                    report_id,
                    run_id,
                    lease_version,
                    lease_owner,
                ),
            )
            if updated.rowcount != 1:
                raise RuntimeError("commit predicate changed inside an exclusive transaction")
            # Bind the digest to the rows exactly as persisted; a mismatch rolls back.
            if self._result_digest(db, report_id) != digest:
                raise RuntimeError("persisted report does not match its result digest")
        return CommitResult("committed", digest)

    def commit_failed(self, report_id: str, *, run_id: str, error_code: str, reason: str) -> str:
        """Record a terminal failure that Runtime has already confirmed."""
        now = utc_now()
        with self._write() as db:
            row = self._row(report_id)
            if row is None or row["run_id"] != run_id:
                return "unbound"
            updated = db.execute(
                "UPDATE reports SET status = 'failed', terminal_outcome = 'failed',"
                " runtime_error_code = ?, failure_reason = ?, updated_at = ?"
                " WHERE report_id = ? AND run_id = ? AND terminal_outcome IS NULL",
                (error_code, reason[:512], now, report_id, run_id),
            )
            return "committed" if updated.rowcount == 1 else "terminal"

    # Evidence --------------------------------------------------------------
    def _result_digest(self, db: sqlite3.Connection, report_id: str) -> str | None:
        """Recompute the digest from persisted rows; None when they cannot be read back."""
        row = db.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        if row is None or row["terminal_outcome"] != "completed" or row["metadata"] is None:
            return None
        rows = db.execute(
            "SELECT * FROM articles WHERE report_id = ? ORDER BY position", (report_id,)
        ).fetchall()
        if report_type_problems(row):
            return None
        try:
            metadata = json.loads(row["metadata"])
            articles = [self._article(article) for article in rows]
        except (TypeError, ValueError):
            return None
        try:
            return self._digest_from(row, metadata, articles)
        except (TypeError, ValueError):  # includes SubmissionError from canonical JSON
            return None

    @staticmethod
    def _digest_from(row: sqlite3.Row, metadata: Any, articles: list[dict[str, Any]]) -> str:
        return _digest(
            {
                "report_id": row["report_id"],
                "title": row["title"],
                "content": row["content"],
                "status": row["status"],
                "source_url": row["source_url"],
                "generated_at": row["generated_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "metadata": metadata,
            },
            input_digest=row["input_digest"],
            run_id=row["run_id"],
            articles=articles,
        )

    @staticmethod
    def _article(row: sqlite3.Row) -> dict[str, Any]:
        article = dict(row)
        type_errors = retained_type_problems(
            article, text=ARTICLE_TEXT, integer=ARTICLE_INTEGER, label="article "
        )
        if type_errors:
            raise CorruptEvidence(f"{type_errors[0]} (position {article['position']!r})")
        article["has_grc_content"] = bool(article["has_grc_content"])
        for name in ARTICLE_LIST_FIELDS:
            try:
                value = json.loads(article[name])
            except (TypeError, ValueError) as error:
                raise CorruptEvidence(
                    f"article {article['position']} {name} is not JSON"
                ) from error
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise CorruptEvidence(
                    f"article {article['position']} {name} is not a list of strings"
                )
            article[name] = value
        return article

    def recompute_result_digest(self, report_id: str) -> str | None:
        return self._result_digest(self._db, report_id)

    def articles(self, report_id: str) -> list[dict[str, Any]]:
        """Committed articles in order; raises ``CorruptEvidence`` for unreadable rows."""
        rows = self._db.execute(
            "SELECT * FROM articles WHERE report_id = ? ORDER BY position", (report_id,)
        ).fetchall()
        return [self._article(row) for row in rows]

    def article_count(self, report_id: str) -> int:
        row = self._db.execute(
            "SELECT COUNT(*) AS n FROM articles WHERE report_id = ?", (report_id,)
        ).fetchone()
        return int(row["n"])

    def verify_committed(self, report_id: str) -> EvidenceCheck:
        """Check a committed outcome against its retained input, binding and rows.

        Used before any reuse and on every read. It never repairs anything: a
        problem means the outcome must not be re-acknowledged or published.
        """
        record = self.get(report_id)
        if record is None or record.terminal_outcome != "completed":
            return EvidenceCheck(False, ["report has no committed result"], None, None)
        problems: list[str] = list(record.retained_type_errors)
        submission = None
        try:
            submission = contract.load_frozen(record.frozen_input, record.input_digest)
        except contract.SubmissionError as error:
            problems.append(f"retained frozen input: {error}")
        if not record.run_id:
            problems.append("committed report has no bound run")
        elif isinstance(record.run_id, str) and not contract.is_run_id(record.run_id):
            problems.append("retained run_id is not a Runtime run UUID")
        if record.status != "completed" or record.result_digest is None:
            problems.append("committed report status or digest is missing")
        metadata = record.metadata
        if record.metadata_error or metadata is None:
            problems.append(record.metadata_error or "metadata is missing")
        try:
            articles = self.articles(report_id)
        except CorruptEvidence as error:
            problems.append(str(error))
            articles = None
        if metadata is not None:
            mode = metadata.get("analysis_mode")
            if mode not in ("model", "fallback"):
                problems.append("metadata.analysis_mode is not model or fallback")
            if mode == "model" and (
                not isinstance(metadata.get("report_plan"), dict)
                or not isinstance(metadata.get("resolved_model"), str)
                or not metadata.get("resolved_model")
            ):
                problems.append("model-mode metadata lacks its plan or resolved model")
            if mode == "fallback" and not metadata.get("fallback_reason"):
                problems.append("fallback metadata lacks its fallback reason")
            if metadata.get("source_url") != record.source_url:
                problems.append("metadata.source_url disagrees with the report record")
            if submission is not None:
                if metadata.get("source_url") != submission["feed_url"]:
                    problems.append("metadata.source_url does not match the frozen feed URL")
                if metadata.get("requested_model") != submission["config"]["model"]:
                    problems.append("metadata.requested_model does not match the frozen model")
            if not isinstance(metadata.get("source_articles"), list):
                problems.append("metadata.source_articles is not a list")
            if articles is not None and metadata.get("article_count") != len(articles):
                problems.append("metadata.article_count does not match the retained articles")
        if articles is not None:
            if not articles:
                problems.append("committed report retains no articles")
            if [article["position"] for article in articles] != list(range(len(articles))):
                problems.append("article positions are not contiguous")
            if any(
                article["article_id"] != article_id(report_id, article["url"])
                for article in articles
            ):
                problems.append("article identity does not match its report and URL")
        recomputed = self._result_digest(self._db, report_id)
        if recomputed is None or recomputed != record.result_digest:
            problems.append("result digest does not match the retained record")
        return EvidenceCheck(not problems, problems, recomputed, submission)

    def output_ref(self, report_id: str) -> dict[str, str]:
        """The exact Runtime output binding for a committed report, from stored rows."""
        record = self.get(report_id)
        if record is None or record.terminal_outcome != "completed" or record.result_digest is None:
            raise ValueError("report has no committed result")
        article_count = self._db.execute(
            "SELECT COUNT(*) AS n FROM articles WHERE report_id = ?", (report_id,)
        ).fetchone()["n"]
        return {
            "schema": contract.OUTPUT_REF_SCHEMA,
            "report_id": record.report_id,
            "run_id": record.run_id or "",
            "input_digest": record.input_digest,
            "result_digest": record.result_digest,
            "status": "completed",
            "analysis_mode": str((record.metadata or {}).get("analysis_mode")),
            "article_count": str(article_count),
            "committed_attempt": str(record.committed_attempt),
            "committed_lease_version": str(record.committed_lease_version),
        }

    def record_attempt(
        self, report_id: str, *, run_id: str, attempt: int, lease_version: int, lease_owner: str
    ) -> int:
        with self._write() as db:
            cursor = db.execute(
                "INSERT INTO attempts (report_id, run_id, attempt, lease_version, lease_owner,"
                " started_at) VALUES (?, ?, ?, ?, ?, ?)",
                (report_id, run_id, attempt, lease_version, lease_owner, utc_now()),
            )
            assert cursor.lastrowid is not None
            return cursor.lastrowid

    def finish_attempt(
        self, attempt_id: int, outcome: str, runtime_error_code: str | None = None
    ) -> None:
        with self._write() as db:
            db.execute(
                "UPDATE attempts SET ended_at = ?, outcome = ?, runtime_error_code = ?"
                " WHERE id = ? AND ended_at IS NULL",
                (utc_now(), outcome, runtime_error_code, attempt_id),
            )

    def attempts(self, report_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT * FROM attempts WHERE report_id = ? ORDER BY id", (report_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def record_boundary(
        self,
        report_id: str,
        *,
        run_id: str,
        attempt: int,
        lease_version: int,
        lease_owner: str,
        boundary: str,
    ) -> None:
        with self._write() as db:
            db.execute(
                "INSERT INTO boundary_invocations (report_id, run_id, attempt, lease_version,"
                " lease_owner, boundary, invoked_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (report_id, run_id, attempt, lease_version, lease_owner, boundary, utc_now()),
            )

    def boundary_counts(self, report_id: str) -> Counter:
        rows = self._db.execute(
            "SELECT boundary, COUNT(*) AS n FROM boundary_invocations WHERE report_id = ?"
            " GROUP BY boundary",
            (report_id,),
        ).fetchall()
        return Counter({row["boundary"]: row["n"] for row in rows})

    def boundary_invocations(self, report_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT * FROM boundary_invocations WHERE report_id = ? ORDER BY id", (report_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def record_publication(
        self,
        report_id: str,
        *,
        result_digest: str | None,
        eligible: bool,
        reason: str,
        composed_sha256: str | None,
    ) -> None:
        with self._write() as db:
            db.execute(
                "INSERT INTO publication_evidence (report_id, result_digest, eligible, reason,"
                " composed_sha256, evaluated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    report_id,
                    result_digest,
                    1 if eligible else 0,
                    reason,
                    composed_sha256,
                    utc_now(),
                ),
            )

    def publication_evidence(self, report_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT * FROM publication_evidence WHERE report_id = ? ORDER BY id", (report_id,)
        ).fetchall()
        return [{**dict(row), "eligible": bool(row["eligible"])} for row in rows]

    def conflicts(self, report_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT * FROM submission_conflicts WHERE report_id = ? ORDER BY id", (report_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def dump(self, report_id: str) -> dict[str, Any]:
        """Evidence view of every product row for one report; never raises on corruption."""
        record = self.get(report_id)
        if record is None:
            return {"report": None}
        facts = record.facts()
        try:
            articles: list[dict[str, Any]] = self.articles(report_id)
            article_error = None
        except CorruptEvidence as error:
            articles = [
                {key: _evidence_value(value) for key, value in dict(row).items()}
                for row in self._db.execute(
                    "SELECT * FROM articles WHERE report_id = ? ORDER BY position", (report_id,)
                ).fetchall()
            ]
            article_error = str(error)
        integrity = None
        if record.terminal_outcome == "completed":
            check = self.verify_committed(report_id)
            integrity = {"intact": check.intact, "problems": check.problems}
        return {
            "report": {
                **{key: _evidence_value(value) for key, value in facts.items()},
                "metadata": record.metadata,
                "metadata_error": record.metadata_error,
                "retained_type_errors": list(record.retained_type_errors),
                "content_sha256": _text_sha256(record.content),
                "frozen_input_sha256": contract.sha256_hex(record.frozen_input),
            },
            "recomputed_result_digest": self.recompute_result_digest(report_id),
            "integrity": integrity,
            "article_error": article_error,
            "articles": [
                {key: value for key, value in article.items() if key != "content"}
                | {"content_sha256": _text_sha256(article["content"])}
                for article in articles
            ],
            "attempts": self.attempts(report_id),
            "boundary_counts": dict(self.boundary_counts(report_id)),
            "boundary_invocations": self.boundary_invocations(report_id),
            "publication_evidence": self.publication_evidence(report_id),
            "conflicts": self.conflicts(report_id),
        }
