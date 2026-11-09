"""History command line.

``fixture`` writes the synthetic replayable export (no provider access).
``export`` reads one bounded page from a DynamoDB table; it issues only Scan
requests, and running it against a live account is a separately approved step.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m history")
    sub = parser.add_subparsers(dest="command", required=True)

    fx = sub.add_parser("fixture", help="write the synthetic export fixture")
    fx.add_argument("--out", type=Path, required=True)
    fx.add_argument("--limit", type=int, default=3)

    ex = sub.add_parser("export", help="read one bounded export page (Scan only)")
    ex.add_argument("--stream", choices=("reports", "articles"), required=True)
    ex.add_argument("--table", required=True)
    ex.add_argument("--region", default="us-east-1")
    ex.add_argument("--limit", type=int, default=25)
    ex.add_argument("--cursor")
    ex.add_argument("--updated-since")
    ex.add_argument("--include-text", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "fixture":
        from history.fixture import write_fixture

        check = write_fixture(args.out, limit=args.limit)
        print(json.dumps(check, sort_keys=True))
        ok = check["replay_identical"] and check["duplicate_record_revisions"] == 0
        return 0 if ok else 1

    import boto3

    from history.export import export_page
    from history.table import DynamoDBTable

    key = "report_id" if args.stream == "reports" else "article_id"
    table = DynamoDBTable(boto3.client("dynamodb", region_name=args.region), args.table, key)
    page = export_page(
        table,
        stream=args.stream,
        cursor=args.cursor,
        limit=args.limit,
        updated_since=args.updated_since,
        include_text=args.include_text,
    )
    json.dump(page, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
