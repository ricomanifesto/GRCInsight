#!/usr/bin/env python3
"""A bounded read of the U.S. Federal Register into a small public data file.

The file records which final and proposed federal rules name a security term in
their title, as the register's public API listed them at one stated time. It is
official metadata only: nothing is generated, and nothing here decides what a
document requires or when it takes effect.

One validator guards both ends. The read never writes a file the validator
rejects, and the site build omits the register lane when the file is absent or
invalid. A failed read leaves the previous file byte-identical and exits 0.

Standard library only. One host, no redirects, at most two pages, a size cap per
response, one retry per request, and a whole-command deadline on a monotonic
clock.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import sys
import tempfile
import threading
import time
from typing import Any, Callable, Sequence
from urllib.parse import urlencode, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "agent"))

from core.regulatory_dates import federal_register_api_url  # noqa: E402

SCHEMA = "grcinsight-regulatory-register/1"
HOST = "www.federalregister.gov"
ENDPOINT = f"https://{HOST}/api/v1/documents.json"
SOURCE_NAME = "U.S. Federal Register"
TYPES = ("Rule", "Proposed Rule")
API_TYPES = ("RULE", "PRORULE")
TERMS = (
    "cybersecurity",
    "cyber incident",
    "information security",
    "data security",
    "data breach",
    "breach notification",
)
MATCH = "title contains a term, case-insensitive, at word boundaries"
FIELDS = (
    "document_number",
    "title",
    "type",
    "action",
    "publication_date",
    "effective_on",
    "comments_close_on",
    "html_url",
    "agencies",
    "docket_ids",
    "regulation_id_numbers",
)
DEFAULT_PATH = REPO_ROOT / "site" / "regulatory-register.json"

MAX_FILE_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
PAGE_SIZE = 100
MAX_PAGES = 2
MAX_CANDIDATES = PAGE_SIZE * MAX_PAGES
MAX_DOCUMENTS = 100
MAX_QUERY_DAYS = 60
LOOKBACK_DAYS = 45
DEADLINE_SECONDS = 30.0
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 10.0
RETRY_PAUSE = 3.0
USER_AGENT = "GRCInsight-regulatory-register/1 (+https://grcinsight.ricomanifesto.com/)"

TOP_KEYS = frozenset({"schema", "source", "read", "documents"})
SOURCE_KEYS = frozenset({"name", "endpoint", "types", "terms", "match"})
READ_KEYS = frozenset(
    {
        "checked_at",
        "query_from",
        "query_to",
        "candidates",
        "pages_read",
        "truncated",
        "invalid_matches",
    }
)
DOCUMENT_KEYS = frozenset(
    {
        "document_number",
        "type",
        "action",
        "title",
        "html_url",
        "publication_date",
        "effective_on",
        "comments_close_on",
        "agencies",
        "regulation_id_numbers",
        "docket_ids",
        "matched_terms",
    }
)
DOCUMENT_NUMBER = re.compile(r"\d{4}-\d{4,6}")
REGULATION_ID = re.compile(r"\d{4}-[A-Z]{2}\d{2}")
CHECKED_AT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
TERM_PATTERNS = {
    term: re.compile(r"\b" + r"\s+".join(map(re.escape, term.split())) + r"\b", re.IGNORECASE)
    for term in TERMS
}


class RegisterInvalid(ValueError):
    """The data file breaks a numbered validity rule; the message never echoes content."""

    def __init__(self, rule: int, reason: str) -> None:
        super().__init__(f"rule {rule}: {reason}")
        self.rule = rule


class ReadFailed(Exception):
    """The read is refused as a whole; the previous file stays as it is."""


def matched_terms(title: str) -> list[str]:
    return [term for term, pattern in TERM_PATTERNS.items() if pattern.search(title)]


def source_record() -> dict[str, Any]:
    return {
        "endpoint": ENDPOINT,
        "match": MATCH,
        "name": SOURCE_NAME,
        "terms": list(TERMS),
        "types": list(TYPES),
    }


def serialize_register(register: dict[str, Any]) -> bytes:
    """Deterministic bytes: sorted keys, two-space indentation, trailing newline."""
    return (json.dumps(register, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


# ----- The validator -----


def _real_date(value: object) -> date | None:
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _count(value: object, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def _short_strings(value: object, items: int, length: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= items
        and all(isinstance(item, str) and 0 < len(item) <= length for item in value)
    )


def _document_fields_valid(document: dict, query_from: date, query_to: date) -> bool:
    """Rule 6 for one document."""
    number = document["document_number"]
    title = document["title"]
    action = document["action"]
    published = _real_date(document["publication_date"])
    return (
        isinstance(number, str)
        and DOCUMENT_NUMBER.fullmatch(number) is not None
        and isinstance(document["html_url"], str)
        and federal_register_api_url(document["html_url"])
        == f"https://{HOST}/api/v1/documents/{number}.json"
        and document["type"] in TYPES
        and isinstance(title, str)
        and 0 < len(title) <= 500
        and CONTROL_CHARACTER.search(title) is None
        and published is not None
        and query_from <= published <= query_to
        and all(
            document[name] is None or _real_date(document[name]) is not None
            for name in ("effective_on", "comments_close_on")
        )
        and (action is None or (isinstance(action, str) and len(action) <= 200))
    )


def _document_lists_valid(document: dict) -> bool:
    """Rule 7 for one document."""
    numbers = document["regulation_id_numbers"]
    return (
        _short_strings(document["agencies"], 10, 200)
        and isinstance(numbers, list)
        and len(numbers) <= 10
        and all(isinstance(n, str) and REGULATION_ID.fullmatch(n) for n in numbers)
        and _short_strings(document["docket_ids"], 20, 200)
    )


def _document_terms_valid(document: dict) -> bool:
    """Rule 8 for one document: each recorded term really is in the title."""
    terms = document["matched_terms"]
    # Element types first: a nested object must fail the rule, not raise while hashing.
    return (
        isinstance(terms, list)
        and bool(terms)
        and all(isinstance(term, str) for term in terms)
        and len(set(terms)) == len(terms)
        and all(term in TERM_PATTERNS for term in terms)
        and isinstance(document["title"], str)
        and all(TERM_PATTERNS[term].search(document["title"]) for term in terms)
    )


def validate_register(register: object, size: int) -> dict[str, Any]:
    """Return the register when every rule holds; otherwise raise the first rule broken."""
    # 1. Size, a JSON object, exactly four keys.
    if size > MAX_FILE_BYTES:
        raise RegisterInvalid(1, "file is larger than 256 KB")
    if not isinstance(register, dict) or set(register) != TOP_KEYS:
        raise RegisterInvalid(1, "not an object with exactly the four top-level keys")
    # 2. Schema and source constants.
    source = register["source"]
    if register["schema"] != SCHEMA:
        raise RegisterInvalid(2, "unknown schema")
    if not isinstance(source, dict) or source != source_record():
        raise RegisterInvalid(2, "source does not match this reader's endpoint, types and terms")
    # 3. The read time and the queried dates.
    read = register["read"]
    if not isinstance(read, dict) or set(read) != READ_KEYS:
        raise RegisterInvalid(3, "read record does not have exactly its seven keys")
    checked_at = read["checked_at"]
    try:
        valid_time = isinstance(checked_at, str) and CHECKED_AT.fullmatch(checked_at) is not None
        valid_time = valid_time and bool(datetime.strptime(checked_at, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        valid_time = False
    query_from, query_to = _real_date(read["query_from"]), _real_date(read["query_to"])
    if (
        not valid_time
        or query_from is None
        or query_to is None
        or query_from > query_to
        or (query_to - query_from).days > MAX_QUERY_DAYS
    ):
        raise RegisterInvalid(3, "read time or queried dates are not valid")
    # 4. Counts that reconcile examined rows, unreadable matches and listed documents.
    documents = register["documents"]
    listed = len(documents) if isinstance(documents, list) else 0
    if not (
        _count(read["candidates"], 1, MAX_CANDIDATES)
        and read["pages_read"] in (1, 2)
        and not isinstance(read["pages_read"], bool)
        and isinstance(read["truncated"], bool)
        and _count(read["invalid_matches"], 0, MAX_CANDIDATES)
        and listed + read["invalid_matches"] <= read["candidates"]
        and read["candidates"] <= PAGE_SIZE * read["pages_read"]
        and (read["pages_read"] == 1) == (read["candidates"] <= PAGE_SIZE)
        and (not read["truncated"] or read["pages_read"] == MAX_PAGES)
    ):
        raise RegisterInvalid(4, "read counts are out of range or do not reconcile")
    # 5. A bounded, ordered list of whole document records.
    if (
        not isinstance(documents, list)
        or len(documents) > MAX_DOCUMENTS
        or not all(isinstance(d, dict) and set(d) == DOCUMENT_KEYS for d in documents)
    ):
        raise RegisterInvalid(5, "documents is not a list of at most 100 complete records")
    numbers = [d["document_number"] for d in documents]
    if len(set(map(str, numbers))) != len(numbers):
        raise RegisterInvalid(5, "a document number is repeated")
    order = [(str(d["publication_date"]), str(d["document_number"])) for d in documents]
    if order != sorted(order, reverse=True):
        raise RegisterInvalid(5, "documents are not newest first")
    # 6-8. Each document, one rule at a time across the whole list.
    if not all(_document_fields_valid(d, query_from, query_to) for d in documents):
        raise RegisterInvalid(6, "a document field is not valid")
    if not all(_document_lists_valid(d) for d in documents):
        raise RegisterInvalid(7, "a document list is too long or malformed")
    if not all(_document_terms_valid(d) for d in documents):
        raise RegisterInvalid(8, "a recorded term is not in its document title")
    return register


def validate_register_bytes(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_FILE_BYTES:
        raise RegisterInvalid(1, "file is larger than 256 KB")
    try:
        register = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RegisterInvalid(1, "not valid JSON") from None
    return validate_register(register, len(data))


def load_register(path: Path) -> dict[str, Any] | None:
    """The validated register, or None when there is no file. Size is checked before reading."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return None
    if size > MAX_FILE_BYTES:
        raise RegisterInvalid(1, "file is larger than 256 KB")
    return validate_register_bytes(path.read_bytes())


