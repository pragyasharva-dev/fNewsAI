# fNewsAI — Architecture & How It Works

Living doc. Whenever code changes, this file changes in the same turn — see
`CLAUDE.md` § Documentation. `CLAUDE.md` holds conventions/review rules;
this file holds what the system *is*, why it's built this way, and how data
actually moves through it.

## How to read this repo (start here)

Read in this order — each step assumes the previous one:

1. **`CLAUDE.md`** (project root) — conventions and rules, 2 min.
2. **This file, in full**, before opening any `.py` file — it explains *why*,
   which makes the code readable on first pass instead of needing re-reads.
3. **`src/fnewsai/cli.py`** — the whole pipeline in one place (`run()`).
   Read this first among the code so you have the map before the details.
4. **`src/fnewsai/models.py`** — the three shapes (`Article`, `Claim`,
   `Verdict`) that flow between every stage. Know these before the stages.
5. **`src/fnewsai/pipeline/`, in this order**: `ingestion.py` (plain Python,
   no LLM) → `extraction.py` (first LLM call) → `verification.py` (the
   agentic loop — read `verify_claim()` slowly, it's the core mechanic) →
   `report.py` (plain Python again).
6. **`src/fnewsai/providers/base.py`** — the two contracts (`LLMProvider`,
   `SearchProvider`), read before the concrete implementations.
7. **`src/fnewsai/providers/groq_llm.py`** and **`tavily_search.py`** —
   concrete implementations. Note that `pipeline/` never imports these
   directly — only `cli.py` does, via `providers/__init__.py`'s factories.
8. **`src/fnewsai/config.py`** and **`errors.py`** — skim, supporting cast.
9. **`tests/`** — skim after step 5's `verification.py`; `test_verification.py`'s
   fake providers are a second, simpler explanation of the same loop.

Then run it and watch a real report come out before re-reading the loop:

```
uv run python -m fnewsai --text "India launched a new AI mission in 2024. It is the best decision ever."
```

Seeing real output first makes `verification.py` click faster than reading
it cold.

## What this is

Input: a news article (URL or raw text). Output: a per-claim verdict —
Verified / Likely True / Insufficient Evidence / Outdated / Misleading /
Disputed / Likely False — each with a confidence score, a temporal status,
an explanation, and sources.

Deliberately **not** a whole-article real/fake classifier. An article is
split into individual claims first (`extraction.py`), and only claims
classified as checkable facts get verified — predictions and opinions are
labeled and skipped, because no amount of searching resolves "this is the
biggest initiative in history" or "this will create 100,000 jobs by 2030."

## Why it's a package, not two scripts

Earlier in this project there were two flat scripts (`verify.py`, a
hardcoded step-by-step pipeline; `agentic_verify.py`, a single-claim
agentic loop) — kept side by side on purpose, to learn the difference
between "code decides the steps" and "the model decides the steps." Both
are retired now that the agentic pattern won that comparison and the
project moved to "full modular, production-type architecture" on request.
The current package keeps the *agentic* pattern (the model still decides
how many times to search per claim) but restructures everything around it:
swappable providers, central config, typed errors, and per-module tests —
the things a script pair can't give you.

## Directory layout

```
src/fnewsai/
  config.py              Settings — see "Configuration" below
  errors.py              Typed exceptions — see "Error handling" below
  models.py              Shared data shapes (Article, Claim, Verdict)
  cli.py                 Wires providers into pipeline stages, the only file
                          that knows the whole pipeline order
  __main__.py            Lets `python -m fnewsai` find cli.main()

  providers/
    base.py               LLMProvider, SearchProvider — the abstract contracts
    groq_llm.py            Groq implementation of LLMProvider
    tavily_search.py        Tavily implementation of SearchProvider
    __init__.py            get_llm_provider() / get_search_provider() factories

  pipeline/
    ingestion.py           URL/HTML -> Article
    extraction.py           Article -> list[Claim]
    verification.py          Claim -> verdict (the agentic search loop + judge)
    report.py                results -> Markdown

tests/
  test_ingestion.py, test_verification.py, test_report.py
```

## Data flow, end to end

```
CLI (cli.py::run)
  │
  ├─ fetch_article(url)  or  Article(text=...)      [pipeline/ingestion.py]
  │     HTTP GET -> BeautifulSoup -> Article{title, date, text}
  │
  ├─ extract_claims(article, llm)                    [pipeline/extraction.py]
  │     one LLM call, structured output -> list[Claim{claim, type, event_date}]
  │
  ├─ for each Claim where type == "fact":
  │     ├─ verify_claim(claim, llm, search)           [pipeline/verification.py]
  │     │     agentic loop: model gets a `search` tool, decides how many
  │     │     times to call it, stops itself when it has enough evidence
  │     │     -> free-text findings string
  │     └─ judge(claim, findings, llm)                [pipeline/verification.py]
  │           one LLM call, structured output -> Verdict
  │
  └─ build_report(article, [(claim, verdict_or_none), ...])  [pipeline/report.py]
        plain Python string formatting, no LLM call -> Markdown report
```

Claims typed `prediction`/`opinion` skip verification entirely — they pass
through to the report as `(claim, None)`, and `report.py` prints "Not
checked" for those instead of forcing a verdict onto something
unfalsifiable.

## The provider abstraction — why it exists, not just what it is

`providers/base.py` defines two abstract base classes:

- **`LLMProvider`** — `chat()` (one turn, may return tool calls) and
  `parse()` (one turn, returns a validated Pydantic instance).
- **`SearchProvider`** — `search(query)` -> formatted evidence text.

Every file under `pipeline/` imports only these two interfaces — never
`groq`, `tavily`, or any SDK type directly. That's the actual point of the
abstraction: **swapping Groq for Anthropic, or Tavily for another search
API, means writing one new file in `providers/` and adding one line to the
factory functions in `providers/__init__.py` — nothing in `pipeline/`
changes.** This was a specific requirement when the project moved to a
"production type" architecture (the user wanted providers swappable via
config, not via editing pipeline code).

`ChatMessage` (also in `base.py`) is the provider-agnostic chat turn shape.
Each provider converts this to/from its own wire format internally — e.g.
`GroqProvider._to_wire()` builds Groq's OpenAI-style message dicts from a
list of `ChatMessage`. Pipeline code never sees Groq's wire format.

### `GroqProvider` specifics

- **Model selection is dynamic, never hardcoded.** `_pick_model()` calls
  `groq.models.list()` and tries a preferred-name list first
  (`llama-3.3-70b-versatile`, then others), falling back to a keyword scan
  that excludes non-chat models (whisper, guard, orpheus/tts). This exists
  because Groq has deprecated model IDs without notice during this
  project's own development — a hardcoded name previously 404'd mid-session.
  Override with the `GROQ_MODEL` env var to skip auto-selection.
- **`parse()`** doesn't use a dedicated structured-output API — it appends
  a "respond with ONLY JSON matching this schema" instruction to the first
  message and sets `response_format={"type": "json_object"}`, then
  validates the response against the Pydantic schema. If the model's JSON
  is malformed, this raises `ProviderError` with the raw text included,
  rather than letting a `JSONDecodeError` propagate unexplained.

### `TavilySearchProvider` specifics

Thin wrapper: calls `tavily.search()`, formats results as
`"title (url)\ncontent"` blocks joined by blank lines. This exact format is
what the LLM sees as "search results" during the verification loop and
during `judge()` — if search quality looks bad, check this formatting
first, since it's the only shaping applied to raw Tavily output.

## The agentic verification loop — the core mechanic

`verification.py::verify_claim()` is deliberately not a fixed number of
search calls. The loop:

1. Send the conversation so far (system prompt + claim) to the LLM, with
   one tool available: `search(query)`.
2. If the model's response has no tool calls, its text **is** the final
   answer — return it and stop.
3. If it does call the tool, run the search ourselves (the model never
   touches the network), append the result as a `role="tool"` message, and
   go back to step 1.
4. Cap at `max_turns` (config default 6). If the model never stops calling
   the tool, raise `VerificationTimeoutError` — safer than looping forever
   or silently returning nothing.

Observed real behavior (see project history): given "India launched a new
AI mission in 2024," the model searched 3 times, each query more specific
than the last (broad → date-qualified → source-specific), then stopped on
its own once it had two independent official sources. That adaptiveness —
spending more searches on harder claims, fewer on easy ones — is the reason
this pattern was kept over the fixed one-search-per-claim pipeline it
replaced.

The `search` tool's JSON schema sets `additionalProperties: False`. This
was added after a real failure: without it, the model once called the tool
with invented extra fields (`{"cursor": 2, "id": 0}` instead of `{"query":
...}`) and Groq rejected the call with a 400. Tightening the schema is the
fix — a reminder that tool schemas need to be as strict as the arguments
you're actually prepared to receive.

`judge()` is a separate, single LLM call — takes the loop's free-text
findings plus the claim and asks for a structured `Verdict`. Kept separate
from the search loop itself so the loop's job stays "gather evidence" and
never has to also emit valid structured JSON while mid-tool-call.

## Configuration

`config.py::Settings` is the single place every tunable value is read from
— `llm_provider`, `search_provider`, model/API key names, `max_search_turns`,
`tavily_max_results`. All sourced from environment variables (via
`python-dotenv` loading `.env`) with defaults. **Nothing else in the
codebase should call `os.getenv` directly for one of these** — that would
create a second source of truth for a setting this file already owns.

## Error handling

`errors.py` defines a small exception hierarchy so callers catch
*our* errors, not provider-native ones:

- `ProviderError` — an LLM or search call failed (network, auth, rate
  limit, bad/unparseable response). Every provider method that can fail
  wraps the underlying SDK exception into this.
- `IngestionError` — fetching or parsing a source article failed.
- `VerificationTimeoutError` — the agentic loop hit `max_turns` without a
  final answer.

`cli.py::main()` catches the common base `FNewsAIError` and prints a clean
one-line message to stderr instead of a stack trace — this was verified
directly (ran with empty API keys, got `Error: GROQ_API_KEY is not set`
instead of a traceback).

## Testing approach

Tests never call real APIs — `test_verification.py` uses hand-written fake
`LLMProvider`/`SearchProvider` implementations (`FakeLLM`, `FakeSearch`)
that return scripted responses, so the loop's *control flow* (stop on
no-tool-call, raise on turn exhaustion) is verified without spending a
token or a search credit. `test_ingestion.py` tests HTML parsing directly
(no network — passes raw HTML strings). `test_report.py` checks Markdown
formatting against hand-built `Verdict`/`Claim` objects. This is why the
provider abstraction pays for itself in tests, not just in "swappability."

