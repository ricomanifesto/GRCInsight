"""Source eligibility policy shared by analysis and public report validation."""

from collections.abc import Mapping
from html import unescape
from html.parser import HTMLParser
import re

VIRTUAL_EVENT_EXCLUSION = "excluded virtual-event promotion"
_MARKER = re.compile(r"\[\s*virtual\s+event\s*\]", re.IGNORECASE)
_MARKDOWN_ESCAPE = re.compile(r"\\([\\\[\]])")


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"br", "p", "div", "li", "tr", "td", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        self.handle_starttag(tag, [])


def contains_virtual_event(value: object) -> bool:
    """Recognize the bracketed promotion marker without changing source content."""
    if isinstance(value, Mapping):
        return any(contains_virtual_event(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_virtual_event(item) for item in value)
    if not isinstance(value, str):
        return False
    parser = _VisibleText()
    # Feed content may have both XML/HTML entity encoding and Markdown escapes.
    parser.feed(unescape(value))
    parser.close()
    text = re.sub(r"\\\r?\n", "\n", unescape("".join(parser.parts)))
    while True:
        decoded = _MARKDOWN_ESCAPE.sub(r"\1", text)
        if decoded == text:
            break
        text = decoded
    # Match the public validator's inline emphasis/code label normalization.
    return _MARKER.search(re.sub(r"[*_`]+", "", text)) is not None
