# Testing Log

This file documents every test run against the RAG football chatbot pipeline.
Each entry records the configuration, raw results, observations, and actions taken.

---

## What we are testing

### Retrieval quality checklist
For each test run, evaluate against these criteria:

- [ ] Scores above 0.75 for most results (7-8 out of 10)
- [ ] Relevant titles — query subject matches returned matches
- [ ] Diverse dates — results span multiple seasons, not all from one game
- [ ] Chunk text is on-topic — 200 char preview visibly relates to the query
- [ ] Player form queries return recent dates only (date filter working)
- [ ] No live blog content (minute-by-minute logs should not appear)

---

## Configuration at time of test

| Parameter            | Value                        |
|----------------------|------------------------------|
| Embedding model      | text-embedding-3-small       |
| Vector dimensions    | 1536                         |
| Chunk target tokens  | 150                          |
| Chunk overlap        | 1 sentence                   |
| top_k                | 10                           |
| Low score threshold  | 0.75                         |
| Date range in index  | 2016-01-01 to present        |
| Total vectors        | 66,994                       |
| Live blogs excluded  | Yes                          |
| Gender tagged        | Yes (men / women)            |

---

## Test Runs

---
## PRE LLM LAYER TESTING

### Test Run 1 — Retrieval only (no LLM)
**Date:** 2026-03-27
**Script:** `src/retrieval/test_retrieval.py`
**Purpose:** Validate that Pinecone is returning relevant chunks before wiring up the LLM.

#### Results

```
Query: How do Arsenal play against the high press?
All 10 results [LOW] — scores 0.57–0.59. Titles broadly relevant (Arsenal matches) but
one WSL result slipped through (Man City Caroline Weir, 2020) indicating gender filter
not yet applied at query time.

Query: How do Liverpool set up defensively away from home?
All 10 results [LOW] — scores 0.59–0.61. Titles loosely relevant but no result directly
addresses defensive away setup. Chunks are contextually related but not precise.

Query: How do Manchester City build up play from the back?
All 10 results [LOW] — scores 0.63–0.69. Best performing query of the three. Chunks
visibly reference Guardiola's buildup tactics, Walker/Gvardiol positioning etc.

Queries 4–7 (player form / fantasy): crashed with PineconeApiException 400.
Date filter failed — $gte operator requires a number, not a date string.
```

#### Observations

- All scores below 0.75 threshold — no results passed the quality bar
- Manchester City query performed best (0.69 top score), suggesting more tactical detail in the data for that team
- Gender filter not applied at query time — WSL results appearing in men's queries
- `published_at` stored as string in Pinecone metadata — date filtering broken
- Retrieval is returning topically related content but scores suggest chunks are not precise enough matches

#### Actions taken

- Fixed `published_at` storage: changed from `str(published_at)` to Unix timestamp (int) in embed script
- Re-embedded all 66,992 vectors
- Fixed date filter in test_retrieval.py to convert `from_date` string to Unix timestamp before querying
- Gender filter at query time — deferred, to be addressed in retrieval layer

---

### Test Run 2 — Retrieval with fixed timestamp + date filter
**Date:** 2026-03-28
**Script:** `src/retrieval/test_retrieval.py`
**Purpose:** Validate fixes to `published_at` Unix timestamp storage and date filter. First full run of all 7 queries.

#### Results

```
Tactical queries (no date filter):
- Arsenal high press:         all [LOW], scores 0.57–0.59
- Liverpool defensive away:   all [LOW], scores 0.59–0.61
- Man City build up:          all [LOW], scores 0.63–0.69

Player form queries (from 2025-09-01):
- Salah recent form:          all [LOW], scores 0.52–0.62 — date filter working, all results post Sep 2025
- Bukayo Saka this season:    all [LOW], scores 0.52–0.59 — date filter working, all results post Sep 2025

Fantasy queries (from 2025-09-01):
- Strikers in form:           all [LOW], scores 0.43–0.46 — weakest performing query
- Midfielders goals/assists:  all [LOW], scores 0.45–0.49 — weak scores
```

