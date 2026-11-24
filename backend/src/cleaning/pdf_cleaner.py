"""PDF cleaner.

Input: the document-level raw_text (pages joined with PAGE_SEPARATOR) and the per-page texts.
Steps:
  1. Page numbers   -> category `page_number`
  2. Repeated headers/footers (fuzzy, across pages) -> `header_footer`
  3. Blank-line collapsing, hard-wrap re-joining, de-hyphenation, whitespace -> `whitespace`
  4. Simple tables: runs of short lines are kept as separate lines; if a consistent column
     layout can be guessed, cells are re-joined into " | " rows.

All rules/thresholds live at the top of this file so they are easy to tune or extend.
"""

import math
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from typing import Optional

from rapidfuzz import fuzz

from src.cleaning.common import (
    HEADER_FOOTER,
    PAGE_NUMBER,
    WHITESPACE,
    CleanResult,
    Edit,
    Line,
    apply_edits,
    inner_whitespace_edits,
    split_lines,
)
from src.schemas import PAGE_SEPARATOR, PageText

# ----------------------------------------------------------------------------
# Rules and thresholds
# ----------------------------------------------------------------------------

# Page numbers
PAGE_NUMBER_ANYWHERE = [
    re.compile(r"(?:page|pg\.?|p\.)\s*\d+(?:\s*(?:of|/)\s*\d+)?", re.IGNORECASE),
]
PAGE_NUMBER_AT_EDGE = [  # only trusted in the first/last lines of a page
    re.compile(r"\d+\s*(?:of|/)\s*\d+", re.IGNORECASE),
    re.compile(r"[-–—]\s*\d+\s*[-–—]"),
]
BARE_NUMBER = re.compile(r"\d{1,4}")
PAGE_NUMBER_EDGE_LINES = 2

# Headers / footers
EDGE_LINES = 3  # candidate lines at the top and bottom of every page
HEADER_FOOTER_SIMILARITY = 88.0  # rapidfuzz ratio (0-100) after digit normalization
HEADER_FOOTER_MIN_PAGE_FRACTION = 0.5
HEADER_FOOTER_MIN_PAGES = 2

# Re-joining hard-wrapped lines
BULLET_START = re.compile(r"^(?:[•●▪◦·*\-–—]|\d{1,3}[.)]|[A-Za-z][.)])\s+")
SENTENCE_END = re.compile(r"[.!?:;][\"'”’)\]]*$")
WRAP_WIDTH_PERCENTILE = 0.9
WRAP_FILL_RATIO = 0.85  # a line this close to the max width is probably wrapped
MIN_WRAP_WIDTH = 40

# Tables
TABLE_CELL_MAX_CHARS = 28
MIN_TABLE_RUN = 6
MAX_TABLE_COLUMNS = 8
MAX_TABLE_LEADING_LINES = 2  # e.g. a caption directly above the cells


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------


def clean_pdf(raw_text: str, pages: list[PageText]) -> CleanResult:
    page_starts = _page_starts(pages)
    if PAGE_SEPARATOR.join(p.text for p in pages) != raw_text:
        raise ValueError("raw_text does not match the joined page texts.")

    lines = split_lines(raw_text)
    for line in lines:
        line.page = max(0, bisect_right(page_starts, line.start) - 1)

    by_page: dict[int, list[int]] = defaultdict(list)
    for i, line in enumerate(lines):
        if not line.is_blank:
            by_page[line.page].append(i)

    _mark_page_numbers(lines, by_page)
    _mark_headers_footers(lines, by_page)

    edits = _build_edits(lines)
    clean_text, segments = apply_edits(raw_text, edits)
    return CleanResult(clean_text=clean_text, removed_segments=segments)


# ----------------------------------------------------------------------------
# Step 1: page numbers
# ----------------------------------------------------------------------------


def _page_starts(pages: list[PageText]) -> list[int]:
    starts: list[int] = []
    offset = 0
    for page in pages:
        starts.append(offset)
        offset += len(page.text) + len(PAGE_SEPARATOR)
    return starts


