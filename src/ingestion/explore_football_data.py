import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}


def get(endpoint, params=None):
    response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # 1. Check a single PL match to see what stats are available
    print("=== Single match detail ===")
    matches = get("/competitions/PL/matches", params={"season": 2025, "limit": 1})
    match_id = matches["matches"][0]["id"]
    match = get(f"/matches/{match_id}")
    print(json.dumps(match, indent=2))

    # 2. Check top scorers endpoint
    print("\n=== Top scorers ===")
    scorers = get("/competitions/PL/scorers", params={"season": 2025, "limit": 5})
    print(json.dumps(scorers, indent=2))
