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
MIN_SCORE = 0.50

# --- Gender detection ---
# Defaults to men's football unless the query explicitly mentions women's game.
# Mirrors the keyword list used at ingestion time in embed_reports.py.

WOMENS_KEYWORDS = ["women", "wsl", "ladies", "women's champions league", "lionesses", "wcl",
                   "women's", "womens"]


def detect_query_gender(query):
    query_lower = query.lower()
    if any(kw in query_lower for kw in WOMENS_KEYWORDS):
        return "women"
    return "men"


# --- Step 1: Query normalisation ---
# Expands abbreviations and nicknames to full proper names before anything else touches the query.

def rewrite_query(query: str, history: list[dict] = None) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a football query normaliser. "
                "Your job is to expand player abbreviations and nicknames, and resolve pronouns using conversation history. "
                "For team names, use EXACTLY these names — do not expand or alter them: "
                "'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton', 'Burnley', "
                "'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds', 'Liverpool', "
                "'Manchester City', 'Manchester United', 'Newcastle', 'Nottingham Forest', "
                "'Sunderland', 'Tottenham', 'West Ham', 'Wolves'. "
                "Shorthand mappings for teams: 'Spurs' → 'Tottenham', 'Villa' → 'Aston Villa', "
                "'Man City' → 'Manchester City', 'Man Utd' → 'Manchester United', "
                "'Forest' → 'Nottingham Forest', 'Leeds United' → 'Leeds', 'Leeds Utd' → 'Leeds'. "
                "For players, expand abbreviations: 'DCL' → 'Calvert-Lewin', "
                "'KDB' → 'De Bruyne', 'TAA' → 'Trent Alexander-Arnold'. "
                "If the question refers to a player or team mentioned in recent conversation history, "
                "make those references explicit in the rewritten question. "
                "Preserve the original phrasing and intent exactly — do not rephrase, summarise or add information. "
                "Return only the rewritten question as a plain string, nothing else."
            )
        }
    ]
    if history:
        messages.extend(history[-2:])
    messages.append({"role": "user", "content": query})

    response = openai_client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=100,
    )
    return response.choices[0].message.content.strip()


# --- Step 2: Query classification ---
# Uses gpt-4o-mini to decide whether the query needs structured stats, RAG, or both.
# Structured output enforces the response matches the schema exactly.

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
- Any question asking about a specific positional role (e.g. "best right winger", "best center mid", "best number 10", "best false 9", "best box-to-box", "best defensive mid", "best left back") → rag only — structured data only stores four broad positions (GK/DEF/MID/FWD) and cannot distinguish specific roles within them
- Squad or personnel questions (e.g. "who is their goalkeeper?", "who plays left back for X?", "who is X's number 9?", "what is X's starting XI?") → rag only — stats do not store squad composition or positional assignments
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
        # structured output ensuring response matches the schema
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "query_classification",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "types": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["rag", "stats"]}
                        }
                    },
                    "required": ["types"],
                    "additionalProperties": False
                }
            }
        },
        temperature=0,
    )
    data = json.loads(response.choices[0].message.content)
    return set(data["types"])


# --- Step 3a: Stats branch ---
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
                    "When passing team names as parameters, use EXACTLY these names as stored in the database — "
                    "do not expand or alter them: "
                    "'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton', 'Burnley', "
                    "'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds', 'Liverpool', "
                    "'Manchester City', 'Manchester United', 'Newcastle', 'Nottingham Forest', "
                    "'Sunderland', 'Tottenham', 'West Ham', 'Wolves'. "
                    "For player names, expand abbreviations and nicknames — "
                    "e.g. 'DCL' → 'Calvert-Lewin', 'TAA' → 'Trent Alexander-Arnold', 'KDB' → 'De Bruyne'."
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


# --- Step 3b: RAG branch ---
# Embeds the query and retrieves the most relevant match report chunks from Pinecone.
# Retrieves current-season chunks only — no fallback to older seasons.

