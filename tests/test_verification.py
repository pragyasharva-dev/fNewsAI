"""Verification loop tested against fake providers — no network, no API keys."""
import pytest

from fnewsai.errors import VerificationTimeoutError
from fnewsai.models import Claim
from fnewsai.pipeline.verification import verify_claim
from fnewsai.providers.base import ChatMessage, LLMResponse, ToolCall


class FakeLLM:
    """Scripted: searches once, then answers."""
    def __init__(self, turns):
        self._turns = list(turns)

    def chat(self, messages: list[ChatMessage], tools=None) -> LLMResponse:
        return self._turns.pop(0)


class FakeSearch:
    def search(self, query: str, max_results: int = 5) -> str:
        return f"result for {query}"


def test_stops_when_model_returns_text_without_tool_call():
    claim = Claim(claim="X happened", type="fact")
    llm = FakeLLM([
        LLMResponse(text=None, tool_calls=[ToolCall(id="1", name="search", arguments={"query": "X"})]),
        LLMResponse(text="Verified, confidence 0.9", tool_calls=[]),
    ])
    result = verify_claim(claim, llm, FakeSearch(), max_turns=6)
    assert result == "Verified, confidence 0.9"


def test_raises_when_turns_exhausted_without_final_answer():
    claim = Claim(claim="X happened", type="fact")
    llm = FakeLLM([
        LLMResponse(text=None, tool_calls=[ToolCall(id=str(i), name="search", arguments={"query": "X"})])
        for i in range(3)
    ])
    with pytest.raises(VerificationTimeoutError):
        verify_claim(claim, llm, FakeSearch(), max_turns=3)