# ----- The read -----


class Deadline:
    """Time left in the whole command, on a monotonic clock."""

    def __init__(
        self,
        clock: Callable[[], float],
        seconds: float = DEADLINE_SECONDS,
        start: float | None = None,
    ) -> None:
        self.clock = clock
        self.end = (clock() if start is None else start) + seconds

    def remaining(self) -> float:
        return self.end - self.clock()


def query_url(read_date: date, page: int) -> str:
    params: list[tuple[str, str]] = [
        ("conditions[term]", " | ".join(f'"{t}"' if " " in t else t for t in TERMS)),
        *[("conditions[type][]", value) for value in API_TYPES],
        ("conditions[publication_date][gte]", (read_date - timedelta(LOOKBACK_DAYS)).isoformat()),
        ("conditions[publication_date][lte]", (read_date + timedelta(1)).isoformat()),
        *[("fields[]", field) for field in FIELDS],
        ("per_page", str(PAGE_SIZE)),
        ("order", "newest"),
    ]
    if page > 1:
        params.append(("page", str(page)))
    return f"{ENDPOINT}?{urlencode(params)}"


def _https_connection(host: str, port: int, timeout: float) -> http.client.HTTPConnection:
    return http.client.HTTPSConnection(
        host, port, timeout=timeout, context=ssl.create_default_context()
    )


