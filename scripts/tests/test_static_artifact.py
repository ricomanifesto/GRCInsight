import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from build_static_artifact import (  # noqa: E402
    DEPLOY_CONFIG,
    StaticArtifactError,
    build_static_artifact,
    read_current_build,
)

GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_AUTHOR_DATE": "2026-01-02T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-02T00:00:00Z",
}
SITE_FILES = {
    "README.md": "# Static site\n",
    "index.html": (
        '<!doctype html><title>GRCInsight</title><a href="#finding-1">1</a>\n'
    ),
    "index.md": "# GRC Intelligence Report\n",
    "evidence-manifest.json": '{"schema_version": 1}\n',
    "publication-state.json": '{"outcome": "retained"}\n',
    "publication-history.json": '{"events": []}\n',
    "publication-history/index.html": "<!doctype html><title>History</title>\n",
    "sitemap.xml": "<urlset></urlset>\n",
    "static/app.js": "void 0;\n",
    "static/renderer.js": "void 0;\n",
    "static/style.css": "body{}\n",
    "static/favicon.ico": "ico",
    "archive/index.html": "<!doctype html><title>Archive</title>\n",
    "archive/2026-01-01T00-00-00Z/index.html": "<!doctype html><title>One</title>\n",
    "archive/2026-01-01T00-00-00Z/report.md": "# One\n",
    "archive/2026-01-01T00-00-00Z/evidence-manifest.json": "{}\n",
    "archive/2026-01-02T00-00-00Z/index.html": "<!doctype html><title>Two</title>\n",
    "archive/2026-01-02T00-00-00Z/report.md": "# Two\n",
    "archive/2026-01-02T00-00-00Z/evidence-manifest.json": "{}\n",
}
OUTSIDE_FILES = {
    ".gitignore": "data/\n",
    ".github/workflows/deploy-site.yml": "name: Deploy\n",
    "Makefile": "check-site:\n",
    "README.md": "# GRCInsight\n",
    "agent/core/report_plan.py": "PLAN = 1\n",
    "cmd/server/main.go": "package main\n",
    "configs/config.json": "{}\n",
    "internal/report/report.go": "package report\n",
    # Local fakes of the check-site gate; real content runs the real gate below.
    "scripts/build_site.py": "import sys\nassert sys.argv[1:] == ['--check']\n",
    "scripts/check_site_report.py": "print('check')\n",
    "scripts/check_site_renderer.py": "print('renderer')\n",
}


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=GIT_ENV,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class Fixture:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.source = workspace / "source"
        self.output = workspace / "store"
        self.receipts = workspace / "receipts"
        self.source.mkdir()
        _git(self.source, "init", "--quiet", "--initial-branch=main")
        for relative_path, content in SITE_FILES.items():
            _write(self.source / "site" / relative_path, content)
        for relative_path, content in OUTSIDE_FILES.items():
            _write(self.source / relative_path, content)
        self.revision = self.commit("fixture", ".")

    def build(self, **overrides):
        options = {
            "source": self.source,
            "revision": self.revision,
            "output": self.output,
            "receipts": self.receipts,
            **overrides,
        }
        return build_static_artifact(**options)

    def commit(self, message: str, *paths: str) -> str:
        _git(self.source, "add", "--all", "--force", "--", *paths)
        _git(self.source, "commit", "--quiet", "--no-gpg-sign", "-m", message)
        return _git(self.source, "rev-parse", "HEAD")


@pytest.fixture
def fixture() -> Iterator[Fixture]:
    with tempfile.TemporaryDirectory(prefix="grc-artifact-") as temp_dir:
        yield Fixture(Path(temp_dir))


def _current_digest(fixture: Fixture) -> str:
    return read_current_build(fixture.output).inventory_digest


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_publishes_the_tracked_site_tree_verbatim(fixture):
    for relative_path in [
        "site/.env",
        "site/AGENTS.md",
        "site/test-results/x.html",
        "site/build-receipt.json",
        "site/archive/2026-01-03T00-00-00Z/index.html",
    ]:
        _write(fixture.source / relative_path, "untracked\n")
    (fixture.source / "site" / "static" / "linked.css").symlink_to("style.css")

    result = fixture.build()

    assert _snapshot(result.artifact_dir) == {
        relative_path: hashlib.sha256(content.encode()).hexdigest()
        for relative_path, content in SITE_FILES.items()
    }
    assert result.file_count == len(SITE_FILES)
    assert result.total_bytes == sum(len(content) for content in SITE_FILES.values())
    assert _current_digest(fixture) == result.inventory_digest
    assert sorted(path.name for path in fixture.output.iterdir()) == [
        "builds",
        "current.json",
    ]


