from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import ALLOWED_ORIGINS
from src.routes.ask import router as ask_router
from src.routes.process import router as process_router
from src.routes.samples import router as samples_router

app = FastAPI(title="Data Quality Cleaner and Comparison Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process_router)
app.include_router(ask_router)
app.include_router(samples_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
