import json
import sys
from query import ask

def print_result(result):
    print(f"\nAnswer: {result['answer']}")
    print(f"Confidence: {result['confidence']}")
    if result.get("caveat"):
        print(f"Caveat: {result['caveat']}")
    if result.get("sources"):
        print("Sources:")
        for s in result["sources"]:
            print(f"  - {s.get('title', 'Unknown')} ({s.get('published_at', '?')})")
    print(f"Query types: {result.get('query_types', [])}")
    print(f"Retrieval scores: {result.get('retrieval_scores', [])}")
    print()


if __name__ == "__main__":
    # Single query mode: python3 cli.py "How has Salah been playing?"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        result = ask(query)
        print_result(result)
        sys.exit(0)

    # Interactive mode
    print("Football RAG — type your question or 'quit' to exit.\n")
    while True:
        try:
            query = input("Q: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            break
        result = ask(query)
        print_result(result)