#### Observations

- **Date filter is now working** — player form and fantasy queries correctly return only post-2025 results
- **All scores remain below 0.75 threshold** — no results passing the quality bar across any query type
- **Tactical queries returning topically relevant content** — Man City chunks reference Guardiola, Walker, Gvardiol positioning. Arsenal chunks reference pressing and counter-pressing. Titles are broadly correct.
- **Fantasy queries performing worst** (0.43–0.49) — likely because match reports aren't written to answer "which players are in form" style questions. The language doesn't match.
- **WSL result still appearing** in Arsenal query (Caroline Weir, 2020) — gender filter not yet applied at query time
- **Core concern: scores are uniformly low** — this may be a characteristic of `text-embedding-3-small` on this type of query, or it may indicate chunk quality issues. Will become clearer once LLM layer is added — low retrieval scores don't necessarily mean poor answers.

#### Actions taken

- Results recorded. Low score threshold may need to be lowered for this dataset — to be reviewed after LLM layer is built and end-to-end quality can be assessed.
- Gender filter at query time to be added to retrieval layer.

---

### Test Run 3 — Full chunks visible
**Date:** 2026-03-28
**Script:** `src/retrieval/test_retrieval.py`
**Purpose:** Evaluate chunk content quality with full text visible (removed 200 char truncation).

#### Results

```
Scores unchanged from Test Run 2. All results [LOW].

Tactical queries:
- Arsenal high press:       0.57–0.59. Content relevant — pressing, counter-pressing
                            mentioned. WSL result still appearing (Caroline Weir).
- Liverpool defensive away: 0.59–0.61. Loosely relevant. No result directly addresses
                            defensive away setup specifically.
- Man City build up:        0.63–0.69. Best quality. Chunks clearly describe Guardiola's
                            buildup — Fernandinho as auxiliary CB, Walker/Gvardiol
                            advancing, patient possession play.

Player form (from 2025-09-01):
- Salah:   0.52–0.62. Strong content — contract dispute, dropped from lineup,
           return to form post-AFCON. Date filter working correctly.
- Saka:    0.52–0.59. Relevant content — hip injury, rested more this season,
           individual performances described. Date filter working.

Fantasy (from 2025-09-01):
- Strikers in form:          0.43–0.46. Weak. Individual striker mentions scattered
                             across unrelated match reports. No direct "form" summary.
- Midfielders goals/assists: 0.45–0.49. Weak. Fernandes assist record mentioned but
                             content is incidental rather than focused.
```

#### Observations

- **Chunk content is broadly useful for tactical and player queries** — full text confirms retrieval is working despite low scores
- **Fantasy queries remain the weakest** — match reports don't summarise form, they describe individual matches. This is a fundamental KB limitation.
- **Gender filter still not applied at query time** — WSL result persists in Arsenal query
- **Low score threshold of 0.75 is too strict** for this dataset — content is useful even at 0.57

#### Actions taken

- Lower `LOW_SCORE_THRESHOLD` to 0.45 to reduce noise in output
- Proceed to LLM layer — chunk quality sufficient to generate answers
- Gender filter to be wired in at retrieval layer build

---

## CLASSIFIER TESTING

### Test Run 1 — LLM classifier (gpt-4o-mini)
**Date:** 2026-03-29
**Script:** `src/retrieval/test_classifier.py`
**Purpose:** Validate that the gpt-4o-mini classifier correctly routes queries to `rag`, `stats`, or both.

#### Results

```
[PASS] How do Arsenal press high?
       expected: {'rag'}             got: {'rag'}

[PASS] How does Guardiola set up against a low block?
       expected: {'rag'}             got: {'rag'}

[PASS] How do Liverpool defend set pieces?
       expected: {'rag'}             got: {'rag'}

[PASS] How many goals has Salah scored?
       expected: {'stats'}           got: {'stats'}

[PASS] Who has the most assists this season?
       expected: {'stats'}           got: {'stats'}

[PASS] What was the score in Arsenal vs Chelsea?
       expected: {'stats'}           got: {'stats'}

[FAIL] Who has been clinical in front of goal?
       expected: {'stats', 'rag'}    got: {'stats'}

[FAIL] How has Salah been playing this season?
       expected: {'stats', 'rag'}    got: {'rag'}

[PASS] Which midfielders have been contributing recently?
       expected: {'stats', 'rag'}    got: {'stats', 'rag'}

[PASS] Is Saka worth picking for fantasy this week?
       expected: {'stats', 'rag'}    got: {'stats', 'rag'}

8/10 passed
```

