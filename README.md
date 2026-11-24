# Data Quality Demo

Cleans messy PDFs and websites, reports how much junk they contained, and compares RAG answers on raw vs cleaned data.

## Backend (FastAPI)

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate    macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your OpenRouter key
uvicorn main:app --reload --port 8000
```

Check: http://localhost:8000/api/health and http://localhost:8000/docs

## Frontend (React + Vite + TypeScript)

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173 and it should show "Backend status: ok".

## Structure

- `backend/src/ingest` raw PDF and web extraction
- `backend/src/cleaning` PDF/web cleaners and junk report
- `backend/src/rag` chunker, Chroma store, answering
- `backend/src/routes` API endpoints
- `backend/samples` messy demo sources
- `frontend/src/components` UI components
