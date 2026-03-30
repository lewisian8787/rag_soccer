import os
from datetime import datetime
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 10
LOW_SCORE_THRESHOLD = 0.75

# Each query has an optional from_date filter.
# Recency-sensitive queries (player form, fantasy) are filtered to recent reports.
# Tactical queries have no date filter — historical context is still relevant.
TEST_QUERIES = [
    # Tactical — no date filter
    {"query": "How do Arsenal play against the high press?",           "from_date": None},
    {"query": "How do Liverpool set up defensively away from home?",   "from_date": None},
    {"query": "How do Manchester City build up play from the back?",   "from_date": None},
    # Player form — last 6 months only
    {"query": "How has Salah been performing recently?",               "from_date": "2025-09-01"},
    {"query": "How has Bukayo Saka been playing this season?",         "from_date": "2025-09-01"},
    # Fantasy — last 6 months only
    {"query": "Which strikers have been in good form recently?",       "from_date": "2025-09-01"},
    {"query": "Which midfielders have been contributing goals and assists?", "from_date": "2025-09-01"},
]


def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL,
    )
    return response.data[0].embedding


def run_query(query, from_date=None):
    embedding = get_embedding(query)

    # Build optional metadata filter for Pinecone.
    # If from_date is set, only return chunks from reports published after that date.
    pinecone_filter = {}
    if from_date:
        # Pinecone requires numeric values for $gte — convert date string to Unix timestamp
        timestamp = int(datetime.strptime(from_date, "%Y-%m-%d").timestamp())
        pinecone_filter = {"published_at": {"$gte": timestamp}}

    results = index.query(
        vector=embedding,
        top_k=TOP_K,
        include_metadata=True,
        filter=pinecone_filter if pinecone_filter else None,
    )

    date_label = f" (from {from_date})" if from_date else ""
    print(f"\nQuery: {query}{date_label}")
    print("─" * 60)

    for i, match in enumerate(results["matches"], 1):
        score = match["score"]
        meta = match["metadata"]
        title = meta.get("title", "Unknown")
        published_at = datetime.fromtimestamp(meta.get("published_at", 0)).strftime("%Y-%m-%d")
        chunk_text = meta.get("chunk_text", "")

        flag = "[LOW]" if score < LOW_SCORE_THRESHOLD else f"[{i}]  "
        print(f"{flag} Score: {score:.4f} | {title[:50]} | {published_at}")
        print(f"      \"{chunk_text}...\"")
        print()


if __name__ == "__main__":
    for item in TEST_QUERIES:
        run_query(item["query"], from_date=item["from_date"])
