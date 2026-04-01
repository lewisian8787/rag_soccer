# Plan: Multi-Turn Conversation Loop

## Context

The app is currently stateless — every question is independent, with no memory of prior turns. This prevents natural follow-up questions ("What about his assists?" has no referent). We need to:
1. Pass conversation history to the backend on each request
2. Use that history in two pipeline stages: query rewriting (pronoun resolution) and final answer generation
3. Apply a sliding-window eviction policy to keep context bounded

---

## Architecture Decision: Client-Side History

History lives in React state and is sent with every request. No database, no session IDs, no server-side state. Rationale: this is a class project; football Q&A sessions are short and topically focused; oldest turns are the least relevant anyway.

**Context evacuation strategy: Sliding Window (cap = 10 turns = 20 messages)**
- When the window fills, drop the oldest user+assistant pair before sending
- Implemented in `App.tsx` in the `onResult` callback
- No summarization LLM call needed — over-engineering for realistic session lengths

---

## Critical Files

- [backend/api/main.py](../backend/api/main.py)
- [backend/retrieval/football/football_pipeline.py](../backend/retrieval/football/football_pipeline.py)
- [backend/retrieval/fpl/fpl_pipeline.py](../backend/retrieval/fpl/fpl_pipeline.py)
- [frontend/src/hooks/useAsk.ts](../frontend/src/hooks/useAsk.ts)
- [frontend/src/App.tsx](../frontend/src/App.tsx)
- [backend/tests/test_pipeline.py](../backend/tests/test_pipeline.py)

---

## Implementation Steps

### 1. Backend: Pydantic request model (`main.py`)

Add typed request model and update the endpoint:

```python
class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class AskRequest(BaseModel):
    query: str
    mode: str = "football"
    from_date: str | None = None
    gender: str | None = None
    history: list[ConversationTurn] = []
```

Change endpoint parameter from `body: dict` to `body: AskRequest`. Pass `history=[t.model_dump() for t in body.history]` to `run_pipeline`.

### 2. Backend: Pipeline signatures (`football_pipeline.py`)

- `run_pipeline(query, from_date=None, gender=None, history=None)` — add `history=None`
- `rewrite_query(query, history=None)` — add `history` param
- `generate_response(..., history=None)` — add `history` param
- `ask(query, ..., history=None)` — forward through

### 3. Backend: `rewrite_query` — pronoun/coreference resolution

Inject last 2 messages (= 1 prior turn) before the current query so the model can resolve "he/his/them" references:

```python
messages = [{"role": "system", "content": REWRITE_SYSTEM_PROMPT}]
if history:
    messages.extend(history[-2:])   # last user+assistant pair only
messages.append({"role": "user", "content": query})
```

### 4. Backend: `generate_response` — conversation memory

Insert prior turns between the system prompt and the current retrieval-augmented user message:

```python
messages = [{"role": "system", "content": ANSWER_SYSTEM_PROMPT}]
if history:
    messages.extend(history)        # all turns in the sliding window
messages.append({"role": "user", "content": user_message})  # chunks + stats
```

### 5. Backend: FPL stub (`fpl_pipeline.py`)

Add `history=None` to its `run_pipeline` / `ask` signatures to keep the interface consistent. No functional change.

### 6. Frontend: `useAsk.ts` — accept and send history

Add `ConversationTurn` type. Change `ask(query, mode)` to `ask(query, mode, history: ConversationTurn[] = [])`. Include `history` in the JSON body.

### 7. Frontend: `App.tsx` — manage conversation window

Add a second piece of state alongside the existing `history` sidebar state:

```typescript
const MAX_HISTORY_TURNS = 10
const [conversationHistory, setConversationHistory] = useState<ConversationTurn[]>([])
```

In `handleAsk`: pass `conversationHistory` to `ask()`.

In `onResult` callback: append new user+assistant pair, then slice to `MAX_HISTORY_TURNS * 2`:

```typescript
setConversationHistory(prev => {
    const updated = [...prev,
        { role: 'user', content: r.query },
        { role: 'assistant', content: r.answer },
    ]
    const max = MAX_HISTORY_TURNS * 2
    return updated.length > max ? updated.slice(updated.length - max) : updated
})
```

On mode change: also clear `conversationHistory`.

### 8. Frontend: `App.tsx` — thread view in main panel

Replace the single `<AnswerCard>` display with a scrollable thread that maps over all `history` entries. Each entry renders a right-aligned user bubble and an `<AnswerCard>`. The streaming in-progress turn renders below the history. Add `scrollIntoView` on new history entries.

Optionally add a "New conversation" button to clear both history arrays without a page refresh.

---

## What is NOT Changed

- The `<<<META>>>` delimiter + metadata JSON parsing in `generate_response`
- SSE stream format (`token`, `done`, `error`)
- `AskResult` TypeScript interface
- `classify_query`, `fetch_stats_context`, `retrieve_match_report_chunks`, `build_context`, `_build_user_message`
- No new packages in `requirements.txt` or `package.json`

---

## Verification

1. Start backend: `uvicorn backend.api.main:app --reload`
2. Load frontend in browser
3. Ask "Who scored in the last Liverpool game?"
4. Follow up with "What about his assists this season?" — should resolve "his" correctly
5. Check network tab: second request should include `history` array with first Q&A pair
6. After 10+ turns, check that `history` array in request stays at ≤ 20 messages
7. Switch mode (football → fpl → football) — conversation history should reset
8. Run `pytest backend/tests/test_pipeline.py` — all existing tests should still pass