import json
import sys
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "retrieval"))
from query import ask

TEST_QUERIES = [
    # RAG only — tactical
    {"query": "How do Arsenal like to play?",                        "from_date": None, "gender": None},
    {"query": "How does Liverpool press?",                           "from_date": None, "gender": None},
    {"query": "How do Manchester City build out from the back?",     "from_date": None, "gender": None},

    # Stats only
    {"query": "How many goals has Haaland scored this season?",      "from_date": None, "gender": None},
    {"query": "Who are the top 5 assisters this season?",            "from_date": None, "gender": None},
    {"query": "What was the score in the last Arsenal game?",        "from_date": None, "gender": None},

    # Mixed — player form
    {"query": "How has Saka been playing this season?",              "from_date": None, "gender": None},
    {"query": "How has Bruno Fernandes been performing?",            "from_date": None, "gender": None},

    # Mixed — fantasy
    {"query": "Is Haaland worth picking for fantasy this week?",     "from_date": None, "gender": None},
    {"query": "Which strikers have been in form recently?",          "from_date": None, "gender": None},

    # Natural language — match recap
    {"query": "What happened in the last Arsenal game?",             "from_date": None, "gender": None},
    {"query": "What happened in the last Liverpool game?",           "from_date": None, "gender": None},
    {"query": "How did Chelsea get on at the weekend?",              "from_date": None, "gender": None},
    {"query": "What was the result when Spurs played Man United?",   "from_date": None, "gender": None},

    # Natural language — mixed intent
    {"query": "Is Salah still the best player in the league?",       "from_date": None, "gender": None},
    {"query": "Why are Manchester United struggling this season?",    "from_date": None, "gender": None},
]


def run():
    for i, item in enumerate(TEST_QUERIES, 1):
        query = item["query"]
        print(f"\n{'='*60}")
        print(f"[{i}/{len(TEST_QUERIES)}] {query}")
        print("="*60)

        result = ask(query, from_date=item["from_date"], gender=item["gender"])

        print(f"Answer:           {result.get('answer')}")
        print(f"Confidence:       {result.get('confidence')}")
        print(f"Caveat:           {result.get('caveat')}")
        print(f"Query types:      {result.get('query_types')}")
        print(f"Retrieval scores: {result.get('retrieval_scores')}")
        if result.get("sources"):
            print("Sources:")
            for s in result["sources"]:
                print(f"  - {s.get('title', '?')} ({s.get('published_at', '?')})")


if __name__ == "__main__":
    run()
