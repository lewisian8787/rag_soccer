import json


def run_pipeline(query, from_date=None, gender=None):
    """FPL pipeline — stub. No data ingested yet."""
    msg = (
        "FPL mode is coming soon. "
        "We're working on integrating price, points, ownership and fixture data. "
        "Check back shortly."
    )
    yield f"data: {json.dumps({'type': 'token', 'text': msg})}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'confidence': 'low', 'sources': [], 'caveat': 'No FPL data has been ingested yet. This feature is in early development.'})}\n\n"


def ask(query, from_date=None, gender=None):
    return {
        "answer": "FPL mode is coming soon — no data ingested yet.",
        "confidence": "low",
        "sources": [],
        "caveat": "This feature is in early development.",
        "query": query,
        "query_types": ["fpl"],
        "retrieval_scores": [],
    }
