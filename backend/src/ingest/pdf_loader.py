"""Raw PDF extraction. No cleaning: text is returned exactly as PyMuPDF yields it."""

import pymupdf

from src.ingest.errors import IngestError
from src.schemas import PAGE_SEPARATOR, PageText

MIN_TEXT_CHARS = 20  # below this total, treat the PDF as scanned / image-only


def load_pdf(data: bytes) -> list[PageText]:
    """Extract per-page text from PDF bytes, preserving page numbers."""
    if not data:
        raise IngestError("The uploaded file is empty.")
    if not data.lstrip().startswith(b"%PDF"):
        raise IngestError("The uploaded file is not a PDF.")

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise IngestError("Could not open this PDF. The file may be corrupted.")

    try:
        if doc.needs_pass:
            raise IngestError("This PDF is password-protected and cannot be read.")
        if doc.page_count == 0:
            raise IngestError("This PDF has no pages.")

        pages: list[PageText] = []
        for index, page in enumerate(doc):
            pages.append(PageText(page_number=index + 1, text=page.get_text("text")))
    except IngestError:
        raise
    except Exception:
        raise IngestError("Failed to extract text from this PDF.", 500)
    finally:
        doc.close()

    total_chars = sum(len(p.text.strip()) for p in pages)
    if total_chars < MIN_TEXT_CHARS:
        raise IngestError(
            "No extractable text found. This looks like a scanned or image-only PDF "
            "(OCR is not supported)."
        )
    return pages


def join_pages(pages: list[PageText]) -> str:
    """Build the document-level raw_text. Offsets in the API refer to this string."""
    return PAGE_SEPARATOR.join(p.text for p in pages)