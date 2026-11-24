"""Build a compact junk report from a cleaner's removal log.

Scores and category values are fractions of the original source's character count.
Consequently, the category values sum to ``junk_score`` (up to floating point
rounding), which makes the report directly comparable across sources.
"""

from collections import defaultdict

from src.schemas import RemovedSegment


def build_junk_report(
    raw_text: str, removed_segments: list[RemovedSegment]
) -> tuple[float, dict[str, float], str]:
    """Return ``(junk_score, category_breakdown, summary)`` for a cleaned source."""
    source_size = len(raw_text)
    removed_by_category: dict[str, int] = defaultdict(int)
    removed_chars = 0

    for segment in removed_segments:
        # Use the logged source range as the authoritative removed length. This
        # keeps scoring aligned with the offsets rendered by the diff view.
        length = max(0, segment.end - segment.start)
        if length == 0:
            continue
        removed_chars += length
        removed_by_category[segment.category] += length

    if source_size == 0:
        return 0.0, {}, "No source text was available to assess."

    junk_score = min(1.0, removed_chars / source_size)
    breakdown = {
        category: count / source_size
        for category, count in sorted(removed_by_category.items())
    }

    if removed_chars == 0:
        summary = "No junk text was detected in the source."
    else:
        percent = f"{junk_score:.1%}"
        category_count = len(removed_by_category)
        noun = "category" if category_count == 1 else "categories"
        summary = (
            f"{percent} of the source text was removed as junk across "
            f"{category_count} {noun}."
        )

    return junk_score, breakdown, summary
