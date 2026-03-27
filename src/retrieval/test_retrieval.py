import os
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 5
LOW_SCORE_THRESHOLD = 0.75

TEST_QUERIES = [
    # Tactical
    "How do Arsenal play against the high press?",
    "How do Liverpool set up defensively away from home?",
    "How do Manchester City build up play from the back?",
    # Player form
    "How has Salah been performing recently?",
    "How has Bukayo Saka been playing this season?",
    # Fantasy
    "Which strikers have been in good form recently?",
    "Which midfielders have been contributing goals and assists?",
]


def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL,
    )
    return response.data[0].embedding


def run_query(query):
    embedding = get_embedding(query)
    results = index.query(vector=embedding, top_k=TOP_K, include_metadata=True)

    print(f"\nQuery: {query}")
    print("─" * 60)

    for i, match in enumerate(results["matches"], 1):
        score = match["score"]
        meta = match["metadata"]
        title = meta.get("title", "Unknown")
        published_at = meta.get("published_at", "")[:10]
        chunk_text = meta.get("chunk_text", "")[:200]

        flag = "[LOW]" if score < LOW_SCORE_THRESHOLD else f"[{i}]  "
        print(f"{flag} Score: {score:.4f} | {title[:50]} | {published_at}")
        print(f"      \"{chunk_text}...\"")
        print()


if __name__ == "__main__":
    for query in TEST_QUERIES:
        run_query(query)
