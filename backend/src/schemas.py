"""Pydantic models: the API contract. Keep in sync with frontend/src/types/index.ts.

Offset convention: `RemovedSegment.start` / `.end` are character offsets into the
FULL `raw_text` of the document (end is exclusive), so raw_text[start:end] == text.
For PDFs, raw_text is the per-page texts joined with PAGE_SEPARATOR.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

PAGE_SEPARATOR = "\n\n"


class PageText(BaseModel):
    page_number: int  # 1-based
    text: str


class RemovedSegment(BaseModel):
    text: str
    category: str
    start: int
    end: int


class ProcessResponse(BaseModel):
    source_id: str
    source_name: str
    source_type: Literal["pdf", "web"]
    raw_text: str
    clean_text: str = ""
    removed_segments: list[RemovedSegment] = Field(default_factory=list)
    junk_score: float = 0.0  # removed chars / original chars, 0.0 - 1.0
    # Per-category removed chars / original chars; values sum to junk_score.
    breakdown: dict[str, float] = Field(default_factory=dict)
    summary: str = ""
    # Phase 1 extras (needed by Phase 2 cleaners); optional so the core contract is unchanged.
    pages: Optional[list[PageText]] = None  # PDF only
    raw_html: Optional[str] = None  # web only


class AskRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=2000)


class RetrievedChunk(BaseModel):
    text: str
    chunk_index: int
    start: int
    end: int


class AskSideResponse(BaseModel):
    answer: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)


class AskResponse(BaseModel):
    raw: AskSideResponse
    clean: AskSideResponse


class SampleSource(BaseModel):
    name: str
    label: str
