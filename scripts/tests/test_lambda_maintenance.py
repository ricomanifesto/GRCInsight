"""Maintenance pauses defer Go invocation rather than masking unhealthy results."""

import pytest

from scripts import check_lambda_maintenance as check


@pytest.mark.parametrize(
    "value,expected",
    [
        ({}, "available"),
        ({"ReservedConcurrentExecutions": 0}, "paused"),
        ({"ReservedConcurrentExecutions": 2}, "available"),
    ],
)
def test_known_control_plane_concurrency_has_explicit_health_mode(value, expected):
    assert check.mode(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"error": "unknown"},
        {"ReservedConcurrentExecutions": None},
        {"ReservedConcurrentExecutions": False},
        {"ReservedConcurrentExecutions": -1},
        {"ReservedConcurrentExecutions": "0"},
    ],
)
def test_unknown_concurrency_refuses(value):
    with pytest.raises(ValueError):
        check.mode(value)
