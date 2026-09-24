from fnewsai.models import Article, Claim, Verdict
from fnewsai.pipeline.report import build_report


def test_report_includes_claim_and_skips_unchecked():
    article = Article(title="T", date="2024-01-01", text="...")
    fact = Claim(claim="Fact claim", type="fact")
    opinion = Claim(claim="Opinion claim", type="opinion")
    verdict = Verdict(claim="Fact claim", verdict="Verified", temporal_status="Current",
                       confidence=0.9, explanation="because", sources=["http://x"])
    report = build_report(article, [(fact, verdict), (opinion, None)])
    assert "Fact claim" in report and "Verified" in report and "http://x" in report
    assert "Not checked" in report
