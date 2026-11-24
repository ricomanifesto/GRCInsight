"""Workflow outputs are data at the shell boundary, including retry paths."""

from pathlib import Path
import textwrap

import pytest

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github/workflows/lambda-report-generation.yml"
)


def assert_data_boundary(source, name, bindings):
    block = source.split(f"    - name: {name}\n", 1)[1].split("\n    - name:", 1)[0]
    metadata, shell = block.split("      run: |\n", 1)
    for variable, expression in bindings.items():
        assert f"{variable}: ${{{{ {expression} }}}}" in metadata
        assert f'"${variable}"' in shell
    assert "${{" not in textwrap.dedent(shell)


@pytest.mark.parametrize(
    "name,bindings",
    [
        ("Retrieve generated report", {"REPORT_ID": "steps.handle.outputs.REPORT_ID"}),
        (
            "Persist retained publication state",
            {
                "ATTEMPTED_AT": "steps.get-report.outputs.attempted_at",
                "REFUSAL_CATEGORY": "steps.get-report.outputs.refusal_category",
            },
        ),
        (
            "Commit and push report",
            {
                "FEED_URL": "steps.feed-url.outputs.FEED_URL",
                "PUBLISHED_AT": "steps.get-report.outputs.published_at",
            },
        ),
    ],
)
def test_generation_output_values_enter_shell_via_environment(name, bindings):
    assert_data_boundary(WORKFLOW.read_text(), name, bindings)
