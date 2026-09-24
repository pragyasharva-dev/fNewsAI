"""Tavily implementation of SearchProvider."""
from tavily import TavilyClient

from ..config import settings
from ..errors import ProviderError
from .base import SearchProvider


class TavilySearchProvider(SearchProvider):
    def __init__(self):
        if not settings.tavily_api_key:
            raise ProviderError("TAVILY_API_KEY is not set")
        self._client = TavilyClient(api_key=settings.tavily_api_key)

    def search(self, query: str, max_results: int = 5) -> str:
        try:
            results = self._client.search(query, max_results=max_results)["results"]
        except Exception as e:  # tavily-python raises plain Exception subclasses
            raise ProviderError(f"Tavily search failed for {query!r}: {e}") from e

        if not results:
            return "No results found."
        return "\n\n".join(f"{r['title']} ({r['url']})\n{r['content']}" for r in results)
