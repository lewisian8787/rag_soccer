import sys
import os

RETRIEVAL_DIR = os.path.join(os.path.dirname(__file__), "..", "retrieval")
sys.path.insert(0, RETRIEVAL_DIR)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import football.query as football_pipeline
import fpl.query as fpl_pipeline

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_pipeline(mode: str):
    if mode == "fpl":
        return fpl_pipeline
    return football_pipeline


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/ask")
def ask_endpoint(body: dict):
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    pipeline = _get_pipeline(body.get("mode", "football"))
    result = pipeline.ask(
        query=query,
        from_date=body.get("from_date"),
        gender=body.get("gender"),
    )
    return result


@app.post("/api/ask/stream")
def ask_stream_endpoint(body: dict):
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    pipeline = _get_pipeline(body.get("mode", "football"))
    return StreamingResponse(
        pipeline.stream_ask(
            query=query,
            from_date=body.get("from_date"),
            gender=body.get("gender"),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
