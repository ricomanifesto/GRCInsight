"""The Federal Register read and its data file: bounds, failures and the validator."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import socket
import threading
import time
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_BUILDER = REPO_ROOT / "scripts" / "build_site.py"
FIXTURES = REPO_ROOT / "agent" / "tests" / "fixtures" / "federal-register"
AUGUST = FIXTURES / "fixture-window-2026-07-01_2026-08-15.json"
NOVEMBER = FIXTURES / "fixture-window-2026-09-27_2026-11-10.json"
UTC = timezone.utc
READ_AT = datetime(2026, 11, 10, 12, 20, 5, tzinfo=UTC)


@pytest.fixture(scope="module")
def rr() -> Any:
    # The builder imports the register module; reuse that exact module object.
    return runpy.run_path(str(SITE_BUILDER))["regulatory_register"]


# ----- Fakes -----


class Clock:
    """A monotonic clock that only moves when the code under test waits or reads."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class Transport:
    """Serves scripted outcomes in order and records every request."""

    def __init__(self, clock: Clock, outcomes: list) -> None:
        self.clock = clock
        self.outcomes = list(outcomes)
        self.urls: list[str] = []

    def __call__(self, url: str, deadline) -> tuple[int, bytes]:
        self.urls.append(url)
        outcome = self.outcomes.pop(0)
        return outcome(self.clock, deadline) if callable(outcome) else outcome


def page(results: list[dict], count: int | None = None, total_pages: int = 1) -> tuple[int, bytes]:
    body = {
        "count": len(results) if count is None else count,
        "total_pages": total_pages,
        "results": results,
    }
    return 200, json.dumps(body).encode()


def result(number: str, title: str, *, type_: str = "Rule", day: str = "2026-11-02", **extra):
    y, m, d = day.split("-")
    row = {
        "document_number": number,
        "title": title,
        "type": type_,
        "action": "Final rule." if type_ == "Rule" else "Proposed rule.",
        "publication_date": day,
        "effective_on": None,
        "comments_close_on": None,
        "html_url": f"https://www.federalregister.gov/documents/{y}/{m}/{d}/{number}/a-title",
        "agencies": [{"name": "Federal Communications Commission", "id": 161}],
        "docket_ids": [],
        "regulation_id_numbers": [],
    }
    row.update(extra)
    return row


def filler(n: int, start: int = 1) -> list[dict]:
    return [result(f"2026-{20000 + start + i}", f"Unrelated title {i}") for i in range(n)]


def stall(seconds: float):
    def run(clock: Clock, deadline):
        clock.now += min(seconds, deadline.remaining())
        raise TimeoutError("stalled")

    return run


def refresh(rr, path: Path, transport: Transport, clock: Clock, now: datetime = READ_AT):
    return rr.refresh(
        path, transport=transport, clock=clock, sleep=clock.sleep, now=lambda: now, start=0.0
    )


@pytest.fixture
def register_path(tmp_path: Path) -> Path:
    path = tmp_path / "regulatory-register.json"
    path.write_bytes(b'{"previous": "file"}\n')
    return path


# ----- Accepted reads -----


def test_an_accepted_read_writes_a_valid_deterministic_file(rr, register_path):
    clock = Clock()
    rows = [result("2026-21001", "Cybersecurity Incident Reporting")] + filler(4)
    transport = Transport(clock, [page(rows)])
    written, reason = refresh(rr, register_path, transport, clock)
    assert written, reason
    data = register_path.read_bytes()
    document = rr.validate_register_bytes(data)
    assert data == rr.serialize_register(document)
    assert data.endswith(b"\n") and json.loads(data) == document
    assert document["read"] == {
        "candidates": 5,
        "checked_at": "2026-11-10T12:20:05Z",
        "invalid_matches": 0,
        "pages_read": 1,
        "query_from": "2026-09-26",
        "query_to": "2026-11-11",
        "truncated": False,
    }
    [entry] = document["documents"]
    assert entry["agencies"] == ["Federal Communications Commission"]
    assert entry["matched_terms"] == ["cybersecurity"]


def test_two_identical_responses_differ_only_in_the_read_time(rr, tmp_path):
    rows = [result("2026-21001", "Data Breach Notification Rule")] + filler(3)
    files = []
    for minute in (20, 45):
        path = tmp_path / f"{minute}.json"
        clock = Clock()
        refresh(rr, path, Transport(clock, [page(rows)]), clock, READ_AT.replace(minute=minute))
        files.append(json.loads(path.read_text()))
    first, second = files
    assert first["documents"] == second["documents"]
    assert first["read"]["checked_at"] != second["read"]["checked_at"]
    first["read"].pop("checked_at"), second["read"].pop("checked_at")
    assert first == second


