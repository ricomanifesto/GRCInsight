"""Retained article-field evidence used by new control findings.

The headline is identity, not an article evidence segment. This receipt records
which input field supplied the exact normalized passage; it does not attest the
publisher's truth or recover provenance from an old flattened snippet.
"""

import re
import unicodedata
from typing import Any

ORIGINS = ("summary", "content")
MAX_SEGMENT_LENGTH = 700


def _bounded_text(value: str) -> str:
    text = " ".join(value.split())
    if len(text) > MAX_SEGMENT_LENGTH:
        # Cut at whitespace, never manufacture a partial word beyond a headline.
        end = text.rfind(" ", 0, MAX_SEGMENT_LENGTH + 1)
        text = text[:end] if end >= 0 else ""
    return text


def capture_article_evidence(*, summary: str, content: str) -> list[dict[str, str]]:
    return [
        {"origin": origin, "text": text}
        for origin, value in (("summary", summary), ("content", content))
        if (text := _bounded_text(value))
    ]


def article_segments(source: dict[str, Any]) -> dict[str, str]:
    segments = source.get("article_evidence")
    if not isinstance(segments, list) or len(segments) > len(ORIGINS):
        raise ValueError("source requires bounded retained article evidence")
    by_origin: dict[str, str] = {}
    for segment in segments:
        if not isinstance(segment, dict) or set(segment) != {"origin", "text"}:
            raise ValueError("article evidence segment has unsupported fields")
        origin, text = segment["origin"], segment["text"]
        if not isinstance(origin, str) or origin not in ORIGINS or origin in by_origin:
            raise ValueError("article evidence segment has invalid or duplicate origin")
        if (
            not isinstance(text, str)
            or not 1 <= len(text) <= MAX_SEGMENT_LENGTH
            or " ".join(text.split()) != text
        ):
            raise ValueError("article evidence must retain normalized bounded text")
        by_origin[origin] = text
    return by_origin


def has_non_headline_text(text: str, title: str) -> bool:
    """Require lexical evidence beyond the headline, regardless of repetitions.

    This conservative eligibility check is not a semantic quality score. It can
    reject useful text that reuses only headline words; editorial review still
    decides whether newly supplied words actually add useful information.
    """

    def words(value: str) -> set[str]:
        return set(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold()))

    return bool(words(text) - words(title))


def eligible_article_segments(source: dict[str, Any]) -> dict[str, str]:
    return {
        origin: text
        for origin, text in article_segments(source).items()
        if len(text) >= 40 and has_non_headline_text(text, str(source.get("title", "")))
    }
