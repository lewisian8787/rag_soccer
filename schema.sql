CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS match_reports (
    id              SERIAL PRIMARY KEY,
    title           TEXT,
    url             TEXT UNIQUE,
    published_at    TIMESTAMPTZ,
    source          TEXT
);

CREATE TABLE IF NOT EXISTS match_report_bodies (
    id                SERIAL PRIMARY KEY,
    match_report_id   INTEGER REFERENCES match_reports(id),
    body              TEXT
);

CREATE TABLE IF NOT EXISTS match_report_chunks (
    id                SERIAL PRIMARY KEY,
    match_report_id   INTEGER REFERENCES match_reports(id),
    chunk_index       INTEGER,
    chunk_text        TEXT,
    embedding         vector(1536)
);

CREATE INDEX ON match_report_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