def test_rebuild_into_another_store_is_byte_identical(fixture):
    first = fixture.build()
    second = fixture.build(output=fixture.workspace / "second-store")
    repeat = fixture.build()

    assert len(first.inventory_digest) == 64
    assert second.inventory_digest == first.inventory_digest
    assert _snapshot(second.artifact_dir) == _snapshot(first.artifact_dir)
    assert _snapshot(second.deploy_dir) == _snapshot(first.deploy_dir)
    assert repeat.reused_existing_build is True
    assert repeat.build_dir == first.build_dir


def test_deploy_layout_carries_only_version_and_artifact_bytes(fixture):
    result = fixture.build()
    output_dir = result.deploy_dir / ".vercel" / "output"

    assert DEPLOY_CONFIG == {"version": 3}
    assert sorted(path.name for path in result.deploy_dir.iterdir()) == [".vercel"]
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "config.json",
        "static",
    ]
    assert json.loads((output_dir / "config.json").read_text()) == {"version": 3}
    assert _snapshot(output_dir / "static") == _snapshot(result.artifact_dir)


def test_receipt_binds_site_revision_and_inventory(fixture):
    result = fixture.build()
    receipt = json.loads(result.receipt_path.read_text())

    assert result.receipt_path.parent == fixture.receipts.resolve()
    assert receipt["site"] == "GRCInsight"
    assert receipt["source_revision"] == fixture.revision
    assert receipt["source_prefix"] == "site/"
    assert receipt["inventory_digest"] == result.inventory_digest
    assert [entry["path"] for entry in receipt["inventory"]] == sorted(
        SITE_FILES, key=str.encode
    )
    lines = "".join(
        f"{entry['sha256']} {entry['bytes']} {entry['path']}\n"
        for entry in receipt["inventory"]
    )
    assert hashlib.sha256(lines.encode()).hexdigest() == result.inventory_digest
    deploy_layout = receipt["deploy_layout"]
    assert deploy_layout["static_inventory_digest"] == result.inventory_digest
    assert receipt["commands"]
    assert all(command["exit_status"] == 0 for command in receipt["commands"])


def test_disk_drift_fails_and_keeps_the_last_good_build(fixture):
    accepted = fixture.build()
    before = _snapshot(fixture.output)
    _write(fixture.source / "site" / "index.html", "<p>local edit</p>\n")

    with pytest.raises(
        StaticArtifactError, match=r"site/index\.html.*differs from pinned"
    ):
        fixture.build()
    assert _snapshot(fixture.output) == before
    assert _current_digest(fixture) == accepted.inventory_digest


def test_staged_change_fails_even_when_the_worktree_matches(fixture):
    _write(fixture.source / "site" / "publication-state.json", '{"outcome": "x"}\n')
    _git(fixture.source, "add", "site/publication-state.json")
    state = fixture.source / "site" / "publication-state.json"
    _write(state, SITE_FILES["publication-state.json"])

    with pytest.raises(
        StaticArtifactError, match=r"publication-state\.json.*index differs"
    ):
        fixture.build()


def test_missing_file_fails_and_keeps_the_last_good_build(fixture):
    fixture.build()
    before = _snapshot(fixture.output)
    (fixture.source / "site" / "sitemap.xml").unlink()

    with pytest.raises(StaticArtifactError, match=r"site/sitemap\.xml.*missing"):
        fixture.build()
    assert _snapshot(fixture.output) == before


def test_revision_without_a_required_file_fails(fixture):
    _git(fixture.source, "rm", "--quiet", "site/publication-history.json")
    revision = fixture.commit("drop history", ".")

    with pytest.raises(
        StaticArtifactError, match=r"publication-history\.json.*required"
    ):
        fixture.build(revision=revision)


def test_archive_entry_without_its_report_fails(fixture):
    _git(fixture.source, "rm", "--quiet", "site/archive/2026-01-02T00-00-00Z/report.md")
    revision = fixture.commit("drop report", ".")

    with pytest.raises(
        StaticArtifactError, match=r"archive/2026-01-02T00-00-00Z/report\.md.*required"
    ):
        fixture.build(revision=revision)


def test_tracked_symlink_is_refused(fixture):
    (fixture.source / "site" / "static" / "linked.css").symlink_to("style.css")
    revision = fixture.commit("symlink", ".")

    with pytest.raises(StaticArtifactError, match=r"site/static/linked\.css.*symlink"):
        fixture.build(revision=revision)


