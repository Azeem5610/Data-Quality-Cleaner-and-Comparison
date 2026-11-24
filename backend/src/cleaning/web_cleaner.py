"""Web cleaner.

Input: the raw HTML and the naive visible text (one fragment per line) from the loader.
Steps:
  1. trafilatura extracts the main content. Each raw line is aligned against it: lines
     before/after the main-content region, or inside it but absent from trafilatura's
     output, are junk. Junk is categorized with the pattern lists below
     (`cookie_consent`, `navigation`, `boilerplate`).
  2. Inline fragments the naive extractor split across lines (text around <a>, <b>, ...)
     are re-joined into the paragraphs trafilatura found.
  3. Exact and near-duplicate paragraphs are removed (`duplicate`, rapidfuzz).
  4. Extra whitespace is collapsed (`whitespace`).

If trafilatura finds nothing usable, the cleaner falls back to pattern rules only.
All rules/thresholds live at the top of this file so they are easy to tune or extend.
"""

import re
from bisect import bisect_left
from dataclasses import dataclass
from typing import Optional

import trafilatura
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process

from src.cleaning.common import (
    BOILERPLATE,
    COOKIE_CONSENT,
    DUPLICATE,
    NAVIGATION,
    WHITESPACE,
    CleanResult,
    Edit,
    Line,
    apply_edits,
    inner_whitespace_edits,
    split_lines,
)

# ----------------------------------------------------------------------------
# Rules and thresholds
# ----------------------------------------------------------------------------


def _compile(patterns: list[str]) -> list["re.Pattern[str]"]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


COOKIE_CONSENT_PATTERNS = _compile(
    [
        r"\bcookies?\b",
        r"\bconsent\b",
        r"\bgdpr\b|\bccpa\b",
        r"^(accept|reject|decline|allow|deny)( all| essential| necessary| selected)?( cookies)?$",
        r"^(got it|i agree|i accept|agree|okay|ok|dismiss|close)[.!]?$",
        r"(manage|customi[sz]e|update|change) (my |your )?(cookie |privacy )?(preferences|settings|choices)",
        r"privacy (settings|preferences|choices|notice)",
        r"do not sell",
        r"\bwe (use|collect|store)\b.*\b(data|information|technolog)",
    ]
)

NAVIGATION_PATTERNS = _compile(
    [
        r"^skip to (main )?(content|navigation)$",
        r"^(home|about|about us|contact|contact us|products?|services?|solutions|pricing|plans|"
        r"blog|news|careers|jobs|support|help|help center|faqs?|resources|docs|documentation|"
        r"login|log in|sign in|sign up|register|get started|menu|search|cart|checkout|"
        r"my account|account|shop|store|partners|customers|company|team|events|press|"
        r"investors|downloads?|community|overview|features|back to top|top)$",
        r"^(previous|next|prev|older|newer)( (page|post|article|posts))?\b",
        r"^[»«›‹><|/•·]+$",
        r"^you are here",
        r"^breadcrumb",
        r"^toggle (navigation|menu)",
        r"^(open|close) (menu|navigation)",
    ]
)

BOILERPLATE_PATTERNS = _compile(
    [
        r"\bnewsletters?\b",
        r"\bsubscribe\b",
        r"\bsign up (for|to|now|today)\b",
        r"\b(your|work|business) e-?mail( address)?\b",
        r"^(email|e-mail)( address)?\*?:?$",
        r"^(share|tweet|pin it|follow us)\b.{0,30}$",
        r"^(facebook|twitter|x|linkedin|instagram|youtube|pinterest|tiktok|whatsapp|telegram|reddit)$",
        r"©|\bcopyright\b|\ball rights reserved\b",
        r"^(privacy( policy)?|terms( of (use|service|sale))?|terms (&|and) conditions|sitemap|"
        r"accessibility|disclaimer|legal( notice)?|imprint)$",
        r"\bpowered by\b|\bwebsite by\b|\bdesigned by\b",
        r"^(read|learn|find out|see|view) (more|all)\b.{0,30}$",
        r"^click here\b",
        r"^(advertisement|advertise|sponsored( content)?|ad)$",
        r"^(listen|watch|explore more|more tech|in case you missed it)$",
        r"^related (articles|posts|links|content|reading)\b",
        r"^(was this (page|article|post) helpful|rate this|did you find)",
        r"^(print|download) (this )?(page|article)$",
    ]
)

# Checked in this order; first match wins.
CATEGORY_RULES: list[tuple[str, list["re.Pattern[str]"]]] = [
    (COOKIE_CONSENT, COOKIE_CONSENT_PATTERNS),
    (NAVIGATION, NAVIGATION_PATTERNS),
    (BOILERPLATE, BOILERPLATE_PATTERNS),
]