def test_the_query_is_bounded_to_one_host_two_types_and_an_explicit_field_list(rr):
    url = rr.query_url(READ_AT.date(), 1)
    assert url.startswith("https://www.federalregister.gov/api/v1/documents.json?")
    assert "conditions%5Btype%5D%5B%5D=RULE" in url and "conditions%5Btype%5D%5B%5D=PRORULE" in url
    assert "conditions%5Bpublication_date%5D%5Bgte%5D=2026-09-26" in url
    assert "conditions%5Bpublication_date%5D%5Blte%5D=2026-11-11" in url
    assert "per_page=100" in url and "order=newest" in url and "fields%5B%5D=title" in url
    assert "&page=" not in url
    assert rr.query_url(READ_AT.date(), 2).endswith("&page=2")


def test_three_or_more_pages_read_two_and_record_truncation(rr, register_path):
    clock = Clock()
    first = [result("2026-21001", "Cybersecurity Labeling")] + filler(99, start=1)
    second = filler(100, start=200)
    transport = Transport(clock, [page(first, 250, 3), page(second, 250, 3)])
    written, reason = refresh(rr, register_path, transport, clock)
    assert written, reason
    assert len(transport.urls) == 2
    read = json.loads(register_path.read_text())["read"]
    assert read["truncated"] is True and read["pages_read"] == 2 and read["candidates"] == 200


def test_a_qualifying_record_with_broken_metadata_is_counted_not_listed(rr, register_path):
    clock = Clock()
    rows = [
        result("2026-21001", "Information Security Program Rule"),
        result("2026-21002", "Cyber Incident Rule", regulation_id_numbers=["bad"]),
        result("2026-21003", "Data Security Rule", html_url="http://example.test/x"),
    ] + filler(2)
    written, reason = refresh(rr, register_path, Transport(clock, [page(rows)]), clock)
    assert written, reason
    document = json.loads(register_path.read_text())
    assert [d["document_number"] for d in document["documents"]] == ["2026-21001"]
    assert document["read"]["invalid_matches"] == 2


def test_word_boundaries_and_case_decide_a_match(rr):
    assert rr.matched_terms("CYBERSECURITY Standards") == ["cybersecurity"]
    assert rr.matched_terms("Cyber  Incident Reporting; Data Breach") == [
        "cyber incident",
        "data breach",
    ]
    assert rr.matched_terms("Cybersecurityish rules") == []
    assert rr.matched_terms("Metadata security") == []


# ----- Failed reads leave the file byte-identical -----


def redirect(location: str):
    return 302, f"Redirecting to {location}".encode()


FAILURES = {
    "redirect": [redirect("https://www.federalregister.gov/elsewhere")],
    "redirect to the unblock host": [redirect("https://unblock.federalregister.gov/")],
    "HTML body": [(200, b"<!doctype html><html><body>blocked</body></html>")],
    "429 after one retry": [(429, b""), (429, b"")],
    "5xx after one retry": [(503, b"<html>"), (502, b"")],
    "invalid JSON": [(200, b'{"count": 3, "results": [')],
    "a JSON array": [(200, b"[]")],
    "count zero": [(200, b'{"description":"Documents of type ","count":0}')],
    "results contradict count": [page(filler(3), count=5)],
    "another type": [page([result("2026-21001", "Cybersecurity notice", type_="Notice")])],
    "a result without a title": [page([{"type": "Rule", "document_number": "2026-21001"}])],
    "oversized body": [(200, b" " * (1024 * 1024 + 1))],
    # The 100-document limit never drops matches silently: the whole read is refused.
    "more than 100 matching documents": [
        page([result(f"2026-{30000 + i}", f"Cybersecurity rule {i}") for i in range(100)], 101, 2),
        page([result("2026-30100", "Cybersecurity rule 100")], 101, 2),
    ],
    "a repeated record across pages": [
        page(filler(100), 120, 2),
        page(filler(20, start=95), 120, 2),
    ],
    "a count that changes between pages": [
        page(filler(100), 120, 2),
        page(filler(21, start=300), 121, 2),
    ],
}


