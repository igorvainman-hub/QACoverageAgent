from __future__ import annotations

import re
from pathlib import Path

from schemas import DocumentSection

HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.MULTILINE)
TOP_HEADING = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
UNSAFE = re.compile(r"[^A-Za-z0-9_/-]+")


def _slug(text: str) -> str:
    return UNSAFE.sub("-", text).strip("-")


def parse_document(path: Path) -> list[DocumentSection]:
    """Deterministically split a Markdown document at ## and ### headings."""
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(HEADING.finditer(text))
    if not matches:
        return [DocumentSection(path=path.stem, title=path.stem, raw_content=text.strip())] if text.strip() else []

    sections: list[DocumentSection] = []
    top = TOP_HEADING.search(text)
    root = _slug(top.group(1).strip()) if top else _slug(path.stem)
    level_two = root
    for index, match in enumerate(matches):
        hashes, title = match.groups()
        title = title.strip()
        if len(hashes) == 2:
            level_two = f"{root}/{_slug(title)}"
            section_path = level_two
        else:
            section_path = f"{level_two}/{_slug(title)}"
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[match.end():end].strip()
        sections.append(DocumentSection(path=section_path, title=title, raw_content=content))
    return sections