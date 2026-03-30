import requests
import psycopg2
import time
from dotenv import load_dotenv
import os

load_dotenv()

GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
DB_CONN = os.getenv("DATABASE_URL")


def fetch_match_reports(page=1, from_date=None):
    url = "https://content.guardianapis.com/search"
    params = {
        "api-key": GUARDIAN_API_KEY,
        "section": "football",
        "tag": "tone/matchreports",
        "show-fields": "bodyText,headline",
        "page-size": 50,
        "page": page,
        "order-by": "newest",
    }
    if from_date:
        params["from-date"] = from_date  # format: YYYY-MM-DD
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def save_to_db(conn, report):
    fields = report.get("fields", {})
    body = fields.get("bodyText", "").strip()
    if not body:
        return False

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO match_reports (title, url, published_at, source)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
        """,
        (
            report["webTitle"],
            report["webUrl"],
            report["webPublicationDate"],
            "guardian",
        ),
    )
    row = cur.fetchone()
    if row:
        report_id = row[0]
        cur.execute(
            "INSERT INTO match_report_bodies (match_report_id, body) VALUES (%s, %s)",
            (report_id, body),
        )
        conn.commit()
        cur.close()
        return True

    conn.commit()
    cur.close()
    return False  # duplicate


def run(from_date=None, max_pages=None):
    conn = psycopg2.connect(DB_CONN)
    page = 1
    total_saved = 0

    try:
        while True:
            print(f"Fetching page {page}...")
            data = fetch_match_reports(page, from_date=from_date)
            response = data["response"]
            results = response["results"]
            total_pages = response["pages"]

            if not results:
                break

            for report in results:
                saved = save_to_db(conn, report)
                if saved:
                    total_saved += 1

            print(f"  Page {page}/{total_pages} — {total_saved} saved so far")

            if page >= total_pages:
                break
            if max_pages and page >= max_pages:
                break

            page += 1
            time.sleep(0.5)
    finally:
        conn.close()

    print(f"\nDone. Total saved: {total_saved}")


if __name__ == "__main__":
    run()
