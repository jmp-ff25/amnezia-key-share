import html
import re

import nh3
from markupsafe import Markup

MAX_RICH_TEXT_LENGTH = 40_000
MEDIA_PATH_RE = re.compile(r"^/media/[0-9a-f]{32}\.(?:png|jpg|gif|webp)$")


def _attribute_filter(tag: str, attribute: str, value: str) -> str | None:
    if tag == "img" and attribute == "src":
        return value if MEDIA_PATH_RE.fullmatch(value) else None
    return value


_cleaner = nh3.Cleaner(
    tags={
        "p", "br", "h2", "h3", "strong", "em", "u", "s", "blockquote",
        "ul", "ol", "li", "a", "img", "span", "hr", "pre", "code",
    },
    attributes={
        "a": {"href", "title"},
        "img": {"src", "alt", "title"},
        "span": {"style"},
        "p": {"style"},
        "h2": {"style"},
        "h3": {"style"},
    },
    attribute_filter=_attribute_filter,
    filter_style_properties={"color", "font-family", "text-align"},
    url_schemes={"http", "https", "mailto"},
    url_relative="pass_through",
    link_rel="noopener noreferrer",
    clean_content_tags={"script", "style", "iframe", "object", "svg"},
)


def clean_rich_text(value: str) -> str:
    clean = value.strip()
    if len(clean) > MAX_RICH_TEXT_LENGTH:
        raise ValueError("Текст слишком длинный (не более 40 000 символов)")
    if not clean:
        return ""
    sanitized = _cleaner.clean(clean)
    if len(sanitized) > MAX_RICH_TEXT_LENGTH:
        raise ValueError("Текст слишком длинный (не более 40 000 символов)")
    return sanitized


def render_rich_text(value: str | None, format_name: str = "html") -> Markup:
    if not value:
        return Markup("")
    if format_name == "plain":
        paragraphs = [html.escape(part).replace("\n", "<br>") for part in value.split("\n\n")]
        # Escaped text is wrapped only in our fixed paragraph tags.
        return Markup("".join(f"<p>{part}</p>" for part in paragraphs if part))  # noqa: S704
    # nh3 removes unsafe tags, attributes, and URL schemes before marking HTML safe.
    return Markup(clean_rich_text(value))  # noqa: S704
