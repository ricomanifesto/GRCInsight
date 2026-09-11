"""Extract optional article text only from supported static HTML.

This is not a browser or a CSS visibility evaluator. Rendering instructions,
unsupported markup and ambiguous ownership make the entire fetched document
unavailable, including its titles. Callers must retain vetted feed content in
that case. Plain text and balanced, unstyled semantic/inline HTML are supported;
the positive tag/attribute sets below define that deliberately limited contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
NON_CONTENT_TAGS = {"head", "template", "nav", "aside"}
SHARED_ROLES = {"navigation", "complementary", "banner", "contentinfo", "search"}
BLOCK_TAGS = {
    "article",
    "main",
    "section",
    "div",
    "p",
    "br",
    "hr",
    "li",
    "ul",
    "ol",
    "table",
    "tr",
    "td",
    "th",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "footer",
}
STATIC_TAGS = (
    BLOCK_TAGS
    | NON_CONTENT_TAGS
    | {
        "html",
        "body",
        "title",
        "meta",
        "a",
        "abbr",
        "b",
        "cite",
        "code",
        "del",
        "em",
        "i",
        "ins",
        "kbd",
        "mark",
        "q",
        "s",
        "samp",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
        "time",
        "u",
        "var",
        "pre",
        "blockquote",
        "dl",
        "dt",
        "dd",
        "figure",
        "figcaption",
        "address",
        "wbr",
    }
)
STATIC_ATTRIBUTES = {
    "role",
    "itemprop",
    "lang",
    "dir",
    "title",
    "href",
    "name",
    "property",
    "content",
    "charset",
    "datetime",
    "cite",
    "colspan",
    "rowspan",
    "scope",
    "start",
    "reversed",
    "value",
}


@dataclass(eq=False)
class _Element:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    parent: _Element | None = None
    children: list[_Element | str] = field(default_factory=list)
    excluded: bool = False
    in_article: bool = False


class _ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Element("document")
        self.stack = [self.root]
        self.nodes = [self.root]
        self.title_parts: list[str] = []
        self.meta_titles: list[str] = []
        self.supported = True

    def handle_starttag(self, tag, attrs):
        attributes = {key: value or "" for key, value in attrs}
        # Decline unknown rendering state globally, even in shared chrome. Do
        # not grow a CSS classifier or use partial text from such a document.
        if (
            tag not in STATIC_TAGS
            or not attributes.keys() <= STATIC_ATTRIBUTES
            or len(attrs) != len(attributes)
        ):
            self.supported = False
        parent = self.stack[-1]
        excluded = (
            parent.excluded
            or tag in NON_CONTENT_TAGS
            or attributes.get("role", "").lower() in SHARED_ROLES
            or (tag == "footer" and not parent.in_article)
        )
        node = _Element(
            tag,
            attributes,
            parent,
            excluded=excluded,
            in_article=parent.in_article or tag == "article",
        )
        parent.children.append(node)
        self.nodes.append(node)
        if tag == "meta" and parent.tag in {"document", "head"}:
            key = attributes.get("property", attributes.get("name", "")).lower()
            if key in {"og:title", "twitter:title"}:
                self.meta_titles.append(attributes.get("content", ""))
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.supported = False
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                if index != len(self.stack) - 1:
                    self.supported = False
                del self.stack[index:]
                return
        self.supported = False

    def handle_data(self, data):
        current = self.stack[-1]
        if current.tag == "title" and current.parent and current.parent.tag in {"head", "document"}:
            self.title_parts.append(data)
        if not current.excluded:
            current.children.append(data)


def _within(node: _Element, ancestor: _Element) -> bool:
    current: _Element | None = node
    while current is not None:
        if current is ancestor:
            return True
        current = current.parent
    return False


def _visible_text(node: _Element) -> str:
    if node.excluded:
        return ""
    text = "".join(
        child if isinstance(child, str) else _visible_text(child) for child in node.children
    )
    # Preserve newlines, including visible Markdown escapes, until policy runs.
    return "\n" + text + "\n" if node.tag in BLOCK_TAGS else text


def _choose_owner(candidates: list[_Element], nodes: list[_Element], title: str) -> _Element | None:
    if len(candidates) == 1:
        return candidates[0]
    normalized_title = " ".join(title.split()).casefold()
    matching = [
        candidate
        for candidate in candidates
        if normalized_title
        and any(
            node.tag in {"h1", "h2"}
            and _within(node, candidate)
            and " ".join(_visible_text(node).split()).casefold() == normalized_title
            for node in nodes
        )
    ]
    if len(matching) == 1:
        return matching[0]
    with_heading = [
        candidate
        for candidate in candidates
        if any(node.tag == "h1" and _within(node, candidate) for node in nodes)
    ]
    return with_heading[0] if len(with_heading) == 1 else None


def extract_article_text(html: str, *, title: str) -> str:
    """Return owned static text, or empty text to preserve the vetted feed record.

    Styling (including classes/IDs), visibility hints, scripts and unknown markup
    are intentionally unsupported. Even an apparently visible CSS child override
    does not establish eligibility. No fetched projection survives uncertainty.
    """
    parser = _ArticleParser()
    parser.feed(html)
    parser.close()
    if not parser.supported or len(parser.stack) != 1:
        return ""
    nodes = [node for node in parser.nodes if not node.excluded]
    mains = [node for node in nodes if node.tag == "main" or node.attrs.get("role") == "main"]
    main = _choose_owner(mains, nodes, title)
    if mains and main is None:
        return ""
    articles = [
        node
        for node in nodes
        if node.tag == "article" and (main is None or _within(node, main) or _within(main, node))
    ]
    bodies = [node for node in nodes if "articleBody" in node.attrs.get("itemprop", "").split()]
    main_headings = [
        node
        for node in nodes
        if node.tag == "h1"
        and main is not None
        and _within(node, main)
        and not any(_within(node, candidate) for candidate in articles)
    ]
    main_heading = main_headings[0] if len(main_headings) == 1 else None
    if articles:
        owner = _choose_owner(articles, nodes, title)
        if owner is not None and main_heading is not None:
            owned_headings = [
                node for node in nodes if node.tag in {"h1", "h2"} and _within(node, owner)
            ]
            expected_titles = {
                " ".join(value.split()).casefold() for value in (title, _visible_text(main_heading))
            }
            if owned_headings and not any(
                " ".join(_visible_text(node).split()).casefold() in expected_titles
                for node in owned_headings
            ):
                owner = None
    elif mains:
        owner = main
    elif bodies:
        owner = _choose_owner(bodies, nodes, title)
    else:
        owner = next((node for node in nodes if node.tag == "body"), parser.root)

    # Empty or ambiguous explicit containers never fall back to the raw page
    # or to independently projected titles from the uncertain document.
    if owner is None:
        return ""
    content = _visible_text(owner)
    if not content.strip():
        return ""
    titles = ["".join(parser.title_parts), *parser.meta_titles]
    if main_heading is not None and not _within(main_heading, owner):
        titles.append(_visible_text(main_heading))
    return "\n\n".join(part.strip() for part in [*titles, content] if part.strip())
