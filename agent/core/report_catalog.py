"""The application-owned report catalog, read from versioned contract files.

Control labels, review questions, decisions, reference controls, priorities,
sectors, finding labels, risk keywords and regulatory publishers are authored once
in ``core/contracts/report-catalog-v6.json``. The provider response schema for
report plans lives in ``core/contracts/report-v6.schema.json``. Both sit beside the
modules that read them, so publication checks need only ``agent/core``. Tests keep
the browser renderer's copies of the labels in step with the catalog.
"""

import json
from pathlib import Path
from typing import Any

CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"
CATALOG_PATH = CONTRACTS_DIR / "report-catalog-v6.json"
SCHEMA_PATH = CONTRACTS_DIR / "report-v6.schema.json"

CATALOG: dict[str, Any] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def report_plan_schema() -> dict[str, Any]:
    """A fresh copy of the provider schema for report plans."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
