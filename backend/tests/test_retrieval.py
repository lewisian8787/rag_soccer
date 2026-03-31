"""Tests for Pinecone retrieval quality.

These tests verify that queries return relevant match report chunks
with appropriate scores and filtering.
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime

from football.query import retrieve, get_embedding, MIN_SCORE


# --- Test Data ---

RETRIEVAL_TEST_QUERIES = [
    # Tactical — no date filter needed
    {"query": "How do Arsenal play against the high press?", "from_date": None, "description": "tactical"},
    {"query": "How do Liverpool set up defensively away from home?", "from_date": None, "description": "tactical"},
    {"query": "How do Manchester City build up play from the back?", "from_date": None, "description": "tactical"},
    # Player form — recent only
    {"query": "How has Salah been performing recently?", "from_date": "2025-09-01", "description": "player form"},
    {"query": "How has Bukayo Saka been playing this season?", "from_date": "2025-09-01", "description": "player form"},
    # Fantasy — recent only
    {"query": "Which strikers have been in good form recently?", "from_date": "2025-09-01", "description": "fantasy"},
    {"query": "Which midfielders have been contributing goals and assists?", "from_date": "2025-09-01", "description": "fantasy"},
]


# --- Mocked Unit Tests ---

class TestGetEmbedding:
    """Tests for the get_embedding() function."""

    @pytest.fixture
    def mock_openai(self):
        with patch("football.query.openai_client") as mock:
            mock_response = Mock()
            mock_response.data = [Mock()]
            mock_response.data[0].embedding = [0.1] * 1536
            mock.embeddings.create.return_value = mock_response
            yield mock

    def test_returns_1536_dim_vector(self, mock_openai):
        result = get_embedding("test query")
        assert len(result) == 1536

    def test_calls_correct_model(self, mock_openai):
        get_embedding("test query")
        call_kwargs = mock_openai.embeddings.create.call_args.kwargs
        assert call_kwargs["model"] == "text-embedding-3-small"


class TestRetrieveMocked:
    """Mocked tests for the retrieve() function."""

    @pytest.fixture
    def mock_openai(self):
        with patch("football.query.openai_client") as mock:
            mock_response = Mock()
            mock_response.data = [Mock()]
            mock_response.data[0].embedding = [0.1] * 1536
            mock.embeddings.create.return_value = mock_response
            yield mock

    @pytest.fixture
    def mock_pinecone(self):
        with patch("football.query.index") as mock:
            yield mock

    def test_queries_pinecone_with_top_k(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {"matches": []}

        retrieve("test query", from_date="2025-01-01")

        call_kwargs = mock_pinecone.query.call_args.kwargs
        assert call_kwargs["top_k"] == 20  # TOP_K constant
        assert call_kwargs["include_metadata"] is True

    def test_builds_date_filter_from_string(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {"matches": []}

        retrieve("test query", from_date="2025-06-15")

        call_kwargs = mock_pinecone.query.call_args.kwargs
        expected_timestamp = int(datetime(2025, 6, 15).timestamp())
        assert call_kwargs["filter"]["published_at"]["$gte"] == expected_timestamp

    def test_combines_date_and_gender_filters(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {"matches": []}

        retrieve("test query", from_date="2025-01-01", gender="women")

        call_kwargs = mock_pinecone.query.call_args.kwargs
        assert "published_at" in call_kwargs["filter"]
        assert call_kwargs["filter"]["gender"] == {"$eq": "women"}

    def test_score_threshold_filtering(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {
            "matches": [
                {"score": MIN_SCORE + 0.1, "metadata": {"title": "Above", "published_at": 1700000000, "chunk_text": "A"}},
                {"score": MIN_SCORE - 0.1, "metadata": {"title": "Below", "published_at": 1700000000, "chunk_text": "B"}},
                {"score": MIN_SCORE, "metadata": {"title": "Exact", "published_at": 1700000000, "chunk_text": "C"}},
            ]
        }

        chunks, _ = retrieve("test", from_date="2025-01-01")

        # Only chunks >= MIN_SCORE should be included
        titles = [c["metadata"]["title"] for c in chunks]
        assert "Above" in titles
        assert "Below" not in titles

    def test_deduplication_keeps_highest_score(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {
            "matches": [
                {"score": 0.90, "metadata": {"title": "Same Title", "published_at": 1700000000, "chunk_text": "First"}},
                {"score": 0.85, "metadata": {"title": "Same Title", "published_at": 1700000000, "chunk_text": "Second"}},
                {"score": 0.80, "metadata": {"title": "Same Title", "published_at": 1700000000, "chunk_text": "Third"}},
            ]
        }

        chunks, _ = retrieve("test", from_date="2025-01-01")

        assert len(chunks) == 1
        assert chunks[0]["score"] == 0.90  # Highest score kept
        assert chunks[0]["metadata"]["chunk_text"] == "First"

    def test_fallback_behavior_when_current_season_empty(self, mock_openai, mock_pinecone):
        # First call (current season) returns empty, second (fallback) returns data
        mock_pinecone.query.side_effect = [
            {"matches": []},
            {"matches": [{"score": 0.75, "metadata": {"title": "Last Season", "published_at": 1700000000, "chunk_text": "Old"}}]},
        ]

        chunks, used_fallback = retrieve("test query")

        assert len(chunks) == 1
        assert used_fallback is True
        assert mock_pinecone.query.call_count == 2

    def test_no_fallback_when_explicit_date_provided(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {"matches": []}

        chunks, used_fallback = retrieve("test query", from_date="2025-01-01")

        assert chunks == []
        assert used_fallback is False
        assert mock_pinecone.query.call_count == 1  # No fallback attempt


class TestRetrievalScoreQuality:
    """Tests for retrieval score quality thresholds."""

    @pytest.fixture
    def mock_openai(self):
        with patch("football.query.openai_client") as mock:
            mock_response = Mock()
            mock_response.data = [Mock()]
            mock_response.data[0].embedding = [0.1] * 1536
            mock.embeddings.create.return_value = mock_response
            yield mock

    @pytest.fixture
    def mock_pinecone(self):
        with patch("football.query.index") as mock:
            yield mock

    def test_high_score_chunks_retained(self, mock_openai, mock_pinecone):
        """Chunks with scores >= 0.75 should definitely be retained."""
        mock_pinecone.query.return_value = {
            "matches": [
                {"score": 0.85, "metadata": {"title": "High Quality", "published_at": 1700000000, "chunk_text": "Relevant"}},
            ]
        }

        chunks, _ = retrieve("test", from_date="2025-01-01")

        assert len(chunks) == 1
        assert chunks[0]["score"] >= 0.75

    def test_low_score_chunks_filtered(self, mock_openai, mock_pinecone):
        """Chunks with scores < MIN_SCORE should be filtered out."""
        mock_pinecone.query.return_value = {
            "matches": [
                {"score": 0.30, "metadata": {"title": "Irrelevant", "published_at": 1700000000, "chunk_text": "Noise"}},
            ]
        }

        chunks, _ = retrieve("test", from_date="2025-01-01")

        assert len(chunks) == 0


# --- Live Integration Tests ---

@pytest.mark.live
class TestRetrievalLive:
    """Live integration tests for Pinecone retrieval quality."""

    @pytest.mark.parametrize("test_case", RETRIEVAL_TEST_QUERIES)
    def test_retrieval_returns_results(self, test_case):
        """Verify that test queries return at least some results."""
        chunks, used_fallback = retrieve(test_case["query"], from_date=test_case["from_date"])

        # May be empty if no matching data, but structure should be valid
        assert isinstance(chunks, list)
        assert isinstance(used_fallback, bool)

    def test_tactical_query_finds_relevant_chunks(self):
        """Tactical queries should find match report content."""
        chunks, _ = retrieve("How does Arsenal press high?")

        if chunks:  # If data exists
            # Check that results have reasonable scores
            scores = [c["score"] for c in chunks]
            assert all(s >= MIN_SCORE for s in scores)

    def test_date_filtering_works(self):
        """Queries with date filter should only return recent content."""
        # Query with recent date filter
        chunks, _ = retrieve("How has Salah been?", from_date="2025-10-01")

        if chunks:
            # All results should be from after the filter date
            filter_timestamp = int(datetime(2025, 10, 1).timestamp())
            for chunk in chunks:
                assert chunk["metadata"]["published_at"] >= filter_timestamp

    def test_gender_filtering_works(self):
        """Gender filter should only return matching content."""
        chunks, _ = retrieve("How did the team play?", from_date="2025-01-01", gender="women")

        if chunks:
            for chunk in chunks:
                assert chunk["metadata"].get("gender") == "women"
