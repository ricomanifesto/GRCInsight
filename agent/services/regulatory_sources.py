"""Bounded, optional ingestion of publisher-owned regulatory date metadata."""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any

import httpx
from loguru import logger

from core.regulatory_dates import document_effective_date, federal_register_api_url
from core.runtime import earliest_deadline, get_model_deadline

DOCUMENT_FIELDS = ("document_number", "html_url", "type", "effective_on")


async def enrich_regulatory_sources(
    sources: list[dict[str, Any]], *, model_deadline: float | None = None
) -> list[dict[str, Any]]:
    """Attach fresh provider receipts to the workflow's already bounded source set.

    Ignore incoming date receipts. Only this direct API read can populate them.
    Unsupported sources and failed/null lookups retain Unknown dates. Validation
    and rendering never fetch the network or guess missing dates from prose.
    """
    enriched = [{**source, "effective_date_evidence": None} for source in sources]
    targets: dict[str, list[dict[str, Any]]] = {}
    for source in enriched:
        api_url = federal_register_api_url(str(source.get("url") or ""))
        if api_url:
            targets.setdefault(api_url, []).append(source)
    deadline = earliest_deadline(model_deadline, get_model_deadline())
    budget = min(5.0, deadline - time.monotonic()) if deadline is not None else 5.0
    if not targets or budget <= 0:
        return enriched

    async with httpx.AsyncClient(timeout=min(2.0, budget), follow_redirects=False) as client:

        async def fetch_records() -> None:
            for api_url, matching_sources in targets.items():
                try:
                    response = await client.get(
                        api_url, params=[("fields[]", field) for field in DOCUMENT_FIELDS]
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ValueError("document response must be an object")
                    receipt = {
                        "provider": "federal-register-api-v1",
                        "api_url": api_url,
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "document": {field: payload.get(field) for field in DOCUMENT_FIELDS},
                    }
                    for source in matching_sources:
                        document_effective_date({**source, "effective_date_evidence": receipt})
                    for source in matching_sources:
                        source["effective_date_evidence"] = receipt
                except (httpx.HTTPError, ValueError):
                    logger.warning("Regulatory date metadata unavailable; retaining Unknown")

        try:
            await asyncio.wait_for(fetch_records(), timeout=budget)
        except TimeoutError:
            logger.warning("Regulatory metadata budget exhausted; retaining Unknown dates")
    return enriched
