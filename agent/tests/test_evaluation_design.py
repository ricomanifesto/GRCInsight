from dataclasses import FrozenInstanceError
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, cast

import pytest

from core.evaluation_design import (
    census_cost_decision,
    half_width,
    labeling_budget_table,
    required_sample_size,
)

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "evaluation_design.py"


@pytest.mark.parametrize(
    ("epsilon", "delta", "two_sided", "one_sided"),
    [(0.05, 0.05, 738, 600), (0.10, 0.05, 185, 150), (0.20, 0.10, 38, 29)],
)
def test_hoeffding_sample_sizes_match_pinned_values(epsilon, delta, two_sided, one_sided):
    assert required_sample_size(epsilon, delta).hoeffding_n == two_sided
    assert required_sample_size(epsilon, delta, sided="one").hoeffding_n == one_sided


def test_required_sample_size_echoes_inputs_and_is_frozen():
    design = required_sample_size(0.05, 0.05)
    assert (design.epsilon, design.delta, design.sided, design.population) == (
        0.05,
        0.05,
        "two",
        None,
    )
    assert design.serfling_n is None
    assert design.recommendation == "sample"
    with pytest.raises(FrozenInstanceError):
        setattr(design, "hoeffding_n", 1)


def test_small_population_recommends_census():
    design = required_sample_size(0.10, 0.05, sided="one", population=71)
    assert design.hoeffding_n == 150
    assert design.serfling_n is not None and design.serfling_n <= 71
    assert design.recommendation == "census"


def test_serfling_size_is_smallest_n_meeting_the_bound():
    design = required_sample_size(0.05, 0.05, population=10_000)
    assert design.serfling_n is not None
    assert design.serfling_n < design.hoeffding_n
    assert design.recommendation == "sample"
    assert half_width(design.serfling_n, 0.05, population=10_000) <= 0.05
    assert half_width(design.serfling_n - 1, 0.05, population=10_000) > 0.05


def test_half_width_matches_pinned_values():
    assert half_width(20, 0.05) == pytest.approx(0.304, abs=5e-4)
    assert half_width(600, 0.05, sided="one") == pytest.approx(0.050, abs=5e-4)


def test_serfling_half_width_shrinks_to_zero_for_a_census():
    assert half_width(20, 0.05, sided="one", population=71) == pytest.approx(0.234, abs=5e-4)
    assert half_width(50, 0.05, sided="one", population=71) == pytest.approx(0.096, abs=5e-4)
    assert half_width(71, 0.05, sided="one", population=71) == 0.0


def test_census_cost_decision_uses_explicit_ceiling():
    within = census_cost_decision(71, 0.02, 2.0)
    assert within.estimated_cost == pytest.approx(1.42)
    assert within.recommendation == "census"
    over = census_cost_decision(500, 0.02, 2.0)
    assert over.estimated_cost == pytest.approx(10.0)
    assert over.recommendation == "sample"
    assert census_cost_decision(10, 0.0, 0.0).recommendation == "census"


def test_labeling_budget_table_maps_counts_to_one_sided_bounds():
    table = labeling_budget_table([20, 150, 600], 0.05)
    assert list(table) == [20, 150, 600]
    assert table[600] == pytest.approx(0.050, abs=5e-4)
    assert table[150] == pytest.approx(math.sqrt(math.log(1 / 0.05) / 300))
    assert labeling_budget_table([20], 0.05, sided="two")[20] == pytest.approx(0.304, abs=5e-4)


@pytest.mark.parametrize(
    "call",
    [
        lambda: required_sample_size(0, 0.05),
        lambda: required_sample_size(1, 0.05),
        lambda: required_sample_size(0.05, 0),
        lambda: required_sample_size(0.05, 1),
        lambda: required_sample_size(0.05, 0.05, sided=cast(Any, "both")),
        lambda: required_sample_size(0.05, 0.05, population=0),
        lambda: half_width(0, 0.05),
        lambda: half_width(10, 1.5),
        lambda: half_width(10, 0.05, population=9),
        lambda: census_cost_decision(10, -0.01, 1.0),
        lambda: census_cost_decision(10, 0.01, -1.0),
        lambda: census_cost_decision(0, 0.01, 1.0),
        lambda: labeling_budget_table([], 0.05),
        lambda: labeling_budget_table([0], 0.05),
    ],
)
def test_invalid_design_inputs_raise(call):
    with pytest.raises(ValueError):
        call()


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args],
        text=True,
        capture_output=True,
        env={},
    )


def test_cli_prints_tables_offline_without_environment():
    process = run_cli(
        "--epsilon",
        "0.10",
        "--delta",
        "0.05",
        "--sided",
        "one",
        "--population",
        "71",
        "--counts",
        "20",
        "600",
    )
    assert process.returncode == 0, process.stderr
    assert "hoeffding_n: 150" in process.stdout
    assert "recommendation: census" in process.stdout
    assert "20\t0.2737" in process.stdout
    assert "600\t0.0500" in process.stdout


def test_cli_rejects_invalid_design_with_exit_code_two():
    process = run_cli("--epsilon", "1.5", "--delta", "0.05")
    assert process.returncode == 2
    assert "epsilon" in process.stderr
