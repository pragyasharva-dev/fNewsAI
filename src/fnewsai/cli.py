"""Entry point: python -m fnewsai <url> | --text "..."

Wires providers (from config) into the pipeline stages. This is the only file
that knows all the stages exist — each stage only knows the provider interfaces.
"""
import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")  # ponytail: Windows cp1252 console can't print some model output

from .errors import FNewsAIError
from .models import Article
from .pipeline.extraction import extract_claims
from .pipeline.ingestion import fetch_article
from .pipeline.report import build_report
from .pipeline.verification import judge, verify_claim
from .providers import get_llm_provider, get_search_provider


def run(article: Article) -> str:
    llm = get_llm_provider()
    search = get_search_provider()

    results = []
    for claim in extract_claims(article, llm):
        verdict = None
        if claim.type == "fact":
            findings = verify_claim(claim, llm, search)
            verdict = judge(claim, findings, llm)
        results.append((claim, verdict))
    return build_report(article, results)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--text")
    args = ap.parse_args()
    if not (args.url or args.text):
        ap.error("give a URL or --text")

    try:
        article = fetch_article(args.url) if args.url else Article(title="", date=None, text=args.text)
        print(run(article))
    except FNewsAIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
