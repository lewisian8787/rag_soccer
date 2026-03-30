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

---

## END-TO-END PIPELINE TESTING

### Test Run 1 — Full pipeline, 16 queries
**Date:** 2026-03-30
**Script:** `src/retrieval/test_pipeline.py`
**Purpose:** First full end-to-end test across all query types — tactical (RAG), stats, player form (mixed), fantasy (mixed), and natural language match recap queries.

#### Results

```
[1/16] How do Arsenal like to play?
Query types: ['rag'] | Scores: 0.6472–0.6118
Answer: Arteta's Arsenal play fluent, expressive attacking football, emphasising possession and defensive discipline.
Sources: 2021-10-30, 2024-02-17, 2025-10-18
ISSUE: 2021 source (Ramsdale/Leicester) is stale.

[2/16] How does Liverpool press?
Query types: ['rag'] | Scores: 0.5699–0.5392 (weakest tactical retrieval)
Answer: Describes Klopp's high-intensity pressing, counter-pressing and forward aggression.
Sources: 2021-04-03, 2022-04-27, 2017-10-01
ISSUE: All sources are Klopp era. Slot has a notably different pressing style. Answer is outdated.

[3/16] How do Manchester City build out from the back?
Query types: ['rag'] | Scores: 0.6861–0.6292 (best tactical retrieval)
Answer: Describes Guardiola's possession-based build-up, Ederson distribution, full-back roles.
Sources: 2020-07-05, 2018-09-22, 2024-03-31
ISSUE: 2018 and 2020 sources are stale. Principles broadly consistent but personnel outdated.

[4/16] How many goals has Haaland scored this season?
Query types: ['stats'] | Scores: []
Answer: 22 goals.
PASS: Stats tool correctly called, factual answer returned.

[5/16] Who are the top 5 assisters this season?
Query types: ['stats'] | Scores: []
Answer: Bruno Fernandes (16), Rayan Cherki (8), Haaland (7), then several on 6.
PASS: Stats tool correctly called. Notable that Fernandes has 16 assists.

[6/16] What was the score in the last Arsenal game?
Query types: ['stats'] | Scores: []
Answer: Arsenal 2-0 Everton.
PASS: Stats tool correctly returned match result.

[7/16] How has Saka been playing this season?
Query types: ['rag', 'stats'] | Scores: 0.6789–0.6251 (best mixed retrieval)
Answer: Instrumental in creating goals, described as best player on pitch in multiple games.
Sources: 2024-11-23, 2022-10-20
ISSUE: 2022 source (PSV Europa League) is stale. Stats not visible in answer despite being fetched.

[8/16] How has Bruno Fernandes been performing?
Query types: ['rag', 'stats'] | Scores: 0.6236–0.5681
Answer: 28 appearances, 8 goals, 16 assists, avg rating 7.58. Good synthesis of stats and narrative.
Sources: 2025-03-16, 2023-10-21, 2023-09-23
PASS: Best mixed query result — stats and RAG well synthesised.

[9/16] Is Haaland worth picking for fantasy this week?
Query types: ['rag', 'stats'] | Scores: 0.5634–0.5362
Answer: Recommended pick based on recent Brentford performance.
Sources: 2025-10-05
CONCERN: Only one source, from October 2025. No fixture difficulty considered. Weak fantasy answer.

[10/16] Which strikers have been in form recently?
Query types: ['rag', 'stats'] | Scores: 0.5206–0.4697 (weakest overall retrieval)
Answer: Ivan Toney, Lukaku, Mitrovic.
FAIL: All three players are outdated. Lukaku reference is from 2021 Belgium international. Mitrovic from 2021 Championship. No date filter applied.

[11/16] What happened in the last Arsenal game?
Query types: ['rag'] | Scores: 0.6872–0.6557 (best retrieval of all 16 queries)
Answer: Arsenal held by Fulham, Saka goal ruled out for offside by VAR.
Sources: 2024-12-08
CONCERN: Routed to RAG only — no stats call. Result came from match report text, not the DB. Accuracy depends on whether this is genuinely the last Arsenal game in the index.

[12/16] What happened in the last Liverpool game?
Query types: ['rag'] | Scores: 0.6728–0.6414
Answer: Leeds drew with Liverpool 3-3 in injury time, Tanaka late strike.
Sources: 2025-12-06
CONCERN: Same as above — RAG only, not stats. Result plausible but not verified against DB.

[13/16] How did Chelsea get on at the weekend?
Query types: ['rag', 'stats'] | Scores: 0.6369–0.6265
Answer: Chelsea lost 3-0 to Everton on March 21, 2026.
PASS: Correct routing, recent result returned. No sources listed despite RAG being called.

[14/16] What was the result when Spurs played Man United?
Query types: ['stats'] | Scores: []
Answer: Not enough information found.
FAIL: Stats tool called but returned nothing — likely fixture not found or team name mismatch. RAG not called, which might have found match report text.

[15/16] Is Salah still the best player in the league?
Query types: ['rag', 'stats'] | Scores: 0.6404–0.5766
Answer: Among the top performers — 5 goals, 6 assists in 22 appearances. Praised in match reports.
Sources: 2023-11-12
CONCERN: Primary source is 2023. Confidence "high" despite stale evidence.

[16/16] Why are Manchester United struggling this season?
Query types: ['rag'] | Scores: 0.6218–0.5883
Answer: Describes Ten Hag era — defensive fragility, Højlund ineffective, lack of cohesion.
Sources: 2023-12-23, 2024-04-13, 2024-10-06
FAIL: Ten Hag was sacked in October 2024. Ruben Amorim is now manager. Answer is factually misleading.
```

