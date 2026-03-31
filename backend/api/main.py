import sys
import os

RETRIEVAL_DIR = os.path.join(os.path.dirname(__file__), "..", "retrieval")
sys.path.insert(0, RETRIEVAL_DIR)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import football.football_pipeline as football_pipeline
import fpl.fpl_pipeline as fpl_pipeline  # noqa: F401 — fpl stub

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_pipeline(mode: str):
    # mode is contained in the request body
    if mode == "fpl":
        return fpl_pipeline
    return football_pipeline


@app.get("/health")
def health():
    return {"status": "ok"}


# main and really only route.
@app.post("/api/ask/stream")
def ask_stream_endpoint(body: dict):
    # Extract and validate the query string from the request body.
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    # Select the correct pipeline module based on the mode sent by the frontend
    pipeline = _get_pipeline(body.get("mode", "football"))

    # wraps the return in FastAPI's StreamingRepsonse object, which sends tokens back
    # to the front end as soon as they are generated. 
    return StreamingResponse(
        pipeline.run_pipeline(
            query=query,
            from_date=body.get("from_date"),
            gender=body.get("gender"),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
