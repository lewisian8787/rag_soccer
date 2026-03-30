import os
import re
import json
from datetime import datetime, timedelta
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

from football.stats_tools import TOOLS, FUNCTION_MAP
from football.query_stats import format_stats_context

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o"
CLASSIFIER_MODEL = "gpt-4o-mini"
TOP_K = 20  # fetch more to compensate for deduplication
MIN_SCORE = 0.45


# --- System prompt ---

# stream = true on request to Open AI generates token by token

STREAM_SYSTEM_PROMPT = """
You are an expert football tactics analyst with deep knowledge of the game.
You answer questions about tactics, team setups, player form and fantasy football.

You are given two types of context:
1. MATCH REPORT EXCERPTS — narrative descriptions from match reports
2. STRUCTURED STATS — factual data from a stats database (goals, assists, ratings etc.)

Use both sources where available. Structured stats take priority for factual claims.
Match reports provide tactical and narrative context.

Guidelines:
- Base your answer only on the provided context — do not use outside knowledge
- If the context doesn't contain enough information, say so
- Keep answers focused and analytical — avoid vague generalities
- Be concise — state the fact directly, do not explain how it was calculated or restate the question
- For leaderboard or ranking questions, aim to return 10 entries unless the user specifies otherwise
- Only include stats relevant to the question — if goals are asked for, show goals only; if no specific stat is requested, include the key stats for that category
- For ALL list-based answers, format each item on its own line (use newlines, not commas or semicolons). Add one short sentence before or after the list as context — no further commentary
- If examples are pulled, they should be from the last 3 years, or only when the current manager was in charge
- Stick to a particular season if it is specified
- For tactical questions, only respond with information across a reasonable time frame
- Avoid pointless statements or repeating yourself
- If you are presenting a list, number each entry
- Don't ever use the phrase, based on the context available, or something similar as it is implied

Output your response in EXACTLY this format — answer text first, then the delimiter, then metadata JSON:

[Your answer here as plain prose]
<<<META>>>
{"confidence": "high|medium|low", "sources": [{"title": "...", "published_at": "YYYY-MM-DD"}], "caveat": "..." or null}

Rules for the metadata:
- sources should only include match reports you actually drew from
- caveat should be null if there are no limitations worth flagging
"""




# --- Query classification ---
# Uses gpt-4o-mini to decide whether the query needs structured stats, RAG, or both.

CLASSIFIER_PROMPT = """You are a query router for a football analytics chatbot.

Classify the user's question into one or more of these categories:
- "rag"   — needs match report narrative (tactics, team shape, player form descriptions, atmosphere)
- "stats" — needs structured data (goals, assists, cards, ratings, results, leaderboards)

Rules:
- Pure tactical questions (e.g. "How does Arsenal press?", "How do Liverpool defend set pieces?") → rag only
- Pure stat lookups (e.g. "How many goals has Salah scored?", "What was the score?") → stats only
- Player form questions (e.g. "How has Salah been playing?", "Is Saka in form?") → always both — narrative context AND stats are needed
- Fantasy questions (e.g. "Is X worth picking?", "Who should I start?") → always both
- Subjective quality questions about players (e.g. "Who has been clinical?", "Who has been creative?") → always both — stats confirm it, reports explain it
- Match recap questions (e.g. "What happened in the last X game?", "How did X get on?", "What was the result when X played Y?") → always both — stats for the actual result, RAG for the narrative context
- Any references to 'recent' or 'as of late' or anything that implies recent, only utilize sources from the last month

When in doubt, return both.

Respond with valid JSON only, no explanation:
{"types": ["rag", "stats"]}
"""


def classify_query(query: str) -> set[str]:
    response = openai_client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": query},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(response.choices[0].message.content)
    return set(data.get("types", ["rag"]))


# --- Stats fetch via LLM tool calling ---
# Sends the query to gpt-4o-mini with the tool definitions as the menu.
# The model selects the right function and extracts parameters.
# We then execute the function and return formatted context.

