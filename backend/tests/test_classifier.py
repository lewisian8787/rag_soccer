"""Tests for query classification.

The classifier routes queries to RAG, stats, or both pipelines.
"""

import json
import pytest
from unittest.mock import patch, Mock

from football.football_pipeline import classify_query


# --- Test Data ---
# Organized by expected classification

RAG_ONLY_QUERIES = [
    # Pure tactical questions
    "How do Arsenal press high?",
    "How does Guardiola set up against a low block?",
    "How do Liverpool defend set pieces?",
    "What formation does Arsenal use when they don't have the ball?",
    "How do Manchester City build out from the back?",
    "How does Chelsea use their fullbacks in attack?",
    "What is Liverpool's pressing trigger?",
    "How do Tottenham transition from defence to attack?",
    "How does Arsenal's back four hold their shape without the ball?",
    "What role does Rodri play in City's build-up?",
    "How do Manchester United defend against teams that play out wide?",
    "How does Newcastle set up to defend crosses?",
    "What is Aston Villa's structure in midfield?",
    "How do Brighton play out of a press?",
    "How does Spurs use the half-spaces in attack?",
    "What does Arsenal do differently at home vs away?",
    "How does Liverpool's midfield press coordinated with the forwards?",
    "How do Chelsea defend corners?",
    "What is Fulham's defensive shape?",
    "How do Brentford use long balls to bypass the press?",
]

STATS_ONLY_QUERIES = [
    # Pure stat lookups
    "How many goals has Salah scored?",
    "Who has the most assists this season?",
    "What was the score in Arsenal vs Chelsea?",
    "How many yellow cards has Bruno Fernandes received?",
    "Who has played the most minutes in the Premier League this season?",
    "Who are the top five scorers in the league?",
    "How many goals has Haaland scored at home?",
    "What was the result of Liverpool's last away game?",
    "How many red cards have been issued this season?",
    "Who has the highest average rating this season?",
    "How many assists does Trent Alexander-Arnold have?",
    "What is Arsenal's home record this season?",
    "Who has scored the most headed goals?",
    "How many goals has Chelsea conceded this season?",
    "Did Salah score in the last derby?",
    "Who has the most clean sheets this season?",
    "How many goals has Son scored against Arsenal?",
    "What is Manchester City's points total?",
    "Who scored first in Arsenal vs Spurs?",
    "How many hat tricks have there been this season?",
]

BOTH_QUERIES = [
    # Player form
    "How has Salah been playing this season?",
    "Is Bukayo Saka in good form right now?",
    "How has Haaland been performing recently?",
    "Has Bruno Fernandes been consistent this season?",
    "How is Trent Alexander-Arnold performing this season?",
    "Has Martinelli been effective this season?",
    "How has De Bruyne looked since returning from injury?",
    "Is Son Heung-min playing well this season?",
    "How has Virgil van Dijk been at the back recently?",
    "Has Palmer been as good as last season?",
    "How is Rashford performing under the new manager?",
    "Is Isak living up to expectations this season?",
    "How has Watkins been since his injury return?",
    "Has Salah looked as sharp as previous seasons?",
    "Is Diogo Jota playing well when selected?",
    # Fantasy
    "Is Saka worth picking for fantasy this week?",
    "Should I start Haaland or Watkins this gameweek?",
    "Which defenders are good fantasy picks right now?",
    "Who is the best value striker in fantasy football?",
    "Which goalkeeper should I pick for the next two gameweeks?",
    "Is Palmer a good captain choice this week?",
    "Which Arsenal players are worth owning in fantasy?",
    "Who should I transfer in for the next gameweek?",
    "Which midfielders have the best upcoming fixtures?",
    "Is Son a reliable fantasy asset this season?",
    # Subjective quality
    "Who has been clinical in front of goal?",
    "Which midfielders have been contributing recently?",
    "Who has been the most creative player in the league?",
    "Which defenders have been the most commanding this season?",
    "Who has been the best player at Arsenal this season?",
    "Which striker has looked the most dangerous recently?",
    "Who has been the standout performer at Liverpool?",
    "Which forwards have been threatening but unlucky in front of goal?",
    "Who has been the most consistent fullback in the league?",
    "Which players have improved the most this season?",
    # Mixed / edge cases
    "Why has Haaland scored so many goals this season?",
    "Is Arsenal's attack as effective without Saka?",
    "How has Liverpool coped since Salah's injury?",
    "Which team has the best attack in the league right now?",
    "Why are Chelsea struggling to score this season?",
    "Has Spurs improved defensively under their new manager?",
    "How does Arsenal's goal threat compare to last season?",
    "Who is the best penalty taker in the league?",
    "Which team creates the most chances from open play?",
    "Is Manchester City as dominant as they were under peak Guardiola?",
    "How does Liverpool's press affect their opponents' passing?",
    "Which players tend to perform well in big matches?",
    "Has Arsenal's defensive record improved since the new season?",
    "Who is the most important player for Man City right now?",
    "Which teams struggle the most away from home?",
]


