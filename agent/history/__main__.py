"""History command line.

``fixture`` writes the synthetic replayable export (no provider access).
``export`` reads one bounded page from a DynamoDB table; it issues only Scan
requests, and running it against a live account is a separately approved step.
``export-report`` exports one report and the evidence it binds by key, with
GetItem calls only (at most ``1 + 2 * --max-revisions``) and never a Scan.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _keyed_tables(region: str, reports_table: str, articles_table: str):
    import boto3

    from history.table import DynamoDBTable

    client = boto3.client("dynamodb", region_name=region)
    return (
        DynamoDBTable(client, reports_table, "report_id"),
        DynamoDBTable(client, articles_table, "article_id"),
    )


def _keyed_summary(doc: dict) -> dict:
    """Counts and labels only: never report bodies or article text."""
    (report,) = doc["reports"][0]["records"]
    articles = doc["articles"][0]["records"]
    keyed = doc["reports"][0]["coverage"]["keyed_read"]
    revisions = [r for r in articles if r["record_type"] == "source_article_revision"]
    return {
        "report_id": keyed["report_id"],
        "get_item_calls": keyed["get_item_calls"],
        "missing_keys": keyed["missing_keys"],
        "outcome": report["outcome"],
        "conclusion_status": report["conclusion_status"],
        "integrity": report["integrity"]["status"],
        "provenance_class": report["provenance_class"],
        "revisions": len(revisions),
        "appearances": len(articles) - len(revisions),
        "revision_integrity": sorted({r["integrity"]["status"] for r in revisions}),
        "source_attributions": len(
            (report.get("generated_conclusions") or {}).get("source_attribution") or []
        ),
    }


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

    kx = sub.add_parser(
        "export-report", help="export one report and its bound evidence by key (GetItem only)"
    )
    kx.add_argument("--report-id", required=True)
    kx.add_argument("--reports-table", default="grcinsight-reports")
    kx.add_argument("--articles-table", default="grcinsight-articles")
    kx.add_argument("--region", default="us-east-1")
    kx.add_argument("--max-revisions", type=int, default=60)
    kx.add_argument("--include-text", action="store_true")
    kx.add_argument("--out", type=Path, help="write the document here; default stdout")

    args = parser.parse_args(argv)
    if args.command == "export-report":
        from history.export import KeyedReadBoundExceeded, ReportNotFound, export_report

        reports, articles = _keyed_tables(args.region, args.reports_table, args.articles_table)
        try:
            doc = export_report(
                reports,
                articles,
                args.report_id,
                include_text=args.include_text,
                max_revisions=args.max_revisions,
            )
        except ReportNotFound:
            print(json.dumps({"error": "report not found", "report_id": args.report_id}))
            return 2
        except KeyedReadBoundExceeded as err:
            print(json.dumps({"error": str(err), "report_id": args.report_id}))
            return 3
        text = json.dumps(doc, sort_keys=True, indent=1) + "\n"
        if args.out is None:
            sys.stdout.write(text)
            return 0
        args.out.write_text(text)
        print(json.dumps(_keyed_summary(doc), sort_keys=True))
        return 0
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
