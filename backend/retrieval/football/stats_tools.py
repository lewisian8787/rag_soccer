from football.query_stats import (
    get_player_team,
    get_player_season_totals,
    get_player_goal_history,
    get_recent_player_form,
    get_team_recent_results,
    get_team_stats_by_venue,
    get_team_defensive_stats,
    get_team_attacking_stats,
    get_team_top_scorers,
    get_league_defensive_ranking,
    get_league_attacking_ranking,
    get_match_scorers,
    get_top_scorers,
    get_top_assisters,
    get_top_rated_players,
    get_most_booked_players,
)

# --- Tool definitions ---
# Passed to gpt-4o-mini so it can select the right function and extract parameters.
# One definition per SQL function in query_stats.py.

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_player_team",
            "description": "Get the team a player currently plays for, based on their most recent match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "The player's name e.g. 'Igor Thiago', 'Semenyo', 'Haaland'"
                    }
                },
                "required": ["player_name"]
            }
        }
    },
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
            "name": "get_team_top_scorers",
            "description": "Get the top goalscorers for a specific team this season, ranked by goals. Use this when the question asks who has scored the most for a particular team — e.g. 'who is Leeds top scorer?' or 'who has been scoring for Everton?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "The team's name e.g. 'Leeds', 'Everton', 'Wolves'"
                    },
                    "since_date": {
                        "type": "string",
                        "description": "Only include matches from this date onwards. Format: YYYY-MM-DD"
                    }
                },
                "required": ["team_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_scorers",
            "description": "Get the top goalscorers in the Premier League this season, ranked by total goals. Use for questions about top scorers league-wide, in-form strikers, or who has been scoring recently. Use since_date to filter to recent form (e.g. last 30 days).",
            "parameters": {
                "type": "object",
                "properties": {
                    "since_date": {
                        "type": "string",
                        "description": "Only include matches from this date onwards. Format: YYYY-MM-DD e.g. '2026-02-28'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_assisters",
            "description": "Get the players with the most assists in the Premier League this season. Use since_date to filter to recent form.",
            "parameters": {
                "type": "object",
                "properties": {
                    "since_date": {
                        "type": "string",
                        "description": "Only include matches from this date onwards. Format: YYYY-MM-DD e.g. '2026-02-28'"
                    }
                },
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
    {
        "type": "function",
        "function": {
            "name": "get_recent_player_form",
            "description": "Get a player's goals, assists, average rating and appearances over a specific recent window. Use this for questions about a player's recent form, how they've been playing lately, or their stats over the last N weeks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "The player's name e.g. 'Salah', 'Haaland'"
                    },
                    "since_date": {
                        "type": "string",
                        "description": "Start of the form window. Format: YYYY-MM-DD e.g. '2026-02-28'"
                    }
                },
                "required": ["player_name", "since_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_defensive_stats",
            "description": "Get a team's goals conceded, clean sheets and average goals conceded per game. Use for questions about defensive record, best defences, or how solid a team has been at the back. Accepts an optional since_date to restrict to recent games.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "The team's name e.g. 'Arsenal', 'Chelsea'"
                    },
                    "since_date": {
                        "type": "string",
                        "description": "Only include matches from this date onwards. Format: YYYY-MM-DD"
                    }
                },
                "required": ["team_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_attacking_stats",
            "description": "Get a team's goals scored and average goals scored per game. Use for questions about attacking output, most clinical teams, or how free-scoring a team has been. Accepts an optional since_date to restrict to recent games.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "The team's name e.g. 'Arsenal', 'Liverpool'"
                    },
                    "since_date": {
                        "type": "string",
                        "description": "Only include matches from this date onwards. Format: YYYY-MM-DD"
                    }
                },
                "required": ["team_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_league_defensive_ranking",
            "description": "Rank all Premier League teams by goals conceded (fewest first). Use for questions about which teams have the best defence, fewest goals conceded, or most clean sheets across the league. Accepts an optional since_date for recent form.",
            "parameters": {
                "type": "object",
                "properties": {
                    "since_date": {
                        "type": "string",
                        "description": "Only include matches from this date onwards. Format: YYYY-MM-DD"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_league_attacking_ranking",
            "description": "Rank all Premier League teams by goals scored (most first). Use for questions about the most prolific teams, highest scoring sides, or best attacks across the league. Accepts an optional since_date for recent form.",
            "parameters": {
                "type": "object",
                "properties": {
                    "since_date": {
                        "type": "string",
                        "description": "Only include matches from this date onwards. Format: YYYY-MM-DD"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_most_booked_players",
            "description": "Get the players with the most yellow or red cards in the Premier League this season. Can be filtered to a specific team. Use for questions about disciplinary records, bookings, or suspensions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_type": {
                        "type": "string",
                        "enum": ["yellow", "red"],
                        "description": "Whether to rank by yellow cards or red cards. Defaults to yellow."
                    },
                    "team_name": {
                        "type": "string",
                        "description": "Filter to players from a specific team e.g. 'Leeds', 'Arsenal'. Omit for the whole league."
                    }
                },
                "required": []
            }
        }
    },
]

# --- Dispatcher ---
# Maps function name returned by the LLM to the actual Python function.

# FINAL TOOL MAP

FUNCTION_MAP = {
    "get_player_team": get_player_team,
    "get_player_season_totals": get_player_season_totals,
    "get_team_top_scorers": get_team_top_scorers,
    "get_player_goal_history": get_player_goal_history,
    "get_recent_player_form": get_recent_player_form,
    "get_team_recent_results": get_team_recent_results,
    "get_team_stats_by_venue": get_team_stats_by_venue,
    "get_team_defensive_stats": get_team_defensive_stats,
    "get_team_attacking_stats": get_team_attacking_stats,
    "get_league_defensive_ranking": get_league_defensive_ranking,
    "get_league_attacking_ranking": get_league_attacking_ranking,
    "get_match_scorers": get_match_scorers,
    "get_top_scorers": get_top_scorers,
    "get_top_assisters": get_top_assisters,
    "get_top_rated_players": get_top_rated_players,
    "get_most_booked_players": get_most_booked_players,
}
