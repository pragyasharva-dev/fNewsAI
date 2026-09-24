"""Turn a URL or raw text into an Article."""
import requests
from bs4 import BeautifulSoup

from ..errors import IngestionError
from ..models import Article


def extract_article(html: str) -> Article:
    soup = BeautifulSoup(html, "html.parser")
    meta = lambda **kw: (tag := soup.find("meta", attrs=kw)) and tag.get("content")
    title = meta(property="og:title") or (soup.title.string.strip() if soup.title else "")
    date = meta(property="article:published_time") or meta(name="date") or (
        (t := soup.find("time")) and (t.get("datetime") or t.get_text(strip=True)))
    # ponytail: <p> text is enough for most news sites; swap in trafilatura if pages come back noisy
    text = "\n".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
    return Article(title=title or "", date=date, text=text)


def fetch_article(url: str) -> Article:
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 fNewsAI"})
        resp.raise_for_status()
    except requests.RequestException as e:
        raise IngestionError(f"Could not fetch {url}: {e}") from e
    return extract_article(resp.text)
