# Implementation: Multi-Turn Conversation

## Summary

Implemented full multi-turn conversation support. Users can now ask follow-up questions with context from prior turns.

**Status**: ✅ Complete — 32 backend tests pass, frontend builds without errors

---

## Architecture: Client-Side History + Sliding Window

- **History storage**: React state (`conversationHistory`) sends compact `{role, content}` pairs on every request
- **No database/sessions**: Stateless design, history resets on page refresh or mode change
- **Eviction**: Sliding window (max 10 turns = 20 messages), oldest pair dropped when full
- **Why sliding window**: Realistic football Q&A sessions are short; oldest context is least relevant; no extra LLM summarization call needed

---

## Changes Made

### Backend

**`main.py`**: 
- Added Pydantic models `ConversationTurn` + `AskRequest`
- Updated `/api/ask/stream` endpoint to accept and forward `history` to pipeline

**`football_pipeline.py`**:
- `rewrite_query(history)`: Injects last 2 messages so normalizer resolves "he/his" to player from prior turn
- `generate_response(history)`: Injects all turns between system prompt and current retrieval-augmented message
- `run_pipeline(history)`: Threads history through both functions
- `ask(history)`: Non-streaming entry point also accepts history

**`fpl_pipeline.py`**: 
- Added `history=None` signature to `run_pipeline()` and `ask()` for interface consistency

### Frontend

**`useAsk.ts`**: 
- Added `ConversationTurn` type for type safety
- Updated `ask()` function to accept `history: ConversationTurn[] = []` and include in request body

**`App.tsx`**:
- New state: `conversationHistory` (sliding window, max 10 turns)
- Pass to `ask()` on every request
- Update in `onResult` callback with new turn + slice logic
- Clear on mode change
- **Thread UI**: Render all history entries + in-progress turn, auto-scroll to new messages
- Added `useRef` + `useEffect` for smooth scrolling to bottom

---

## Context Management Strategy

**Token Budget**:
- System prompt: ~450 tokens
- Each history turn (user): ~30-80 tokens
- Each history turn (assistant): ~80-250 tokens
- Current user message with RAG/stats: ~3,000-5,000 tokens
- GPT-4o context: 128,000 tokens (safe working: ~40,000)

**Result**: ~200-350 tokens per turn → 30+ turns before approaching limits. Cap of 10 turns is conservative.

**Sliding Window Implementation**:
- Max `MAX_HISTORY_TURNS = 10` in `App.tsx`
- When `conversationHistory.length > 20` (10 pairs × 2), slice oldest pair
- Applied before every `ask()` call, enforced in `onResult` callback

---

## How Follow-Up Questions Work

1. **User Q1**: "Who scored in the last Liverpool game?"
2. **Answer A1**: Retrieved match reports + stats → "Liverpool beat Everton 2-1. Diaz 23', Salah 67' (pen)"
3. **User Q2**: "What about his assists?"
4. **Backend processing**:
   - `rewrite_query()` injects Q1 + A1 → expands "his" → "Salah's assists"
   - `generate_response()` has full context (Q1, A1, new query) → generates contextual answer
5. **Result**: Pronouns resolved, no ambiguity

---

## Verification Results

✅ **32 backend tests passed** — all existing tests remain valid with optional `history` param (defaults to `None`)
✅ **Frontend TypeScript compiles** — no errors, clean build
✅ **No breaking changes** — fully backward-compatible

---

## Files Modified

- `backend/api/main.py`
- `backend/retrieval/football/football_pipeline.py`
- `backend/retrieval/fpl/fpl_pipeline.py`
- `frontend/src/hooks/useAsk.ts`
- `frontend/src/App.tsx`

## Files NOT Modified (by design)

- `<<<META>>>` delimiter parsing in `generate_response`
- SSE stream format (`token`, `done`, `error`)
- `AskResult` TypeScript interface
- Classification, stats fetching, RAG retrieval, context building functions
- No new dependencies added