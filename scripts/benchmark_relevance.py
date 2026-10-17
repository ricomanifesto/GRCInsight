"""Validate replay cases locally; run paid model calls only with --run-paid.

With --corpus, validate a labeled JSONL corpus. Adding --recordings replays
recorded decision responses offline through the enabled route.
"""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "agent"))

from config.settings import settings  # noqa: E402
from core.relevance_benchmark import (  # noqa: E402
    RecordedResponses,
    load_gate_spec,
    load_recordings,
    replay_corpus,
    run_comparison,
)
from core.relevance_corpus import SPLITS, load_corpus  # noqa: E402
from models.api import ArticleInput  # noqa: E402
from services.model_service import GRCModelService  # noqa: E402
from services.relevance_decisions import LABELS, MAX_ARTICLES, MAX_BATCH_ARTICLES  # noqa: E402

GATE_TEMPLATE = REPO_ROOT / "docs" / "relevance-gate-spec.template.json"
MAX_INPUT_BYTES = 16 * 1024 * 1024


def _check_size(parser: argparse.ArgumentParser, path: Path) -> None:
    if path.stat().st_size > MAX_INPUT_BYTES:
        parser.error(f"{path.name} exceeds 16 MiB")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_corpus(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    _check_size(parser, args.corpus)
    validation = load_corpus(args.corpus)
    if validation.errors or not args.recordings:
        print(json.dumps({**validation.summary(), "status": "validated_only", "network_calls": 0}))
        if validation.errors:
            sys.exit(1)
        return
    if args.output_dir is None:
        parser.error("--recordings requires --output-dir")
    _check_size(parser, args.recordings)
    try:
        recordings = load_recordings(args.recordings.read_text(encoding="utf-8").splitlines())
        spec_path = args.gate_spec or GATE_TEMPLATE
        spec = load_gate_spec(spec_path)
        rows, summary = asyncio.run(
            replay_corpus(
                validation,
                RecordedResponses(recordings),
                split=args.split,
                thresholds=args.threshold or [settings.grc_relevance_min_probability],
                focus_areas=tuple(settings.analysis_focus_areas),
                batch_size=args.batch_size,
                gate_spec=spec,
            )
        )
    except ValueError as error:
        parser.error(str(error))
    summary["gate_spec"] = {"file": spec_path.name, "sha256": _sha256(spec_path)}
    summary["inputs"] = {
        "corpus_sha256": _sha256(args.corpus),
        "recordings_sha256": _sha256(args.recordings),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    selections = args.output_dir / "selections.jsonl"
    selections.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "replayed",
                "network_calls": 0,
                "split": args.split,
                "overall": [
                    (result["gates"] or {}).get("overall") for result in summary["results"]
                ],
                "outputs": {
                    selections.name: _sha256(selections),
                    summary_path.name: _sha256(summary_path),
                },
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "cases", type=Path, nargs="?", help="JSON array of {article, expected} records"
    )
    parser.add_argument(
        "--run-paid",
        action="store_true",
        help="Explicitly allow inference using OPENROUTER_API_KEY",
    )
    parser.add_argument("--repeats", type=int, choices=range(1, 11), default=3)
    parser.add_argument("--corpus", type=Path, help="Labeled JSONL corpus to validate or replay")
    parser.add_argument("--recordings", type=Path, help="Recorded decision responses (JSONL)")
    parser.add_argument("--split", choices=SPLITS, default="development")
    parser.add_argument(
        "--threshold",
        type=float,
        action="append",
        help="Selected-label threshold; repeat to sweep the development split",
    )
    parser.add_argument("--batch-size", type=int, default=MAX_BATCH_ARTICLES)
    parser.add_argument("--gate-spec", type=Path, help="Gate spec; defaults to the template")
    parser.add_argument("--output-dir", type=Path, help="Directory for replay outputs")
    args = parser.parse_args()
    if (args.cases is None) == (args.corpus is None):
        parser.error("Give either a cases file or --corpus")
    if args.corpus is not None:
        if args.run_paid:
            parser.error("Corpus replay never makes paid calls")
        run_corpus(parser, args)
        return
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
    report = asyncio.run(run_comparison(articles, expected, GRCModelService, repeats=args.repeats))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
