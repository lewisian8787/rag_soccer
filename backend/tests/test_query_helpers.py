"""Unit tests for pure helper functions in query.py.

These tests require no mocking — they test pure functions with no external dependencies.
"""

import pytest
from datetime import datetime

# Import the functions and constants to test
from football.football_pipeline import build_context, _build_user_message, RECENCY_PATTERN


class TestBuildContext:
    """Tests for the build_context() function."""

    def test_formats_single_chunk(self):
        chunks = [
            {
                "score": 0.85,
                "metadata": {
                    "title": "Arsenal 2-1 Chelsea",
                    "published_at": int(datetime(2025, 10, 15).timestamp()),
                    "chunk_text": "Arsenal pressed high from the start.",
                }
            }
        ]
        result = build_context(chunks)

        assert "Arsenal 2-1 Chelsea" in result
        assert "2025-10-15" in result
        assert "Arsenal pressed high from the start." in result

    def test_formats_multiple_chunks_with_separator(self):
        chunks = [
            {
                "score": 0.85,
                "metadata": {
                    "title": "Match A",
                    "published_at": int(datetime(2025, 10, 15).timestamp()),
                    "chunk_text": "Text A",
                }
            },
            {
                "score": 0.78,
                "metadata": {
                    "title": "Match B",
                    "published_at": int(datetime(2025, 10, 12).timestamp()),
                    "chunk_text": "Text B",
                }
            },
        ]
        result = build_context(chunks)

        assert "Match A" in result
        assert "Match B" in result
        assert "---" in result  # Separator between chunks

    def test_empty_chunks_returns_empty_string(self):
        result = build_context([])
        assert result == ""

    def test_handles_missing_metadata_fields(self):
        chunks = [
            {
                "score": 0.85,
                "metadata": {
                    "title": "Some Match",
                    "published_at": 0,  # Unix epoch
                    "chunk_text": "",
                }
            }
        ]
        result = build_context(chunks)

        assert "Some Match" in result
        # Unix epoch renders as 1970-01-01 or 1969-12-31 depending on timezone
        assert "1970-01-01" in result or "1969-12-31" in result


class TestBuildUserMessage:
    """Tests for the _build_user_message() function."""

    def test_includes_question(self):
        result = _build_user_message("How does Arsenal press?", [], "", False)
        assert "Question: How does Arsenal press?" in result

    def test_includes_stats_context_when_provided(self):
        stats = "Goals: 10\nAssists: 5"
        result = _build_user_message("Query", [], stats, False)

        assert "STRUCTURED STATS:" in result
        assert "Goals: 10" in result

    def test_includes_rag_context_when_chunks_provided(self):
        chunks = [
            {
                "score": 0.85,
                "metadata": {
                    "title": "Arsenal vs Chelsea",
                    "published_at": int(datetime(2025, 10, 15).timestamp()),
                    "chunk_text": "Arsenal pressed high.",
                }
            }
        ]
        result = _build_user_message("Query", chunks, "", False)

        assert "MATCH REPORT EXCERPTS:" in result
        assert "Arsenal pressed high." in result

    def test_includes_both_contexts(self):
        chunks = [
            {
                "score": 0.85,
                "metadata": {
                    "title": "Match",
                    "published_at": int(datetime(2025, 10, 15).timestamp()),
                    "chunk_text": "Narrative text.",
                }
            }
        ]
        stats = "Player stats here"
        result = _build_user_message("Query", chunks, stats, False)

        assert "STRUCTURED STATS:" in result
        assert "MATCH REPORT EXCERPTS:" in result

    def test_includes_fallback_note_when_flag_set(self):
        result = _build_user_message("Query", [], "", used_fallback=True)

        assert "previous season" in result.lower()
        assert "2024/25" in result

    def test_no_fallback_note_when_flag_false(self):
        result = _build_user_message("Query", [], "", used_fallback=False)

        assert "previous season" not in result.lower()


class TestRecencyPattern:
    """Tests for the RECENCY_PATTERN regex."""

    @pytest.mark.parametrize("query", [
        "How has Salah been playing recently?",
        "Is Saka in form?",
        "Who has been on fire lately?",
        "Which players are looking sharp right now?",
        "Has Haaland been clinical recently?",
        "Who is in good form at the moment?",
        "Is Palmer back to his best?",
        "Which strikers have hit the ground running?",
        "How are Arsenal playing currently?",
        "Who has been flying this season?",
    ])
    def test_matches_recency_language(self, query):
        assert RECENCY_PATTERN.search(query) is not None

    @pytest.mark.parametrize("query", [
        "How many goals has Salah scored?",
        "What was the score in Arsenal vs Chelsea?",
        "How does Liverpool defend set pieces?",
        "Who is the top scorer this season?",
        "What formation does Arsenal use?",
        "How many assists does Trent have?",
    ])
    def test_does_not_match_non_recency_queries(self, query):
        assert RECENCY_PATTERN.search(query) is None

    def test_case_insensitive(self):
        assert RECENCY_PATTERN.search("Is he IN FORM?") is not None
        assert RECENCY_PATTERN.search("RECENTLY played well") is not None
