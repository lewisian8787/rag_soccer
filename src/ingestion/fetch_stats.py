import os
import time
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONN = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

PREMIER_LEAGUE_ID = 39
SEASON = 2025


def get(endpoint, params=None):
    response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


# --- Fetch all PL fixtures for the season ---

def fetch_fixtures():
    data = get("/fixtures", params={"league": PREMIER_LEAGUE_ID, "season": SEASON, "status": "FT"})
    return data["response"]


# --- Save match to api_matches ---

def save_match(cur, fixture):
    f = fixture["fixture"]
    teams = fixture["teams"]
    goals = fixture["goals"]
    league = fixture["league"]

    cur.execute("""
        INSERT INTO api_matches (id, date, home_team, away_team, home_goals, away_goals, season, matchday)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (
        f["id"],
        f["date"],
        teams["home"]["name"],
        teams["away"]["name"],
        goals["home"],
        goals["away"],
        league["season"],
        league["round"],
    ))


# --- Fetch and save player stats for a fixture ---

def save_player_stats(cur, fixture_id):
    data = get("/fixtures/players", params={"fixture": fixture_id})

    for team_data in data["response"]:
        for player_data in team_data["players"]:
            player = player_data["player"]
            stats = player_data["statistics"][0]
            games = stats["games"]
            goals = stats["goals"]
            cards = stats["cards"]

            # Skip players who didn't play
            if games["minutes"] is None:
                continue

            # Upsert player
            cur.execute("""
                INSERT INTO api_players (id, name, position)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                player["id"],
                player["name"],
                games["position"],
            ))

            # Insert player match stats
            cur.execute("""
                INSERT INTO api_player_match_stats
                    (player_id, match_id, minutes, goals, assists, yellow_cards, red_cards, rating, position, substitute)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                player["id"],
                fixture_id,
                games["minutes"],
                goals["total"] or 0,
                goals["assists"] or 0,
                cards["yellow"] or 0,
                cards["red"] or 0,
                float(games["rating"]) if games["rating"] else None,
                games["position"],
                games["substitute"],
            ))


# --- Main ingestion loop ---
# Fetches all finished PL fixtures, saves match data and player stats.
# Skips fixtures already in the database so it's safe to re-run.

def run():
    conn = psycopg2.connect(DB_CONN)
    cur = conn.cursor()

    print("Fetching fixtures...")
    fixtures = fetch_fixtures()
    print(f"Found {len(fixtures)} finished fixtures")

    # Get already processed fixture IDs
    cur.execute("SELECT id FROM api_matches")
    already_done = {row[0] for row in cur.fetchall()}
    to_process = [f for f in fixtures if f["fixture"]["id"] not in already_done]
    print(f"Already processed: {len(already_done)} — skipping")
    print(f"To process: {len(to_process)}")

    failed = []

    for i, fixture in enumerate(to_process, 1):
        fixture_id = fixture["fixture"]["id"]
        try:
            save_match(cur, fixture)
            save_player_stats(cur, fixture_id)
            conn.commit()
            print(f"  [{i}/{len(to_process)}] fixture {fixture_id}: {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}")
        except Exception as e:
            conn.rollback()
            print(f"  [FAILED] fixture {fixture_id}: {e}")
            failed.append(fixture_id)

        time.sleep(0.3)  # stay well within rate limits

    cur.close()
    conn.close()
    print(f"\nDone. Failed fixtures: {len(failed)}")
    if failed:
        print(f"Failed IDs: {failed}")


if __name__ == "__main__":
    run()