MIN_MAIN_TEXT_CHARS = 80  # below this, trafilatura's result is not trusted
ANCHOR_MIN_KEY_CHARS = 30  # a line this long that appears in the main text anchors the region
REGION_EXTEND_LINES = 4  # how far headings/short lines may extend the region edges
SHORT_LINE_CHARS = 40  # unmatched short junk is labeled navigation, longer is boilerplate
FALLBACK_MAX_PATTERN_LINE_CHARS = 120  # in fallback mode patterns only apply to short lines
DUPLICATE_MIN_CHARS = 15
DUPLICATE_FUZZY_MIN_CHARS = 60
DUPLICATE_SIMILARITY = 92.0

LIST_MARKER = re.compile(r"^\s*(?:[-*•]|\d{1,3}[.)])\s+")
PUNCT_ONLY_JUNK = re.compile(r"[»«›‹><|/•·]+")
NO_SPACE_BEFORE = ".,;:!?)]}%’"
NO_SPACE_AFTER = "([{"


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------


def clean_web(raw_html: str, raw_text: str) -> CleanResult:
    lines = split_lines(raw_text)
    edits: list[Edit] = []

    ids: list[int] = []
    for i, line in enumerate(lines):
        if line.is_blank:
            edits.append(Edit(line.start, line.nl_end, WHITESPACE))
        else:
            ids.append(i)

    main = _build_main(raw_html)
    status, aligned = _classify(lines, ids, main)

    kept: list[int] = []
    for i in ids:
        category = status[i]
        if category is None:
            kept.append(i)
        else:
            edits.append(Edit(lines[i].start, lines[i].nl_end, category))

    groups = _group_lines(lines, kept, main) if aligned else [([i], " ") for i in kept]

    duplicates = _find_duplicates(lines, groups)
    for gi in duplicates:
        for i in groups[gi][0]:
            edits.append(Edit(lines[i].start, lines[i].nl_end, DUPLICATE))

    survivors = [g for gi, g in enumerate(groups) if gi not in duplicates]
    last_line = survivors[-1][0][-1] if survivors else None
    for idxs, mode in survivors:
        for pos, i in enumerate(idxs):
            line = lines[i]
            edits.extend(inner_whitespace_edits(line))
            if line.content_start > line.start:
                edits.append(Edit(line.start, line.content_start, WHITESPACE))
            if pos + 1 < len(idxs):
                nxt = lines[idxs[pos + 1]]
                sep = " | " if mode == "|" else _fragment_separator(line.content, nxt.content)
                edits.append(Edit(line.content_end, line.nl_end, None, sep))
            else:
                if line.content_end < line.end:
                    edits.append(Edit(line.content_end, line.end, WHITESPACE))
                if i == last_line:
                    edits.append(Edit(line.end, line.nl_end, None, ""))

    clean_text, segments = apply_edits(raw_text, edits)
    return CleanResult(clean_text=clean_text, removed_segments=segments)


# ----------------------------------------------------------------------------
# Main-content extraction
# ----------------------------------------------------------------------------


@dataclass
class MainContent:
    key_to_line: dict[str, str]  # normalized key -> trafilatura line
    sorted_keys: list[str]
    blob: str  # all keys concatenated, for substring checks
    semantic_blob: str  # text from semantic main/article elements in the source HTML
    usable: bool


def _key(text: str) -> str:
    """Alphanumeric-only lowercase form, so punctuation/spacing differences don't matter."""
    return re.sub(r"\W+", "", text.lower())


def _extract_main_text(html: str) -> str:
    try:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            include_links=False,
            include_images=False,
            favor_recall=True,
            output_format="txt",
        )
    except Exception:
        return ""
    return text or ""


def _build_main(html: str) -> MainContent:
    text = _extract_main_text(html)
    key_to_line: dict[str, str] = {}
    ordered: list[str] = []
    for raw in text.splitlines():
        line = LIST_MARKER.sub("", raw).strip()
        key = _key(line)
        if key:
            ordered.append(key)
            key_to_line.setdefault(key, line)

    # Trafilatura can return only part of a page, especially on section pages made
    # from linked story cards. Keep a second positive signal from semantic content
    # containers so good text outside Trafilatura's guessed region is not discarded.
    semantic_parts: list[str] = []
    try:
        soup = BeautifulSoup(html, "lxml")
        for root in soup.select("main, article, [role='main']"):
            for raw_line in root.get_text(separator="\n").splitlines():
                key = _key(raw_line.strip())
                if key:
                    semantic_parts.append(key)
    except Exception:
        # The Trafilatura result and explicit junk rules remain available if HTML
        # structure cannot be parsed.
        semantic_parts = []

    return MainContent(
        key_to_line=key_to_line,
        sorted_keys=sorted(set(ordered)),
        blob="".join(ordered),
        semantic_blob="".join(semantic_parts),
        usable=len(text.strip()) >= MIN_MAIN_TEXT_CHARS,
    )


# ----------------------------------------------------------------------------
# Junk classification
# ----------------------------------------------------------------------------


def _match_category(text: str) -> Optional[str]:
    for category, patterns in CATEGORY_RULES:
        if any(p.search(text) for p in patterns):
            return category
    return None


