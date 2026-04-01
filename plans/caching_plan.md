# Plan: Abbreviation Cache with LLM Write-Back

## Context

`rewrite_query` currently calls `gpt-4o-mini` on every single request to normalize abbreviations
like "Spurs" → "Tottenham". There is no cache — even well-known abbreviations hit the LLM every
time. This adds latency and cost for zero benefit on repeat patterns.

The fix is a two-phase approach: a fast dictionary substitution runs first (no LLM cost), and the
LLM is only called for queries that still look like they contain unresolved abbreviations. When the
LLM IS called, it writes any new mappings it discovers back to a JSON file via a tool call, so they
are available next time.

---

## Phase 1: Dictionary pre-substitution (no LLM)

Build `NICKNAME_MAP` from two sources at module load:
- A hardcoded `_BASELINE_MAP` in code — version-controlled, never overwritten by the LLM
- A `nickname_cache.json` sidecar file — LLM-discovered mappings that persist across restarts

Baseline always wins: `NICKNAME_MAP = {**_load_cache(), **_BASELINE_MAP}`

Pre-compile word-boundary regex patterns sorted **longest-key-first** — this is critical to prevent
shorter keys shadowing longer ones (e.g. "Man" must not match before "Man City" gets a chance).

Before any LLM call, run `_apply_nickname_map(query)` to substitute all known keys in one pass.

---

## Phase 2: LLM skip heuristic

After pre-substitution, scan the query for remaining 2–4 letter all-caps tokens (e.g. `DCL`, `KDB`,
`TAA`) using:

```
_INITIALISM_RE = re.compile(r'\b[A-Z]{2,4}\b')
```

If none are found, skip the LLM entirely and return the pre-substituted query. If any remain, the
query likely still contains an unresolved abbreviation and the LLM is called.

---

## Phase 3: LLM call with write-back tool

When the LLM IS needed, it receives a tool definition: `add_to_nickname_cache(abbreviation, full_name)`.

The LLM returns:
- `message.content` — the rewritten query text
- `message.tool_calls` — one call per new mapping it resolved (may be None)

Python handles both: extracts the rewritten string, then processes any tool calls by writing new
mappings to `NICKNAME_MAP`, persisting to `nickname_cache.json`, and rebuilding the compiled patterns.

Guards on write-back:
- Never overwrite a baseline entry
- Never add a key that is a prefix of an existing longer key (prevents "Man" shadowing "Man City")

---

## Baseline map (initial entries)

| Abbreviation  | Full name             |
|---------------|-----------------------|
| Spurs         | Tottenham             |
| Wolves        | Wolverhampton         |
| Villa         | Aston Villa           |
| Man City      | Manchester City       |
| Man Utd       | Manchester United     |
| Man United    | Manchester United     |
| Forest        | Nottingham Forest     |
| DCL           | Calvert-Lewin         |
| KDB           | De Bruyne             |
| TAA           | Trent Alexander-Arnold|
| EPL           | Premier League        |
| PL            | Premier League        |

---

## Files to change

**`backend/retrieval/football/football_pipeline.py`**
- Add `import pathlib` to imports
- Add after imports: `_CACHE_FILE`, `_BASELINE_MAP`, `_load_cache()`, `NICKNAME_MAP`,
  `_build_patterns()`, `_NICKNAME_PATTERNS`, `_apply_nickname_map()`, `_looks_normalized()`
- Add: `NICKNAME_TOOLS` list and `_add_to_nickname_cache()` function
- Replace current `rewrite_query` (~20 lines) with the three-phase version

**`backend/retrieval/football/nickname_cache.json`** (new file)
- Initial content: `{}`

**`backend/tests/test_pipeline.py`**
- Update existing `rewrite_query` mocks to include `tool_calls=None` on mock message (prevents AttributeError)
- Add `TestNicknameMapSubstitution` — pure unit tests, no mocking: word boundary correctness,
  longest-key-first ordering, no false matches (e.g. "Villa" must not match inside "Vanilla")
- Add `TestAddToNicknameCache` — tests persistence logic with temp file patching `_CACHE_FILE`

---

## Verification

1. `"How are Wolves playing?"` → pre-substitution returns `"How are Wolverhampton playing?"`, `_looks_normalized` is True, LLM is never called
2. `"How has DCL been?"` → pre-substitution returns `"How has Calvert-Lewin been?"`, LLM skipped
3. A novel initialism like `"How has AWB played?"` → LLM is called, writes the new mapping to `nickname_cache.json`, subsequent query uses it from the map without hitting the LLM
4. `pytest backend/tests/` passes in full
