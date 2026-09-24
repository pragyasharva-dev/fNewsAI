from fnewsai.pipeline.ingestion import extract_article

HTML = """<html><head><title>Fallback</title>
<meta property="og:title" content="India launches AI mission">
<meta property="article:published_time" content="2024-03-07T10:00:00Z"></head>
<body><nav>Menu</nav><p>India launched a new AI mission.</p><p>It will create jobs.</p></body></html>"""


def test_extracts_title_date_paragraphs():
    a = extract_article(HTML)
    assert a.title == "India launches AI mission"
    assert a.date == "2024-03-07T10:00:00Z"
    assert a.text == "India launched a new AI mission.\nIt will create jobs."


def test_falls_back_when_no_metadata():
    a = extract_article("<p>x</p>")
    assert a == extract_article("<p>x</p>")
    assert a.title == "" and a.date is None and a.text == "x"