CURRENT_SEASON_DATE = "2025-08-01"   # start of 2025/26 season

def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL,
    )
    return response.data[0].embedding


def retrieve_match_report_chunks(query, from_date=None, gender=None):
    # text string query from the user gets embedded — returns a 1536 dimension vector
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

    # Default: current season only — no fallback to older seasons.
    # Falling back previously caused stale data (e.g. players who had
    # transferred being recommended as current squad members).
    chunks = _query_pinecone(CURRENT_SEASON_DATE)
    return chunks, False


# --- Step 4: Assemble context for the final LLM call ---
# Formats retrieved chunks and stats into a structured message block.

def build_context(chunks):
    context_parts = []
    for chunk in chunks:
        meta = chunk["metadata"]
        title = meta.get("title", "Unknown")
        published_at = datetime.fromtimestamp(meta.get("published_at", 0)).strftime("%Y-%m-%d")
        chunk_text = meta.get("chunk_text", "")
        context_parts.append(f"[{title} | {published_at}]\n{chunk_text}")
    return "\n\n---\n\n".join(context_parts)


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


# --- Step 5: Final synthesis and streaming ---
# Makes the single answer-generating LLM call (gpt-4o, stream=True), yields SSE token events
# in real time, holds back chars around <<<META>>> to avoid splitting it mid-stream,
# then parses the trailing metadata JSON and emits a final done event.

ANSWER_SYSTEM_PROMPT = """
You are an expert football tactics analyst with deep knowledge of the game.
You answer questions about tactics, team setups, player form and fantasy football.

You are given two types of context:
1. MATCH REPORT EXCERPTS — narrative descriptions from match reports
2. STRUCTURED STATS — factual data from a stats database (goals, assists, ratings etc.)

Use both sources where available. Structured stats take priority for factual claims.
Match reports provide tactical and narrative context.

Data freshness rules:
- Today's date is {today}. The structured stats DB only contains the current season ({current_season}).
- When discussing current squads, form, or "best player" questions, ONLY name players who appear in the STRUCTURED STATS for this season. If a player is mentioned in match reports but absent from structured stats, they may have transferred and must not be presented as a current squad member.
- NEVER mix men's and women's football data. If the question is about a men's team, ignore any match reports or stats from women's competitions (WSL, Women's Champions League, etc.) and vice versa. Treat them as entirely separate teams.
- Each match report excerpt includes a publication date — ignore excerpts that are clearly from a different season to the one being discussed.

Guidelines:
- Base your answer only on the provided context — do not use outside knowledge
- If the context doesn't contain enough information, say so
- Keep answers focused and analytical — avoid vague generalities
- Be concise — state the fact directly, do not explain how it was calculated or restate the question
- Only include stats relevant to the question — if goals are asked for, show goals only; if no specific stat is requested, include the key stats for that category
- For questions about a specific match (result, scorers, what happened), write the answer as a brief match report in plain prose — 3 to 4 sentences covering the result, who scored, and any notable context. Do not use a list format for this
- For ALL other list-based answers, format each item on its own line (use newlines, not commas or semicolons). Add one short sentence before or after the list as context — no further commentary
- If examples are pulled, they should be from the last 3 years, or only when the current manager was in charge
- Stick to a particular season if it is specified
- For tactical questions, only respond with information across a reasonable time frame
- If the question contains a pronoun or vague reference ('their', 'they', 'the team') that cannot be resolved from the conversation history or the question itself, ask the user to clarify rather than guessing
- Avoid pointless statements or repeating yourself
- If you are presenting a list, number each entry
- Answer in first person as an analyst — never reference your sources, the match reports, the context, or how you derived the answer. Just answer directly as if you know it
- Never say "the match reports suggest", "the narrative indicates", "based on available context", "the data shows", "based on structured stats", "based on the stats", "according to the data", or any similar meta-commentary about sources

Output only your answer as plain prose. Do not include any metadata, delimiters, or JSON.
"""

