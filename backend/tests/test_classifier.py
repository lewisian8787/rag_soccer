import sys
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "retrieval"))
from query import classify_query

TEST_CASES = [
    # Pure tactical — RAG only
    {"query": "How do Arsenal press high?",                           "expected": {"rag"}},
    {"query": "How does Guardiola set up against a low block?",       "expected": {"rag"}},
    {"query": "How do Liverpool defend set pieces?",                  "expected": {"rag"}},

    # Pure stat lookup — stats only
    {"query": "How many goals has Salah scored?",                     "expected": {"stats"}},
    {"query": "Who has the most assists this season?",                "expected": {"stats"}},
    {"query": "What was the score in Arsenal vs Chelsea?",            "expected": {"stats"}},

    # Needs both
    {"query": "Who has been clinical in front of goal?",              "expected": {"rag", "stats"}},
    {"query": "How has Salah been playing this season?",              "expected": {"rag", "stats"}},
    {"query": "Which midfielders have been contributing recently?",   "expected": {"rag", "stats"}},
    {"query": "Is Saka worth picking for fantasy this week?",         "expected": {"rag", "stats"}},
]

passed = 0
failed = 0

for case in TEST_CASES:
    result = classify_query(case["query"])
    ok = result == case["expected"]
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"[{status}] {case['query']}")
    print(f"       expected: {case['expected']}")
    print(f"       got:      {result}")
    print()

print(f"\n{passed}/{len(TEST_CASES)} passed")
sys.exit(0 if failed == 0 else 1)