@pytest.mark.parametrize(
    "relative_path",
    [
        "site/.env",
        "site/AGENTS.md",
        "site/test-results/x.html",
        "site/static/build-receipt.json",
        "site/static/build.log",
        "site/static/screenshot-dark.png",
        "site/static/app.js.map",
        "site/static/build_site.py",
        "site/.well-known/x.txt",
    ],
)
def test_committed_private_or_unsafe_site_paths_fail(fixture, relative_path):
    _write(fixture.source / relative_path, "planted\n")
    revision = fixture.commit(f"plant {relative_path}", ".")

    with pytest.raises(StaticArtifactError, match=relative_path[len("site/") :]):
        fixture.build(revision=revision)
    assert not (fixture.output / "current.json").exists()


def test_size_ceiling_fails_explicitly(fixture):
    with pytest.raises(StaticArtifactError, match=r"exceeds the 16-byte file ceiling"):
        fixture.build(limits={"max_file_bytes": 16, "max_total_bytes": 1 << 30})
    with pytest.raises(
        StaticArtifactError, match=r"total .* exceeds the 64-byte ceiling"
    ):
        fixture.build(limits={"max_file_bytes": 1 << 30, "max_total_bytes": 64})


@pytest.mark.parametrize("hook", ["before_promote", "before_pointer_swap"])
def test_promotion_failure_keeps_the_accepted_build(fixture, hook):
    accepted = fixture.build()
    before = _snapshot(fixture.output / accepted.build_dir)
    _write(fixture.source / "site" / "publication-state.json", '{"outcome": "next"}\n')
    revision = fixture.commit("next state", ".")

    def interrupt() -> None:
        raise RuntimeError(f"injected {hook}")

    with pytest.raises(RuntimeError, match=f"injected {hook}"):
        fixture.build(revision=revision, hooks={hook: interrupt})
    assert _current_digest(fixture) == accepted.inventory_digest
    assert _snapshot(fixture.output / accepted.build_dir) == before
    assert not [path for path in fixture.output.iterdir() if path.name.startswith(".")]


def _child_build(fixture: Fixture, revision: str, hook: str, body: str):
    script = "\n".join(
        [
            "import os, signal, sys, time",
            "from pathlib import Path",
            f"sys.path.insert(0, {str(SCRIPTS)!r})",
            "from build_static_artifact import build_static_artifact",
            "def hook():",
            *(f"    {line}" for line in body.splitlines()),
            "build_static_artifact(",
            f"    source=Path({str(fixture.source)!r}),",
            f"    revision={revision!r},",
            f"    output=Path({str(fixture.output)!r}),",
            f"    receipts=Path({str(fixture.receipts)!r}),",
            f"    hooks={{{hook!r}: hook}},",
            ")",
        ]
    )
    return subprocess.Popen([sys.executable, "-B", "-c", script], env=GIT_ENV)


def test_interrupted_promotion_blocks_until_the_stale_lock_is_cleared(fixture):
    accepted = fixture.build()
    before = _snapshot(fixture.output / accepted.build_dir)
    _write(fixture.source / "site" / "publication-state.json", '{"outcome": "cut"}\n')
    revision = fixture.commit("interrupted", ".")

    child = _child_build(
        fixture, revision, "before_pointer_swap", "os.kill(os.getpid(), signal.SIGKILL)"
    )
    assert child.wait(timeout=60) == -signal.SIGKILL
    assert _current_digest(fixture) == accepted.inventory_digest
    assert _snapshot(fixture.output / accepted.build_dir) == before
    with pytest.raises(
        StaticArtifactError, match=r"(?s)locked by pid \d+.*not running"
    ):
        fixture.build(revision=revision)

    (fixture.output / ".lock").unlink()
    recovered = fixture.build(revision=revision)
    assert recovered.inventory_digest != accepted.inventory_digest
    assert _current_digest(fixture) == recovered.inventory_digest
    assert not [p for p in fixture.output.iterdir() if p.name.startswith(".staging-")]


def test_second_writer_fails_while_the_first_holds_the_lock(fixture):
    paused = fixture.workspace / "paused"
    release = fixture.workspace / "release"
    child = _child_build(
        fixture,
        fixture.revision,
        "before_promote",
        f"Path({str(paused)!r}).touch()\n"
        f"while not Path({str(release)!r}).exists():\n"
        "    time.sleep(0.025)",
    )
    try:
        deadline = time.monotonic() + 60
        while not paused.exists():
            assert child.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.025)
        with pytest.raises(StaticArtifactError, match=r"locked by pid \d+"):
            fixture.build()
    finally:
        release.touch()
    assert child.wait(timeout=60) == 0
    assert _current_digest(fixture)


