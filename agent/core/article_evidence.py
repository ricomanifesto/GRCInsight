"""Retained article-field evidence used by new control findings.

The headline is identity, not an article evidence segment. This receipt records
which input field supplied the exact normalized passage; it does not attest the
publisher's truth or recover provenance from an old flattened snippet.
"""

import unicodedata
from html import unescape
from html.parser import HTMLParser
from typing import Any

ORIGINS = ("summary", "content")
MAX_SEGMENT_LENGTH = 700
MAX_RAW_BYTES = 4096
EXTRACTION_VERSION = 1

# This is a conservative static-text contract, not a browser/CSS interpreter.
# Unsupported presentation may hide text, so it refuses the entire field.
_BLOCKS = {
    "html",
    "body",
    "article",
    "section",
    "div",
    "p",
    "blockquote",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "td",
    "th",
    "figure",
    "figcaption",
}
_INLINE = {
    "a",
    "abbr",
    "b",
    "strong",
    "i",
    "em",
    "u",
    "s",
    "span",
    "code",
    "small",
    "sub",
    "sup",
    "time",
}
_EXCLUDED = {
    "head",
    "script",
    "template",
    "noscript",
    "svg",
    "math",
    "iframe",
    "object",
    "canvas",
    "nav",
    "aside",
    "footer",
    "header",
    "form",
}
_VOID = {"br", "hr", "img", "wbr", "meta", "input", "source", "embed", "link"}


class _StaticText(HTMLParser):
    def __init__(self) -> None:
        # Tokenize raw HTML first. The parser decodes references in text nodes
        # after tokenization, so encoded quotes cannot terminate attributes.
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []
        self.parts: list[str] = []
        self.invalid = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        suppressed = any(hidden for _, hidden in self.stack)
        if (
            len(attributes) != len(attrs)
            or tag in {"style", "link"}
            or {"class", "id", "style"} & attributes.keys()
            or len(self.stack) >= 64
        ):
            self.invalid = True
        if tag not in _BLOCKS | _INLINE | _EXCLUDED | _VOID and not suppressed:
            self.invalid = True
        hidden = (
            suppressed
            or tag in _EXCLUDED
            or "hidden" in attributes
            or str(attributes.get("aria-hidden", "")).casefold() == "true"
        )
        if not hidden and (tag in _BLOCKS or tag in {"br", "hr"}):
            self.parts.append(" ")
        if tag not in _VOID:
            self.stack.append((tag, hidden))

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1][0] != tag:
            self.invalid = True
            return
        _, hidden = self.stack.pop()
        if not hidden and tag in _BLOCKS:
            self.parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _VOID:
            # HTML does not close non-void elements with '/>'; XML-style repair
            # could expose text that the publisher actually placed in a hidden node.
            self.invalid = True
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if not any(hidden for _, hidden in self.stack):
            # Unconsumed angle brackets signal ambiguous or partially encoded markup.
            if (
                "<" in data
                or ">" in data
                or unescape(data) != data
                or any(unicodedata.category(c).startswith("C") and c not in "\t\r\n" for c in data)
            ):
                self.invalid = True
            self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.invalid = True

    def handle_charref(self, name: str) -> None:
        self.invalid = True

    def handle_decl(self, decl: str) -> None:
        if decl.casefold() != "doctype html":
            self.invalid = True

    def unknown_decl(self, data: str) -> None:
        self.invalid = True

    def handle_pi(self, data: str) -> None:
        self.invalid = True


def _extract_text(raw: str) -> str:
    """Derive bounded static article text; refuse ambiguous input, never repair it."""
    if not isinstance(raw, str):
        return ""
    try:
        if len(raw.encode("utf-8")) > MAX_RAW_BYTES:
            return ""
        if any(unicodedata.category(c).startswith("C") and c not in "\t\r\n" for c in raw):
            return ""
        parser = _StaticText()
        parser.feed(raw)
        # EOF recovery differs across Python patch versions: some emit an
        # unfinished tag as data and others discard it. Neither is a receipt.
        if parser.rawdata:
            return ""
        parser.close()
    except (ValueError, UnicodeError):
        return ""
    if parser.invalid or parser.stack:
        return ""
    return " ".join("".join(parser.parts).split())


def _bounded_text(value: str) -> str:
    text = " ".join(value.split())
    if len(text) > MAX_SEGMENT_LENGTH:
        # Cut at whitespace, never manufacture a partial word beyond a headline.
        end = text.rfind(" ", 0, MAX_SEGMENT_LENGTH + 1)
        text = text[:end] if end >= 0 else ""
    return text


def capture_article_evidence(*, summary: str, content: str) -> list[dict[str, Any]]:
    return [
        {
            "origin": origin,
            "extraction_version": EXTRACTION_VERSION,
            "raw_text": value,
            "text": text,
        }
        for origin, value in (("summary", summary), ("content", content))
        if (text := _bounded_text(_extract_text(value)))
    ]


def article_segments(source: dict[str, Any]) -> dict[str, str]:
    segments = source.get("article_evidence")
    if not isinstance(segments, list) or len(segments) > len(ORIGINS):
        raise ValueError("source requires bounded retained article evidence")
    by_origin: dict[str, str] = {}
    for segment in segments:
        if not isinstance(segment, dict) or set(segment) != {
            "origin",
            "extraction_version",
            "raw_text",
            "text",
        }:
            raise ValueError("article evidence segment has unsupported fields")
        origin, text = segment["origin"], segment["text"]
        if not isinstance(origin, str) or origin not in ORIGINS or origin in by_origin:
            raise ValueError("article evidence segment has invalid or duplicate origin")
        if (
            type(segment["extraction_version"]) is not int
            or segment["extraction_version"] != EXTRACTION_VERSION
            or not isinstance(segment["raw_text"], str)
            or text != _bounded_text(_extract_text(segment["raw_text"]))
            or not isinstance(text, str)
            or not 1 <= len(text) <= MAX_SEGMENT_LENGTH
            or " ".join(text.split()) != text
        ):
            raise ValueError("article evidence must retain normalized bounded text")
        by_origin[origin] = text
    return by_origin


def has_non_headline_text(text: str, title: str) -> bool:
    """Reject canonical headline copies, repeated copies and partial copies.

    Both inputs come through the same text extraction boundary. A character
    stream makes copy detection independent of typography and word splitting.
    This is a copy guard, not proof of semantic usefulness or quote completeness.
    """

    def canonical(value: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if c.isalnum())

    headline, passage = canonical(_extract_text(title)), canonical(text)
    if not headline or not passage:
        return False
    repeated = headline * (len(passage) // len(headline) + 2)
    return passage not in repeated


def eligible_article_segments(source: dict[str, Any]) -> dict[str, str]:
    return {
        origin: text
        for origin, text in article_segments(source).items()
        if len(text) >= 40 and has_non_headline_text(text, str(source.get("title", "")))
    }
