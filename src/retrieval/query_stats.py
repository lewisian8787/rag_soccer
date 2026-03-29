import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DB_CONN = os.getenv("DATABASE_URL")


# -- Connect to the local database --
def get_conn():
    return psycopg2.connect(DB_CONN, cursor_factory=psycopg2.extras.RealDictCursor)

# --  THIS FILE LISTS ALL POSSIBLE SQL QUERIES THAT WOULD BE NEEDED --
# -- last updated march 29

def get_player_season_totals(player_name: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
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
                WHERE p.name ILIKE %s
                GROUP BY p.name
            """, (f"%{player_name}%",))
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
                WHERE m.home_team ILIKE %s
                  AND m.away_team ILIKE %s
                  AND (s.goals > 0 OR s.assists > 0)
                ORDER BY m.date DESC, s.goals DESC
                LIMIT 50
            """, (f"%{home_team}%", f"%{away_team}%"))
            return [dict(r) for r in cur.fetchall()]


def get_top_scorers(limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.name,
                    SUM(s.goals) AS goals,
                    SUM(s.assists) AS assists,
                    COUNT(*) AS appearances
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                GROUP BY p.name
                ORDER BY goals DESC
                LIMIT %s
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]


def get_top_assisters(limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.name,
                    SUM(s.assists) AS assists,
                    SUM(s.goals) AS goals,
                    COUNT(*) AS appearances
                FROM api_player_match_stats s
                JOIN api_players p ON p.id = s.player_id
                GROUP BY p.name
                ORDER BY assists DESC
                LIMIT %s
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]


def get_top_rated_players(position: str = None, since_date: str = None, limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            conditions = ["s.rating IS NOT NULL"]
            params = []

            if position:
                conditions.append("s.position ILIKE %s")
                params.append(f"%{position}%")
            if since_date:
                conditions.append("m.date >= %s")
                params.append(since_date)

            where = " AND ".join(conditions)
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
                HAVING COUNT(*) >= 3
                ORDER BY avg_rating DESC
                LIMIT %s
            """, params)
            return [dict(r) for r in cur.fetchall()]


def get_most_booked_players(card_type: str = "yellow", team_name: str = None, limit: int = 10) -> list[dict]:
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


def format_stats_context(data: list[dict] | dict | None, label: str) -> str:
    if not data:
        return f"[No {label} data found]"
    if isinstance(data, dict):
        data = [data]
    lines = [f"[{label}]"]
    for row in data:
        lines.append("  " + ", ".join(f"{k}: {v}" for k, v in row.items()))
    return "\n".join(lines)
