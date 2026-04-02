# Code conventions

## Structure
For pipeline and hook files, organise code in the order it executes — top of file is first to run, bottom is last.
Use high-level section comments to separate stages (e.g. `# --- Step 1: Query normalisation ---`). Keep comments brief and descriptive of what the block does, not how.

This applies primarily to:
- `backend/retrieval/football/football_pipeline.py`
- `frontend/src/hooks/useAsk.ts`
- `frontend/src/App.tsx`

## Comments
One short comment per logical block. No inline comments unless the logic is genuinely non-obvious. No docstrings on straightforward functions.

## General
No abstractions for one-off operations — three similar lines of code is better than a premature helper. If something is removed, remove it fully — no commented-out code, no `_old` variables.

## Frontend
Components are display only — logic lives in hooks. Don't move business logic into components.

## Backend — adding a new stats tool
Three steps, always all three:
1. SQL function in `query_stats.py`
2. Tool definition in `stats_tools.py`
3. Entry in `FUNCTION_MAP` in `stats_tools.py`

## Commits
Commit after each meaningful change — don't batch unrelated work. Use the format we have established: short imperative subject line, one sentence body if needed, always include the co-author footer.
