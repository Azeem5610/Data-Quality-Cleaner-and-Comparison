from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import config

app = FastAPI(title="Data Quality Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