@pytest.mark.parametrize("case", list(FAILURES))
def test_failed_reads_keep_the_previous_file(rr, register_path, case):
    before = register_path.read_bytes()
    clock = Clock()
    transport = Transport(clock, FAILURES[case])
    written, reason = refresh(rr, register_path, transport, clock)
    assert not written and reason
    assert register_path.read_bytes() == before
    assert not transport.outcomes, "every scripted outcome should be consumed"


def test_timeouts_are_retried_once_then_fail(rr, register_path):
    before = register_path.read_bytes()
    clock = Clock()
    transport = Transport(clock, [stall(2), stall(2)])
    written, reason = refresh(rr, register_path, transport, clock)
    assert not written and "timed out" in reason
    assert len(transport.urls) == 2 and clock.sleeps == [3.0]
    assert register_path.read_bytes() == before


def test_a_retry_succeeds_after_one_server_error(rr, register_path):
    clock = Clock()
    rows = [result("2026-21001", "Cybersecurity rule")] + filler(1)
    transport = Transport(clock, [(500, b""), page(rows)])
    written, _ = refresh(rr, register_path, transport, clock)
    assert written and len(transport.urls) == 2


def test_no_request_leaves_the_register_host_or_exceeds_one_retry(rr, register_path):
    clock = Clock()
    transport = Transport(clock, [(503, b""), (503, b"")])
    refresh(rr, register_path, transport, clock)
    assert len(transport.urls) == 2
    assert all(url.startswith("https://www.federalregister.gov/api/v1/") for url in transport.urls)
    with pytest.raises(rr.ReadFailed):
        rr.https_get("https://unblock.federalregister.gov/", rr.Deadline(time.monotonic, 1))
    with pytest.raises(rr.ReadFailed):
        rr.https_get("http://www.federalregister.gov/api/v1/x", rr.Deadline(time.monotonic, 1))


def test_main_exits_zero_with_one_reason_line_on_failure(rr, register_path, monkeypatch, capsys):
    before = register_path.read_bytes()

    def refused(_url, _deadline):
        return 302, b"<html>secret body text</html>"

    monkeypatch.setattr(rr, "https_get", refused)
    assert rr.main(["refresh", "--path", str(register_path)]) == 0
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and err[0].startswith("regulatory register: read failed")
    assert "secret body text" not in err[0]
    assert register_path.read_bytes() == before


# ----- The whole-command deadline -----


def test_a_stalled_transport_returns_within_the_deadline(rr, register_path):
    before = register_path.read_bytes()
    clock = Clock()
    transport = Transport(clock, [stall(28.5), stall(60)])
    written, reason = refresh(rr, register_path, transport, clock)
    assert not written and reason
    assert clock.now <= 30.0 + 1e-9
    assert clock.sleeps == [1.5], "the retry pause is cut to the time remaining"
    assert register_path.read_bytes() == before


def test_a_stall_on_the_second_page_also_fails_within_the_deadline(rr, register_path):
    before = register_path.read_bytes()
    clock = Clock()
    transport = Transport(clock, [page(filler(100), 150, 2), stall(60), stall(60)])
    written, _ = refresh(rr, register_path, transport, clock)
    assert not written and clock.now <= 30.0 + 1e-9
    assert register_path.read_bytes() == before


def test_no_write_happens_once_the_deadline_has_passed(rr, register_path):
    before = register_path.read_bytes()
    clock = Clock()

    def late(clock: Clock, _deadline):
        clock.now = 30.0
        return page([result("2026-21001", "Cybersecurity rule")])

    written, reason = refresh(rr, register_path, Transport(clock, [late]), clock)
    assert not written and "deadline" in reason
    assert register_path.read_bytes() == before
    assert sorted(p.name for p in register_path.parent.iterdir()) == [register_path.name]


def test_the_real_transport_gives_up_on_a_silent_server_within_its_budget(rr):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    accepted: list[socket.socket] = []
    thread = threading.Thread(target=lambda: accepted.append(server.accept()[0]), daemon=True)
    thread.start()
    started = time.monotonic()
    try:
        with pytest.raises((TimeoutError, OSError)):
            rr.fetch_https(
                "127.0.0.1",
                server.getsockname()[1],
                "/api/v1/documents.json",
                rr.Deadline(time.monotonic, 1.0),
            )
        assert time.monotonic() - started < 2.5
    finally:
        for conn in accepted:
            conn.close()
        server.close()


