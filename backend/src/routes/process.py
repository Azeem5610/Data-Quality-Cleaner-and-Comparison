"""POST /api/process: raw extraction, cleaning, and junk report."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.cleaning.junk_report import build_junk_report
from src.cleaning.pdf_cleaner import clean_pdf
from src.cleaning.web_cleaner import clean_web
from src.ingest.errors import IngestError
from src.ingest.pdf_loader import join_pages, load_pdf
from src.ingest.web_loader import load_web
from src.rag.store import index_source
from src.schemas import ProcessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["process"])

MAX_PDF_BYTES = 25 * 1024 * 1024  # 25 MB


def _new_source_id() -> str:
    return uuid.uuid4().hex[:12]


def _process_pdf(upload: UploadFile) -> ProcessResponse:
    filename = upload.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise IngestError("Only PDF files are supported. Please upload a .pdf file.")

    data = upload.file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise IngestError("That PDF is too large (over 25 MB).", 413)

    pages = load_pdf(data)
    raw_text = join_pages(pages)
    result = clean_pdf(raw_text, pages)
    junk_score, breakdown, summary = build_junk_report(raw_text, result.removed_segments)
    source_id = _new_source_id()
    index_source(source_id, raw_text, result.clean_text)
    return ProcessResponse(
        source_id=source_id,
        source_name=filename,
        source_type="pdf",
        raw_text=raw_text,
        clean_text=result.clean_text,
        removed_segments=result.removed_segments,
        junk_score=junk_score,
        breakdown=breakdown,
        summary=summary,
        pages=pages,
    )


def _process_web(url: str) -> ProcessResponse:
    normalized_url, html, text = load_web(url)
    return process_web_content(normalized_url, html, text)


def process_web_content(source_name: str, html: str, text: str) -> ProcessResponse:
    """Clean, report, and index already-extracted web content."""
    result = clean_web(html, text)
    junk_score, breakdown, summary = build_junk_report(text, result.removed_segments)
    source_id = _new_source_id()
    index_source(source_id, text, result.clean_text)
    return ProcessResponse(
        source_id=source_id,
        source_name=source_name,
        source_type="web",
        raw_text=text,
        clean_text=result.clean_text,
        removed_segments=result.removed_segments,
        junk_score=junk_score,
        breakdown=breakdown,
        summary=summary,
        raw_html=html,
    )


# Plain `def` (not async): blocking I/O (PyMuPDF, requests) runs in FastAPI's threadpool.
@router.post("/process", response_model=ProcessResponse)
def process(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
) -> ProcessResponse:
    has_file = file is not None and bool(file.filename)
    has_url = bool(url and url.strip())

    if has_file == has_url:
        raise HTTPException(
            status_code=400,
            detail="Provide either a PDF file or a URL (exactly one of the two).",
        )

    try:
        if has_file:
            assert file is not None
            return _process_pdf(file)
        assert url is not None
        return _process_web(url)
    except IngestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception:
        logger.exception("Unexpected failure while processing source")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while cleaning this source. Please try another file or URL.",
        )
