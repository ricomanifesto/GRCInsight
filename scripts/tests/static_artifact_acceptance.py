"""Acceptance for a built static artifact.

Not collected by default: it needs a store produced by
scripts/build_static_artifact.py and the pinned source repository.

    STATIC_ARTIFACT_STORE=<store> STATIC_ARTIFACT_SOURCE=<repo> \\
        python3 -B -m pytest scripts/tests/static_artifact_acceptance.py \\
        -p no:cacheprovider
"""

import http.client
import json
import os
import posixpath
import re
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_static_artifact import CurrentBuild, read_current_build  # noqa: E402
from serve_static_artifact import create_artifact_server  # noqa: E402

PUBLIC_ROOT = "https://ricomanifesto.github.io/GRCInsight/"
STORE = os.environ.get("STATIC_ARTIFACT_STORE")
SOURCE = os.environ.get("STATIC_ARTIFACT_SOURCE")
CONTENT_TYPES = {
    "": "application/octet-stream",
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".xml": "application/xml; charset=utf-8",
}
NEGATIVE_ROUTES = [
    "/scripts/check_site_report.py",
    "/scripts/build_site.py",
    "/Makefile",
    "/go.mod",
    "/package.json",
    "/test-results/",
    "/.git/HEAD",
    "/.github/workflows/deploy-site.yml",
    "/node_modules/",
    "/AGENTS.md",
    "/.env",
    "/.env.example",
    "/src/",
    "/agent/",
    "/agent/core/report_plan.py",
    "/internal/",
    "/cmd/server/main.go",
    "/configs/config.json",
    "/deployments/",
    "/site/index.html",
    "/../go.mod",
    "/static/..%2f..%2fgo.mod",
    "/static/",
    "/archive/2026-01-01T00-00-00Z/",
]

pytestmark = pytest.mark.skipif(
    not STORE or not SOURCE,
    reason="STATIC_ARTIFACT_STORE and STATIC_ARTIFACT_SOURCE are required",
)


@pytest.fixture(scope="module")
def current() -> CurrentBuild:
    return read_current_build(Path(str(STORE)), verify=True)


@pytest.fixture(scope="module")
def address(current: CurrentBuild) -> Iterator[tuple[str, int]]:
    server = create_artifact_server(
        root=current.artifact_dir,
        site="GRCInsight",
        inventory_digest=current.inventory_digest,
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[0], server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def _get(address: tuple[str, int], path: str) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection(*address, timeout=10)
    connection.putrequest("GET", path, skip_accept_encoding=True)
    connection.endheaders()
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response.status, dict(response.getheaders()), body


def _files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        assert not path.is_symlink(), path
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def _git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=str(SOURCE), check=True, capture_output=True
    ).stdout


def _tracked_site_files(revision: str) -> list[str]:
    names = _git("ls-tree", "-r", "-z", "--name-only", revision, "--", "site").decode()
    return sorted(name[len("site/") :] for name in names.split("\0") if name)


def _archive_directories(files: dict[str, bytes]) -> list[str]:
    return sorted(
        {
            match.group(1)
            for name in files
            if (match := re.match(r"^archive/([^/]+)/index\.html$", name))
        }
    )


def test_inventory_equals_git_ls_files_site_with_pinned_bytes(current):
    files = _files(current.artifact_dir)
    assert sorted(files) == _tracked_site_files(current.source_revision)
    for relative_path, content in files.items():
        blob = f"{current.source_revision}:site/{relative_path}"
        pinned = _git("cat-file", "blob", blob)
        assert content == pinned, relative_path


def test_every_file_is_served_with_its_bytes_and_type(current, address):
    files = _files(current.artifact_dir)
    for relative_path, content in files.items():
        status, headers, body = _get(address, f"/{relative_path}")
        assert status == 200, relative_path
        assert body == content, relative_path
        assert headers["Content-Type"] == CONTENT_TYPES[Path(relative_path).suffix]
        assert headers["X-Static-Artifact"] == f"GRCInsight {current.inventory_digest}"
    archives = _archive_directories(files)
    for route in [
        "/",
        "/archive/",
        "/publication-history/",
        f"/archive/{archives[0]}/",
        f"/archive/{archives[-1]}/",
    ]:
        status, headers, _ = _get(address, route)
        assert status == 200, route
        assert headers["Content-Type"] == "text/html; charset=utf-8", route


def test_json_parses_and_sitemap_lists_only_resolvable_root_pages(current, address):
    for path in current.artifact_dir.rglob("*.json"):
        json.loads(path.read_text())
    state = json.loads((current.artifact_dir / "publication-state.json").read_text())
    assert state["outcome"] in {"published", "retained"}
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [
        element.text or ""
        for element in ET.parse(current.artifact_dir / "sitemap.xml").findall(
            "sm:url/sm:loc", namespace
        )
    ]
    assert locations == [PUBLIC_ROOT, f"{PUBLIC_ROOT}publication-history/"]
    for location in locations:
        status, _, _ = _get(address, f"/{location[len(PUBLIC_ROOT):]}")
        assert status == 200, location


def test_current_report_keeps_review_map_anchors_and_retained_notice(current, address):
    status, _, body = _get(address, "/")
    served = body.decode()
    committed = _git("cat-file", "blob", f"{current.source_revision}:site/index.html")
    assert status == 200
    assert set(re.findall(r'\sid="([^"]+)"', served)) == set(
        re.findall(r'\sid="([^"]+)"', committed.decode())
    )
    targets = re.findall(r'class="review-map".*?</nav>', served, re.DOTALL)
    assert targets, "current report has a review map"
    finding_links = set(re.findall(r'href="#(finding-\d+)"', targets[0]))
    assert finding_links
    for anchor in finding_links:
        assert f'id="{anchor}"' in served, anchor
    assert f'<link rel="canonical" href="{PUBLIC_ROOT}">' in served
    state = json.loads((current.artifact_dir / "publication-state.json").read_text())
    if state["outcome"] == "retained":
        assert 'class="publication-notice"' in served


def test_archived_reports_resolve_relative_links_and_markdown(current, address):
    files = _files(current.artifact_dir)
    for directory in [_archive_directories(files)[0], _archive_directories(files)[-1]]:
        status, _, body = _get(address, f"/archive/{directory}/")
        assert status == 200, directory
        references = set(
            re.findall(
                r'(?:href|src)="(?![a-z][a-z0-9+.-]*:|//|#)([^"#?]+)', body.decode()
            )
        )
        assert references, directory
        for reference in references:
            target = posixpath.normpath(f"/archive/{directory}/{reference}")
            if reference.endswith("/"):
                target += "/"
            status, _, _ = _get(address, target)
            assert status == 200, (directory, reference)
        status, headers, markdown = _get(address, f"/archive/{directory}/report.md")
        assert status == 200, directory
        assert headers["Content-Type"] == "text/markdown; charset=utf-8"
        assert markdown == files[f"archive/{directory}/report.md"]


@pytest.mark.parametrize("route", NEGATIVE_ROUTES)
def test_implementation_private_and_unlisted_paths_return_404(address, route):
    status, _, _ = _get(address, route)
    assert status == 404