def _find_region(keys: list[str], main: MainContent) -> Optional[tuple[int, int]]:
    anchors = [
        pos for pos, key in enumerate(keys) if len(key) >= ANCHOR_MIN_KEY_CHARS and key in main.blob
    ]
    if not anchors:
        return None
    start, end = anchors[0], anchors[-1]

    steps = 0
    while start > 0 and steps < REGION_EXTEND_LINES and keys[start - 1] in main.key_to_line:
        start -= 1
        steps += 1
    steps = 0
    while end + 1 < len(keys) and steps < REGION_EXTEND_LINES and keys[end + 1] in main.key_to_line:
        end += 1
        steps += 1
    return start, end


def _classify(
    lines: list[Line], ids: list[int], main: MainContent
) -> tuple[dict[int, Optional[str]], bool]:
    """Return ({line index: junk category or None to keep}, whether main-content alignment was used)."""
    texts = [lines[i].content for i in ids]
    keys = [_key(t) for t in texts]
    region = _find_region(keys, main) if main.usable else None

    status: dict[int, Optional[str]] = {}

    if region is None:  # fallback: pattern rules only, on short lines
        for i, text in zip(ids, texts):
            category = None
            if len(text) <= FALLBACK_MAX_PATTERN_LINE_CHARS:
                category = _match_category(text)
            status[i] = category
        return status, False

    start, end = region
    for pos, (i, text, key) in enumerate(zip(ids, texts, keys)):
        if key and key in main.semantic_blob:
            # Semantic article/page content outranks Trafilatura's partial boundary.
            # Known junk patterns still win so an in-article cookie notice is removed.
            category = _match_category(text)
            status[i] = category
            continue
        if start <= pos <= end:
            keep = key in main.blob if key else not PUNCT_ONLY_JUNK.fullmatch(text)
            if keep:
                status[i] = None
                continue
        category = _match_category(text)
        if category is None:
            category = NAVIGATION if (pos <= end and len(text) <= SHORT_LINE_CHARS) else BOILERPLATE
        status[i] = category
    return status, True


# ----------------------------------------------------------------------------
# Re-joining inline fragments into paragraphs
# ----------------------------------------------------------------------------


def _is_prefix(sorted_keys: list[str], acc: str) -> bool:
    pos = bisect_left(sorted_keys, acc)
    return pos < len(sorted_keys) and sorted_keys[pos].startswith(acc)


def _fragment_separator(a: str, b: str) -> str:
    if b and b[0] in NO_SPACE_BEFORE:
        return ""
    if a and a[-1] in NO_SPACE_AFTER:
        return ""
    return " "


def _group_lines(
    lines: list[Line], kept: list[int], main: MainContent
) -> list[tuple[list[int], str]]:
    """Group consecutive kept lines whose concatenation equals one trafilatura line.
    Returns [(line indices, mode)], mode "|" for table rows, " " otherwise. If alignment
    fails, lines are left as they are (one group per line)."""
    groups: list[tuple[list[int], str]] = []
    buffer: list[int] = []
    acc = ""

    for i in kept:
        text = lines[i].content
        key = _key(text)

        if not key:  # punctuation-only fragment
            if buffer:
                buffer.append(i)
            elif groups and len(text) <= 3 and text[0] in NO_SPACE_BEFORE:
                groups[-1][0].append(i)
            else:
                groups.append(([i], " "))
            continue

        trial = acc + key
        if not _is_prefix(main.sorted_keys, trial):
            for j in buffer:
                groups.append(([j], " "))
            buffer, acc = [], ""
            trial = key
            if not _is_prefix(main.sorted_keys, trial):
                groups.append(([i], " "))
                continue

        buffer.append(i)
        acc = trial
        if acc in main.key_to_line:
            mode = "|" if "|" in main.key_to_line[acc] else " "
            groups.append((buffer, mode))
            buffer, acc = [], ""

    for j in buffer:
        groups.append(([j], " "))
    return groups


# ----------------------------------------------------------------------------
# Duplicates
# ----------------------------------------------------------------------------


def _find_duplicates(lines: list[Line], groups: list[tuple[list[int], str]]) -> set[int]:
    """Indices of groups that repeat an earlier group (exact, or fuzzy for long paragraphs)."""
    seen_exact: set[str] = set()
    seen_long: list[str] = []
    duplicates: set[int] = set()

    for gi, (idxs, mode) in enumerate(groups):
        norm = re.sub(r"\s+", " ", " ".join(lines[i].content for i in idxs).lower()).strip()
        if len(norm) < DUPLICATE_MIN_CHARS:
            continue
        if norm in seen_exact:
            duplicates.add(gi)
            continue
        if (
            mode != "|"
            and len(norm) >= DUPLICATE_FUZZY_MIN_CHARS
            and seen_long
            and process.extractOne(
                norm, seen_long, scorer=fuzz.ratio, score_cutoff=DUPLICATE_SIMILARITY
            )
            is not None
        ):
            duplicates.add(gi)
            continue
        seen_exact.add(norm)
        if mode != "|" and len(norm) >= DUPLICATE_FUZZY_MIN_CHARS:
            seen_long.append(norm)
    return duplicates
