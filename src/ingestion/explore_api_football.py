import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}


def get(endpoint, params=None):
    response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # 1. Check a single PL match to see what stats are returned
    print("=== Single PL match ===")
    fixtures = get("/fixtures", params={"league": 39, "season": 2024, "round": "Regular Season - 1"})
    print(json.dumps(fixtures, indent=2))

    # 2. Check player stats for that match
    fixture_id = fixtures["response"][0]["fixture"]["id"]
    print(f"\n=== Player stats for fixture {fixture_id} ===")
    stats = get("/fixtures/players", params={"fixture": fixture_id})
    print(json.dumps(stats["response"][0], indent=2))
