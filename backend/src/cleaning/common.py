"""Shared building blocks for the cleaners.

Edit model
----------
Cleaners never rewrite text directly. They read the ORIGINAL `raw_text` and produce a
list of `Edit`s, each one a range [start, end) of raw_text plus an optional replacement:

  - category set, replacement ""   -> a logged removal (becomes a RemovedSegment)
  - category None, replacement " " -> an unlogged re-join (e.g. hard-wrapped line break
                                      turned into a space; nothing was "junk")

`apply_edits` applies them in one pass and returns the clean text plus the removed
segments. Because every removal is an edit on the original text, offsets are exact:

    segment.start / segment.end are offsets into the FULL raw_text (end exclusive)
    and raw_text[segment.start:segment.end] == segment.text

Adjacent removals of the same category are merged into one segment.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from src.schemas import RemovedSegment

# Category set (keep small and stable: the UI color-codes these).
HEADER_FOOTER = "header_footer"
PAGE_NUMBER = "page_number"
NAVIGATION = "navigation"
COOKIE_CONSENT = "cookie_consent"
BOILERPLATE = "boilerplate"
DUPLICATE = "duplicate"
WHITESPACE = "whitespace"

CATEGORIES = (
    HEADER_FOOTER,
    PAGE_NUMBER,
    NAVIGATION,
    COOKIE_CONSENT,
    BOILERPLATE,
    DUPLICATE,
    WHITESPACE,
)

INNER_SPACE_RUN = re.compile(r"[ \t\u00a0]{2,}")


@dataclass(frozen=True)
class Edit:
    start: int
    end: int  # exclusive
    category: Optional[str] = None  # None => not logged as a removal
    replacement: str = ""


@dataclass
class CleanResult:
    clean_text: str
    removed_segments: list[RemovedSegment] = field(default_factory=list)


@dataclass
class Line:
    """One line of raw_text with absolute offsets."""

    start: int  # offset of first character
    end: int  # offset just past the last character, before the "\n"
    nl_end: int  # offset just past the "\n" (== end for a last line with no newline)
    text: str  # raw_text[start:end]
    page: int = 0  # 0-based page index (PDF only)
    category: Optional[str] = None  # set when the whole line is junk

    @property
    def content(self) -> str:
        return self.text.strip()

    @property
    def is_blank(self) -> bool:
        return not self.text.strip()

    @property
    def content_start(self) -> int:
        return self.start + len(self.text) - len(self.text.lstrip())

    @property
    def content_end(self) -> int:
        return self.start + len(self.text.rstrip())


def split_lines(raw_text: str) -> list[Line]:
    """Split on "\\n" only, so offsets stay exact."""
    lines: list[Line] = []
    pos = 0
    n = len(raw_text)
    while pos < n:
        nl = raw_text.find("\n", pos)
        if nl == -1:
            lines.append(Line(pos, n, n, raw_text[pos:n]))
            break
        lines.append(Line(pos, nl, nl + 1, raw_text[pos:nl]))
        pos = nl + 1
    return lines


def inner_whitespace_edits(line: Line) -> list[Edit]:
    """Collapse runs of 2+ spaces/tabs inside a line to a single character (logged)."""
    edits: list[Edit] = []
    cs, ce = line.content_start, line.content_end
    segment = line.text[cs - line.start : ce - line.start]
    for match in INNER_SPACE_RUN.finditer(segment):
        edits.append(Edit(cs + match.start() + 1, cs + match.end(), WHITESPACE))
    return edits


def merge_segments(segments: list[RemovedSegment]) -> list[RemovedSegment]:
    merged: list[RemovedSegment] = []
    for seg in segments:
        if merged and merged[-1].category == seg.category and merged[-1].end == seg.start:
            prev = merged[-1]
            merged[-1] = RemovedSegment(
                text=prev.text + seg.text,
                category=prev.category,
                start=prev.start,
                end=seg.end,
            )
        else:
            merged.append(seg)
    return merged


def apply_edits(raw_text: str, edits: list[Edit]) -> tuple[str, list[RemovedSegment]]:
    """Apply non-overlapping edits to raw_text. Overlapping/invalid edits are skipped."""
    ordered = sorted(edits, key=lambda e: (e.start, e.end))
    parts: list[str] = []
    segments: list[RemovedSegment] = []
    cursor = 0
    for edit in ordered:
        if edit.start < cursor or edit.end < edit.start:
            continue
        parts.append(raw_text[cursor : edit.start])
        parts.append(edit.replacement)
        if edit.category is not None and edit.end > edit.start:
            segments.append(
                RemovedSegment(
                    text=raw_text[edit.start : edit.end],
                    category=edit.category,
                    start=edit.start,
                    end=edit.end,
                )
            )
        cursor = edit.end
    parts.append(raw_text[cursor:])
    return "".join(parts), merge_segments(segments)