"""Document dates attested by structured publisher metadata, never inferred from prose."""

from datetime import date, datetime
import re
from typing import Any
from urllib.parse import urlsplit


def federal_register_api_url(source_url: str) -> str | None:
    """Resolve only a bounded Federal Register document identity to its fixed API."""
    try:
        parsed = urlsplit(source_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"www.federalregister.gov", "federalregister.gov"}
            or parsed.port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
        ):
            return None
        match = re.fullmatch(
            r"/documents/\d{4}/\d{2}/\d{2}/(\d{4}-\d{4,6})(?:/[^/]+)?/?", parsed.path
        )
        if match:
            return f"https://www.federalregister.gov/api/v1/documents/{match[1]}.json"
    except ValueError:
        pass
    return None


def document_effective_date(source: dict[str, Any]) -> str | None:
    """Validate a retained ingestion receipt and return the provider's document date.

    The receipt is written by source ingestion from the publisher API response.
    It is not a model-produced field or an independent interpretation of legal text.
    Publication checks are offline and trust the same retained source metadata as
    the other source-evidence fields; this is not a cryptographic attestation.
    """
    evidence = source.get("effective_date_evidence")
    if evidence is None:
        return None
    error = "invalid document effective date evidence"
    if not isinstance(evidence, dict):
        raise ValueError(error)
    api_url = federal_register_api_url(str(source.get("url") or ""))
    document = evidence.get("document")
    if (
        not api_url
        or evidence.get("provider") != "federal-register-api-v1"
        or evidence.get("api_url") != api_url
        or not isinstance(document, dict)
        or document.get("type") != "Rule"
        or federal_register_api_url(str(document.get("html_url") or "")) != api_url
        or api_url.rsplit("/", 1)[1] != f"{document.get('document_number')}.json"
    ):
        raise ValueError(error)
    value = document.get("effective_on")
    retrieved_at = evidence.get("retrieved_at")
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(error)
    if not isinstance(retrieved_at, str):
        raise ValueError(error)
    try:
        date.fromisoformat(value)
        timestamp = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError(error)
    except ValueError as cause:
        raise ValueError(error) from cause
    return value
