"""Shared pytest fixtures for backend tests."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


# --- OpenAI Mock Fixtures ---

@pytest.fixture
def mock_openai_client():
    """Mock the OpenAI client for all API calls."""
    with patch("football.query.openai_client") as mock:
        yield mock


@pytest.fixture
def mock_classifier_response():
    """Factory for creating mock classifier responses."""
    def _make_response(types: list[str]):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({"types": types})
        return mock_response
    return _make_response


@pytest.fixture
def mock_rewrite_response():
    """Factory for creating mock query rewrite responses."""
    def _make_response(rewritten_query: str):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = rewritten_query
        return mock_response
    return _make_response


@pytest.fixture
def mock_embedding_response():
    """Mock embedding response with a dummy 1536-dim vector."""
    mock_response = Mock()
    mock_response.data = [Mock()]
    mock_response.data[0].embedding = [0.1] * 1536
    return mock_response


@pytest.fixture
def mock_tool_call_response():
    """Factory for creating mock tool call responses."""
    def _make_response(function_name: str, arguments: dict):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.tool_calls = [Mock()]
        mock_response.choices[0].message.tool_calls[0].function.name = function_name
        mock_response.choices[0].message.tool_calls[0].function.arguments = json.dumps(arguments)
        return mock_response
    return _make_response


@pytest.fixture
def mock_stream_response():
    """Factory for creating mock streaming responses."""
    def _make_response(answer: str, confidence: str = "high", sources: list = None, caveat: str = None):
        sources = sources or []
        meta = json.dumps({
            "confidence": confidence,
            "sources": sources,
            "caveat": caveat,
        })
        full_text = f"{answer}\n<<<META>>>\n{meta}"

        # Simulate streaming chunks
        chunks = []
        for char in full_text:
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta.content = char
            chunks.append(chunk)
        return chunks
    return _make_response


# --- Pinecone Mock Fixtures ---

@pytest.fixture
def mock_pinecone_index():
    """Mock the Pinecone index for vector queries."""
    with patch("football.query.index") as mock:
        yield mock


@pytest.fixture
def sample_pinecone_matches():
    """Sample Pinecone query results for testing."""
    return {
        "matches": [
            {
                "id": "chunk-1",
                "score": 0.85,
                "metadata": {
                    "title": "Arsenal 2-1 Chelsea | Premier League",
                    "published_at": int(datetime(2025, 10, 15).timestamp()),
                    "chunk_text": "Arsenal pressed high from the start, with Saka causing problems down the right.",
                    "gender": "men",
                }
            },
            {
                "id": "chunk-2",
                "score": 0.78,
                "metadata": {
                    "title": "Liverpool 3-0 Manchester United | Premier League",
                    "published_at": int(datetime(2025, 10, 12).timestamp()),
                    "chunk_text": "Salah was clinical, converting both chances that fell his way.",
                    "gender": "men",
                }
            },
            {
                "id": "chunk-3",
                "score": 0.42,  # Below MIN_SCORE threshold
                "metadata": {
                    "title": "Everton 1-1 West Ham | Premier League",
                    "published_at": int(datetime(2025, 10, 10).timestamp()),
                    "chunk_text": "A dull affair with few chances created.",
                    "gender": "men",
                }
            },
        ]
    }


@pytest.fixture
def sample_chunks():
    """Pre-filtered chunks (above MIN_SCORE) for context building tests."""
    return [
        {
            "score": 0.85,
            "metadata": {
                "title": "Arsenal 2-1 Chelsea | Premier League",
                "published_at": int(datetime(2025, 10, 15).timestamp()),
                "chunk_text": "Arsenal pressed high from the start, with Saka causing problems down the right.",
            }
        },
        {
            "score": 0.78,
            "metadata": {
                "title": "Liverpool 3-0 Manchester United | Premier League",
                "published_at": int(datetime(2025, 10, 12).timestamp()),
                "chunk_text": "Salah was clinical, converting both chances that fell his way.",
            }
        },
    ]


# --- Stats Mock Fixtures ---

@pytest.fixture
def sample_stats_context():
    """Sample formatted stats context string."""
    return """Player Season Totals for Mohamed Salah:
- Goals: 12
- Assists: 8
- Appearances: 15
- Average Rating: 7.8"""


@pytest.fixture
def mock_stats_functions():
    """Mock the stats query functions."""
    with patch("football.query.FUNCTION_MAP") as mock:
        mock.get.return_value = Mock(return_value=[
            {"player_name": "Mohamed Salah", "goals": 12, "assists": 8}
        ])
        yield mock