#### Observations

- Pure tactical queries (RAG only) — all 3 passed. Classifier correctly avoids stats for tactical questions.
- Pure stat queries (stats only) — all 3 passed. Direct stat lookups routed correctly.
- "Both" queries — 2 failed, 2 passed.
  - "Who has been clinical in front of goal?" returned `stats` only — classifier treated it as a pure stat lookup, missing the narrative/form context that match reports provide.
  - "How has Salah been playing this season?" returned `rag` only — classifier treated it as a form question and missed the stats dimension.
- The two failures are both edge cases where the query reads like one type but benefits from both.

#### Actions taken

- Classifier prompt refined to handle ambiguous "form + stats" queries — see Test Run 2 below.

---

### Test Run 2 — LLM classifier after prompt refinement
**Date:** 2026-03-29
**Script:** `src/retrieval/test_classifier.py`
**Purpose:** Validate prompt fix for the two failing "both" cases from Test Run 1.

#### What changed in the prompt

The original prompt gave one general rule: "Most questions need both. Pure tactical → rag only. Pure stat lookups → stats only." That was too vague for edge cases.

The updated prompt adds explicit rules for each failure pattern:

1. **Player form questions** — added the rule: *"Player form questions (e.g. 'How has Salah been playing?') → always both"*. The classifier was previously reading "How has Salah been playing?" as narrative-only because it contains no stats keywords. The explicit rule forces both.

2. **Subjective quality questions** — added the rule: *"Subjective quality questions about players (e.g. 'Who has been clinical?') → always both — stats confirm it, reports explain it"*. The classifier was reading "clinical in front of goal" as a stats lookup only. The added framing (stats confirm, reports explain) gives the model a reason to include rag.

3. **Added a fallback**: *"When in doubt, return both."* This biases the classifier toward inclusion on genuinely ambiguous queries, at the cost of occasionally fetching stats that aren't used.

#### Results

```
[PASS] How do Arsenal press high?
       expected: {'rag'}             got: {'rag'}

[PASS] How does Guardiola set up against a low block?
       expected: {'rag'}             got: {'rag'}

[PASS] How do Liverpool defend set pieces?
       expected: {'rag'}             got: {'rag'}

[PASS] How many goals has Salah scored?
       expected: {'stats'}           got: {'stats'}

[PASS] Who has the most assists this season?
       expected: {'stats'}           got: {'stats'}

[PASS] What was the score in Arsenal vs Chelsea?
       expected: {'stats'}           got: {'stats'}

[PASS] Who has been clinical in front of goal?
       expected: {'stats', 'rag'}    got: {'stats', 'rag'}

[PASS] How has Salah been playing this season?
       expected: {'stats', 'rag'}    got: {'stats', 'rag'}

[PASS] Which midfielders have been contributing recently?
       expected: {'stats', 'rag'}    got: {'stats', 'rag'}

[PASS] Is Saka worth picking for fantasy this week?
       expected: {'stats', 'rag'}    got: {'stats', 'rag'}

10/10 passed
```

#### Observations

- All 10 cases pass. Pure tactical and pure stat queries unaffected by the changes.
- Both previously failing cases now correctly return `{'rag', 'stats'}`.
- The "when in doubt, return both" fallback is a deliberate bias — a missed stats fetch is cheaper than a wrong answer.

#### Actions taken

- Classifier prompt accepted. No further changes needed at this stage.
- Next: end-to-end test of full `ask()` pipeline combining classifier, RAG retrieval, and stats queries.
