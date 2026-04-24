from __future__ import annotations

import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import markdownify as to_markdown

SOURCE_URL = "https://www.retrosheet.org/eventfile.htm"
OUTPUT_PATH = Path("docs/eventfile.md")
REQUEST_TIMEOUT_SECONDS = 30.0

ABBREVIATIONS = {
    "adj.",
    "al.",
    "approx.",
    "cf.",
    "dr.",
    "e.g.",
    "etc.",
    "fig.",
    "i.e.",
    "jr.",
    "mr.",
    "mrs.",
    "ms.",
    "no.",
    "prof.",
    "sr.",
    "st.",
    "vs.",
}

SENTENCE_STARTERS = set('"\'([')


def fetch_page(url: str = SOURCE_URL) -> str:
    with httpx.Client(follow_redirects=True, timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def build_main_fragment(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for selector in ("script", "style", "ul.nav", 'font[size="2"]'):
        for tag in soup.select(selector):
            tag.decompose()

    body = soup.body
    if body is None:
        raise ValueError("expected HTML body element")

    heading = find_main_heading(body)
    if heading is not None:
        drop_siblings_before(body, heading)

    unwrap_blockquotes_with_h3(body)
    convert_inline_labels_to_headings(soup, body)
    normalize_text_nodes(body)
    prune_trailing_separators(body)
    return str(body)


def find_main_heading(body: Tag) -> Tag | None:
    for tag in body.find_all(["h1", "h2", "h3", "center"]):
        if tag.get_text(" ", strip=True) == "The Event File":
            if tag.name == "center" and isinstance(tag.parent, Tag):
                return tag.parent
            return tag
    return None


def drop_siblings_before(parent: Tag, marker: Tag) -> None:
    current = parent.contents[:]
    for child in current:
        if child is marker:
            break
        if isinstance(child, Tag):
            child.decompose()
        else:
            child.extract()


def prune_trailing_separators(body: Tag) -> None:
    for child in reversed(body.contents[:]):
        if isinstance(child, Tag) and child.name in {"hr", "br"}:
            child.decompose()
            continue
        if isinstance(child, str) and not child.strip():
            child.extract()
            continue
        break


def unwrap_blockquotes_with_h3(body: Tag) -> None:
    for blockquote in body.find_all("blockquote"):
        if blockquote.find("h3") is None:
            continue
        blockquote.unwrap()


def convert_inline_labels_to_headings(soup: BeautifulSoup, body: Tag) -> None:
    for paragraph in body.find_all("p"):
        container = heading_container(paragraph)
        if container is None:
            continue

        heading_nodes = leading_heading_nodes(container)
        if not heading_nodes:
            continue

        heading_text = collapse_whitespace("".join(node.get_text(" ", strip=True) if isinstance(node, Tag) else str(node) for node in heading_nodes))
        heading_text = re.sub(r"\s+", " ", heading_text).strip(" .:;-")
        if not heading_text:
            continue

        heading = soup.new_tag("h4")
        heading.string = heading_text
        paragraph.insert_before(heading)

        for node in heading_nodes:
            node.extract()

        trim_leading_punctuation(paragraph)
        if not paragraph.get_text(" ", strip=True):
            paragraph.decompose()


def heading_container(paragraph: Tag) -> Tag | None:
    meaningful_children = [
        child
        for child in paragraph.contents
        if not (isinstance(child, NavigableString) and not collapse_whitespace(str(child)))
    ]
    if not meaningful_children:
        return None

    first = meaningful_children[0]
    if isinstance(first, Tag) and first.name != "span":
        return first
    return paragraph


def leading_heading_nodes(paragraph: Tag) -> list[Tag | NavigableString]:
    nodes: list[Tag | NavigableString] = []
    found_label = False

    for child in paragraph.contents:
        if isinstance(child, NavigableString):
            text = str(child)
            if not found_label:
                if collapse_whitespace(text):
                    return []
                continue
            if is_heading_connector(text):
                nodes.append(child)
                continue
            break

        if is_bold_italic_label(child):
            nodes.append(child)
            found_label = True
            continue

        break

    if not found_label:
        return []

    while nodes and isinstance(nodes[-1], NavigableString) and not collapse_whitespace(str(nodes[-1])):
        nodes.pop()

    return nodes


def is_bold_italic_label(tag: Tag) -> bool:
    return tag.name == "span" and "font-weight:bold" in (tag.get("style") or "").replace(" ", "").lower() and tag.find("i") is not None


def is_heading_connector(text: str) -> bool:
    collapsed = collapse_whitespace(text)
    return collapsed in {"", "and", "or", "/", ",", "&"}


def trim_leading_punctuation(tag: Tag) -> None:
    node: Tag | NavigableString = tag

    while isinstance(node, Tag):
        if not node.contents:
            return
        first = node.contents[0]
        if isinstance(first, NavigableString):
            trimmed = re.sub(r"^[\s.:;-]+", "", str(first))
            if trimmed:
                first.replace_with(trimmed)
                return
            first.extract()
            node = tag
            continue
        node = first


def normalize_text_nodes(body: Tag) -> None:
    for text_node in list(body.descendants):
        if not isinstance(text_node, NavigableString):
            continue
        parent = text_node.parent
        if not isinstance(parent, Tag) or parent.name in {"pre", "code", "script", "style"}:
            continue

        original = str(text_node)
        normalized = collapse_inline_whitespace(original)
        if normalized == original:
            continue
        text_node.replace_with(normalized)


def collapse_inline_whitespace(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[ \t\r\f\v]{2,}", " ", text)
    return text


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def convert_html_to_markdown(html: str) -> str:
    markdown = to_markdown(
        html,
        heading_style="ATX",
        bullets="-",
        autolinks=False,
        strong_em_symbol="*",
    )
    markdown = markdown.replace("\r\n", "\n")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip() + "\n"


def normalize_markdown(markdown: str) -> str:
    parts = re.split(r"(\n\s*\n)", markdown.strip())
    normalized_parts: list[str] = []

    for part in parts:
        if re.fullmatch(r"\n\s*\n", part):
            normalized_parts.append("\n\n")
            continue

        block = part.strip("\n")
        if not block:
            continue

        list_item = normalize_list_item_block(block)
        if list_item is not None:
            normalized_parts.append(list_item)
            continue

        if is_plain_paragraph(block):
            paragraph = " ".join(line.strip() for line in block.splitlines())
            normalized_parts.append(insert_sentence_newlines(paragraph))
            continue

        normalized_parts.append(block)

    return "".join(normalized_parts).strip() + "\n"


def is_plain_paragraph(block: str) -> bool:
    lines = block.splitlines()
    if not lines:
        return False

    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            continue
        if stripped.startswith(("#", ">", "```", "|")):
            return False
        if stripped in {"---", "***", "___"}:
            return False
        if re.match(r"[-*+]\s", stripped):
            return False
        if re.match(r"\d+\.\s", stripped):
            return False
        if line.startswith(("    ", "\t")):
            return False

    return True


def normalize_list_item_block(block: str) -> str | None:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return None

    match = re.match(r"(?P<marker>\d+\.|[-*+])\s+(?P<content>.*)", lines[0])
    if match is None:
        return None

    if any(re.match(r"(?:\d+\.|[-*+])\s+", line) for line in lines[1:]):
        return None

    content = " ".join([match.group("content"), *lines[1:]]).strip()
    normalized = insert_sentence_newlines(content)
    indent = " " * (len(match.group("marker")) + 1)
    return f"{match.group('marker')} {normalized.replace('\n', f'\n{indent}')}"


def insert_sentence_newlines(paragraph: str) -> str:
    text = re.sub(r"\s+", " ", paragraph).strip()
    result: list[str] = []
    index = 0

    while index < len(text):
        char = text[index]
        result.append(char)

        if char == "." and should_break_sentence(text, index):
            next_index = index + 1
            while next_index < len(text) and text[next_index].isspace():
                next_index += 1
            result.append("\n")
            index = next_index
            continue

        index += 1

    return "".join(result)


def should_break_sentence(text: str, period_index: int) -> bool:
    if period_index <= 0 or period_index >= len(text) - 1:
        return False

    next_char = text[period_index + 1]
    if not next_char.isspace():
        return False

    previous_char = text[period_index - 1]
    next_index = period_index + 1
    while next_index < len(text) and text[next_index].isspace():
        next_index += 1

    if next_index >= len(text):
        return False

    next_non_space = text[next_index]
    if next_non_space not in SENTENCE_STARTERS and not next_non_space.isupper() and not next_non_space.isdigit():
        return False

    if previous_char.isdigit() and next_non_space.isdigit():
        return False

    token = surrounding_token(text, period_index)
    token_lower = token.lower()
    if token_lower in ABBREVIATIONS:
        return False
    if re.fullmatch(r"(?:[A-Za-z]\.){2,}", token):
        return False
    if token_lower.startswith(("http://", "https://", "www.")):
        return False

    prefix = text[max(0, period_index - 20) : period_index + 1]
    last_word = re.search(r"([A-Za-z]+\.)$", prefix)
    if last_word and last_word.group(1).lower() in ABBREVIATIONS:
        return False

    return True


def surrounding_token(text: str, index: int) -> str:
    start = index
    while start > 0 and not text[start - 1].isspace():
        start -= 1

    end = index + 1
    while end < len(text) and not text[end].isspace():
        end += 1

    return text[start:end]


def generate_markdown(html: str) -> str:
    fragment = build_main_fragment(html)
    markdown = convert_html_to_markdown(fragment)
    return normalize_markdown(markdown)


def write_output(markdown: str, output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")


def main() -> None:
    html = fetch_page()
    markdown = generate_markdown(html)
    write_output(markdown)


if __name__ == "__main__":
    main()
