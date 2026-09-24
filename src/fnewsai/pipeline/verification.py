"""Agentic verification: the model owns the search-vs-stop decision for each claim."""
import json

from ..config import settings
from ..errors import VerificationTimeoutError
from ..models import Claim, Verdict
from ..providers import ChatMessage, LLMProvider, SearchProvider, ToolCall

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search",
        "description": "Search the web for current information relevant to a claim.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The search query text."}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}

_SYSTEM_PROMPT = (
    "You verify factual claims. You have a `search` tool — use it as many times as you need "
    "to find current, reliable evidence, preferring official sources, then major outlets "
    "(Reuters, AP, BBC, The Hindu, Indian Express), then secondary sources. Establish when the "
    "claim was true and whether it's still current. When you have enough evidence, respond with "
    "plain text (no tool call): a verdict, a confidence 0-1, a temporal status, a short reason, "
    "and the source URLs you relied on."
)


def verify_claim(
    claim: Claim, llm: LLMProvider, search: SearchProvider, max_turns: int | None = None,
) -> str:
    """Runs the model-driven search loop for one claim. Returns free-text findings —
    pass this into `judge()` to get a structured Verdict."""
    max_turns = max_turns or settings.max_search_turns
    messages = [
        ChatMessage(role="system", content=_SYSTEM_PROMPT),
        ChatMessage(role="user", content=f"Claim: {claim.claim}"),
    ]

    for _ in range(max_turns):
        response = llm.chat(messages, tools=[SEARCH_TOOL])

        if not response.tool_calls:
            return response.text

        messages.append(ChatMessage(role="assistant", content=response.text, tool_calls=response.tool_calls))
        for call in response.tool_calls:
            result = search.search(call.arguments.get("query", claim.claim))
            messages.append(ChatMessage(role="tool", content=result, tool_call_id=call.id))

    raise VerificationTimeoutError(f"No final verdict for {claim.claim!r} within {max_turns} turns")


def judge(claim: Claim, findings: str, llm: LLMProvider) -> Verdict:
    """Turns free-text findings into a structured, storable Verdict."""
    prompt = (
        f"Claim: {claim.claim}\n\nResearch findings:\n{findings}\n\n"
        "Give a verdict based only on these findings. Use 'Outdated' when the claim was true "
        "but no longer is, and 'Misleading' when old information is presented as new."
    )
    verdict = llm.parse([ChatMessage(role="user", content=prompt)], schema=Verdict)
    verdict.claim = claim.claim
    return verdict
