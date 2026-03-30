import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "retrieval"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from query import ask, stream_ask

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/ask")
def ask_endpoint(body: dict):
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    result = ask(
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

    return StreamingResponse(
        stream_ask(
            query=query,
            from_date=body.get("from_date"),
            gender=body.get("gender"),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
