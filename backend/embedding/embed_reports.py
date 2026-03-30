import os
import time
import psycopg2
import re
from datetime import timezone
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

DB_CONN = os.getenv("DATABASE_URL")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

TARGET_TOKENS = 150
OVERLAP_SENTENCES = 1
EMBEDDING_MODEL = "text-embedding-3-small"


# --- Chunking ---
# Splits a match report body into overlapping chunks of roughly TARGET_TOKENS size.
# Paragraphs are merged if small, split at sentence boundaries if too large.
# Overlap carries the last sentence of the previous chunk into the next one
# to avoid losing context at chunk boundaries.

def estimate_tokens(text):
    return len(text) // 4


def split_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text.strip())


def chunk_report(body):
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]

    normalized = []
    buffer = ""

    for para in paragraphs:
        if estimate_tokens(buffer + " " + para) < TARGET_TOKENS:
            buffer = (buffer + " " + para).strip()
        else:
            if buffer:
                normalized.append(buffer)
            if estimate_tokens(para) > TARGET_TOKENS:
                sentences = split_sentences(para)
                current = ""
                for sentence in sentences:
                    if estimate_tokens(current + " " + sentence) < TARGET_TOKENS:
                        current = (current + " " + sentence).strip()
                    else:
                        if current:
                            normalized.append(current)
                        current = sentence
                if current:
                    normalized.append(current)
            else:
                buffer = para

    if buffer:
        normalized.append(buffer)

    chunks = []
    for i, chunk in enumerate(normalized):
        if i == 0:
            chunks.append(chunk)
        else:
            prev_sentences = split_sentences(normalized[i - 1])
            overlap = " ".join(prev_sentences[-OVERLAP_SENTENCES:])
            chunks.append(overlap + " " + chunk)

    return chunks


# --- Gender detection ---
# Classifies a report as men's or women's football based on title keywords.
# Used as a metadata filter at query time so users can search one or the other.

WOMENS_KEYWORDS = ["women", "wsl", "ladies", "women's champions league", "lionesses", "wcl"]


def detect_gender(title):
    title_lower = title.lower()
    if any(kw in title_lower for kw in WOMENS_KEYWORDS):
        return "women"
    return "men"


# --- Embedding ---
# Sends text to OpenAI and returns a 1536-dimension vector.
# This must use the same model as the query embedding at retrieval time.

def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL,
    )
    return response.data[0].embedding


# --- Main embed loop ---
# Fetches all reports from postgres, chunks and embeds each one,
# then upserts vectors to Pinecone. Pinecone upsert is idempotent —
# re-running with the same IDs will safely overwrite existing vectors.
# Failed reports are logged and skipped rather than crashing the run.

def embed_all(batch_size=7523):
    conn = psycopg2.connect(DB_CONN)
    cur = conn.cursor()

    # including logic to exclude live blogs
    cur.execute("""
        SELECT mr.id, mr.title, mr.published_at, mrb.body
        FROM match_report_bodies mrb
        JOIN match_reports mr ON mr.id = mrb.match_report_id
        WHERE mr.published_at >= '2016-01-01'
        -- Exclude live blogs — these are minute-by-minute match logs, not match reports.
        -- They produce very poor chunks (e.g. "45+2: Yellow card for Soucek") that
        -- are useless for tactical or player form queries.
        AND mr.title NOT ILIKE '%%as it happened%%'
        AND mr.title NOT ILIKE '%%– live%%'
        AND mr.title NOT ILIKE '%%- live%%'
        LIMIT %s
    """, (batch_size,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    print(f"Reports to process: {len(rows)}")
    failed = []

    for report_id, title, published_at, body in rows:
        try:
            chunks = chunk_report(body)
            gender = detect_gender(title)
            vectors = []

            for i, chunk_text in enumerate(chunks):
                embedding = get_embedding(chunk_text)
                vectors.append({
                    "id": f"{report_id}-{i}",
                    "values": embedding,
                    "metadata": {
                        "match_report_id": report_id,
                        "chunk_index": i,
                        "chunk_text": chunk_text,
                        "title": title,
                        # stored as Unix timestamp (int) so Pinecone can filter with $gte
                        "published_at": int(published_at.replace(tzinfo=timezone.utc).timestamp()),
                        "gender": gender,
                    }
                })

            index.upsert(vectors=vectors)
            print(f"  report {report_id}: {len(chunks)} chunks upserted")

        except Exception as e:
            print(f"  [FAILED] report {report_id}: {e}")
            failed.append(report_id)

        time.sleep(0.1)

    print(f"\nDone. Failed reports: {len(failed)}")
    if failed:
        print(f"Failed IDs: {failed}")


if __name__ == "__main__":
    embed_all()