def fetch_stats_context(query: str, since_date: str = None) -> str:
    # Default to current season if no date specified — mirrors RAG's CURRENT_SEASON_DATE default
    effective_date = since_date or CURRENT_SEASON_DATE
    date_instruction = (
        f" Default to data from {effective_date} onwards by passing since_date='{effective_date}' "
        f"to any tool that supports it, unless the user explicitly asks about an earlier period."
    )

    response = openai_client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a football stats assistant. "
                    "Use the available tools to fetch data relevant to the user's question. "
                    "Call the most appropriate tool with the correct parameters extracted from the question. "
                    "Always expand abbreviations and nicknames to full names before passing as parameters — "
                    "e.g. 'DCL' → 'Calvert-Lewin', 'TAA' → 'Trent Alexander-Arnold', 'KDB' → 'De Bruyne', "
                    "'Spurs' → 'Tottenham', 'Man United' → 'Manchester United', 'Man City' → 'Manchester City', "
                    "'Wolves' → 'Wolverhampton', 'Villa' → 'Aston Villa', 'Leicester' → 'Leicester'."
                    + date_instruction
                )
            },
            {"role": "user", "content": query},
        ],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0,
    )

    message = response.choices[0].message

    if not message.tool_calls:
        return ""

    parts = []
    for tool_call in message.tool_calls:
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)

        fn = FUNCTION_MAP.get(fn_name)
        if not fn:
            continue

        result = fn(**fn_args)
        parts.append(format_stats_context(result, fn_name))

    return "\n\n".join(parts)


# --- Retrieve relevant chunks from Pinecone ---

def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL,
    )
    return response.data[0].embedding


CURRENT_SEASON_DATE = "2025-08-01"   # start of 2025/26 season
FALLBACK_SEASON_DATE = "2024-08-01"  # start of 2024/25 season — fallback if current season empty


def retrieve(query, from_date=None, gender=None):
    # text string query from the user gets embedded. Return 1536 dimension vector
    embedding = get_embedding(query)

    def _query_pinecone(cutoff_date):
        pinecone_filter = {}
        if cutoff_date:
            timestamp = int(datetime.strptime(cutoff_date, "%Y-%m-%d").timestamp())
            pinecone_filter["published_at"] = {"$gte": timestamp}
        if gender:
            pinecone_filter["gender"] = {"$eq": gender}
        results = index.query(
            vector=embedding,
            top_k=TOP_K,
            include_metadata=True,
            filter=pinecone_filter if pinecone_filter else None,
        )
        # Deduplicate by article title — multiple chunks from the same report waste context slots
        seen_titles = set()
        unique = []
        for r in results["matches"]:
            if r["score"] < MIN_SCORE:
                continue
            title = r["metadata"].get("title", "")
            if title not in seen_titles:
                seen_titles.add(title)
                unique.append(r)
        return unique

    # If caller specified a date, use it directly with no fallback
    if from_date is not None:
        return _query_pinecone(from_date), False

    # Default: try current season first
    chunks = _query_pinecone(CURRENT_SEASON_DATE)
    if chunks:
        return chunks, False

    # Fall back to previous season and flag it
    chunks = _query_pinecone(FALLBACK_SEASON_DATE)
    return chunks, bool(chunks)


# --- Build context string from retrieved chunks ---

def build_context(chunks):
    context_parts = []
    for chunk in chunks:
        meta = chunk["metadata"]
        title = meta.get("title", "Unknown")
        published_at = datetime.fromtimestamp(meta.get("published_at", 0)).strftime("%Y-%m-%d")
        chunk_text = meta.get("chunk_text", "")
        context_parts.append(f"[{title} | {published_at}]\n{chunk_text}")
    return "\n\n---\n\n".join(context_parts)


# --- Main query function ---

RECENCY_PATTERN = re.compile(
    r"\b("
    # Recency adverbs
    r"recently|lately|of late|as of late|nowadays|these days|"
    r"right now|at the moment|currently|presently|"
    # Form/momentum language
    r"in form|in good form|on form|on fire|hot streak|flying|"
    r"sharp|clinical|looking good|looking sharp|back to his best|"
    r"hit the ground running"
    r")\b",
    re.IGNORECASE
)


def ask(query, from_date=None, gender=None):
    """Non-streaming entry point — collects stream_ask output into a dict. Used by tests and CLI."""
    answer_parts = []
    meta = {}
    for raw in stream_ask(query, from_date=from_date, gender=gender):
        if not raw.startswith("data: "):
            continue
        event = json.loads(raw[6:])
        if event["type"] == "token":
            answer_parts.append(event["text"])
        elif event["type"] == "done":
            meta = event
    return {
        "answer": "".join(answer_parts),
        "confidence": meta.get("confidence", "low"),
        "sources": meta.get("sources", []),
        "caveat": meta.get("caveat"),
        "query": query,
        "query_types": meta.get("query_types", []),
        "retrieval_scores": [],
    }


# --- Streaming system prompt ---
# Instructs the model to output answer text, then a delimiter, then compact metadata JSON.
# This lets us stream the answer tokens and parse metadata cleanly at the end.

