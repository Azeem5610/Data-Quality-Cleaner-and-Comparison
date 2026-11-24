# Implementation Plan: Data Quality Cleaner and Comparison Demo

## Project Structure

```text
data-quality-demo/
├── app.py                  # Streamlit UI (entry point)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── src/
│   ├── config.py           # loads .env, constants
│   ├── ingest/
│   │   ├── pdf_loader.py   # raw PDF extraction
│   │   └── web_loader.py   # raw website fetching
│   ├── cleaning/
│   │   ├── pdf_cleaner.py
│   │   ├── web_cleaner.py
│   │   └── junk_report.py  # junk score + category breakdown
│   ├── rag/
│   │   ├── chunker.py
│   │   ├── store.py        # ChromaDB (two collections: raw, clean)
│   │   └── answer.py       # retrieval + LLM answer
│   └── ui/
│       └── diff_view.py    # side-by-side highlighting
├── samples/                # your messy demo PDF and saved web page
└── data/                   # chroma_db, uploads (git-ignored)
```

---

## Phase 0: Project Setup

### Files to Create

**`requirements.txt`**
```text
streamlit
pymupdf
trafilatura
beautifulsoup4
lxml
requests
chromadb
sentence-transformers
openai
python-dotenv
rapidfuzz
```
*(Note: Pin exact versions later with `pip freeze` once everything works.)*

**`.env.example`**
```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_DIR=data/chroma_db
CHUNK_SIZE=800
CHUNK_OVERLAP=100
TOP_K=4
```

**`.gitignore`**
```gitignore
.env
venv/
.venv/
__pycache__/
*.pyc
data/
.streamlit/secrets.toml
.DS_Store
.idea/
.vscode/
```

**Additional Tasks:**
- Create the folder structure above with empty `__init__.py` files and a short `README.md`.

> **Done when:** Folders exist, `pip install -r requirements.txt` succeeds, and `config.py` loads the `.env` values.

---

## Phase 1: Raw Ingestion

Extract text exactly as a naive pipeline would, with no cleaning.

- **`pdf_loader.py`:** Extract text per page with PyMuPDF.
- **`web_loader.py`:** Fetch the URL and return the full text of the page, including menus and footers.
- Keep the original per-page or per-section structure, because the diff view needs it later.

> **Done when:** You can load your sample PDF and URL and see the raw junk in the output.

---

## Phase 2: Cleaning Engine

The core of your pitch, so spend the most time here. Every removal must be tagged with a category.

- **PDF cleaner:** Detect lines repeating across many pages (headers and footers), remove page numbers, re-join broken line wraps, and collapse extra whitespace and hyphenation breaks.
- **Web cleaner:** Use `trafilatura` for main-content extraction, then strip leftover navigation, cookie text, and boilerplate phrases with your own rules; remove duplicate lines and blocks.
- **Output for each:** Cleaned text plus a list of removed segments: `{"text": ..., "category": ...}`.

> **Done when:** Both sample sources clean visibly well, with removals logged.

---

## Phase 3: Junk Report

- **Junk Score Formula:**
  $$\text{Junk Score} = \frac{\text{Removed Characters}}{\text{Original Characters}}$$
- **Category Breakdown:** Headers/footers, navigation, page numbers, duplicates, boilerplate, and whitespace.
- **Summary Output:** Plain-language summary line (e.g., *"34% of this document was junk, mostly repeated headers and navigation"*).

> **Done when:** A function returns a score plus breakdown you can drop straight into the UI.

---

## Phase 4: Chunking and Vector Store

- **Chunker:** Sentence-aware splitting (semantic chunking can come later).
- **Vector Store:** Two ChromaDB collections built from the same source: `raw` and `clean`.
- **Metadata:** Store `source name`, `file type`, and `chunk index`.

> **Done when:** You can index one source into both collections and retrieve top chunks from each.

---

## Phase 5: Dual RAG Answering

- Run one question through retrieval and the LLM twice—once on `raw` and once on `clean`—with identical settings.
- Return each answer plus the retrieved chunks used.
- **Prompt Rule (for both):** Answer *only* from the provided context.

> **Done when:** For your chosen test question, `raw` gives a worse answer and `clean` gives a correct one. *(If the contrast is weak, change your sample document or question, not the logic.)*

---

## Phase 6: Streamlit UI

Build a single-screen interface containing:
1. Upload / URL input.
2. Junk Score card with the category breakdown.
3. Side-by-side raw vs. cleaned view with removed text highlighted.
4. Question box with two answer panels and source chunks underneath.

> **Done when:** The full demo flow runs from one screen without touching the terminal.

---

## Phase 7: Demo Polish and Rehearsal

- [ ] Cache results so the demo doesn't wait on re-processing.
- [ ] Add a "Load Sample" button for your prepared PDF and website.
- [ ] Handle errors gracefully (bad URL, empty PDF, API failure).
- [ ] Rehearse the pitch once end-to-end with the 5-step flow.
- [ ] Record a screen capture as a backup in case the internet fails during the meeting.

---

## Optional Extras (If Time Remains)

- Word (`.docx`) and Markdown (`.md`) cleaners.
- Metadata and duplicate detection across multiple files.
- Export cleaned data as JSON or Markdown.