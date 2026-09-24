from .base import ChatMessage, LLMProvider, LLMResponse, SearchProvider, ToolCall
from .groq_llm import GroqProvider
from .tavily_search import TavilySearchProvider

__all__ = [
    "ChatMessage", "LLMProvider", "LLMResponse", "SearchProvider", "ToolCall",
    "GroqProvider", "TavilySearchProvider",
    "get_llm_provider", "get_search_provider",
]


def get_llm_provider(name: str | None = None) -> LLMProvider:
    """Factory: pick a provider by name (defaults to config). Add a branch here
    when a new LLMProvider implementation is added — nothing else needs to change."""
    from ..config import settings
    name = name or settings.llm_provider
    if name == "groq":
        return GroqProvider()
    raise ValueError(f"Unknown LLM provider: {name!r}")


def get_search_provider(name: str | None = None) -> SearchProvider:
    from ..config import settings
    name = name or settings.search_provider
    if name == "tavily":
        return TavilySearchProvider()
    raise ValueError(f"Unknown search provider: {name!r}")
