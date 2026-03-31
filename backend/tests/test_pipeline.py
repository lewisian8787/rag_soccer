"""Tests for the full query pipeline.

Tests the integration of classification, retrieval, stats fetching, and generation.
"""

import json
import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

from football.query import (
    ask,
    stream_ask,
    retrieve,
    fetch_stats_context,
    stream_generate,
    rewrite_query,
    MIN_SCORE,
)


# --- Test Data ---

PIPELINE_TEST_QUERIES = [
    # RAG only — tactical
    {"query": "How do Arsenal like to play?", "from_date": None, "gender": None},
    {"query": "How does Liverpool press?", "from_date": None, "gender": None},
    {"query": "How do Manchester City build out from the back?", "from_date": None, "gender": None},
    # Stats only
    {"query": "How many goals has Haaland scored this season?", "from_date": None, "gender": None},
    {"query": "Who are the top 5 assisters this season?", "from_date": None, "gender": None},
    {"query": "What was the score in the last Arsenal game?", "from_date": None, "gender": None},
    # Mixed — player form
    {"query": "How has Saka been playing this season?", "from_date": None, "gender": None},
    {"query": "How has Bruno Fernandes been performing?", "from_date": None, "gender": None},
    # Mixed — fantasy
    {"query": "Is Haaland worth picking for fantasy this week?", "from_date": None, "gender": None},
    {"query": "Which strikers have been in form recently?", "from_date": None, "gender": None},
    # Natural language — match recap
    {"query": "What happened in the last Arsenal game?", "from_date": None, "gender": None},
    {"query": "What happened in the last Liverpool game?", "from_date": None, "gender": None},
    {"query": "How did Chelsea get on at the weekend?", "from_date": None, "gender": None},
    {"query": "What was the result when Spurs played Man United?", "from_date": None, "gender": None},
]


# --- Mocked Unit Tests ---

class TestRewriteQuery:
    """Tests for query normalization."""

    @pytest.fixture
    def mock_openai(self):
        with patch("football.query.openai_client") as mock:
            yield mock

    def test_expands_abbreviations(self, mock_openai):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "How is Wolverhampton playing?"
        mock_openai.chat.completions.create.return_value = mock_response

        result = rewrite_query("How is Wolves playing?")
        assert result == "How is Wolverhampton playing?"

    def test_preserves_full_names(self, mock_openai):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "How is Arsenal playing?"
        mock_openai.chat.completions.create.return_value = mock_response

        result = rewrite_query("How is Arsenal playing?")
        assert result == "How is Arsenal playing?"


