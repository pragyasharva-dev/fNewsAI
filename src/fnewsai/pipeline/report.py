"""Format results as Markdown. Plain Python, no LLM call."""
from ..models import Article, Claim, Verdict


def build_report(article: Article, results: list[tuple[Claim, Verdict | None]]) -> str:
    out = [f"# Verification report: {article.title or 'Untitled'}",
           f"Published: {article.date or 'unknown'}\n"]
    for i, (claim, verdict) in enumerate(results, 1):
        out.append(f"## {i}. {claim.claim}\nType: {claim.type}")
        if verdict is None:
            out.append(f"Verdict: Not checked ({claim.type}s can't be fact-checked)\n")
            continue
        out.append(f"Verdict: **{verdict.verdict}** ({verdict.confidence:.0%}) | Temporal: {verdict.temporal_status}")
        out.append(f"Reason: {verdict.explanation}")
        out += [f"- source: {s}" for s in verdict.sources]
        out.append("")
    return "\n".join(out)
