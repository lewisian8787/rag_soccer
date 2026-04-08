import os
from contextlib import contextmanager
from datetime import datetime
import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

DB_CONN = os.getenv("DATABASE_URL")

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1, 10, DB_CONN, cursor_factory=psycopg2.extras.RealDictCursor
        )
    return _pool


# -- Borrow a connection from the pool, commit on exit, return it when done --
@contextmanager
def get_conn():
    conn = _get_pool().getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _get_pool().putconn(conn)

# --  THIS FILE LISTS ALL POSSIBLE SQL QUERIES THAT WOULD BE NEEDED --
# -- last updated march 29

def get_player_team(player_name: str) -> dict | None:
    """Get the team a player currently plays for, based on their most recent match."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.name, s.team
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                WHERE p.name ILIKE %s
                ORDER BY m.date DESC
                LIMIT 1
            """, (f"%{player_name}%",))
            row = cur.fetchone()
            return dict(row) if row else None


def get_player_season_totals(player_name: str, since_date: str = None) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            conditions = ["p.name ILIKE %s"]
            params = [f"%{player_name}%"]
            if since_date:
                conditions.append("m.date >= %s")
                params.append(since_date)
            where = " AND ".join(conditions)
            cur.execute(f"""
                SELECT
                    p.name,
                    COUNT(*) AS appearances,
                    SUM(s.goals) AS goals,
                    SUM(s.assists) AS assists,
                    SUM(s.yellow_cards) AS yellow_cards,
                    SUM(s.red_cards) AS red_cards,
                    ROUND(AVG(s.rating)::numeric, 2) AS avg_rating
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                WHERE {where}
                GROUP BY p.name
            """, params)
            row = cur.fetchone()
            return dict(row) if row else None


def get_player_goal_history(player_name: str, limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.name,
                    m.date::date AS match_date,
                    m.home_team,
                    m.away_team,
                    s.goals,
                    s.assists,
                    s.minutes,
                    s.rating
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                WHERE p.name ILIKE %s
                  AND s.goals > 0
                ORDER BY m.date DESC
                LIMIT %s
            """, (f"%{player_name}%", limit))
            return [dict(r) for r in cur.fetchall()]


def get_team_recent_results(team_name: str, home_or_away: str = None, limit: int = 5) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            if home_or_away == "home":
                cur.execute("""
                    SELECT date::date AS match_date, home_team, away_team, home_goals, away_goals
                    FROM api_matches
                    WHERE home_team ILIKE %s
                    ORDER BY date DESC
                    LIMIT %s
                """, (f"%{team_name}%", limit))
            elif home_or_away == "away":
                cur.execute("""
                    SELECT date::date AS match_date, home_team, away_team, home_goals, away_goals
                    FROM api_matches
                    WHERE away_team ILIKE %s
                    ORDER BY date DESC
                    LIMIT %s
                """, (f"%{team_name}%", limit))
            else:
                cur.execute("""
                    SELECT date::date AS match_date, home_team, away_team, home_goals, away_goals
                    FROM api_matches
                    WHERE home_team ILIKE %s OR away_team ILIKE %s
                    ORDER BY date DESC
                    LIMIT %s
                """, (f"%{team_name}%", f"%{team_name}%", limit))
            return [dict(r) for r in cur.fetchall()]


def get_team_stats_by_venue(team_name: str, home_or_away: str = None) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            if home_or_away == "home":
                cur.execute("""
                    SELECT
                        COUNT(*) AS played,
                        SUM(CASE WHEN home_goals > away_goals THEN 1 ELSE 0 END) AS wins,
                        SUM(CASE WHEN home_goals = away_goals THEN 1 ELSE 0 END) AS draws,
                        SUM(CASE WHEN home_goals < away_goals THEN 1 ELSE 0 END) AS losses,
                        SUM(home_goals) AS goals_scored,
                        SUM(away_goals) AS goals_conceded,
                        ROUND(AVG(away_goals)::numeric, 2) AS avg_conceded
                    FROM api_matches
                    WHERE home_team ILIKE %s
                """, (f"%{team_name}%",))
            elif home_or_away == "away":
                cur.execute("""
                    SELECT
                        COUNT(*) AS played,
                        SUM(CASE WHEN away_goals > home_goals THEN 1 ELSE 0 END) AS wins,
                        SUM(CASE WHEN away_goals = home_goals THEN 1 ELSE 0 END) AS draws,
                        SUM(CASE WHEN away_goals < home_goals THEN 1 ELSE 0 END) AS losses,
                        SUM(away_goals) AS goals_scored,
                        SUM(home_goals) AS goals_conceded,
                        ROUND(AVG(home_goals)::numeric, 2) AS avg_conceded
                    FROM api_matches
                    WHERE away_team ILIKE %s
                """, (f"%{team_name}%",))
            else:
                cur.execute("""
                    SELECT
                        COUNT(*) AS played,
                        SUM(CASE
                            WHEN home_team ILIKE %s AND home_goals > away_goals THEN 1
                            WHEN away_team ILIKE %s AND away_goals > home_goals THEN 1
                            ELSE 0 END) AS wins,
                        SUM(CASE WHEN home_goals = away_goals THEN 1 ELSE 0 END) AS draws,
                        SUM(CASE
                            WHEN home_team ILIKE %s AND home_goals < away_goals THEN 1
                            WHEN away_team ILIKE %s AND away_goals < home_goals THEN 1
                            ELSE 0 END) AS losses,
                        SUM(CASE WHEN home_team ILIKE %s THEN home_goals ELSE away_goals END) AS goals_scored,
                        SUM(CASE WHEN home_team ILIKE %s THEN away_goals ELSE home_goals END) AS goals_conceded
                    FROM api_matches
                    WHERE home_team ILIKE %s OR away_team ILIKE %s
                """, (f"%{team_name}%",) * 8)
            row = cur.fetchone()
            return dict(row) if row else None


def get_match_scorers(home_team: str, away_team: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.name,
                    s.team,
                    s.goals,
                    s.assists,
                    m.home_team,
                    m.away_team,
                    m.home_goals,
                    m.away_goals,
                    m.date::date AS match_date
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                WHERE (
                    (m.home_team ILIKE %s AND m.away_team ILIKE %s)
                    OR (m.home_team ILIKE %s AND m.away_team ILIKE %s)
                )
                  AND (s.goals > 0 OR s.assists > 0)
                ORDER BY m.date DESC, s.goals DESC
                LIMIT 50
            """, (f"%{home_team}%", f"%{away_team}%", f"%{away_team}%", f"%{home_team}%"))
            return [dict(r) for r in cur.fetchall()]