def _mark_page_numbers(lines: list[Line], by_page: dict[int, list[int]]) -> None:
    bare: list[tuple[int, int, int]] = []  # (page index, line index, value)
    for page, idxs in by_page.items():
        edge = set(idxs[:PAGE_NUMBER_EDGE_LINES]) | set(idxs[-PAGE_NUMBER_EDGE_LINES:])
        for i in idxs:
            text = lines[i].content
            if any(p.fullmatch(text) for p in PAGE_NUMBER_ANYWHERE):
                lines[i].category = PAGE_NUMBER
            elif i in edge:
                if any(p.fullmatch(text) for p in PAGE_NUMBER_AT_EDGE):
                    lines[i].category = PAGE_NUMBER
                elif BARE_NUMBER.fullmatch(text):
                    bare.append((page, i, int(text)))

    # A bare number is only a page number if values track the page index with a constant
    # offset on most pages. This protects table cells that happen to sit at a page edge.
    offsets = Counter(value - (page + 1) for page, _, value in bare)
    if not offsets:
        return
    offset, count = offsets.most_common(1)[0]
    n_pages = len(by_page)
    needed = max(1 if n_pages == 1 else 2, math.ceil(0.5 * n_pages))
    if count >= needed:
        for page, i, value in bare:
            if value - (page + 1) == offset:
                lines[i].category = PAGE_NUMBER


# ----------------------------------------------------------------------------
# Step 2: repeated headers / footers
# ----------------------------------------------------------------------------


