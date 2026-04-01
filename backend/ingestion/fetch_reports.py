import requests
import psycopg2
import time
from dotenv import load_dotenv
import os

load_dotenv()

GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
DB_CONN = os.getenv("DATABASE_URL")

# Article types to ingest, each as a Guardian tone tag.
# match_reports uses the current season only; all others go back 3 seasons.
# tone/minutebyminute is intentionally excluded — these are live blogs that
# produce useless chunks (e.g. "45+2: Yellow card for Soucek").
ARTICLE_TYPES = [
    {"tag": "tone/matchreports", "from_date": "2025-08-01", "epl_only": True},
    {"tag": "tone/analysis",     "from_date": "2022-08-01", "epl_only": False},
    {"tag": "tone/features",     "from_date": "2022-08-01", "epl_only": False},
    {"tag": "tone/interview",    "from_date": "2022-08-01", "epl_only": False},
    {"tag": "tone/profiles",     "from_date": "2022-08-01", "epl_only": False},
]


def fetch_articles(tag, page=1, from_date=None, epl_only=False):
    url = "https://content.guardianapis.com/search"
    # Match reports are tagged football/premier-league at article level.
    # Long-form content (interviews, profiles etc.) is not — applying the EPL
    # filter there would return almost nothing, so we omit it for those types.
    # Always exclude women's football — football/womensfootball is the consistent
    # catch-all tag the Guardian applies to all WSL and women's content.
    combined_tag = f"{tag},football/premierleague" if epl_only else tag
    params = {
        "api-key": GUARDIAN_API_KEY,
        "section": "football",
        "tag": combined_tag,
        "show-fields": "bodyText,headline",
        "page-size": 50,
        "page": page,
        "order-by": "newest",
    }
    if from_date:
        params["from-date"] = from_date
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


LIVE_BLOG_PATTERNS = ["as it happened", "– live", "- live"]


def is_live_blog(title):
    title_lower = title.lower()
    return any(p in title_lower for p in LIVE_BLOG_PATTERNS)


def save_to_db(conn, report, article_type):
    fields = report.get("fields", {})
    body = fields.get("bodyText", "").strip()
    if not body:
        return False

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO match_reports (title, url, published_at, source, article_type)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
        """,
        (
            report["webTitle"],
            report["webUrl"],
            report["webPublicationDate"],
            "guardian",
            article_type,
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


def run_for_type(conn, tag, from_date, epl_only=False, max_pages=None):
    """Fetch and save all articles for a single Guardian tone tag."""
    # Derive a short article_type label from the tag (e.g. "tone/analysis" → "analysis")
    article_type = tag.split("/")[-1]
    page = 1
    total_saved = 0

    while True:
        print(f"  [{article_type}] Fetching page {page}...")
        data = fetch_articles(tag, page=page, from_date=from_date, epl_only=epl_only)
        response = data["response"]
        results = response["results"]
        total_pages = response["pages"]

        if not results:
            break

        for report in results:
            if is_live_blog(report["webTitle"]):
                continue
            saved = save_to_db(conn, report, article_type)
            if saved:
                total_saved += 1

        print(f"  [{article_type}] Page {page}/{total_pages} — {total_saved} saved so far")

        if page >= total_pages:
            break
        if max_pages and page >= max_pages:
            break

        page += 1
        time.sleep(0.5)

    return total_saved


def run(max_pages=None):
    conn = psycopg2.connect(DB_CONN)
    grand_total = 0

    try:
        for article_def in ARTICLE_TYPES:
            tag = article_def["tag"]
            from_date = article_def["from_date"]
            epl_only = article_def["epl_only"]
            print(f"\nFetching {tag} from {from_date} (EPL only: {epl_only})...")
            saved = run_for_type(conn, tag, from_date, epl_only=epl_only, max_pages=max_pages)
            grand_total += saved
            print(f"  → {saved} articles saved for {tag}")
    finally:
        conn.close()

    print(f"\nDone. Grand total saved: {grand_total}")


if __name__ == "__main__":
    run()