def get_team_top_scorers(team_name: str, limit: int = 10, since_date: str = None) -> list[dict]:
    """Top scorers for a specific team, ranked by goals."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            conditions = ["(m.home_team ILIKE %s OR m.away_team ILIKE %s)"]
            params = [f"%{team_name}%", f"%{team_name}%"]
            if since_date:
                conditions.append("m.date >= %s")
                params.append(since_date)
            where = " AND ".join(conditions)
            params.append(limit)
            cur.execute(f"""
                SELECT
                    p.name,
                    SUM(s.goals) AS goals,
                    SUM(s.assists) AS assists,
                    COUNT(*) AS appearances
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                WHERE {where}
                GROUP BY p.name
                HAVING SUM(s.goals) > 0
                ORDER BY goals DESC
                LIMIT %s
            """, params)
            return [dict(r) for r in cur.fetchall()]


def get_top_scorers(limit: int = 50, since_date: str = None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            conditions = []
            params = []
            if since_date:
                conditions.append("m.date >= %s")
                params.append(since_date)
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(limit)
            cur.execute(f"""
                SELECT
                    p.name,
                    SUM(s.goals) AS goals,
                    SUM(s.assists) AS assists,
                    COUNT(*) AS appearances
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                {where}
                GROUP BY p.name
                ORDER BY goals DESC
                LIMIT %s
            """, params)
            return [dict(r) for r in cur.fetchall()]


def get_top_assisters(limit: int = 50, since_date: str = None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            conditions = []
            params = []
            if since_date:
                conditions.append("m.date >= %s")
                params.append(since_date)
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(limit)
            cur.execute(f"""
                SELECT
                    p.name,
                    SUM(s.assists) AS assists,
                    SUM(s.goals) AS goals,
                    COUNT(*) AS appearances
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                {where}
                GROUP BY p.name
                ORDER BY assists DESC
                LIMIT %s
            """, params)
            return [dict(r) for r in cur.fetchall()]


POSITION_MAP = {
    "goalkeeper": "G",
    "goalie": "G",
    "keeper": "G",
    "defender": "D",
    "defenders": "D",
    "midfielder": "M",
    "midfielders": "M",
    "mid": "M",
    "forward": "F",
    "forwards": "F",
    "striker": "F",
    "strikers": "F",
    "attacker": "F",
    "attackers": "F",
    "winger": "F",
    "wingers": "F",
}


def get_top_rated_players(position: str = None, since_date: str = None, limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            conditions = ["s.rating IS NOT NULL"]
            params = []

            if position:
                mapped = POSITION_MAP.get(position.lower(), position)
                conditions.append("s.position = %s")
                params.append(mapped)
            if since_date:
                conditions.append("m.date >= %s")
                params.append(since_date)

            where = " AND ".join(conditions)
            if since_date:
                days = (datetime.now() - datetime.strptime(since_date, "%Y-%m-%d")).days
                if days <= 35:
                    min_appearances = 1
                elif days <= 70:
                    min_appearances = 4
                else:
                    min_appearances = 10
            else:
                min_appearances = 10
            params.append(min_appearances)
            params.append(limit)

            cur.execute(f"""
                SELECT
                    p.name,
                    s.position,
                    ROUND(AVG(s.rating)::numeric, 2) AS avg_rating,
                    COUNT(*) AS appearances,
                    SUM(s.goals) AS goals,
                    SUM(s.assists) AS assists
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                WHERE {where}
                GROUP BY p.name, s.position
                HAVING COUNT(*) >= %s
                ORDER BY avg_rating DESC
                LIMIT %s
            """, params)
            return [dict(r) for r in cur.fetchall()]


def get_most_booked_players(card_type: str = "yellow", team_name: str = None, limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            order_col = "red_cards" if card_type == "red" else "yellow_cards"

            conditions = []
            params = []

            if team_name:
                conditions.append("(m.home_team ILIKE %s OR m.away_team ILIKE %s)")
                params.extend([f"%{team_name}%", f"%{team_name}%"])

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(limit)

            cur.execute(f"""
                SELECT
                    p.name,
                    SUM(s.yellow_cards) AS yellow_cards,
                    SUM(s.red_cards) AS red_cards,
                    COUNT(*) AS appearances
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                {where}
                GROUP BY p.name
                HAVING SUM(s.{order_col}) > 0
                ORDER BY SUM(s.{order_col}) DESC
                LIMIT %s
            """, params)
            return [dict(r) for r in cur.fetchall()]


def get_recent_player_form(player_name: str, since_date: str) -> dict | None:
    """Goals, assists, average rating and appearances for a player over a recent window."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.name,
                    COUNT(*) AS appearances,
                    SUM(s.goals) AS goals,
                    SUM(s.assists) AS assists,
                    ROUND(AVG(s.rating)::numeric, 2) AS avg_rating
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                JOIN api_matches m ON m.id = s.match_id
                WHERE p.name ILIKE %s
                  AND m.date >= %s
                GROUP BY p.name
            """, (f"%{player_name}%", since_date))
            row = cur.fetchone()
            return dict(row) if row else None


def get_team_defensive_stats(team_name: str, since_date: str = None) -> dict | None:
    """Goals conceded, clean sheets and average goals conceded per game for a team."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            conditions = ["(home_team ILIKE %s OR away_team ILIKE %s)"]
            params = [f"%{team_name}%", f"%{team_name}%"]
            if since_date:
                conditions.append("date >= %s")
                params.append(since_date)
            where = " AND ".join(conditions)
            cur.execute(f"""
                SELECT
                    COUNT(*) AS played,
                    SUM(CASE WHEN home_team ILIKE %s THEN away_goals ELSE home_goals END) AS goals_conceded,
                    SUM(CASE
                        WHEN home_team ILIKE %s AND away_goals = 0 THEN 1
                        WHEN away_team ILIKE %s AND home_goals = 0 THEN 1
                        ELSE 0 END) AS clean_sheets,
                    ROUND(AVG(CASE WHEN home_team ILIKE %s THEN away_goals ELSE home_goals END)::numeric, 2) AS avg_conceded_per_game
                FROM api_matches
                WHERE {where}
            """, [f"%{team_name}%"] * 4 + params)
            row = cur.fetchone()
            return dict(row) if row else None


