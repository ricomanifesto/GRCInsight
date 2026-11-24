"""PR tokens are bounded and workflow dependencies are immutable."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def test_all_external_actions_are_pinned_to_immutable_commits():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        for action in re.findall(r"uses:\s*(\S+)", path.read_text()):
            assert action.startswith("./") or re.fullmatch(
                r"[^@]+@[a-f0-9]{40}", action
            ), (
                path.name,
                action,
            )


def test_pull_request_ci_token_is_explicitly_read_only():
    source = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "\npermissions:\n  contents: read\n" in source
    assert "\n    permissions:" not in source
    assert "pull_request:" in source


def test_repository_script_contracts_run_in_ci():
    source = (ROOT / ".github/workflows/ci.yml").read_text()
    assert (
        "uv run --project agent python -m pytest -q scripts/tests -p no:cacheprovider"
        in source
    )