CONFIDENCE_ASSESSMENT_PROMPT = """You are a quality assessor for a football analytics chatbot.

You will be given a question, a description of the data that was available, and the answer that was generated.
Your job is to assess how confident we should be in the answer on a scale of 1-10.

Scoring guide:
- 10: Answer is based entirely on precise structured stats — fully factual, no ambiguity
- 7-9: Strong match report evidence directly relevant to the question, or stats + supporting narrative
- 4-6: Some relevant context but incomplete, or match reports that are tangentially related
- 2-3: Weak retrieval, thin context, or the answer had to hedge significantly
- 1: No useful data was available

Also flag a caveat if there is a meaningful limitation worth telling the user (e.g. conflicting information, question is about a player not in current stats, the answer had to hedge significantly). Do NOT flag data coverage limitations — the retrieval window is handled by the system and you cannot infer it from the chunks. Return null if there is nothing genuinely worth flagging.

Be strict — only give high scores when the data clearly supports the answer."""


def _assess_confidence(answer: str, query: str, chunks: list, stats_context: str) -> tuple[int, str | None]:
    """Makes a mini LLM call to assess confidence and caveat after the answer has been streamed."""
    has_stats = bool(stats_context)
    has_chunks = bool(chunks)

    context_parts = []
    if stats_context:
        context_parts.append(f"STRUCTURED STATS:\n{stats_context}")
    if has_chunks:
        avg_score = sum(c["score"] for c in chunks) / len(chunks)
        rag_summary = build_context(chunks)
        context_parts.append(
            f"MATCH REPORT CHUNKS ({len(chunks)} retrieved, avg relevance score: {avg_score:.2f}):\n{rag_summary}"
        )
    if not context_parts:
        context_parts.append("No data was available.")

    user_message = (
        f"Question: {query}\n\n"
        f"Data used to generate the answer:\n\n{'---'.join(context_parts)}\n\n"
        f"Answer given: {answer}"
    )

    response = openai_client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {"role": "system", "content": CONFIDENCE_ASSESSMENT_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "confidence_assessment",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "confidence": {"type": "integer"},
                        "caveat": {"type": ["string", "null"]},
                    },
                    "required": ["confidence", "caveat"],
                    "additionalProperties": False,
                },
            },
        },
        temperature=0,
    )

    data = json.loads(response.choices[0].message.content)
    confidence = max(1, min(10, int(data["confidence"])))
    caveat = data["caveat"].strip() if data["caveat"] else None
    return confidence, caveat


def _build_sources(chunks):
    return [
        {
            "title": c["metadata"].get("title", ""),
            "published_at": datetime.fromtimestamp(c["metadata"].get("published_at", 0)).strftime("%Y-%m-%d"),
        }
        for c in chunks
    ]


