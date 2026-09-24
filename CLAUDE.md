# fNewsAI

AI-powered news claim verification system, built while the user learns
agentic LLM concepts hands-on. The user is a full participant in
architecture decisions (which model, which pattern, agentic vs. fixed
pipeline) — Claude's job is to explain tradeoffs and implement what's
decided, not to pick the stack unilaterally or skip ahead of what's been
discussed.

Full architecture, current status, and what's not-yet-built: `docs/DOCUMENTATION.md`.
Keep that file in sync whenever a module lands or a decision changes — this
file is conventions/review rules only.

## Stack

- `uv` for deps/env, Python 3.11 (`uv sync`, `uv run <script>.py`)
- `groq` for LLM API (free tier) — model name is resolved at runtime via
  `groq.models.list()`, never hardcoded, since Groq deprecates model IDs
  without notice (see `agentic_verify.py::_pick_model`)
- `tavily-python` for web search (LLM-facing search API, free tier)
- `python-dotenv` for API keys — `.env` is gitignored, never commit or print
  key values
- `pydantic` for structured LLM outputs (fixed-pipeline version only)
- `requests` / `beautifulsoup4` for article ingestion from a URL
- `anthropic` — present from an earlier paid-API exploration; the active
  path is Groq + Tavily (free). Don't remove without asking.

## Conventions to enforce during review

- **YAGNI / no premature structure**: this is a learning project first.
  Don't add config layers, retry logic, or abstractions before a concrete
  need shows up in a run.
- **Ponytail-style shortcuts are fine but must be marked**: a `# ponytail:`
  comment naming the shortcut and the upgrade path — that's the expected way
  to note something deliberately simple, not a gap to fix silently.
- **Loop safety**: any agentic loop needs a `max_turns` (or equivalent) cap —
  never let the model call tools unbounded.
- **Model IDs**: never hardcode a Groq model name as the only option;
  resolve dynamically or allow a `GROQ_MODEL` env override.
- Type hints on function signatures; docstrings only where the *why* isn't
  obvious from the name.
- Don't collapse the fixed-pipeline and agentic implementations into one
  file, or delete either, without asking — the comparison between them is
  a deliberate teaching artifact (see `docs/DOCUMENTATION.md`).

## Secrets

- `.env` holds `GROQ_API_KEY` / `TAVILY_API_KEY` (and previously
  `ANTHROPIC_API_KEY`). Gitignored. Never echo key values into chat,
  commits, or logs.

## Git Commits

Follow whatever attribution lines are given in the session's system
reminder at commit time (this has varied across sessions). Don't assume a
fixed rule — check the current session's instructions before committing.

## Documentation

Keep module descriptions, architecture, comparison tables, and "what's not
yet built" in `docs/DOCUMENTATION.md`. Update it after every code change
that adds/removes a module or changes a decision — that's the file a fresh
session should read to understand where things stand, not git log.