def test_unsafe_outputs_and_revisions_are_refused(fixture):
    with pytest.raises(StaticArtifactError, match="inside the source tree"):
        fixture.build(output=fixture.source / "public")
    with pytest.raises(StaticArtifactError, match="inside the output store"):
        fixture.build(receipts=fixture.output / "receipts")
    with pytest.raises(StaticArtifactError, match="full commit id"):
        fixture.build(revision="HEAD")
    with pytest.raises(StaticArtifactError, match="not a commit"):
        fixture.build(revision="0" * 40)


ROOT = SCRIPTS.parent


class CommittedContent:
    """A disposable clone of the committed site with one accepted build."""

    def __init__(self, workspace: Path) -> None:
        self.template = workspace / "template"
        _git(
            ROOT,
            "clone",
            "--quiet",
            "--shared",
            "--no-checkout",
            str(ROOT),
            str(self.template / "source"),
        )
        source = self.template / "source"
        _git(source, "reset", "--quiet")
        _git(source, "checkout", "--quiet", "HEAD", "--", "site")
        self.revision = _git(self.template / "source", "rev-parse", "HEAD")
        self.accepted = build_static_artifact(
            source=self.template / "source",
            revision=self.revision,
            output=self.template / "store",
            receipts=workspace / "receipts",
        )

    def copy(self, destination: Path) -> Fixture:
        shutil.copytree(self.template, destination, symlinks=True)
        fixture = Fixture.__new__(Fixture)
        fixture.workspace = destination
        fixture.source = destination / "source"
        fixture.output = destination / "store"
        fixture.receipts = destination / "receipts"
        fixture.revision = self.revision
        return fixture


@pytest.fixture(scope="module")
def committed() -> Iterator[CommittedContent]:
    with tempfile.TemporaryDirectory(prefix="grc-committed-") as temp_dir:
        yield CommittedContent(Path(temp_dir))


def test_committed_content_passes_the_check_site_gate_before_promotion(committed):
    receipt = json.loads(committed.accepted.receipt_path.read_text())
    commands = [" ".join(command["argv"]) for command in receipt["commands"]]

    for script in [
        "build_site.py --check",
        "check_site_report.py",
        "check_site_renderer.py",
    ]:
        assert any(script in command for command in commands), script


@pytest.mark.parametrize(
    ("relative_path", "change", "expected"),
    [
        (
            "site/publication-history.json",
            lambda text: text[:-8],
            r"publication-history\.json is not valid JSON",
        ),
        (
            "site/archive/INDEX/evidence-manifest.json",
            lambda text: text + "}",
            r"evidence-manifest\.json is not valid JSON",
        ),
        (
            "site/sitemap.xml",
            lambda text: text.replace("</urlset>", ""),
            r"sitemap\.xml is not well-formed XML",
        ),
        (
            "site/index.md",
            lambda text: text + "\nAn unrendered paragraph.\n",
            r"(?s)check-site gate .*build_site\.py.*exit status",
        ),
    ],
)
def test_invalid_committed_content_fails_and_keeps_the_accepted_build(
    committed, relative_path, change, expected
):
    # A self-deleting directory: each copy holds about 54 MB of site and store.
    with tempfile.TemporaryDirectory(prefix="grc-invalid-") as temp_dir:
        _assert_invalid_content_keeps_accepted_build(
            committed, Path(temp_dir), relative_path, change, expected
        )


def _assert_invalid_content_keeps_accepted_build(
    committed, workspace, relative_path, change, expected
):
    fixture = committed.copy(workspace / "copy")
    before = _snapshot(fixture.output)
    if "/INDEX/" in relative_path:
        newest = sorted((fixture.source / "site" / "archive").glob("*Z"))[-1].name
        relative_path = relative_path.replace("INDEX", newest)
    target = fixture.source / relative_path
    target.write_text(change(target.read_text()))
    revision = fixture.commit(f"invalid {relative_path}", relative_path)

    with pytest.raises(StaticArtifactError, match=expected):
        fixture.build(revision=revision)
    assert _snapshot(fixture.output) == before
    assert _current_digest(fixture) == committed.accepted.inventory_digest
