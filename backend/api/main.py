import sys
import os

RETRIEVAL_DIR = os.path.join(os.path.dirname(__file__), "..", "retrieval")
sys.path.insert(0, RETRIEVAL_DIR)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal

import football.football_pipeline as football_pipeline
import fpl.fpl_pipeline as fpl_pipeline  # noqa: F401 — fpl stub
from football.query_stats import get_standings


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    query: str
    mode: str = "football"
    from_date: str | None = None
    gender: str | None = None
    history: list[ConversationTurn] = []


app = FastAPI()

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://dugout.ianlewis.online",
    os.getenv("FRONTEND_URL", ""),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ALLOWED_ORIGINS if o],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_pipeline(mode: str):
    # mode is contained in the request body
    if mode == "fpl":
        return fpl_pipeline
    return football_pipeline


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


@app.get("/api/standings")
def standings_endpoint():
    try:
        return get_standings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# main and really only route.
@app.post("/api/ask/stream")
def ask_stream_endpoint(body: AskRequest):
    # Extract and validate the query string from the request body.
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    # Select the correct pipeline module based on the mode sent by the frontend
    pipeline = _get_pipeline(body.mode)

    # wraps the return in FastAPI's StreamingRepsonse object, which sends tokens back
    # to the front end as soon as they are generated.
    return StreamingResponse(
        pipeline.run_pipeline(
            query=query,
            from_date=body.from_date,
            gender=body.gender,
            history=[t.model_dump() for t in body.history],
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