def drip_server(prefix: bytes, dripped: bytes, interval: float):
    """A local server that sends ``prefix`` at once, then ``dripped`` one byte at a time."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    stop = threading.Event()

    def serve() -> None:
        try:
            conn, _ = server.accept()
        except OSError:
            return
        with conn:
            try:
                conn.recv(4096)
                conn.sendall(prefix)
                for byte in dripped:
                    if stop.is_set():
                        return
                    conn.sendall(bytes([byte]))
                    time.sleep(interval)
            except OSError:
                return

    threading.Thread(target=serve, daemon=True).start()
    return server, stop


def plain_http(host: str, port: int, timeout: float):
    import http.client

    return http.client.HTTPConnection(host, port, timeout=timeout)


@pytest.mark.parametrize(
    "prefix, dripped",
    [
        (b"HTTP/1.1 200 OK\r\nContent-Length: 60\r\n\r\n", b"x" * 60),
        (b"", b"HTTP/1.1 200 OK\r\nX-Slow: " + b"y" * 60 + b"\r\n\r\n{}"),
    ],
    ids=["body", "headers"],
)
def test_a_slow_drip_cannot_outlast_the_absolute_deadline(rr, prefix, dripped):
    # Each byte arrives well inside any per-receive timeout; only an absolute
    # bound on the whole request stops it.
    server, stop = drip_server(prefix, dripped, 0.025)
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            rr.fetch_https(
                "127.0.0.1",
                server.getsockname()[1],
                "/api/v1/documents.json",
                rr.Deadline(time.monotonic, 0.2),
                plain_http,
            )
        elapsed = time.monotonic() - started
        assert elapsed < 0.5, f"returned after {elapsed:.3f}s with a 0.2s deadline"
    finally:
        stop.set()
        server.close()


def test_a_slow_drip_during_refresh_writes_nothing(rr, register_path, monkeypatch):
    before = register_path.read_bytes()
    body = json.dumps(
        {"count": 1, "total_pages": 1, "results": [result("2026-21001", "Cybersecurity rule")]}
    ).encode()
    head = b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(body)
    server, stop = drip_server(head, body, 0.02)
    port = server.getsockname()[1]
    monkeypatch.setattr(rr, "DEADLINE_SECONDS", 0.3)

    def dripping(_url, deadline):
        return rr.fetch_https("127.0.0.1", port, "/", deadline, plain_http)

    started = time.monotonic()
    try:
        written, reason = rr.refresh(register_path, transport=dripping, now=lambda: READ_AT)
    finally:
        stop.set()
        server.close()
    assert not written and reason
    assert time.monotonic() - started < 0.8
    assert register_path.read_bytes() == before


# ----- Atomic writes -----


def test_an_interrupted_write_leaves_the_previous_file_intact(rr, register_path, monkeypatch):
    before = register_path.read_bytes()

    def interrupted(_src, _dst):
        raise OSError("interrupted")

    monkeypatch.setattr(rr.os, "replace", interrupted)
    clock = Clock()
    rows = [result("2026-21001", "Cybersecurity rule")]
    written, reason = refresh(rr, register_path, Transport(clock, [page(rows)]), clock)
    assert not written and "interrupted" in reason
    assert register_path.read_bytes() == before
    assert sorted(p.name for p in register_path.parent.iterdir()) == [register_path.name]


def test_the_read_refuses_to_write_a_file_its_validator_rejects(rr, register_path, monkeypatch):
    before = register_path.read_bytes()

    def reject(_data):
        raise rr.RegisterInvalid(5, "documents")

    monkeypatch.setattr(rr, "validate_register_bytes", reject)
    clock = Clock()
    rows = [result("2026-21001", "Cybersecurity rule")]
    written, reason = refresh(rr, register_path, Transport(clock, [page(rows)]), clock)
    assert not written and "rule 5" in reason
    assert register_path.read_bytes() == before


# ----- The saved real responses -----


def saved_register(rr, fixture: Path, checked_at: str) -> dict:
    response = json.loads(fixture.read_text())
    query_from, query_to = fixture.stem.removeprefix("fixture-window-").split("_")
    return rr.assemble([response], checked_at, query_from, query_to)


def test_the_saved_august_response_yields_the_one_title_match(rr):
    register = saved_register(rr, AUGUST, "2026-11-10T18:28:59Z")
    rr.validate_register_bytes(rr.serialize_register(register))
    assert [d["document_number"] for d in register["documents"]] == ["2026-15601"]
    assert register["read"]["candidates"] == 57 and register["read"]["invalid_matches"] == 0
    assert register["documents"][0]["matched_terms"] == ["cybersecurity"]
    assert register["documents"][0]["effective_on"] == "2026-09-29"


def test_the_saved_november_response_yields_no_title_match(rr):
    register = saved_register(rr, NOVEMBER, "2026-11-10T18:28:59Z")
    rr.validate_register_bytes(rr.serialize_register(register))
    assert register["documents"] == [] and register["read"]["candidates"] == 30


# ----- The validator, one violation per rule -----


def valid_register(rr) -> dict:
    return saved_register(rr, AUGUST, "2026-11-10T18:28:59Z")


def mutate(rr, change) -> bytes:
    register = copy.deepcopy(valid_register(rr))
    change(register)
    return rr.serialize_register(register)


def doc0(register: dict) -> dict:
    return register["documents"][0]


VIOLATIONS = {
    1: [
        lambda r: r.update(extra=1),
        lambda r: r.pop("read"),
        lambda r: r.update(documents=[{"title": "x" * 300_000}]),
    ],
    2: [
        lambda r: r.update(schema="grcinsight-regulatory-register/2"),
        lambda r: r["source"].update(endpoint="https://example.test/api"),
        lambda r: r["source"].update(terms=["cybersecurity"]),
        lambda r: r["source"].pop("match"),
    ],
    3: [
        lambda r: r["read"].update(checked_at="2026-11-10T18:28:59+00:00"),
        lambda r: r["read"].update(query_from="2026-02-30"),
        lambda r: r["read"].update(query_from="2026-08-16"),
        lambda r: r["read"].update(query_from="2026-05-01"),
    ],
    4: [
        lambda r: r["read"].update(candidates=0),
        lambda r: r["read"].update(candidates=True),
        lambda r: r["read"].update(pages_read=3),
        lambda r: r["read"].update(truncated="no"),
        lambda r: r["read"].update(invalid_matches=201),
        lambda r: r["read"].update(invalid_matches=57),
        lambda r: r["read"].update(truncated=True),
    ],
    5: [
        lambda r: r.update(documents=r["documents"] * 2),
        lambda r: doc0(r).pop("docket_ids"),
        lambda r: r.update(documents="none"),
    ],
    6: [
        lambda r: doc0(r).update(document_number="15601"),
        lambda r: doc0(r).update(html_url="https://www.federalregister.gov/documents/x"),
        lambda r: doc0(r).update(type="Notice"),
        lambda r: doc0(r).update(title=""),
        lambda r: doc0(r).update(title="Cybersecurity\u0007 rule"),
        lambda r: doc0(r).update(publication_date="2026-08-16"),
        lambda r: doc0(r).update(effective_on="soon"),
        lambda r: doc0(r).update(action="x" * 201),
    ],
    7: [
        lambda r: doc0(r).update(agencies=["a"] * 11),
        lambda r: doc0(r).update(regulation_id_numbers=["3060-ak57"]),
        lambda r: doc0(r).update(docket_ids=["d"] * 21),
        lambda r: doc0(r).update(agencies=[7]),
    ],
    8: [
        lambda r: doc0(r).update(matched_terms=[]),
        lambda r: doc0(r).update(matched_terms=["privacy"]),
        lambda r: doc0(r).update(matched_terms=["data breach"]),
    ],
}


@pytest.mark.parametrize(
    "rule, index",
    [(rule, index) for rule, changes in VIOLATIONS.items() for index in range(len(changes))],
)
def test_each_validator_rule_rejects_its_violation(rr, rule, index):
    data = mutate(rr, VIOLATIONS[rule][index])
    with pytest.raises(rr.RegisterInvalid) as raised:
        rr.validate_register_bytes(data)
    assert raised.value.rule == rule
    assert str(raised.value).startswith(f"rule {rule}:")


def test_a_title_without_its_recorded_term_makes_the_file_invalid(rr):
    data = mutate(rr, lambda r: doc0(r).update(title="Modernization of the Alerting Systems"))
    with pytest.raises(rr.RegisterInvalid, match="rule 8"):
        rr.validate_register_bytes(data)


def test_size_is_checked_before_the_file_is_read(rr, tmp_path, monkeypatch):
    path = tmp_path / "regulatory-register.json"
    path.write_bytes(b" " * (256 * 1024 + 1))

    def no_read(*_args, **_kwargs):
        raise AssertionError("an oversized file must not be read")

    monkeypatch.setattr(Path, "read_bytes", no_read)
    with pytest.raises(rr.RegisterInvalid, match="rule 1"):
        rr.load_register(path)


def test_an_absent_file_is_not_an_error(rr, tmp_path):
    assert rr.load_register(tmp_path / "missing.json") is None
