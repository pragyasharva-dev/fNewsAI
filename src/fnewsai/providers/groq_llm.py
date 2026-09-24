"""Groq implementation of LLMProvider."""
import json

from groq import Groq, GroqError
from pydantic import BaseModel

from ..config import settings
from ..errors import ProviderError
from .base import ChatMessage, LLMProvider, LLMResponse, ToolCall

# ponytail: names Groq is likely to have live, tried in order before falling back
# to a keyword scan of the account's model list. Groq deprecates IDs without
# notice, so nothing here is guaranteed — override with GROQ_MODEL if this drifts.
_PREFERRED_MODELS = ("llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b")
_EXCLUDE_KEYWORDS = ("whisper", "guard", "prompt", "orpheus", "tts")


class GroqProvider(LLMProvider):
    def __init__(self):
        if not settings.groq_api_key:
            raise ProviderError("GROQ_API_KEY is not set")
        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model or self._pick_model()

    def _pick_model(self) -> str:
        try:
            ids = {m.id for m in self._client.models.list().data}
        except GroqError as e:
            raise ProviderError(f"Could not list Groq models: {e}") from e
        for preferred in _PREFERRED_MODELS:
            if preferred in ids:
                return preferred
        candidates = [i for i in ids if not any(kw in i for kw in _EXCLUDE_KEYWORDS)]
        if not candidates:
            raise ProviderError("No usable chat model found on this Groq account")
        return candidates[0]

    def _to_wire(self, messages: list[ChatMessage]) -> list[dict]:
        wire = []
        for m in messages:
            entry: dict = {"role": m.role}
            if m.content is not None:
                entry["content"] = m.content
            if m.role == "tool":
                entry["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                entry["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                    for tc in m.tool_calls
                ]
            wire.append(entry)
        return wire

    def chat(self, messages: list[ChatMessage], tools: list[dict] | None = None) -> LLMResponse:
        try:
            resp = self._client.chat.completions.create(
                model=self._model, messages=self._to_wire(messages), tools=tools or None,
            )
        except GroqError as e:
            raise ProviderError(f"Groq chat call failed: {e}") from e

        msg = resp.choices[0].message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
            for tc in (msg.tool_calls or [])
        ]
        return LLMResponse(text=msg.content, tool_calls=tool_calls)

    def parse(self, messages: list[ChatMessage], schema: type[BaseModel]) -> BaseModel:
        wire = self._to_wire(messages)
        wire[0]["content"] += (
            f"\n\nRespond with ONLY a JSON object matching this schema, no other text:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        try:
            resp = self._client.chat.completions.create(
                model=self._model, messages=wire, response_format={"type": "json_object"},
            )
        except GroqError as e:
            raise ProviderError(f"Groq parse call failed: {e}") from e

        raw = resp.choices[0].message.content
        try:
            return schema.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValueError) as e:
            raise ProviderError(f"Model returned invalid JSON for {schema.__name__}: {e}\nRaw: {raw!r}") from e