class TestRetrieve:
    """Tests for the retrieve() function."""

    @pytest.fixture
    def mock_openai(self):
        with patch("football.query.openai_client") as mock:
            # Mock embedding response
            mock_response = Mock()
            mock_response.data = [Mock()]
            mock_response.data[0].embedding = [0.1] * 1536
            mock.embeddings.create.return_value = mock_response
            yield mock

    @pytest.fixture
    def mock_pinecone(self):
        with patch("football.query.index") as mock:
            yield mock

    def test_filters_below_min_score(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {
            "matches": [
                {"score": 0.85, "metadata": {"title": "Match A", "published_at": 1700000000, "chunk_text": "A"}},
                {"score": 0.30, "metadata": {"title": "Match B", "published_at": 1700000000, "chunk_text": "B"}},
            ]
        }

        chunks, used_fallback = retrieve("test query", from_date="2025-01-01")

        assert len(chunks) == 1
        assert chunks[0]["metadata"]["title"] == "Match A"

    def test_deduplicates_by_title(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {
            "matches": [
                {"score": 0.85, "metadata": {"title": "Same Match", "published_at": 1700000000, "chunk_text": "Chunk 1"}},
                {"score": 0.80, "metadata": {"title": "Same Match", "published_at": 1700000000, "chunk_text": "Chunk 2"}},
                {"score": 0.75, "metadata": {"title": "Different Match", "published_at": 1700000000, "chunk_text": "Chunk 3"}},
            ]
        }

        chunks, _ = retrieve("test query", from_date="2025-01-01")

        titles = [c["metadata"]["title"] for c in chunks]
        assert titles == ["Same Match", "Different Match"]

    def test_fallback_to_previous_season(self, mock_openai, mock_pinecone):
        # First call returns empty (current season), second returns results (fallback)
        mock_pinecone.query.side_effect = [
            {"matches": []},  # Current season empty
            {"matches": [{"score": 0.85, "metadata": {"title": "Old Match", "published_at": 1700000000, "chunk_text": "Old"}}]},
        ]

        chunks, used_fallback = retrieve("test query")

        assert len(chunks) == 1
        assert used_fallback is True

    def test_no_fallback_when_current_season_has_data(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {
            "matches": [{"score": 0.85, "metadata": {"title": "Current Match", "published_at": 1700000000, "chunk_text": "Current"}}]
        }

        chunks, used_fallback = retrieve("test query")

        assert len(chunks) == 1
        assert used_fallback is False

    def test_applies_date_filter(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {"matches": []}

        retrieve("test query", from_date="2025-06-01")

        call_kwargs = mock_pinecone.query.call_args.kwargs
        assert "filter" in call_kwargs
        assert "published_at" in call_kwargs["filter"]

    def test_applies_gender_filter(self, mock_openai, mock_pinecone):
        mock_pinecone.query.return_value = {"matches": []}

        retrieve("test query", from_date="2025-01-01", gender="women")

        call_kwargs = mock_pinecone.query.call_args.kwargs
        assert call_kwargs["filter"]["gender"] == {"$eq": "women"}


class TestFetchStatsContext:
    """Tests for the fetch_stats_context() function."""

    @pytest.fixture
    def mock_openai(self):
        with patch("football.query.openai_client") as mock:
            yield mock

    @pytest.fixture
    def mock_function_map(self):
        with patch("football.query.FUNCTION_MAP") as mock:
            yield mock

    def test_returns_empty_when_no_tool_calls(self, mock_openai, mock_function_map):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.tool_calls = None
        mock_openai.chat.completions.create.return_value = mock_response

        result = fetch_stats_context("test query")

        assert result == ""

    def test_executes_selected_tool(self, mock_openai, mock_function_map):
        # Mock the tool call response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_tool_call = Mock()
        mock_tool_call.function.name = "get_player_season_totals"
        mock_tool_call.function.arguments = json.dumps({"player_name": "Salah"})
        mock_response.choices[0].message.tool_calls = [mock_tool_call]
        mock_openai.chat.completions.create.return_value = mock_response

        # Mock the function execution
        mock_fn = Mock(return_value=[{"player_name": "Salah", "goals": 10}])
        mock_function_map.get.return_value = mock_fn

        with patch("football.query.format_stats_context", return_value="Salah: 10 goals"):
            result = fetch_stats_context("How many goals has Salah scored?")

        mock_fn.assert_called_once_with(player_name="Salah")
        assert "Salah" in result or result != ""  # Either formatted or raw


class TestStreamGenerate:
    """Tests for the stream_generate() function."""

    @pytest.fixture
    def mock_openai(self):
        with patch("football.query.openai_client") as mock:
            yield mock

    def test_yields_no_data_message_when_empty_context(self, mock_openai):
        events = list(stream_generate("test", chunks=[], stats_context=""))

        # Should yield token + done events
        assert len(events) == 2
        assert "couldn't find enough" in events[0].lower()

    def test_yields_token_events(self, mock_openai):
        # Mock streaming response
        mock_chunks = []
        for char in "Answer text\n<<<META>>>\n{}":
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta.content = char
            mock_chunks.append(chunk)
        mock_openai.chat.completions.create.return_value = iter(mock_chunks)

        sample_chunks = [{"score": 0.8, "metadata": {"title": "M", "published_at": 1700000000, "chunk_text": "T"}}]
        events = list(stream_generate("test", chunks=sample_chunks))

        # Parse events
        token_events = [e for e in events if '"type": "token"' in e]
        done_events = [e for e in events if '"type": "done"' in e]

        assert len(token_events) > 0
        assert len(done_events) == 1

    def test_includes_query_types_in_done_event(self, mock_openai):
        mock_openai.chat.completions.create.return_value = iter([])

        sample_chunks = [{"score": 0.8, "metadata": {"title": "M", "published_at": 1700000000, "chunk_text": "T"}}]
        events = list(stream_generate("test", chunks=sample_chunks, query_types=["rag", "stats"]))

        done_event = [e for e in events if '"type": "done"' in e][0]
        data = json.loads(done_event.replace("data: ", "").strip())
        assert "rag" in data["query_types"]
        assert "stats" in data["query_types"]


class TestAsk:
    """Tests for the ask() function (non-streaming wrapper)."""

    @pytest.fixture
    def mock_stream_ask(self):
        with patch("football.query.stream_ask") as mock:
            yield mock

    def test_aggregates_stream_tokens(self, mock_stream_ask):
        mock_stream_ask.return_value = iter([
            'data: {"type": "token", "text": "Hello "}\n\n',
            'data: {"type": "token", "text": "world"}\n\n',
            'data: {"type": "done", "confidence": "high", "sources": [], "caveat": null}\n\n',
        ])

        result = ask("test query")

        assert result["answer"] == "Hello world"
        assert result["confidence"] == "high"

    def test_preserves_metadata(self, mock_stream_ask):
        mock_stream_ask.return_value = iter([
            'data: {"type": "token", "text": "Answer"}\n\n',
            'data: {"type": "done", "confidence": "medium", "sources": [{"title": "Match"}], "caveat": "Limited data", "query_types": ["rag"]}\n\n',
        ])

        result = ask("test query")

        assert result["confidence"] == "medium"
        assert result["sources"] == [{"title": "Match"}]
        assert result["caveat"] == "Limited data"
        assert result["query_types"] == ["rag"]


# --- Live Integration Tests ---

@pytest.mark.live
class TestPipelineLive:
    """Live integration tests for the full pipeline."""

    @pytest.mark.parametrize("test_case", PIPELINE_TEST_QUERIES)
    def test_pipeline_returns_valid_response(self, test_case):
        result = ask(
            test_case["query"],
            from_date=test_case["from_date"],
            gender=test_case["gender"],
        )

        # Basic structure checks
        assert "answer" in result
        assert "confidence" in result
        assert result["confidence"] in ["high", "medium", "low"]
        assert "sources" in result
        assert isinstance(result["sources"], list)

    def test_tactical_query_uses_rag(self):
        result = ask("How does Arsenal press high?")
        assert "rag" in result.get("query_types", [])

    def test_stats_query_uses_stats(self):
        result = ask("How many goals has Salah scored this season?")
        assert "stats" in result.get("query_types", [])

    def test_form_query_uses_both(self):
        result = ask("How has Salah been playing this season?")
        query_types = result.get("query_types", [])
        assert "rag" in query_types
        assert "stats" in query_types