#### Observations

**What's working:**
- Classifier routing is accurate across all 16 queries — correct query types fired every time
- Stats-only queries (4, 5, 6) all returned correct, concise factual answers
- Mixed queries (7, 8) are synthesising stats and narrative well, particularly Bruno Fernandes (8)
- Match recap queries (11, 12, 13) returned surprisingly good results with high retrieval scores
- Natural language queries handled without errors

**What's failing:**

1. **Staleness is the primary issue.** Queries 2, 3, 10, 15, 16 all drew from significantly outdated sources. Query 16 (Man United) is the worst case — the answer describes a manager who was sacked 5 months ago.

2. **Confidence is always "high".** Not a single medium or low confidence returned across 16 queries, even when sources are years old and the answer is questionable. The system prompt is not working as intended for confidence scoring.

3. **"Recently/in form" queries (10) completely failed.** No date filter means "which strikers have been in form recently?" returned 2021 results. This is the most user-facing failure.

4. **Match recap queries (11, 12) routed to RAG instead of stats.** "What happened in the last X game?" should hit the stats DB for the result and then RAG for the narrative. Currently it only hits RAG and relies on the most recent matching chunk being the actual last game — which is fragile.

5. **Query 14 (Spurs vs Man United)** — stats tool returned nothing, RAG not attempted. Complete failure.

#### Actions taken

- Applied default `CURRENT_SEASON_DATE = "2025-08-01"` in `retrieve()` with fallback to `FALLBACK_SEASON_DATE = "2024-08-01"`
- Added `RECENCY_PATTERN` in `ask()` — recency/form language defaults to 30-day window
- `since_date` passed through to `fetch_stats_context()` for consistent stats filtering
- Added match recap rule to classifier prompt
- Added `since_date` to `get_top_scorers` and `get_top_assisters`
- Added position mapping (Goalkeeper→G etc.) to `get_top_rated_players`
- Lowered `HAVING COUNT(*) >= 1` when `since_date` is set

---

### Test Run 2 — Full pipeline post-staleness fixes, 16 queries
**Date:** 2026-03-30
**Script:** `src/retrieval/test_pipeline.py`
**Pipeline state:** Current season default filter, recency pattern, match recap classifier rule, position mapping, since_date on leaderboards.

#### Results