# --- Mocked Unit Tests ---
# These tests mock the OpenAI API to verify the classify_query function
# processes responses correctly. They run fast and don't cost API credits.

class TestClassifyQueryMocked:
    """Unit tests with mocked OpenAI responses."""

    @pytest.fixture
    def mock_openai(self):
        with patch("football.football_pipeline.openai_client") as mock:
            yield mock

    def _setup_mock_response(self, mock_openai, types: list[str]):
        """Configure mock to return specified types."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({"types": types})
        mock_openai.chat.completions.create.return_value = mock_response

    def test_returns_set_of_types(self, mock_openai):
        self._setup_mock_response(mock_openai, ["rag", "stats"])
        result = classify_query("test query")
        assert isinstance(result, set)
        assert result == {"rag", "stats"}

    def test_rag_only_response(self, mock_openai):
        self._setup_mock_response(mock_openai, ["rag"])
        result = classify_query("How does Arsenal press?")
        assert result == {"rag"}

    def test_stats_only_response(self, mock_openai):
        self._setup_mock_response(mock_openai, ["stats"])
        result = classify_query("How many goals has Salah scored?")
        assert result == {"stats"}

    def test_both_response(self, mock_openai):
        self._setup_mock_response(mock_openai, ["rag", "stats"])
        result = classify_query("How has Salah been playing?")
        assert result == {"rag", "stats"}

    def test_empty_types_defaults_to_rag(self, mock_openai):
        self._setup_mock_response(mock_openai, [])
        result = classify_query("some query")
        assert result == set()  # Empty set from empty list

    def test_calls_openai_with_correct_model(self, mock_openai):
        self._setup_mock_response(mock_openai, ["rag"])
        classify_query("test")
        call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"

    def test_uses_structured_output_schema(self, mock_openai):
        self._setup_mock_response(mock_openai, ["rag"])
        classify_query("test")
        call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"]["type"] == "json_schema"
        assert call_kwargs["response_format"]["json_schema"]["strict"] is True
        assert call_kwargs["response_format"]["json_schema"]["name"] == "query_classification"


# --- Live Integration Tests ---
# These tests call the real OpenAI API to verify classification accuracy.
# Run with: pytest -m live
# Skip with: pytest -m "not live"

@pytest.mark.live
class TestClassifyQueryLive:
    """Live integration tests against real OpenAI API."""

    @pytest.mark.parametrize("query", RAG_ONLY_QUERIES)
    def test_rag_only_queries(self, query):
        result = classify_query(query)
        assert result == {"rag"}, f"Expected {{'rag'}} for: {query}"

    @pytest.mark.parametrize("query", STATS_ONLY_QUERIES)
    def test_stats_only_queries(self, query):
        result = classify_query(query)
        assert result == {"stats"}, f"Expected {{'stats'}} for: {query}"

    @pytest.mark.parametrize("query", BOTH_QUERIES)
    def test_both_queries(self, query):
        result = classify_query(query)
        assert result == {"rag", "stats"}, f"Expected {{'rag', 'stats'}} for: {query}"
