"""Shared reporting identity used by every GRCInsight publication layer."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import ipaddress
import re
from typing import Any
import unicodedata
from urllib.parse import quote, unquote_to_bytes, urlparse, urlsplit


class ReportingIdentityError(ValueError):
    """Raised when public reporting identity cannot be safely derived."""


def _dot_segment(value: str) -> str | None:
    folded = value.casefold()
    if folded in {".", "%2e"}:
        return "."
    if folded in {"..", ".%2e", "%2e.", "%2e%2e"}:
        return ".."
    return None


def _normalize_reporting_path(value: str) -> str:
    path = value or "/"
    output: list[str] = []
    for index, segment in enumerate(path.split("/")):
        kind = _dot_segment(segment)
        if kind == ".":
            continue
        if kind == "..":
            if output and not (len(output) == 1 and output[0] == ""):
                output.pop()
            continue
        if index == 0 and path.startswith("/"):
            output.append("")
        elif index > 0 or segment:
            output.append(segment)
    normalized = "/".join(output) or "/"
    if path.startswith("/") and not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if _dot_segment(path.rsplit("/", 1)[-1]) and not normalized.endswith("/"):
        normalized += "/"
    return quote(normalized, safe="/!$&'()*+,-.:;=@_~%")


def _normalize_special_url_slashes(value: str) -> str:
    boundary = min(
        (position for marker in ("?", "#") if (position := value.find(marker)) >= 0),
        default=len(value),
    )
    return value[:boundary].replace("\\", "/") + value[boundary:]


def _idna_hostname(value: str) -> str:
    labels: list[str] = []
    for label in unicodedata.normalize("NFC", value).split("."):
        lowered = label.lower()
        if not lowered or lowered.isascii():
            labels.append(lowered)
        else:
            labels.append(f"xn--{lowered.encode('punycode').decode('ascii')}")
    return ".".join(labels)


def normalize_reporting_url(value: Any) -> str:
    """Return the WHATWG-aligned identity pinned by reporting-identity-v1."""
    raw_url = _normalize_special_url_slashes(str(value or "").strip())
    try:
        parsed = urlsplit(raw_url)
    except ValueError as error:
        raise ReportingIdentityError("reporting URL must be a credential-free HTTP URL") from error
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        raise ReportingIdentityError("reporting URL must be a credential-free HTTP URL")
    raw_hostname = parsed.hostname or ""
    if not raw_hostname or re.search(r"[\x00-\x20\x7f]", raw_hostname):
        raise ReportingIdentityError("reporting URL must include a hostname")
    try:
        address = ipaddress.ip_address(raw_hostname)
    except ValueError:
        try:
            if re.search(r"%(?![0-9a-fA-F]{2})", raw_hostname):
                raise ValueError("malformed hostname percent escape")
            decoded_hostname = unquote_to_bytes(raw_hostname).decode("utf-8")
            if re.search(r"[\x00-\x20\x7f#/:<>?@\[\\\]^|]", decoded_hostname):
                raise ValueError("forbidden hostname code point")
            hostname = _idna_hostname(decoded_hostname)
        except (UnicodeError, ValueError) as error:
            raise ReportingIdentityError("reporting URL must include a valid hostname") from error
    else:
        hostname = f"[{address.compressed}]" if address.version == 6 else address.compressed
    try:
        port = parsed.port
    except ValueError as error:
        raise ReportingIdentityError("reporting URL contains an invalid port") from error
    if port is not None and not (
        (parsed.scheme.lower() == "http" and port == 80)
        or (parsed.scheme.lower() == "https" and port == 443)
    ):
        hostname = f"{hostname}:{port}"
    path = _normalize_reporting_path(parsed.path)
    query = quote(parsed.query, safe="!$&()*+,-./:;=?@_~%")
    before_fragment = raw_url.split("#", 1)[0]
    query_suffix = f"?{query}" if parsed.query or "?" in before_fragment else ""
    return f"{parsed.scheme.lower()}://{hostname}{path}{query_suffix}"


def reporting_fragment(article_url: Any) -> str:
    article = normalize_reporting_url(article_url)
    digest = hashlib.sha256(article.encode("utf-8")).hexdigest()[:12]
    return f"reporting-{digest}"


def sentrydigest_issue_date(value: Any) -> str:
    """Return the UTC issue date attested by a timezone-aware feed timestamp."""
    raw_value = str(value or "").strip()
    if not raw_value:
        raise ReportingIdentityError(
            "feed lastBuildDate is required for dated SentryDigest handoffs"
        )
    try:
        parsed = parsedate_to_datetime(raw_value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ReportingIdentityError("feed lastBuildDate must be a valid timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReportingIdentityError("feed lastBuildDate must include a timezone")
    return parsed.astimezone(timezone.utc).date().isoformat()


def sentrydigest_issue_url(feed_home_url: Any, issue_date: Any) -> str:
    feed_home = normalize_reporting_url(feed_home_url)
    if urlparse(feed_home).query:
        raise ReportingIdentityError("feed home URL must not include a query")
    raw_date = str(issue_date or "").strip()
    try:
        canonical_date = datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()
    except ValueError as error:
        raise ReportingIdentityError("SentryDigest issue date must use YYYY-MM-DD") from error
    return f"{feed_home.rstrip('/')}/archive/{canonical_date}/"


def sentrydigest_item_url(feed_home_url: Any, issue_date: Any, article_url: Any) -> str:
    return (
        f"{sentrydigest_issue_url(feed_home_url, issue_date)}" f"#{reporting_fragment(article_url)}"
    )


def legacy_sentrydigest_item_url(feed_home_url: Any, article_url: Any) -> str:
    return f"{normalize_reporting_url(feed_home_url)}#{reporting_fragment(article_url)}"
