"""Pre-register evaluation sample sizes for means of bounded per-case outcomes.

Outcomes such as selection, miss or paired-win indicators are scaled to [0, 1].
Hoeffding's inequality bounds the deviation of their sample mean without any
distributional assumption, and it also holds when cases are drawn without
replacement from a finite pool. Serfling's form tightens it by the factor
``1 - (n - 1) / N`` for a pool of size ``N``; a census has no sampling error.

These bounds choose sample sizes before data exists. Wilson or exact intervals
remain the reported estimator for observed rates, especially near zero.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math
from typing import Literal

Sided = Literal["one", "two"]
Recommendation = Literal["sample", "census"]


@dataclass(frozen=True)
class SampleSizeDesign:
    epsilon: float
    delta: float
    sided: Sided
    population: int | None
    hoeffding_n: int
    serfling_n: int | None
    recommendation: Recommendation


@dataclass(frozen=True)
class CensusCostDecision:
    population: int
    unit_cost: float
    ceiling: float
    estimated_cost: float
    recommendation: Recommendation


def _log_term(delta: float, sided: str) -> float:
    if sided not in ("one", "two"):
        raise ValueError("sided must be 'one' or 'two'")
    if not 0 < delta < 1:
        raise ValueError("delta must be in (0, 1)")
    return math.log((2 if sided == "two" else 1) / delta)


def _check_population(population: int | None, n: int | None = None) -> None:
    if population is None:
        return
    if population < 1:
        raise ValueError("population must be at least 1")
    if n is not None and population < n:
        raise ValueError("population must be at least n")


def half_width(
    n: int, delta: float, *, sided: Sided = "two", population: int | None = None
) -> float:
    """Distribution-free half-width for the mean of n outcomes in [0, 1]."""
    log_term = _log_term(delta, sided)
    if n < 1:
        raise ValueError("n must be at least 1")
    _check_population(population, n)
    if population is None:
        return math.sqrt(log_term / (2 * n))
    if n == population:
        return 0.0
    return math.sqrt((1 - (n - 1) / population) * log_term / (2 * n))


def required_sample_size(
    epsilon: float,
    delta: float,
    *,
    sided: Sided = "two",
    population: int | None = None,
) -> SampleSizeDesign:
    """Smallest n whose half-width is at most epsilon with probability 1 - delta."""
    if not 0 < epsilon < 1:
        raise ValueError("epsilon must be in (0, 1)")
    log_term = _log_term(delta, sided)
    _check_population(population)
    hoeffding_n = math.ceil(log_term / (2 * epsilon**2))
    serfling_n = None
    if population is not None:
        # half_width is nonincreasing in n and zero at a census, so bisect over
        # [1, min(hoeffding_n, population)] for the smallest qualifying n.
        low, high = 1, min(hoeffding_n, population)
        while low < high:
            middle = (low + high) // 2
            if half_width(middle, delta, sided=sided, population=population) <= epsilon:
                high = middle
            else:
                low = middle + 1
        serfling_n = low
    census = population is not None and (
        hoeffding_n >= population
        or (serfling_n is not None and serfling_n >= population)
    )
    return SampleSizeDesign(
        epsilon=epsilon,
        delta=delta,
        sided=sided,
        population=population,
        hoeffding_n=hoeffding_n,
        serfling_n=serfling_n,
        recommendation="census" if census else "sample",
    )


def census_cost_decision(
    population: int, unit_cost: float, ceiling: float
) -> CensusCostDecision:
    """Estimate census cost against an explicit ceiling; nothing is spent."""
    _check_population(population)
    if unit_cost < 0 or ceiling < 0:
        raise ValueError("unit_cost and ceiling must be nonnegative")
    estimated_cost = population * unit_cost
    return CensusCostDecision(
        population=population,
        unit_cost=unit_cost,
        ceiling=ceiling,
        estimated_cost=estimated_cost,
        recommendation="census" if estimated_cost <= ceiling else "sample",
    )


def labeling_budget_table(
    counts: Iterable[int], delta: float, *, sided: Sided = "one"
) -> dict[int, float]:
    """Map each label count to the distribution-free half-width it buys."""
    table = {count: half_width(count, delta, sided=sided) for count in counts}
    if not table:
        raise ValueError("counts must not be empty")
    return table