def _normalize_repeat(text: str) -> str:
    text = re.sub(r"\d+", "#", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _mark_headers_footers(lines: list[Line], by_page: dict[int, list[int]]) -> None:
    n_pages = len(by_page)
    if n_pages < 2:
        return
    min_pages = max(HEADER_FOOTER_MIN_PAGES, math.ceil(HEADER_FOOTER_MIN_PAGE_FRACTION * n_pages))

    candidates: list[tuple[int, int, str]] = []  # (page, line index, normalized text)
    for page, idxs in by_page.items():
        usable = [i for i in idxs if lines[i].category is None]
        edge = list(dict.fromkeys(usable[:EDGE_LINES] + usable[-EDGE_LINES:]))
        for i in edge:
            norm = _normalize_repeat(lines[i].content)
            if any(ch.isalpha() for ch in norm):
                candidates.append((page, i, norm))

    pages_by_norm: dict[str, set[int]] = defaultdict(set)
    for page, _, norm in candidates:
        pages_by_norm[norm].add(page)

    norms = list(pages_by_norm)
    repeated: set[str] = set()
    for u in norms:
        pages = set(pages_by_norm[u])
        for v in norms:
            if v != u and fuzz.ratio(u, v) >= HEADER_FOOTER_SIMILARITY:
                pages |= pages_by_norm[v]
        if len(pages) >= min_pages:
            repeated.add(u)

    for _, i, norm in candidates:
        if norm in repeated:
            lines[i].category = HEADER_FOOTER


# ----------------------------------------------------------------------------
# Step 3: build edits (removals, blank lines, re-joining, tables, whitespace)
# ----------------------------------------------------------------------------


def _plan_paragraph_breaks(lines: list[Line]) -> set[int]:
    """Blank lines to KEEP as paragraph breaks: first blank between two content lines of
    the same page. Everything else (page-boundary blanks, extra blanks) is removed."""
    next_content: list[Optional[int]] = [None] * len(lines)
    nxt: Optional[int] = None
    for i in range(len(lines) - 1, -1, -1):
        next_content[i] = nxt
        if lines[i].category is None and not lines[i].is_blank:
            nxt = i

    breaks: set[int] = set()
    prev: Optional[int] = None
    break_kept = False
    for i, line in enumerate(lines):
        if line.category is not None:
            continue
        if not line.is_blank:
            prev = i
            break_kept = False
            continue
        nxt_i = next_content[i]
        if (
            prev is not None
            and nxt_i is not None
            and not break_kept
            and lines[prev].page == lines[nxt_i].page
        ):
            breaks.add(i)
            break_kept = True
    return breaks


def _content_blocks(lines: list[Line], breaks: set[int]) -> list[list[int]]:
    blocks: list[list[int]] = []
    current: list[int] = []
    for i, line in enumerate(lines):
        if line.category is not None:
            continue
        if line.is_blank:
            if i in breaks and current:
                blocks.append(current)
                current = []
            continue
        current.append(i)
    if current:
        blocks.append(current)
    return blocks


def _short_runs(lines: list[Line], block: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    run: list[int] = []
    for i in block:
        if len(lines[i].content) <= TABLE_CELL_MAX_CHARS:
            run.append(i)
        else:
            if len(run) >= MIN_TABLE_RUN:
                runs.append(run)
            run = []
    if len(run) >= MIN_TABLE_RUN:
        runs.append(run)
    return runs


def _cell_type(cell: str) -> str:
    return "num" if any(ch.isdigit() for ch in cell) else "text"


def _columns_consistent(body: list[str], cols: int) -> bool:
    rows = [body[i : i + cols] for i in range(0, len(body), cols)]
    data = rows[1:]  # first row is treated as the header
    col_types: list[str] = []
    for c in range(cols):
        types = [_cell_type(row[c]) for row in data]
        top = max(set(types), key=types.count)
        if types.count(top) / len(types) < 0.8:
            return False
        col_types.append(top)
    # Require a mix of text and numeric columns; otherwise the guess is too ambiguous.
    return "num" in col_types and "text" in col_types


def _guess_columns(cells: list[str]) -> Optional[tuple[int, int]]:
    """Return (leading_lines_to_skip, columns) if the cells look like a regular table."""
    for cols in range(2, MAX_TABLE_COLUMNS + 1):
        for skip in range(0, MAX_TABLE_LEADING_LINES + 1):
            body = cells[skip:]
            if len(body) % cols or len(body) // cols < 3:
                continue
            if _columns_consistent(body, cols):
                return skip, cols
    return None


def _wrap_width(lengths: list[int]) -> int:
    lengths = [n for n in lengths if n >= 20]
    if len(lengths) < 8:
        return 0
    ordered = sorted(lengths)
    width = ordered[int(WRAP_WIDTH_PERCENTILE * (len(ordered) - 1))]
    return width if width >= MIN_WRAP_WIDTH else 0


def _join_kind(a: Line, b: Line, wrap_width: int) -> Optional[str]:
    """Decide how line `a` continues into line `b`: 'space', 'glue', 'dehyphen' or None."""
    at, bt = a.content, b.content
    if BULLET_START.match(bt):
        return None
    if at.endswith("-") and len(at) > 1 and at[-2].isalpha():
        if bt[0].islower():
            return "dehyphen"
        if bt[0].isalnum():
            return "glue"  # keep the hyphen: "Smith-\nJones" -> "Smith-Jones"
        return None
    if bt[0].islower():
        return "space"
    if at.endswith(","):
        return "space"
    if wrap_width and len(at) >= WRAP_FILL_RATIO * wrap_width and not SENTENCE_END.search(at):
        return "space"
    return None


def _join_edit(a: Line, kind: str) -> Edit:
    if kind == "dehyphen":
        # Remove the hyphen and the line break (logged).
        return Edit(a.content_end - 1, a.nl_end, WHITESPACE, "")
    separator = " " if kind == "space" else ""
    return Edit(a.content_end, a.nl_end, None, separator)


def _build_edits(lines: list[Line]) -> list[Edit]:
    edits: list[Edit] = []

    # Whole-line junk (page numbers, headers/footers): remove line incl. its newline.
    for line in lines:
        if line.category is not None:
            edits.append(Edit(line.start, line.nl_end, line.category))

    # Blank lines: keep at most one paragraph break between content lines on a page.
    breaks = _plan_paragraph_breaks(lines)
    for i, line in enumerate(lines):
        if line.category is None and line.is_blank:
            if i in breaks:
                if line.end > line.start:
                    edits.append(Edit(line.start, line.end, WHITESPACE))
            else:
                edits.append(Edit(line.start, line.nl_end, WHITESPACE))

    blocks = _content_blocks(lines, breaks)

    # Tables: runs of short lines are never wrapped-joined; guess rows when possible.
    table_cells: set[int] = set()
    row_of: dict[int, int] = {}
    row_counter = 0
    for block in blocks:
        for run in _short_runs(lines, block):
            table_cells.update(run)
            guess = _guess_columns([lines[i].content for i in run])
            if guess:
                skip, cols = guess
                body = run[skip:]
                for k, i in enumerate(body):
                    row_of[i] = row_counter + k // cols
                row_counter += len(body) // cols

    prose_lengths = [
        len(lines[i].content) for block in blocks for i in block if i not in table_cells
    ]
    wrap_width = _wrap_width(prose_lengths)

    # Joins between consecutive content lines of the same block.
    joined: set[int] = set()
    for block in blocks:
        for a_i, b_i in zip(block, block[1:]):
            a, b = lines[a_i], lines[b_i]
            if a_i in table_cells or b_i in table_cells:
                if a_i in row_of and row_of.get(a_i) == row_of.get(b_i):
                    edits.append(Edit(a.content_end, a.nl_end, None, " | "))
                    joined.add(a_i)
                continue
            kind = _join_kind(a, b, wrap_width)
            if kind is not None:
                edits.append(_join_edit(a, kind))
                joined.add(a_i)

    # Per-line whitespace tidying.
    last_content = blocks[-1][-1] if blocks else None
    for block in blocks:
        for i in block:
            line = lines[i]
            edits.extend(inner_whitespace_edits(line))
            if line.content_start > line.start:
                edits.append(Edit(line.start, line.content_start, WHITESPACE))
            if i not in joined:  # joined lines have their trailing whitespace covered
                if line.content_end < line.end:
                    edits.append(Edit(line.content_end, line.end, WHITESPACE))
                if i == last_content:
                    edits.append(Edit(line.end, line.nl_end, None, ""))
    return edits