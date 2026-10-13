"""Validate replay cases locally; run paid model calls only with --run-paid."""

import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

from config.settings import settings  # noqa: E402
from core.relevance_benchmark import run_comparison  # noqa: E402
from models.api import ArticleInput  # noqa: E402
from services.model_service import GRCModelService  # noqa: E402
from services.relevance_decisions import (
    LABELS,
    MAX_ARTICLES,
)  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path, help="JSON array of {article, expected} records")
    parser.add_argument(
        "--run-paid",
        action="store_true",
        help="Explicitly allow inference using OPENROUTER_API_KEY",
    )
    parser.add_argument("--repeats", type=int, choices=range(1, 11), default=3)
    args = parser.parse_args()
    raw = args.cases.read_bytes()
    if len(raw) > 1024 * 1024:
        parser.error("Cases file exceeds 1 MiB")
    try:
        cases = json.loads(raw)
        if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_ARTICLES:
            raise ValueError("case count")
        articles, expected = [], []
        for case in cases:
            if (
                not isinstance(case, dict)
                or set(case) != {"article", "expected"}
                or case["expected"] not in LABELS
            ):
                raise ValueError("case schema")
            articles.append(ArticleInput.model_validate(case["article"]))
            expected.append(case["expected"])
    except (ValueError, TypeError, KeyError):
        parser.error("Invalid cases; require 1-64 article/expected pairs with valid labels")
    if not args.run_paid:
        print(json.dumps({"cases": len(articles), "status": "validated_only", "network_calls": 0}))
        return
    if not settings.openrouter_api_key:
        parser.error("OPENROUTER_API_KEY is required for --run-paid")
    # Only this replay process changes mode; no deployment configuration is written.
    settings.grc_relevance_mode = "enabled"
    model = GRCModelService()
    report = asyncio.run(run_comparison(articles, expected, model, repeats=args.repeats))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
