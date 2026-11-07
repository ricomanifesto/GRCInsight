"""Print pre-registered sample sizes and labeling budgets for relevance evaluation.

Offline: makes no network calls, reads no files or environment variables.

Exit codes:
  0  tables printed
  2  invalid arguments or design inputs
"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

from core.evaluation_design import labeling_budget_table, required_sample_size  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--epsilon", type=float, required=True, help="Target half-width")
    parser.add_argument("--delta", type=float, required=True, help="Failure probability")
    parser.add_argument("--sided", choices=("one", "two"), default="two")
    parser.add_argument("--population", type=int, help="Finite pool size, e.g. archived issues")
    parser.add_argument(
        "--counts",
        type=int,
        nargs="+",
        default=[20, 50, 100, 150, 300, 600],
        help="Label counts for the labeling-budget table",
    )
    args = parser.parse_args(argv)
    try:
        design = required_sample_size(
            args.epsilon, args.delta, sided=args.sided, population=args.population
        )
        budget = labeling_budget_table(args.counts, args.delta, sided=args.sided)
    except ValueError as error:
        parser.error(str(error))
    print("Required sample size")
    for field in (
        "epsilon",
        "delta",
        "sided",
        "population",
        "hoeffding_n",
        "serfling_n",
        "recommendation",
    ):
        print(f"{field}: {getattr(design, field)}")
    print()
    print(f"Labeling budget ({args.sided}-sided, delta={args.delta}, distribution-free)")
    print("labels\thalf_width")
    for count, width in budget.items():
        print(f"{count}\t{width:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