def generate_response(query, chunks, stats_context="", used_fallback=False, query_types=None, retrieval_scores=None, history=None):
    """Yields SSE events: token events for each answer chunk, then a done event with metadata."""
    rag_context = build_context(chunks)

    if not rag_context and not stats_context:
        no_info = json.dumps({"type": "token", "text": "I couldn't find enough relevant information to answer this question."})
        no_data = json.dumps({
            "type": "done",
            "confidence": 1,
            "sources": [],
            "caveat": "No relevant match reports or stats found.",
            "query_types": query_types or [],
            "retrieval_scores": retrieval_scores or [],
        })
        yield f"data: {no_info}\n\n"
        yield f"data: {no_data}\n\n"
        return

    user_message = _build_user_message(query, chunks, stats_context, used_fallback)

    system_prompt = ANSWER_SYSTEM_PROMPT.format(
        today=datetime.now().strftime("%Y-%m-%d"),
        current_season="2025/26",
    )
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )

    full_answer = ""
    usage = {}
    for chunk in response:
        if chunk.usage:
            usage = {
                "prompt_tokens": chunk.usage.prompt_tokens,
                "completion_tokens": chunk.usage.completion_tokens,
                "total_tokens": chunk.usage.total_tokens,
            }
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content or ""
        if not delta:
            continue
        full_answer += delta
        yield f"data: {json.dumps({'type': 'token', 'text': delta})}\n\n"

    confidence, llm_caveat = _assess_confidence(full_answer, query, chunks, stats_context)
    fallback_caveat = (
        "No match reports were found for the current season. Context is from the previous season (2024/25)."
        if used_fallback else None
    )
    caveat = fallback_caveat or llm_caveat
    sources = _build_sources(chunks)
    done_event = json.dumps({
        "type": "done",
        "confidence": confidence,
        "sources": sources,
        "caveat": caveat,
        "query_types": query_types or [],
        "retrieval_scores": retrieval_scores or [],
        "usage": usage,
    })
    yield f"data: {done_event}\n\n"


# --- Orchestration layer ---
# Normalises the query, classifies it (rag/stats/both), applies recency date logic,
# fetches stats via LLM tool calling and/or retrieves Pinecone chunks, then delegates
# to generate_response to make the final LLM synthesis call and stream the answer.

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

AMBIGUOUS_REF_PATTERN = re.compile(
    r"\b(their|they|them|the team|the club|the player|he|she|his|her)\b",
    re.IGNORECASE
)


def run_pipeline(query, from_date=None, gender=None, history=None):
    """Pipeline entry point for streaming responses."""
    try:
        history = history or []

        # Pre-flight: reject queries with unresolvable pronouns when there is no history
        if not history and AMBIGUOUS_REF_PATTERN.search(query):
            clarification = "Could you clarify who you mean? I don't have any previous context to go on."
            yield f"data: {json.dumps({'type': 'token', 'text': clarification})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'confidence': 0, 'sources': [], 'caveat': None, 'query_types': [], 'retrieval_scores': []})}\n\n"
            return

        # Preserve the original query so user doesn't see normalized version
        original_query = query

        # Step 1: Normalise abbreviations and nicknames
        query = rewrite_query(query, history=history)

        # Step 1b: Default to men's football unless the query mentions women's game
        if gender is None:
            gender = detect_query_gender(query)

        # Step 2: Classify the query — returns a set containing 'rag', 'stats', or both
        query_types = classify_query(query)

        # If the query contains recency language ('recently', 'in form', etc.)
        # and no explicit date was provided, default to the last 30 days.
        if from_date is None and RECENCY_PATTERN.search(query):
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # Step 3a: Stats path — LLM tool calling selects and executes the right SQL function(s)
        stats_context = ""
        if "stats" in query_types:
            stats_context = fetch_stats_context(query, since_date=from_date)

        # Step 3b: RAG path — embed and retrieve Pinecone chunks, discard if all scores too low
        chunks = []
        used_fallback = False
        if "rag" in query_types:
            chunks, used_fallback = retrieve_match_report_chunks(query, from_date=from_date, gender=gender)
            if chunks and all(c["score"] < 0.50 for c in chunks):
                chunks = []

        retrieval_scores = [round(c["score"], 4) for c in chunks]

        # Step 4 + 5: Assemble context and stream the answer
        yield from generate_response(original_query, chunks, stats_context=stats_context, used_fallback=used_fallback, query_types=list(query_types), retrieval_scores=retrieval_scores, history=history)

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_event = json.dumps({"type": "error", "message": str(e)})
        yield f"data: {error_event}\n\n"


def ask(query, from_date=None, gender=None, history=None):
    """Non-streaming entry point — collects run_pipeline output into a dict. Used by tests and CLI."""
    answer_parts = []
    meta = {}
    for raw in run_pipeline(query, from_date=from_date, gender=gender, history=history):
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