```
[1] How do Arsenal like to play? | rag | scores 0.57–0.62
Sources: 2025-08-31 to 2025-11-04 — all current season. No stale chunks.
Answer: Describes Arteta's defensive solidity, set-piece innovation, midfield physicality. Good.
PASS

[2] How does Liverpool press? | rag | scores 0.48–0.53
Sources: 2025-09-30 to 2026-01-21 — all current season. Mentions Slot era correctly.
Confidence: medium — appropriate given limited data.
PASS

[3] How do Manchester City build out from the back? | rag | scores 0.59–0.60
Sources: 2025-09-27 to 2025-12-17 — all current season.
Answer: References González, O'Reilly, Doku, Foden — current squad. No stale chunks.
PASS

[4] How many goals has Haaland scored? | stats | scores []
Answer: 22 goals. Correct.
PASS

[5] Top 5 assisters | stats | scores []
Answer: Fernandes 16, Cherki 8, Haaland 7, Wilson 6, Bowen 6. Returned as clean list.
PASS

[6] Last Arsenal game score | stats | scores []
Answer: Arsenal 2-0 Everton. Correct.
PASS

[7] How has Saka been playing? | rag+stats | scores 0.51–0.57
Sources: 2025-08-23 to 2026-01-20 — current season only.
Answer: Covers injuries, form, key contributions. Good synthesis.
PASS

[8] How has Bruno Fernandes been performing? | rag+stats | scores 0.48–0.53
Answer: 8 goals, 16 assists, 7.58 avg rating — league record assists. Well synthesised.
Sources: 2026-02-07 to 2026-03-20 — recent and relevant.
PASS — best mixed query result

[9] Is Haaland worth picking for fantasy? | rag+stats | scores 0.48–0.56
Answer: Recommends as pick, references recent doubles. Good.
PASS

[10] Which strikers have been in form recently? | rag+stats | scores 0.45–0.45
Answer: Gordon, João Pedro, Gibbs-White, Welbeck, Beto — all based on last 30 days. Correct.
PASS — major improvement from Test Run 1 (previously returned 2021 players)

[11] What happened in the last Arsenal game? | rag+stats | scores 0.62–0.64
Answer: Lost to City 2-0 in Carabao Cup final, March 22.
Sources: 2026-03-22 — correct and current.
PASS

[12] What happened in the last Liverpool game? | rag+stats | scores 0.59–0.64
Answer: Lost to Brighton 2-1, March 21. Mentions Salah/Alisson injuries, Slot.
PASS

[13] How did Chelsea get on at the weekend? | rag+stats | scores 0.59–0.63
Answer: Lost 3-0 to Everton. Concise, correct.
PASS

[14] What was the result when Spurs played Man United? | rag+stats | scores 0.54–0.62
Answer: Man United won. No score returned — stats tool found no exact fixture match.
Confidence: medium — appropriate.
PARTIAL — result direction correct but no score

[15] Is Salah still the best player in the league? | rag+stats | scores 0.49–0.56
Answer: Argues no based on stats — Haaland leads goals, Fernandes leads assists. Balanced.
Confidence: medium — appropriate for opinion question.
PASS

[16] Why are Manchester United struggling? | rag | scores 0.53–0.58
Answer: Mentions Amorim, defensive errors, goalkeeping issues, inconsistency. Current and accurate.
Sources: 2025-08-17 to 2026-03-20 — all current season.
PASS — major improvement from Test Run 1 (previously described Ten Hag era)
```

#### Observations

- **Staleness resolved across all 16 queries** — every source is from 2025-26 or 2024-25 season
- **Recency pattern working** — query 10 now returns 2026 players instead of 2021
- **Match recap routing fixed** — queries 11, 12 now correctly call both stats and RAG
- **Confidence scoring improved** — medium returned for queries 2, 14, 15 appropriately
- **Query 14 (Spurs vs Man United)** — partial result, direction correct but no score. Stats tool unable to find exact fixture match
- **Retrieval scores lower overall** — current season filter reduces pool, scores now 0.45–0.64 vs 0.55–0.69 previously. Quality of answers unaffected.

#### Actions taken

- Pipeline in good shape for class project demonstration
- Query 14 fixture matching to be investigated
- Full test suite to be re-run after any further changes
