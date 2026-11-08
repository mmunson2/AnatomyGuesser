"""Fetch a source page as plain text (cached) and grep it, to check a clue's
facts against the page it cites.

    tools/page.py URL [REGEX ...]        print matches with context, or the
                                         cache path and size with no REGEX
    tools/page.py -q QUESTION_ID [REGEX ...]   the page question QUESTION_ID cites

Pages are cached as text in <data>/pages/ (see tools/paths.py); delete a
file to refetch it. Regexes are case-insensitive.
"""

import html
import re
import sys
import urllib.request
from html.parser import HTMLParser

from paths import PAGES, ROOT

CONTEXT = 200
MIN_CHARS = 1500  # shorter than this, the page was blocked
CONSTANTS = {"OPENSTAX": "https://openstax.org/books/anatomy-and-physiology-2e/pages/",
             "WIKI": "https://en.wikipedia.org/wiki/"}


class Text(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "noscript", "svg"}
    BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "tr", "br", "section", "figcaption", "td"}

    def __init__(self):
        super().__init__()
        self.out, self.skipping = [], 0

    def handle_starttag(self, tag, attrs):
        self.skipping += tag in self.SKIP
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        self.skipping -= tag in self.SKIP and self.skipping > 0

    def handle_data(self, data):
        if not self.skipping:
            self.out.append(data)


def text_of(url):
    PAGES.mkdir(parents=True, exist_ok=True)
    path = PAGES / (re.sub(r"[^A-Za-z0-9]+", "_", url.split("://", 1)[-1]).strip("_")[:150] + ".txt")
    if not path.exists():
        text = strip(fetch(url))
        if len(text) < MIN_CHARS:
            # PubMed and some others answer scripts with a cookie wall or 403,
            # headless Chrome included. Not cached, so a retry refetches.
            sys.exit(f"{url}: only {len(text)} chars, probably blocked: {text[:120]!r}\n"
                     "Read it with WebFetch instead, or cite a fetchable page.")
        path.write_text(f"{url}\n\n{text}\n")
    return path, path.read_text()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AnatomyGuesser fact check)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


def strip(raw):
    parser = Text()
    parser.feed(raw)
    text = html.unescape("".join(parser.out))
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def question_url(qid):
    src = (ROOT / "i18n" / "questions.en.js").read_text()
    m = re.search(r"id: '" + re.escape(qid) + r"'.*?(?:url: ([^\n]+?),\n|prompt:)", src, re.S)
    if not m or not m.group(1):
        sys.exit(f"{qid}: no such question, or it has no url")
    expr = m.group(1)
    for name, value in CONSTANTS.items():
        expr = re.sub(rf"\b{name} \+ ", f"'{value}' + ", expr)
    return "".join(re.findall(r"'([^']*)'", expr))


def main(args):
    if not args:
        sys.exit(__doc__)
    if args[0] == "-q":
        url, patterns = question_url(args[1]), args[2:]
    else:
        url, patterns = args[0], args[1:]
    path, text = text_of(url)
    if not patterns:
        print(f"{path} ({len(text)} chars)")
        return
    flat = text.replace("\n", " ")
    for pattern in patterns:
        hits = list(re.finditer(pattern, flat, re.I))
        print(f"== {pattern}: {len(hits)} matches in {url}")
        for m in hits[:6]:
            print("  …" + flat[max(0, m.start() - CONTEXT):m.end() + CONTEXT] + "…")


if __name__ == "__main__":
    main(sys.argv[1:])
