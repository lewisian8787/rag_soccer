# Backend Testing Optimization Plan

**Status: IMPLEMENTED**

## Goal
Convert backend tests from manual scripts to pytest with proper fixtures, mocking, and coverage tracking.

## Current State
- 4 test files using manual `print()`/`sys.exit()` pattern
- All tests make real API calls (OpenAI, Pinecone) — slow and costly
- No unit tests for pure functions
- No coverage measurement

---

## Implementation Steps

### 1. Add pytest configuration

**File:** `backend/pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "live: tests requiring real API calls (deselect with -m 'not live')",
]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["retrieval"]
omit = ["tests/*"]
```

**File:** `backend/tests/conftest.py`
- Shared fixtures for mocking OpenAI and Pinecone clients
- Sample data fixtures (chunks, stats responses)

---

### 2. Add unit tests for pure functions

**File:** `backend/tests/test_query_helpers.py`

Test these functions without any mocking (no external calls):
- `build_context()` — formats chunks into context string
- `_build_user_message()` — builds prompt with context sections
- `RECENCY_PATTERN` — regex matching for recency language

---

### 3. Convert classifier tests to pytest

**File:** `backend/tests/test_classifier.py` (rewrite)

- Use `@pytest.mark.parametrize` for test cases
- Mock `openai_client.chat.completions.create`
- Keep existing 100+ test cases as parameterized data
- Add `@pytest.mark.live` marker for optional real API tests

---

### 4. Convert pipeline tests to pytest

**File:** `backend/tests/test_pipeline.py` (rewrite)

- Mock both OpenAI and Pinecone
- Test `retrieve()` filtering logic (MIN_SCORE, deduplication)
- Test `fetch_stats_context()` tool selection
- Test `stream_generate()` SSE output format
- Keep live integration tests with `@pytest.mark.live`

---

### 5. Convert retrieval tests to pytest

**File:** `backend/tests/test_retrieval.py` (rewrite)

- Mock Pinecone index queries
- Test date filtering logic
- Test fallback behavior (current → previous season)
- Keep live tests with `@pytest.mark.live`

---

## Files to Modify/Create

| File | Action |
|------|--------|
| `backend/pyproject.toml` | Create |
| `backend/tests/conftest.py` | Create |
| `backend/tests/test_query_helpers.py` | Create |
| `backend/tests/test_classifier.py` | Rewrite |
| `backend/tests/test_classifier_100.py` | Delete (merge into test_classifier.py) |
| `backend/tests/test_pipeline.py` | Rewrite |
| `backend/tests/test_retrieval.py` | Rewrite |

---

## Verification

1. **Install dependencies:**
   ```bash
   cd backend && pip install pytest pytest-cov
   ```

2. **Run unit tests (fast, no API calls):**
   ```bash
   pytest -m "not live"
   ```

3. **Run all tests including live:**
   ```bash
   pytest
   ```

4. **Check coverage:**
   ```bash
   pytest --cov=retrieval --cov-report=term-missing -m "not live"
   ```

---

## Notes
- Existing test case data (100+ classifier queries, 14 pipeline queries) will be preserved
- Live tests remain available for manual regression testing
- Mocked tests run in < 1 second total vs 2-5 seconds per test with real APIs