ConnectionFactory = Callable[[str, int, float], http.client.HTTPConnection]


def _fetch_once(
    host: str,
    port: int,
    target: str,
    deadline: Deadline,
    request_end: float,
    connect: ConnectionFactory,
    opened: list[http.client.HTTPConnection],
) -> tuple[int, bytes]:
    clock = deadline.clock

    def budget(limit: float) -> float:
        left = min(limit, request_end, deadline.end) - clock()
        if left <= 0:
            raise TimeoutError("time exhausted")
        return left

    connection = connect(host, port, budget(clock() + CONNECT_TIMEOUT))
    opened.append(connection)
    connection.connect()
    read_end = clock() + READ_TIMEOUT
    sock = connection.sock
    if sock is None:
        raise ConnectionError("no socket")
    sock.settimeout(budget(read_end))
    connection.request(
        "GET",
        target,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": USER_AGENT,
        },
    )
    response = connection.getresponse()
    length = response.getheader("Content-Length")
    if length and length.isdigit() and int(length) > MAX_RESPONSE_BYTES:
        raise ReadFailed("response is larger than 1 MB")
    chunks: list[bytes] = []
    size = 0
    while True:
        # read1 returns after one receive, so the absolute budget is rechecked
        # between receives instead of only after a whole block arrives.
        sock.settimeout(budget(read_end))
        chunk = response.read1(64 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise ReadFailed("response is larger than 1 MB")
        chunks.append(chunk)
    budget(read_end)
    return response.status, b"".join(chunks)


def fetch_https(
    host: str,
    port: int,
    target: str,
    deadline: Deadline,
    connect: ConnectionFactory = _https_connection,
) -> tuple[int, bytes]:
    """One GET that returns or fails within the request bound and the command deadline.

    Socket timeouts bound each receive, not a whole request: a server can drip
    bytes, and name resolution ignores them. The request therefore runs in a
    daemon worker that the caller waits for only as long as time allows; on
    expiry the socket is closed and the request counts as timed out. The
    caller writes nothing afterwards, because the deadline has passed.
    """
    clock = deadline.clock
    if deadline.remaining() <= 0:
        raise TimeoutError("no time remains")
    request_end = min(deadline.end, clock() + CONNECT_TIMEOUT + READ_TIMEOUT)
    opened: list[http.client.HTTPConnection] = []
    outcome: dict[str, Any] = {}

    def run() -> None:
        try:
            outcome["value"] = _fetch_once(
                host, port, target, deadline, request_end, connect, opened
            )
        except BaseException as error:  # noqa: BLE001 - handed to the waiting caller
            outcome["error"] = error

    worker = threading.Thread(target=run, name="regulatory-register-request", daemon=True)
    worker.start()
    worker.join(max(0.0, request_end - clock()))
    for connection in opened:
        connection.close()
    if worker.is_alive() or not outcome:
        raise TimeoutError("request did not finish in time")
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


def https_get(url: str, deadline: Deadline) -> tuple[int, bytes]:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != HOST or parts.port not in (None, 443):
        raise ReadFailed("refused a request to another host or scheme")
    target = parts.path + (f"?{parts.query}" if parts.query else "")
    return fetch_https(HOST, 443, target, deadline)


Transport = Callable[[str, Deadline], tuple[int, bytes]]


def _request(
    transport: Transport, url: str, deadline: Deadline, sleep: Callable[[float], None]
) -> bytes:
    """GET one page: one retry after a pause for transient failures; never a redirect."""
    reason = "no attempt made"
    for attempt in (1, 2):
        if attempt == 2:
            # The pause never outlasts the command's remaining time.
            sleep(max(0.0, min(RETRY_PAUSE, deadline.remaining())))
        if deadline.remaining() <= 0:
            raise ReadFailed(f"deadline reached ({reason})")
        try:
            status, body = transport(url, deadline)
        except TimeoutError:
            reason = "request timed out"
            continue
        except (OSError, http.client.HTTPException):
            reason = "connection error"
            continue
        if status == 429 or 500 <= status <= 599:
            reason = f"HTTP {status}"
            continue
        if 300 <= status <= 399:
            raise ReadFailed("redirect refused")
        if status != 200:
            raise ReadFailed(f"HTTP {status}")
        if len(body) > MAX_RESPONSE_BYTES:
            raise ReadFailed("response is larger than 1 MB")
        return body
    raise ReadFailed(f"{reason} after one retry")


def _page(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ReadFailed("response is not JSON") from None
    if not isinstance(value, dict):
        raise ReadFailed("response is not a JSON object")
    count = value.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ReadFailed("response lists no candidate")
    results = value.get("results")
    if not isinstance(results, list):
        raise ReadFailed("response has no results list")
    for row in results:
        if not isinstance(row, dict) or not isinstance(row.get("title"), str):
            raise ReadFailed("a result has no title")
        if row.get("type") not in TYPES:
            raise ReadFailed("a result has another document type")
    return value


def _agency_names(value: object) -> object:
    if not isinstance(value, list):
        return None
    names = [item.get("name") if isinstance(item, dict) else None for item in value]
    return names if all(isinstance(name, str) for name in names) else None


def assemble(
    pages: Sequence[dict[str, Any]], checked_at: str, query_from: str, query_to: str
) -> dict[str, Any]:
    """The data file from accepted pages, a pure function of the read."""
    count = pages[0]["count"]
    examined: list[dict] = []
    seen: set[str] = set()
    for index, page in enumerate(pages):
        expected = min(count - PAGE_SIZE * index, PAGE_SIZE)
        if page["count"] != count:
            raise ReadFailed("the total changed between pages")
        if len(page["results"]) != expected:
            raise ReadFailed("results contradict the reported count")
        for row in page["results"]:
            number = row.get("document_number")
            if isinstance(number, str):
                if number in seen:
                    raise ReadFailed("a record repeats across the read")
                seen.add(number)
            examined.append(row)
    start, end = date.fromisoformat(query_from), date.fromisoformat(query_to)
    documents, invalid = [], 0
    for row in examined:
        terms = matched_terms(row["title"])
        if not terms:
            continue
        document = {
            "action": row.get("action"),
            "agencies": _agency_names(row.get("agencies")),
            "comments_close_on": row.get("comments_close_on"),
            "docket_ids": row.get("docket_ids"),
            "document_number": row.get("document_number"),
            "effective_on": row.get("effective_on"),
            "html_url": row.get("html_url"),
            "matched_terms": terms,
            "publication_date": row.get("publication_date"),
            "regulation_id_numbers": row.get("regulation_id_numbers"),
            "title": row["title"],
            "type": row["type"],
        }
        if _document_fields_valid(document, start, end) and _document_lists_valid(document):
            documents.append(document)
        else:
            invalid += 1
    if len(documents) > MAX_DOCUMENTS:
        raise ReadFailed("more than 100 matching documents; the read is refused, not cut")
    documents.sort(key=lambda d: (d["publication_date"], d["document_number"]), reverse=True)
    return {
        "documents": documents,
        "read": {
            "candidates": len(examined),
            "checked_at": checked_at,
            "invalid_matches": invalid,
            "pages_read": len(pages),
            "query_from": query_from,
            "query_to": query_to,
            "truncated": count > MAX_CANDIDATES,
        },
        "schema": SCHEMA,
        "source": source_record(),
    }


def write_atomic(path: Path, data: bytes, deadline: Deadline) -> None:
    """Write a temporary file beside the target and rename it over; never after the deadline."""
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if deadline.remaining() <= 0:
            raise ReadFailed("deadline reached before the write")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def refresh(
    path: Path,
    *,
    transport: Transport | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    start: float | None = None,
) -> tuple[bool, str]:
    """Read the register and replace the file only on a fully accepted read."""
    deadline = Deadline(clock, DEADLINE_SECONDS, start)
    get = transport or https_get
    checked = now().astimezone(timezone.utc).replace(microsecond=0)
    read_date = checked.date()
    try:
        first = _page(_request(get, query_url(read_date, 1), deadline, sleep))
        pages = [first]
        if first["count"] > PAGE_SIZE:
            pages.append(_page(_request(get, query_url(read_date, 2), deadline, sleep)))
        register = assemble(
            pages,
            checked.strftime("%Y-%m-%dT%H:%M:%SZ"),
            (read_date - timedelta(LOOKBACK_DAYS)).isoformat(),
            (read_date + timedelta(1)).isoformat(),
        )
        data = serialize_register(register)
        try:
            validate_register_bytes(data)
        except RegisterInvalid as error:
            raise ReadFailed(f"assembled file failed validation ({error})") from None
        if deadline.remaining() <= 0:
            raise ReadFailed("deadline reached before the write")
        write_atomic(path, data, deadline)
    except ReadFailed as error:
        return False, str(error)
    except OSError as error:
        return False, f"write interrupted ({type(error).__name__}: interrupted)"
    return (
        True,
        f"{len(register['documents'])} documents from {register['read']['candidates']} candidates",
    )


def main(argv: Sequence[str] | None = None) -> int:
    start = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    refresh_parser = commands.add_parser("refresh", help="read the register and update the file")
    refresh_parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args(argv)
    written, message = refresh(args.path, start=start)
    if written:
        print(f"regulatory register: updated ({message})")
    else:
        print(f"regulatory register: read failed ({message}); file unchanged", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
