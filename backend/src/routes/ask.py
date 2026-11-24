"""POST /api/ask: compare answers grounded in raw and cleaned source text."""

import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException

from src.config import TOP_K
from src.rag.answer import AnsweringNotConfigured, AnsweringUnavailable, generate_answer
from src.rag.store import retrieve_chunks
from src.schemas import AskRequest, AskResponse, AskSideResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    source_id = request.source_id.strip()
    question = request.question.strip()
    if not source_id.isalnum():
        raise HTTPException(status_code=422, detail="source_id must be alphanumeric.")
    if not question:
        raise HTTPException(status_code=422, detail="question must not be blank.")

    try:
        raw_chunks = retrieve_chunks(source_id, "raw", question, TOP_K)
        clean_chunks = retrieve_chunks(source_id, "clean", question, TOP_K)
    except KeyError:
        raise HTTPException(status_code=404, detail="No indexed source was found for that source_id.")
    except Exception:
        logger.exception("Could not retrieve source chunks")
        raise HTTPException(status_code=500, detail="Could not retrieve this source's chunks.")

    try:
        # The two independent model calls run concurrently to keep comparison latency down.
        with ThreadPoolExecutor(max_workers=2) as executor:
            raw_future = executor.submit(generate_answer, question, raw_chunks)
            clean_future = executor.submit(generate_answer, question, clean_chunks)
            raw_answer = raw_future.result()
            clean_answer = clean_future.result()
    except AnsweringUnavailable as exc:
        status_code = 503 if isinstance(exc, AnsweringNotConfigured) else 502
        raise HTTPException(status_code=status_code, detail=str(exc))
    except Exception:
        logger.exception("Unexpected failure while generating comparison answers")
        raise HTTPException(status_code=502, detail="Could not generate answers for this question.")

    return AskResponse(
        raw=AskSideResponse(answer=raw_answer, chunks=raw_chunks),
        clean=AskSideResponse(answer=clean_answer, chunks=clean_chunks),
    )
