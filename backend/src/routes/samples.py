"""Prepared offline demo sources."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.ingest.web_loader import html_to_visible_text
from src.routes.process import process_web_content
from src.schemas import ProcessResponse, SampleSource

router = APIRouter(prefix="/api", tags=["samples"])
logger = logging.getLogger(__name__)
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"
SAMPLES = {
    "urban-heat": SampleSource(name="urban-heat", label="Urban heat response plan"),
}


@router.get("/samples", response_model=list[SampleSource])
def list_samples() -> list[SampleSource]:
    return list(SAMPLES.values())


@router.post("/samples/{name}", response_model=ProcessResponse)
def load_sample(name: str) -> ProcessResponse:
    sample = SAMPLES.get(name)
    if sample is None:
        raise HTTPException(status_code=404, detail="That demo sample was not found.")

    sample_path = SAMPLES_DIR / f"{name}.html"
    try:
        html = sample_path.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=500, detail="The demo sample could not be loaded.")

    text = html_to_visible_text(html)
    try:
        return process_web_content(f"{sample.label} (sample)", html, text)
    except Exception:
        logger.exception("Could not process the prepared demo sample")
        raise HTTPException(status_code=500, detail="The demo sample could not be processed.")