Run with `python -m pytest tests/ -q` (or `uv run pytest`). 5 tests, all
passing as of the last modular-rewrite commit.

## Verified working (real run, real API keys)

Input: `"India launched a new AI mission in 2024. It is the best decision
ever."` — output: claim 1 (fact) verified at 99% confidence citing
pib.gov.in and reuters.com; claim 2 (opinion) correctly marked "Not
checked." Full pipeline — ingestion, extraction, agentic search loop,
judge, report — confirmed working end to end, not just unit-tested in
isolation.

## Known rough edges / not yet built

- **Windows console encoding**: `cli.py` force-reconfigures stdout to
  UTF-8 because the default Windows `cp1252` console crashes on some
  Unicode characters models produce (hit this in a real run — a narrow
  no-break space, U+202F). Fixed with `sys.stdout.reconfigure()`, but if
  this resurfaces elsewhere, it's the same root cause.
- **Single search tool only** — no second tool for explicit temporal
  reasoning (e.g. "what is today's date"). The verification loop relies on
  the model's training-time sense of "current" plus whatever dates appear
  in search results; there's no injected ground-truth date yet.
- **No retry logic** — a transient network failure raises `ProviderError`
  and the whole claim fails; no automatic retry/backoff. Deliberately
  deferred (YAGNI) until a real run shows it's needed.
- **No cost/token tracking** — nothing in the pipeline records how many
  tokens or search calls a run actually spent.
- **Only Groq + Tavily implemented** — `anthropic` is still a listed
  dependency from before the provider abstraction existed, but there's no
  `AnthropicProvider` class yet. Adding one is the natural next test of
  whether the abstraction actually holds up to a second backend.

## Key files reference

- `src/fnewsai/cli.py` — entry point, wires providers into pipeline stages
- `src/fnewsai/config.py` — all tunables, one place
- `src/fnewsai/errors.py` — typed exceptions
- `src/fnewsai/models.py` — `Article`, `Claim`, `Verdict` (Pydantic)
- `src/fnewsai/providers/` — the swappable LLM/search backends
- `src/fnewsai/pipeline/` — the four pipeline stages
- `.env` — API keys (gitignored, never commit)
- `pyproject.toml` / `uv.lock` — dependency management via `uv`
