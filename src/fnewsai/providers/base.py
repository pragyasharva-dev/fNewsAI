"""Provider interfaces. Every LLM/search backend implements these two ABCs.
Pipeline code depends only on this file, never on a specific provider's SDK types —
that's what makes swapping Groq for Anthropic (or Tavily for another search API)
a new provider file, not a pipeline rewrite.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pydantic import BaseModel


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatMessage:
    """Provider-agnostic chat turn. Pipeline code only ever builds/reads these —
    each provider converts to/from its own wire format internally."""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str | None = None
    tool_call_id: str | None = None       # set on role="tool" messages
    tool_calls: list[ToolCall] = field(default_factory=list)  # set on role="assistant" messages that called tools


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall]


class LLMProvider(ABC):
    """A chat-capable LLM backend."""

    @abstractmethod
    def chat(self, messages: list[ChatMessage], tools: list[dict] | None = None) -> LLMResponse:
        """One turn: send the full conversation, get back text and/or tool calls.
        `tools` uses OpenAI-style function-tool dicts (the de facto common shape)."""

    @abstractmethod
    def parse(self, messages: list[ChatMessage], schema: type[BaseModel]) -> BaseModel:
        """One turn, structured output: return a validated instance of `schema`."""


class SearchProvider(ABC):
    """A web search backend."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> str:
        """Return formatted evidence text (title/url/snippet per result) for a query."""
