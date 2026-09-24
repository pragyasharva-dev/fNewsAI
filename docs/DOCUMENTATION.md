# fNewsAI — Architecture & Status

Living doc: update this whenever a module lands or a decision changes.
`CLAUDE.md` (project root) holds conventions/review rules only — this file
holds what the system actually is and how it works.

## What this is

A claim-level news verification system. Input: a news article (URL or raw
text). Output: per-claim verdicts (Verified / Likely True / Insufficient
Evidence / Outdated / Misleading / Disputed / Likely False), each with a
confidence score, a temporal status, an explanation, and sources.

Not a whole-article real/fake classifier — an article is split into
individual claims first, and only checkable factual claims get verified;
predictions and opinions are labeled and skipped.

## Two implementations, both intentional

### 1. Fixed pipeline — `verify.py`

```
article text
   │
   ▼
extract_claims()   — one LLM call, structured output: list of {claim, type, event_date}
   │
   ▼
research()         — one search per claim, evidence gathered as free text
   │
   ▼
judge()            — one LLM call per claim: evidence + claim → structured Verdict
   │
   ▼
report()           — plain Python, formats results as Markdown
```

- You (the code) decide the step order and count in advance. The model never
  chooses to search again or skip a step.
- Written against the Anthropic API (`claude-opus-5`, with `web_search` as a
  built-in server-side tool and `output_config.format` / `messages.parse` for
  structured output). **Not yet ported** to the free Groq/Tavily stack the
  project settled on — needs either porting or an explicit decision to retire
  this file.
- Status: implemented, unrun against real API keys.

### 2. Agentic loop — `agentic_verify.py`

```
verify_claim_agentic(claim):
  messages = [system prompt with rules, user message with the claim]
  loop (max 6 turns):
    ask Groq for a response, giving it one tool: search(query)
    if model called the tool:
        run search() ourselves (Tavily), append result to messages, loop again
    else:
        model's text response is the final verdict — return it
```

- The model decides how many times to search and when it has enough
  evidence — not hardcoded by us. Observed behavior (real run, claim "India
  launched a new AI mission in 2024"): 3 search turns, progressively
  narrowing toward official sources (broad query → date-qualified query →
  source-specific query), then stopped on its own with a verdict citing two
  official sources.
- Model: resolved dynamically via `groq.models.list()` at import time (see
  `_pick_model()`), not hardcoded — Groq deprecates model IDs without notice.
  Last verified working model: `openai/gpt-oss-120b`.
- Search: Tavily (`tavily.search(query, max_results=5)`), returns
  title/url/content snippets.
- Output: free text, not yet structured/parseable.
- Status: **working end-to-end** for a single hand-entered claim.

## Comparison (why both exist)

| | Fixed pipeline (`verify.py`) | Agentic loop (`agentic_verify.py`) |
|---|---|---|
| Who decides step count | Us, in code | The model, per claim |
| Search calls per claim | Always exactly 1 | 1–6 (observed: 3), adaptive |
| Output format | Structured (Pydantic) | Free text |
| Multi-claim support | Yes (loops over extracted claims) | No — single claim only, manual input |
| LLM provider | Anthropic (paid) | Groq (free) |
| Search provider | Anthropic's built-in `web_search` tool | Tavily (separate API) |

The point of keeping both is pedagogical: seeing the same problem solved as a
hardcoded pipeline vs. a model-driven loop, before deciding which pattern (or
what combination) the real system should use.

## Not yet built

- Multi-claim extraction feeding the agentic loop (currently one claim,
  typed in by hand)
- Structured/parseable output from the agentic loop (currently free text)
- A second tool for temporal reasoning (e.g. "what is today's date",
  explicit event-date vs. publication-date comparison) — the fixed pipeline
  handles this by passing dates into the prompt; the agentic loop doesn't yet
  reason about time explicitly
- Report generation step for the agentic loop
- Error handling around `search()` failures (network errors, bad queries) —
  currently unhandled, will crash the loop
- Cost/token visibility per run

## Key files

- `verify.py` — fixed pipeline (Anthropic API)
- `agentic_verify.py` — agentic loop (Groq + Tavily)
- `test_verify.py` — offline test for `verify.py::extract_article` (HTML
  parsing only, no API calls)
- `.env` — API keys (gitignored)
- `pyproject.toml` / `uv.lock` — dependency management via `uv`