def get_team_attacking_stats(team_name: str, since_date: str = None) -> dict | None:
    """Goals scored and average goals scored per game for a team."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            conditions = ["(home_team ILIKE %s OR away_team ILIKE %s)"]
            params = [f"%{team_name}%", f"%{team_name}%"]
            if since_date:
                conditions.append("date >= %s")
                params.append(since_date)
            where = " AND ".join(conditions)
            cur.execute(f"""
                SELECT
                    COUNT(*) AS played,
                    SUM(CASE WHEN home_team ILIKE %s THEN home_goals ELSE away_goals END) AS goals_scored,
                    ROUND(AVG(CASE WHEN home_team ILIKE %s THEN home_goals ELSE away_goals END)::numeric, 2) AS avg_scored_per_game
                FROM api_matches
                WHERE {where}
            """, [f"%{team_name}%"] * 2 + params)
            row = cur.fetchone()
            return dict(row) if row else None


def get_league_defensive_ranking(since_date: str = None, limit: int = 20) -> list[dict]:
    """All teams ranked by goals conceded — lowest first. Used for 'best defences' questions."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            date_filter = "AND date >= %s" if since_date else ""
            date_params = [since_date] if since_date else []
            cur.execute(f"""
                SELECT
                    team,
                    COUNT(*) AS played,
                    SUM(goals_conceded) AS goals_conceded,
                    SUM(CASE WHEN goals_conceded = 0 THEN 1 ELSE 0 END) AS clean_sheets,
                    ROUND(AVG(goals_conceded)::numeric, 2) AS avg_conceded
                FROM (
                    SELECT home_team AS team, away_goals AS goals_conceded, date
                    FROM api_matches
                    WHERE TRUE {date_filter}
                    UNION ALL
                    SELECT away_team AS team, home_goals AS goals_conceded, date
                    FROM api_matches
                    WHERE TRUE {date_filter}
                ) sub
                GROUP BY team
                ORDER BY goals_conceded ASC, clean_sheets DESC
                LIMIT %s
            """, date_params * 2 + [limit])
            return [dict(r) for r in cur.fetchall()]


