"""Pages installation must be bounded without bypassing package or reader gates."""

from pathlib import Path
from argparse import Namespace
import runpy
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/configure_pages_apt.py"


def configure(tmp_path, contents):
    mirror = tmp_path / "apt-mirrors.txt"
    config = tmp_path / "99pages-acquire"
    mirror.write_text(contents)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--mirror-list", str(mirror), "--config", str(config)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result, mirror, config


def test_runner_mirror_preserves_metadata_and_other_repositories(tmp_path):
    original = (
        "# Ubuntu mirrors\n"
        "http://azure.archive.ubuntu.com/ubuntu/ priority:1\n"
        "https://archive.ubuntu.com/ubuntu/ priority:2\n"
    )
    result, mirror, config = configure(tmp_path, original)
    assert result.returncode == 0, result.stderr
    assert mirror.read_text() == original.replace(
        "http://azure.archive.ubuntu.com/ubuntu/", "https://archive.ubuntu.com/ubuntu/"
    )
    settings = config.read_text()
    assert 'Acquire::Retries "2";' in settings
    assert 'Acquire::http::Timeout "30";' in settings
    assert 'Acquire::https::Timeout "30";' in settings
    assert 'APT::Update::Error-Mode "any";' in settings
    assert "AllowUnauthenticated" not in settings
    assert "AllowInsecure" not in settings


@pytest.mark.parametrize(
    "contents",
    ["https://unexpected.example/ubuntu\n", "http://azure.archive.ubuntu.com/ubuntu-evil\n"],
)
def test_unknown_runner_mirrors_fail_before_any_write(tmp_path, contents):
    result, mirror, config = configure(tmp_path, contents)
    assert result.returncode != 0
    assert mirror.read_text() == contents
    assert not config.exists()


def test_configuration_is_idempotent(tmp_path):
    result, mirror, config = configure(tmp_path, "https://archive.ubuntu.com/ubuntu\n")
    assert result.returncode == 0
    namespace = runpy.run_path(str(SCRIPT))
    before = mirror.read_bytes(), config.read_bytes()
    namespace["configure"](mirror, config)
    assert (mirror.read_bytes(), config.read_bytes()) == before


def test_default_config_loads_after_runner_retry_override(monkeypatch, tmp_path):
    namespace = runpy.run_path(str(SCRIPT))
    captured = []
    mirror = tmp_path / "mirrors"
    mirror.write_text("https://archive.ubuntu.com/ubuntu\n")

    def parse_args(parser):
        captured.append(parser.get_default("config"))
        return Namespace(mirror_list=mirror, config=tmp_path / "config")

    monkeypatch.setattr(namespace["argparse"].ArgumentParser, "parse_args", parse_args)
    namespace["main"]()
    default = captured[0]
    assert default.parent == Path("/etc/apt/apt.conf.d")
    assert default.name.encode("ascii") > b"zz-retries"


def test_workflow_keeps_install_and_visual_gates_mandatory():
    workflow = (ROOT / ".github/workflows/deploy-site.yml").read_text()
    dependency = workflow.index("- name: Install Chromium system dependencies")
    browser = workflow.index("- name: Install Chromium\n")
    capture = workflow.index("- name: Capture dark and light reader evidence")
    upload = workflow.index("- name: Upload Pages artifact")
    assert dependency < browser < capture < upload
    for section in [workflow[dependency:browser], workflow[browser:capture]]:
        assert "timeout-minutes: 5" in section
        assert "continue-on-error" not in section
    assert "sudo python3 scripts/configure_pages_apt.py" in workflow
    assert "playwright@1.62.1 install-deps chromium" in workflow
    assert "playwright@1.62.1 install chromium" in workflow
    assert "--with-deps" not in workflow
    assert "--color-scheme dark" in workflow and "--color-scheme light" in workflow
    assert "if-no-files-found: error" in workflow
