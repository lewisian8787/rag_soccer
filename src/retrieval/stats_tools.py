from query_stats import (
    get_player_season_totals,
    get_player_goal_history,
    get_team_recent_results,
    get_team_stats_by_venue,
    get_match_scorers,
    get_top_scorers,
    get_top_assisters,
    get_top_rated_players,
)

# --- Tool definitions ---
# Passed to gpt-4o-mini so it can select the right function and extract parameters.
# One definition per SQL function in query_stats.py.

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_player_season_totals",
            "description": "Get a player's total goals, assists, yellow cards, red cards, average rating and appearances for the season.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "The player's name e.g. 'Salah', 'Haaland', 'Saka'"
                    }
                },
                "required": ["player_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_goal_history",
            "description": "Get a match-by-match record of every game a player has scored in, ordered most recent first. Use this only for questions about when a player last scored or the dates of specific goals. Do NOT use this to count total goals — use get_player_season_totals for that.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "The player's name e.g. 'Salah', 'Haaland'"
                    }
                },
                "required": ["player_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_recent_results",
            "description": "Get a team's most recent match results including score, home team and away team.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "The team's name e.g. 'Arsenal', 'Liverpool', 'Fulham'"
                    },
                    "home_or_away": {
                        "type": "string",
                        "enum": ["home", "away"],
                        "description": "Filter to home or away games only. Omit for all games."
                    }
                },
                "required": ["team_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_stats_by_venue",
            "description": "Get a team's season record — wins, draws, losses, goals scored and conceded. Can be filtered to home or away games only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "The team's name e.g. 'Arsenal', 'Everton', 'Fulham'"
                    },
                    "home_or_away": {
                        "type": "string",
                        "enum": ["home", "away"],
                        "description": "Filter to home or away record only. Omit for overall season record."
                    }
                },
                "required": ["team_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_match_scorers",
            "description": "Get the players who scored or assisted in a specific match between two teams.",
            "parameters": {
                "type": "object",
                "properties": {
                    "home_team": {
                        "type": "string",
                        "description": "The home team's name e.g. 'Fulham'"
                    },
                    "away_team": {
                        "type": "string",
                        "description": "The away team's name e.g. 'Liverpool'"
                    }
                },
                "required": ["home_team", "away_team"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_scorers",
            "description": "Get the top goalscorers in the Premier League this season, ranked by total goals.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_assisters",
            "description": "Get the players with the most assists in the Premier League this season.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_rated_players",
            "description": "Get the highest rated players by average match rating. Can be filtered by position (e.g. 'Midfielder', 'Forward', 'Defender') and/or a start date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "position": {
                        "type": "string",
                        "description": "Filter by position e.g. 'Midfielder', 'Forward', 'Defender', 'Goalkeeper'"
                    },
                    "since_date": {
                        "type": "string",
                        "description": "Only include matches from this date onwards. Format: YYYY-MM-DD e.g. '2025-12-01'"
                    }
                },
                "required": []
            }
        }
    },
]

# --- Dispatcher ---
# Maps function name returned by the LLM to the actual Python function.

FUNCTION_MAP = {
    "get_player_season_totals": get_player_season_totals,
    "get_player_goal_history": get_player_goal_history,
    "get_team_recent_results": get_team_recent_results,
    "get_team_stats_by_venue": get_team_stats_by_venue,
    "get_match_scorers": get_match_scorers,
    "get_top_scorers": get_top_scorers,
    "get_top_assisters": get_top_assisters,
    "get_top_rated_players": get_top_rated_players,
}