def get_league_attacking_ranking(since_date: str = None, limit: int = 20) -> list[dict]:
    """All teams ranked by goals scored — highest first. Used for 'most clinical teams' questions."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            date_filter = "AND date >= %s" if since_date else ""
            date_params = [since_date] if since_date else []
            cur.execute(f"""
                SELECT
                    team,
                    COUNT(*) AS played,
                    SUM(goals_scored) AS goals_scored,
                    ROUND(AVG(goals_scored)::numeric, 2) AS avg_scored
                FROM (
                    SELECT home_team AS team, home_goals AS goals_scored, date
                    FROM api_matches
                    WHERE TRUE {date_filter}
                    UNION ALL
                    SELECT away_team AS team, away_goals AS goals_scored, date
                    FROM api_matches
                    WHERE TRUE {date_filter}
                ) sub
                GROUP BY team
                ORDER BY goals_scored DESC
                LIMIT %s
            """, date_params * 2 + [limit])
            return [dict(r) for r in cur.fetchall()]


def get_standings() -> list[dict]:
    """Full EPL league table computed from stored match results."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    team,
                    COUNT(*) AS played,
                    SUM(CASE WHEN goals_for > goals_against THEN 1 ELSE 0 END) AS won,
                    SUM(CASE WHEN goals_for = goals_against THEN 1 ELSE 0 END) AS drawn,
                    SUM(CASE WHEN goals_for < goals_against THEN 1 ELSE 0 END) AS lost,
                    SUM(goals_for) AS gf,
                    SUM(goals_against) AS ga,
                    SUM(goals_for - goals_against) AS gd,
                    SUM(CASE
                        WHEN goals_for > goals_against THEN 3
                        WHEN goals_for = goals_against THEN 1
                        ELSE 0 END) AS pts
                FROM (
                    SELECT home_team AS team, home_goals AS goals_for, away_goals AS goals_against
                    FROM api_matches
                    UNION ALL
                    SELECT away_team AS team, away_goals AS goals_for, home_goals AS goals_against
                    FROM api_matches
                ) sub
                GROUP BY team
                ORDER BY pts DESC, gd DESC, gf DESC
            """)
            return [dict(r) for r in cur.fetchall()]


def format_stats_context(data: list[dict] | dict | None, label: str) -> str:
    if not data:
        return f"[No {label} data found]"
    if isinstance(data, dict):
        data = [data]
    lines = [f"[{label}]"]
    for row in data:
        lines.append("  " + ", ".join(f"{k}: {v}" for k, v in row.items()))
    return "\n".join(lines)
