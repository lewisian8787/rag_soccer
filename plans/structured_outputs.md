# Structured Outputs: Query Classification

## Scope

This document covers the use of structured outputs specifically for the `classify_query` LLM call
in `football_pipeline.py`. This is the call that decides whether a query needs RAG, stats, or both.
Structured outputs are not being applied to any other LLM call in the pipeline at this time.

---

## Why `classify_query` specifically?

`classify_query` is the first real decision point in the pipeline after normalization. Its output —
a set containing `"rag"`, `"stats"`, or both — determines which data sources are queried. If this
call returns a malformed response, the entire pipeline routes incorrectly. Every subsequent step
(Pinecone retrieval, SQL tool calling, final synthesis) is downstream of this decision.

It is also the only LLM call in the pipeline that returns a structured decision rather than
free-form text. That makes it the natural and correct place to enforce a schema — the other calls
(rewrite, stats tool selection, final synthesis) either return plain strings or use tool calling,
which has its own schema enforcement built in.

---

## Background & Rationale

## What are structured outputs?

OpenAI offers two ways to get JSON back from a model:

**JSON mode** (`response_format={"type": "json_object"}`)
Guarantees the response is valid JSON. Does not enforce any schema — the model can return any keys
and values it likes. If the shape is wrong, your code either errors or silently falls back.

**Structured outputs** (`response_format={"type": "json_schema", ...}` with `strict: True`)
The model is constrained at the token level to only produce output that matches your exact schema.
Invalid keys, missing required fields, and out-of-enum values are physically impossible. No
defensive fallback needed.

---

## Why it matters for `classify_query`

`classify_query` is the routing decision for the entire pipeline. A bad classification sends the query down the wrong path — stats-only when RAG was needed, or vice versa. The consequences are a degraded or wrong answer with no visible error.

Currently the code does:

```python
data = json.loads(response.choices[0].message.content)
return set(data.get("types", ["rag"]))
```

The `.get("types", ["rag"])` fallback silently masks any model response that uses the wrong key
(e.g. `"type"` instead of `"types"`). With structured outputs and `strict: True`, that scenario
is impossible — the model cannot return a response that doesn't match the schema.

---

## The schema

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "query_classification",
    "strict": true,
    "schema": {
      "type": "object",
      "properties": {
        "types": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["rag", "stats"]
          }
        }
      },
      "required": ["types"],
      "additionalProperties": false
    }
  }
}
```

`strict: true` + `additionalProperties: false` + `required: ["types"]` means the model must return
exactly `{"types": [...]}` where the array contains only `"rag"` and/or `"stats"`. Nothing else
is possible.

---

## What changes in the code

The `response_format` argument to `openai_client.chat.completions.create` is swapped from JSON
mode to the schema above. The `json.loads()` call and the `.get()` fallback can be simplified —
the response is guaranteed to have `types` as a key containing a valid array.

---

## Model support

`gpt-4o-mini` supports structured outputs. No model change is needed.
