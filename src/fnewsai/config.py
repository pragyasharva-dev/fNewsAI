"""Central settings. One place to change a model name, a turn cap, a provider choice.

Values come from environment variables (loaded from .env), with defaults here.
Nothing else in the codebase should call os.getenv directly for these.
"""
from dataclasses import dataclass, field
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq"))
    search_provider: str = field(default_factory=lambda: os.getenv("SEARCH_PROVIDER", "tavily"))

    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    groq_model: str | None = field(default_factory=lambda: os.getenv("GROQ_MODEL"))  # None = auto-pick

    tavily_api_key: str | None = field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))
    tavily_max_results: int = field(default_factory=lambda: int(os.getenv("TAVILY_MAX_RESULTS", "5")))

    max_search_turns: int = field(default_factory=lambda: int(os.getenv("MAX_SEARCH_TURNS", "6")))


settings = Settings()
