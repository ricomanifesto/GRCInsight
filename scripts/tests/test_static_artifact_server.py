import http.client
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from serve_static_artifact import create_artifact_server  # noqa: E402

FILES = {
    "index.html": "<!doctype html><title>Current</title>\n",
    "index.md": "# Current\n",
    "archive/index.html": "<!doctype html><title>Archive</title>\n",
    "archive/2026-01-01T00-00-00Z/index.html": "<!doctype html><title>Dated</title>\n",
    "archive/2026-01-01T00-00-00Z/report.md": "# Dated\n",
    "archive/2026-01-01T00-00-00Z/evidence-manifest.json": '{"schema_version": 1}\n',
    "publication-history/index.html": "<!doctype html><title>History</title>\n",
    "static/icon.svg": '<svg xmlns="http://www.w3.org/2000/svg"></svg>\n',
    "static/favicon.ico": "ico",
    "static/social-preview.png": "png",
    "static/style.css": "body{}\n",
    "static/app.js": "void 0;\n",
    "sitemap.xml": "<urlset></urlset>\n",
    "README.md": "# Static site\n",
}
DIGEST = "b" * 64


@pytest.fixture
def server_address(tmp_path: Path) -> Iterator[tuple[str, int]]:
    root = tmp_path / "artifact"
    for relative_path, content in FILES.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    (tmp_path / "secret.txt").write_text("outside\n")
    (root / "static" / "linked.txt").symlink_to(tmp_path / "secret.txt")
    (root / "linked-dir").symlink_to(root / "archive")

    server = create_artifact_server(
        root=root, site="GRCInsight", inventory_digest=DIGEST, port=0
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[0], server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def _request(address: tuple[str, int], path: str, method: str = "GET"):
    connection = http.client.HTTPConnection(*address, timeout=10)
    connection.putrequest(method, path, skip_accept_encoding=True)
    connection.endheaders()
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response.status, dict(response.getheaders()), body


def test_serves_files_with_explicit_types_and_identity(server_address):
    expectations = {
        "/": ("text/html; charset=utf-8", FILES["index.html"]),
        "/index.html": ("text/html; charset=utf-8", FILES["index.html"]),
        "/index.md": ("text/markdown; charset=utf-8", FILES["index.md"]),
        "/README.md": ("text/markdown; charset=utf-8", FILES["README.md"]),
        "/archive/": ("text/html; charset=utf-8", FILES["archive/index.html"]),
        "/archive/2026-01-01T00-00-00Z/": (
            "text/html; charset=utf-8",
            FILES["archive/2026-01-01T00-00-00Z/index.html"],
        ),
        "/archive/2026-01-01T00-00-00Z/report.md": (
            "text/markdown; charset=utf-8",
            FILES["archive/2026-01-01T00-00-00Z/report.md"],
        ),
        "/archive/2026-01-01T00-00-00Z/evidence-manifest.json": (
            "application/json; charset=utf-8",
            FILES["archive/2026-01-01T00-00-00Z/evidence-manifest.json"],
        ),
        "/publication-history/": (
            "text/html; charset=utf-8",
            FILES["publication-history/index.html"],
        ),
        "/static/icon.svg": ("image/svg+xml", FILES["static/icon.svg"]),
        "/static/favicon.ico": ("image/x-icon", FILES["static/favicon.ico"]),
        "/static/social-preview.png": ("image/png", FILES["static/social-preview.png"]),
        "/static/style.css": ("text/css; charset=utf-8", FILES["static/style.css"]),
        "/static/app.js?v=1": (
            "text/javascript; charset=utf-8",
            FILES["static/app.js"],
        ),
        "/sitemap.xml": ("application/xml; charset=utf-8", FILES["sitemap.xml"]),
    }
    for route, (content_type, body) in expectations.items():
        status, headers, content = _request(server_address, route)
        assert status == 200, route
        assert headers["Content-Type"] == content_type, route
        assert content == body.encode(), route
        assert headers["X-Static-Artifact"] == f"GRCInsight {DIGEST}", route

    status, headers, content = _request(server_address, "/sitemap.xml", "HEAD")
    assert status == 200
    assert content == b""


def test_redirects_an_indexed_directory_without_its_slash(server_address):
    status, headers, _ = _request(server_address, "/archive?from=test")

    assert status == 301
    assert headers["Location"] == "/archive/?from=test"


@pytest.mark.parametrize(
    "route",
    [
        "/static/",
        "/static",
        "/missing.html",
        "/index.html/",
        "/static/linked.txt",
        "/linked-dir/",
        "/linked-dir/index.html",
        "/../secret.txt",
        "/%2e%2e/secret.txt",
        "/static/..%2f..%2fsecret.txt",
        "/static/..%5c..%5csecret.txt",
        "/index.html%00.png",
        "/.git/HEAD",
        "/package.json",
        "//etc/passwd",
    ],
)
def test_returns_404_without_listing_symlinks_or_traversal(server_address, route):
    status, _, content = _request(server_address, route)

    assert status == 404
    assert b"outside" not in content
    assert b"Directory listing" not in content
    assert b"<a href" not in content


def test_rejects_methods_other_than_get_and_head(server_address):
    status, headers, _ = _request(server_address, "/index.html", "POST")

    assert status == 405
    assert headers["Allow"] == "GET, HEAD"
