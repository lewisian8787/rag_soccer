import os
import json
from datetime import datetime
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

from stats_tools import TOOLS, FUNCTION_MAP
from query_stats import format_stats_context

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o"
CLASSIFIER_MODEL = "gpt-4o-mini"
TOP_K = 10
MIN_SCORE = 0.45


# --- System prompt ---

SYSTEM_PROMPT = """
You are an expert football tactics analyst with deep knowledge of the game.
You answer questions about tactics, team setups, player form and fantasy football.

You are given two types of context:
1. MATCH REPORT EXCERPTS — narrative descriptions from match reports
2. STRUCTURED STATS — factual data from a stats database (goals, assists, ratings etc.)

Use both sources where available. Structured stats take priority for factual claims
(e.g. goal counts, dates of goals). Match reports provide tactical and narrative context.

Always respond in the following JSON format:
{
  "answer": "Your detailed answer here",
  "confidence": "high | medium | low",
  "sources": [
    {"title": "Match title", "published_at": "YYYY-MM-DD"}
  ],
  "caveat": "Any important limitations or caveats, or null if none"
}

Guidelines:
- Base your answer only on the provided context — do not use outside knowledge
- If the context doesn't contain enough information, say so and set confidence to low
- Keep answers focused and analytical — avoid vague generalities
- Be concise — state the fact directly, do not explain how it was calculated or restate the question
- Sources should only include match reports you actually drew from
- Set caveat to null if there are no limitations worth flagging
- Stick to a particular season if it is specified
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

def fetch_stats_context(query: str) -> str:
    response = openai_client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a football stats assistant. "
                    "Use the available tools to fetch data relevant to the user's question. "
                    "Call the most appropriate tool with the correct parameters extracted from the question. "
                    "Always expand abbreviations and nicknames to full player names before passing as parameters — "
                    "e.g. 'DCL' → 'Calvert-Lewin', 'TAA' → 'Trent Alexander-Arnold', 'KDB' → 'De Bruyne'."
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


def retrieve(query, from_date=None, gender=None):
    embedding = get_embedding(query)

    pinecone_filter = {}
    if from_date:
        timestamp = int(datetime.strptime(from_date, "%Y-%m-%d").timestamp())
        pinecone_filter["published_at"] = {"$gte": timestamp}
    if gender:
        pinecone_filter["gender"] = {"$eq": gender}

    results = index.query(
        vector=embedding,
        top_k=TOP_K,
        include_metadata=True,
        filter=pinecone_filter if pinecone_filter else None,
    )

    chunks = [r for r in results["matches"] if r["score"] >= MIN_SCORE]
    return chunks


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


# --- Generate answer from LLM ---

def generate(query, chunks, stats_context=""):
    rag_context = build_context(chunks)

    if not rag_context and not stats_context:
        return {
            "answer": "I couldn't find enough relevant information to answer this question.",
            "confidence": "low",
            "sources": [],
            "caveat": "No relevant match reports or stats found."
        }

    sections = []
    if stats_context:
        sections.append(f"STRUCTURED STATS:\n\n{stats_context}")
    if rag_context:
        sections.append(f"MATCH REPORT EXCERPTS:\n\n{rag_context}")

    context_block = "\n\n" + "\n\n".join(sections)
    user_message = f"{context_block}\n\nQuestion: {query}"

    response = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


# --- Main query function ---

def ask(query, from_date=None, gender=None):
    query_types = classify_query(query)

    stats_context = ""
    if "stats" in query_types:
        stats_context = fetch_stats_context(query)

    chunks = []
    if "rag" in query_types:
        chunks = retrieve(query, from_date=from_date, gender=gender)

    result = generate(query, chunks, stats_context=stats_context)
    result["query"] = query
    result["query_types"] = list(query_types)
    result["retrieval_scores"] = [round(c["score"], 4) for c in chunks]
    return result


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
