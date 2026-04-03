# Chunk cap token reduction test

Testing the effect of capping RAG chunks passed to the final LLM call at 8
(down from up to 20). Query: "Tell me about Newcastle's season so far"

## Before cap (20 chunks max)

| Metric | Value |
|---|---|
| Pipeline | rag + stats |
| Chunks returned | 16 |
| Prompt tokens | 4,746 |
| Completion tokens | 159 |
| Total tokens | 4,905 |
| Latency | 8.95s |
| Confidence | 8 |

## After cap (8 chunks max)

| Metric | Value |
|---|---|
| Pipeline | rag + stats |
| Chunks returned | 8 |
| Prompt tokens | 2,771 |
| Completion tokens | 244 |
| Total tokens | 3,015 |
| Latency | 8.37s |
| Confidence | 8 |

## Delta

| Metric | Before | After | Change |
|---|---|---|---|
| Chunks | 16 | 8 | −8 |
| Prompt tokens | 4,746 | 2,771 | **−1,975 (−42%)** |
| Total tokens | 4,905 | 3,015 | **−1,890 (−39%)** |
| Latency | 8.95s | 8.37s | −0.58s |
| Confidence | 8 | 8 | no change |
