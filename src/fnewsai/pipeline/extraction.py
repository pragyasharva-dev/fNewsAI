"""Split an article into atomic, classified claims."""
from pydantic import BaseModel

from ..models import Article, Claim
from ..providers import ChatMessage, LLMProvider


class _Claims(BaseModel):
    claims: list[Claim]


def extract_claims(article: Article, llm: LLMProvider) -> list[Claim]:
    prompt = (
        "Split this news article into atomic, self-contained claims (resolve pronouns so each "
        "claim stands alone). Classify each: fact = checkable against evidence, prediction = "
        "future outcome, opinion = subjective. Skip filler and quotes of pure sentiment.\n\n"
        f"Title: {article.title}\nPublished: {article.date or 'unknown'}\n\n{article.text}"
    )
    result = llm.parse([ChatMessage(role="user", content=prompt)], schema=_Claims)
    return result.claims
