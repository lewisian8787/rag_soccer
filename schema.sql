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

-- Stats tables — sourced from API-Football
-- Used for structured stat queries (goals, assists, cards etc.)
-- that cannot be reliably answered from match report text alone.

CREATE TABLE IF NOT EXISTS api_players (
    id          INTEGER PRIMARY KEY,  -- API-Football player ID
    name        TEXT,
    position    TEXT
);

CREATE TABLE IF NOT EXISTS api_matches (
    id          INTEGER PRIMARY KEY,  -- API-Football fixture ID
    date        TIMESTAMPTZ,
    home_team   TEXT,
    away_team   TEXT,
    home_goals  INTEGER,
    away_goals  INTEGER,
    season      INTEGER,
    matchday    TEXT
);

CREATE TABLE IF NOT EXISTS api_player_match_stats (
    id              SERIAL PRIMARY KEY,
    player_id       INTEGER REFERENCES api_players(id),
    match_id        INTEGER REFERENCES api_matches(id),
    minutes         INTEGER,
    goals           INTEGER,
    assists         INTEGER,
    yellow_cards    INTEGER,
    red_cards       INTEGER,
    rating          FLOAT,
    position        TEXT,
    substitute      BOOLEAN
);