def _build_user_message(query, chunks, stats_context, used_fallback):
    rag_context = build_context(chunks)
    sections = []
    if stats_context:
        sections.append(f"STRUCTURED STATS:\n\n{stats_context}")
    if rag_context:
        sections.append(f"MATCH REPORT EXCERPTS:\n\n{rag_context}")
    context_block = "\n\n" + "\n\n".join(sections) if sections else ""
    fallback_note = (
        "\n\nNote: No match reports were found for the current season. "
        "The following context is from the previous season (2024/25). "
        "Make clear in your answer and caveat that this is last season's data."
        if used_fallback else ""
    )
    return f"{context_block}{fallback_note}\n\nQuestion: {query}"


#using Open AI's stream property = true to formulate the reply as a stream and not as a single block
def stream_generate(query, chunks, stats_context="", used_fallback=False, query_types=None, retrieval_scores=None):
    """Yields SSE events: token events for each answer chunk, then a done event with metadata."""
    rag_context = build_context(chunks)

    if not rag_context and not stats_context:
        no_data = json.dumps({
            "type": "done",
            "confidence": "low",
            "sources": [],
            "caveat": "No relevant match reports or stats found.",
        })
        no_info = json.dumps({"type": "token", "text": "I couldn't find enough relevant information to answer this question."})
        yield f"data: {no_info}\n\n"
        yield f"data: {no_data}\n\n"
        return

    user_message = _build_user_message(query, chunks, stats_context, used_fallback)

    response = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": STREAM_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        stream=True,
    )

    full_text = ""
    answer_flushed = 0
    DELIMITER = "<<<META>>>"
    HOLD = len(DELIMITER) + 5  # hold back enough chars to detect delimiter mid-stream

    for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        if not delta:
            continue
        full_text += delta

        if DELIMITER in full_text:
            continue  # stop flushing once we've seen the delimiter

        safe_to = max(0, len(full_text) - HOLD)
        if safe_to > answer_flushed:
            to_send = full_text[answer_flushed:safe_to]
            answer_flushed = safe_to
            yield f"data: {json.dumps({'type': 'token', 'text': to_send})}\n\n"

    # Flush remaining answer and parse metadata
    if DELIMITER in full_text:
        answer_part, meta_part = full_text.split(DELIMITER, 1)
        remaining = answer_part[answer_flushed:]
    else:
        answer_part = full_text
        remaining = full_text[answer_flushed:]
        meta_part = ""

    if remaining.strip():
        yield f"data: {json.dumps({'type': 'token', 'text': remaining})}\n\n"

    try:
        meta = json.loads(meta_part.strip()) if meta_part.strip() else {}
    except Exception:
        meta = {}

    done_event = json.dumps({
        "type": "done",
        "confidence": meta.get("confidence", "low"),
        "sources": meta.get("sources", []),
        "caveat": meta.get("caveat"),
        "query_types": query_types or [],
        "retrieval_scores": retrieval_scores or [],
    })
    yield f"data: {done_event}\n\n"


def stream_ask(query, from_date=None, gender=None):
    """Pipeline entry point for streaming responses."""
    try:
        query_types = classify_query(query)

        if from_date is None and RECENCY_PATTERN.search(query):
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        stats_context = ""
        if "stats" in query_types:
            stats_context = fetch_stats_context(query, since_date=from_date)

        chunks = []
        used_fallback = False
        if "rag" in query_types:
            chunks, used_fallback = retrieve(query, from_date=from_date, gender=gender)
            if chunks and all(c["score"] < 0.55 for c in chunks):
                chunks = []

        retrieval_scores = [round(c["score"], 4) for c in chunks]
        yield from stream_generate(query, chunks, stats_context=stats_context, used_fallback=used_fallback, query_types=list(query_types), retrieval_scores=retrieval_scores)

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_event = json.dumps({"type": "error", "message": str(e)})
        yield f"data: {error_event}\n\n"


if __name__ == "__main__":
    import sys

    q_arg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None

    if q_arg:
        result = ask(q_arg)
        print(json.dumps(result, indent=2))
    else:
        queries = [
            ("How has Salah been playing this season?", "2025-08-01", None),
            ("When did Salah last score?", None, None),
            ("Who are the top scorers in the Premier League this season?", None, None),
            ("How do Arsenal press high?", None, None),
        ]
        for query, from_date, gender in queries:
            print(f"\n{'='*60}")
            print(f"Q: {query}")
            result = ask(query, from_date=from_date, gender=gender)
            print(json.dumps(result, indent=2))
