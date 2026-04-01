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

OVERLAP_SENTENCES = 1
EMBEDDING_MODEL = "text-embedding-3-small"

# Token targets vary by article type — match reports are dense and factual so
# small chunks work well; long-form content needs more context per chunk.
TARGET_TOKENS_BY_TYPE = {
    "matchreports": 150,
    "analysis":     300,
    "features":     300,
    "profiles":     300,
    "interview":    300,  # fallback only; interviews use chunk_qa() instead
}
DEFAULT_TARGET_TOKENS = 150

# A paragraph is considered a question if it is short and ends with "?".
# Used by is_qa_format() and chunk_qa().
QA_QUESTION_MAX_TOKENS = 40


# --- Chunking helpers ---

def estimate_tokens(text):
    return len(text) // 4


def split_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text.strip())


def _is_question_para(para):
    """Returns True if a paragraph looks like an interview question."""
    return para.strip().endswith("?") and estimate_tokens(para) < QA_QUESTION_MAX_TOKENS


def is_qa_format(body):
    """
    Returns True if the article body looks like a Q&A interview.
    Heuristic: at least 30% of paragraphs are short and end with '?'.
    """
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    if len(paragraphs) < 4:
        return False
    question_count = sum(1 for p in paragraphs if _is_question_para(p))
    return (question_count / len(paragraphs)) >= 0.30


# --- Q&A chunker ---
# Groups paragraphs into question+answer exchanges, each becoming one chunk.
# If an answer is very long it is split at paragraph boundaries, with the
# question prepended to each continuation chunk so it remains meaningful
# in isolation.

QA_MAX_TOKENS = 400


def chunk_qa(body):
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    chunks = []
    current_question = ""
    current_answer_paras = []

    def flush(question, answer_paras):
        if not answer_paras:
            return
        answer = " ".join(answer_paras)
        if estimate_tokens((question + " " + answer).strip()) <= QA_MAX_TOKENS:
            chunks.append((question + " " + answer).strip())
        else:
            # Answer is too long — split at paragraph boundaries, prepend question each time
            buffer = ""
            for para in answer_paras:
                candidate = (buffer + " " + para).strip()
                if estimate_tokens(candidate) <= QA_MAX_TOKENS:
                    buffer = candidate
                else:
                    if buffer:
                        chunks.append((question + " " + buffer).strip())
                    buffer = para
            if buffer:
                chunks.append((question + " " + buffer).strip())

    for para in paragraphs:
        if _is_question_para(para):
            flush(current_question, current_answer_paras)
            current_question = para
            current_answer_paras = []
        else:
            current_answer_paras.append(para)

    flush(current_question, current_answer_paras)
    return chunks


# --- Standard prose chunker ---
# Splits a body into overlapping chunks of roughly target_tokens size.
# Paragraphs are merged if small, split at sentence boundaries if too large.
# Overlap carries the last sentence of the previous chunk into the next one
# to avoid losing context at chunk boundaries.

def chunk_report(body, target_tokens=DEFAULT_TARGET_TOKENS):
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]

    normalized = []
    buffer = ""

    for para in paragraphs:
        if estimate_tokens(buffer + " " + para) < target_tokens:
            buffer = (buffer + " " + para).strip()
        else:
            if buffer:
                normalized.append(buffer)
            if estimate_tokens(para) > target_tokens:
                sentences = split_sentences(para)
                current = ""
                for sentence in sentences:
                    if estimate_tokens(current + " " + sentence) < target_tokens:
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


# --- Chunker dispatcher ---
# Routes to the appropriate chunker based on article type.

def chunk_article(body, article_type):
    if article_type == "interview" and is_qa_format(body):
        return chunk_qa(body)
    target_tokens = TARGET_TOKENS_BY_TYPE.get(article_type, DEFAULT_TARGET_TOKENS)
    return chunk_report(body, target_tokens=target_tokens)


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

    cur.execute("""
        SELECT mr.id, mr.title, mr.published_at, mrb.body, mr.article_type
        FROM match_report_bodies mrb
        JOIN match_reports mr ON mr.id = mrb.match_report_id
        WHERE mr.published_at >= '2022-08-01'
        -- Exclude live blogs as a safety net — these are also filtered at ingestion
        -- time in fetch_reports.py, but any that slipped through are caught here.
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

    for report_id, title, published_at, body, article_type in rows:
        try:
            chunks = chunk_article(body, article_type or "matchreports")
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
                        "article_type": article_type or "matchreports",
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
