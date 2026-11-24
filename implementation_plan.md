# Revised Plan: React + Vite + TypeScript Frontend

Switching the frontend means that the Python code can no longer be rendered by Streamlit. It will instead become a FastAPI backend, and the React application will communicate with it. Phases 1–5 retain the same logic while exposing it through API endpoints. Phase 6 becomes the React build.

## Project Structure

```text
data-quality-demo/
├── backend/
│   ├── main.py                 # FastAPI app entry
│   ├── requirements.txt
│   ├── .env.example
│   ├── src/
│   │   ├── config.py
│   │   ├── ingest/             # pdf_loader.py, web_loader.py
│   │   ├── cleaning/           # pdf_cleaner.py, web_cleaner.py, junk_report.py
│   │   ├── rag/                # chunker.py, store.py, answer.py
│   │   ├── routes/             # process.py, ask.py, samples.py
│   │   └── schemas.py          # Pydantic models (the API contract)
│   ├── samples/                # messy demo PDF + saved web page
│   └── data/                   # chroma_db, uploads (git-ignored)
├── frontend/
│   ├── package.json
│   ├── vite.config.ts          # dev proxy to the backend
│   ├── tsconfig.json
│   ├── .env.example
│   └── src/
│       ├── main.tsx, App.tsx
│       ├── api/client.ts       # typed API calls
│       ├── types/index.ts      # mirrors backend schemas
│       └── components/         # SourceInput, JunkScoreCard,
│                               # DiffView, AskPanel, AnswerCompare
├── .gitignore
└── README.md
```

## Phase 0: Project Setup

### `backend/requirements.txt`

```text
fastapi
uvicorn[standard]
python-multipart
pydantic
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

`python-multipart` is needed for PDF uploads. Uvicorn runs the server.

### `backend/.env.example`

```dotenv
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_DIR=data/chroma_db
CHUNK_SIZE=800
CHUNK_OVERLAP=100
TOP_K=4
ALLOWED_ORIGINS=http://localhost:5173
```

### `frontend/.env.example`

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

### `.gitignore`

```gitignore
# env
.env
backend/.env
frontend/.env

# python
venv/
.venv/
__pycache__/
*.pyc

# node
node_modules/
dist/

# data
backend/data/

# editors / OS
.DS_Store
.idea/
.vscode/
```

Create the frontend with the Vite React + TypeScript template, then add the required dependencies, such as a lightweight data-fetching library and a styling approach like Tailwind or plain CSS modules. Keep the dependencies and structure light because the UI has only a few screens.

**Done when:**

- Backend dependencies install successfully.
- `uvicorn main:app --reload` serves a health-check endpoint.
- The Vite development server starts successfully.
- The frontend can call the health endpoint.
- CORS and the development proxy work correctly.

## Phase 1: Raw Ingestion (Backend)

Implement ingestion behind `POST /api/process`, which accepts a PDF upload or a URL. Return the raw text while preserving its page or section structure.

## Phase 2: Cleaning Engine (Backend)

Keep the cleaning logic unchanged. Return the cleaned text and a list of removed segments:

```json
{
  "text": "...",
  "category": "...",
  "location": "..."
}
```

The `location` field is important for the React diff view because it identifies where each removed segment should be highlighted.

## Phase 3: Junk Report (Backend)

Generate and return the following:

- Junk score
- Category breakdown
- Summary line

Include all of these in the `POST /api/process` response.

## Phase 4: Chunking and Vector Store (Backend)

Create two Chroma collections per processed source:

- Raw collection
- Clean collection

Key both collections with the `source_id` returned to the frontend.

## Phase 5: Dual RAG Answering (Backend)

`POST /api/ask` accepts a source ID and question:

```json
{
  "source_id": "...",
  "question": "..."
}
```

It returns both answers and the retrieved chunks for each side.

### API Contract

Freeze the following contract before building the UI:

| Method | Endpoint | Response |
| --- | --- | --- |
| `POST` | `/api/process` | `{ source_id, raw_text, clean_text, removed_segments[], junk_score, breakdown{}, summary }` |
| `POST` | `/api/ask` | `{ raw: { answer, chunks[] }, clean: { answer, chunks[] } }` |
| `GET` | `/api/samples` | Prepared demo source names |
| `POST` | `/api/samples/{name}` | Loads a prepared demo source |
| `GET` | `/api/health` | Health status |

Mirror this contract with Pydantic schemas in the backend and TypeScript types in the frontend to keep both sides in sync.

## Phase 6: React Frontend

Build the frontend in this order so it remains demonstrable throughout development:

1. **API client and types** — Add typed wrappers for all endpoints.
2. **SourceInput** — Add a PDF drop zone, URL field, and **Load sample** buttons.
3. **JunkScoreCard** — Display the large percentage, category bars, and summary line.
4. **DiffView** — Show raw text on the left and cleaned text on the right. Highlight removed segments and color-code them by category.
5. **AskPanel and AnswerCompare** — Add one question box and two answer cards for raw versus clean results, with expandable source chunks.
6. **App flow and states** — Add loading, error, and empty states.

**Done when:** the complete demo runs in the browser from a single page.

## Phase 7: Demo Polish and Rehearsal

- Cache processed samples so the demo does not wait.
- Add loading skeletons and friendly error messages.
- Record a backup screen recording in case the internet is unavailable.
- Complete one full rehearsal of the pitch flow.