"""Companion: build the Daily Paper edition from public news feeds.

    python tools/build_edition.py [out.json] [--sources tools/edition_sources.json]
                                  [--gemini]   (optional; needs GEMINI_API_KEY)

Runs on a computer or on GitHub Actions (.github/workflows/edition.yml),
never on the Paper. Fetches each RSS/Atom feed in edition_sources.json,
keeps headline, short summary and source name, drops duplicates, and
writes a capped `ta-edition/1` file the Paper validates again before
use. A feed that fails is skipped and reported; the build fails only if
no section has any story, so a bad night never publishes an empty paper.
"""

import html
import json
import os
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import edition  # noqa: E402

MAX_FEED_BYTES = 3 * 1024 * 1024
_TAG = re.compile(r"<[^>]+>")
_ATOM = "{http://www.w3.org/2005/Atom}"


def strip_html(text, tags=True):
    """Tags (summaries only: titles are plain text) and entities out;
    accents folded so the Paper's ASCII-only pass keeps the letter."""
    if not text:
        return ""
    if tags:
        text = _TAG.sub(" ", text)
    text = html.unescape(text)
    text = "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))
    return " ".join(text.split())


def _child_text(node, *names):
    for name in names:
        found = node.find(name)
        if found is not None and (found.text or "").strip():
            return found.text
    return ""


def parse_feed(xml_bytes):
    """[(title, summary)] in feed order, RSS 2.0 or Atom."""
    if len(xml_bytes) > MAX_FEED_BYTES:
        raise ValueError("feed too large")
    root = ET.fromstring(xml_bytes)
    items = []
    for node in root.iter("item"):
        items.append((_child_text(node, "title"), _child_text(node, "description")))
    for node in root.iter(_ATOM + "entry"):
        items.append((_child_text(node, _ATOM + "title"),
                      _child_text(node, _ATOM + "summary", _ATOM + "content")))
    out = [(strip_html(t, tags=False), strip_html(s)) for t, s in items]
    return [(t, s) for t, s in out if t]


def _key(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def build(sources, fetch, now=None, log=print):
    now = int(time.time()) if now is None else now
    sections = {name: [] for name in edition.SECTIONS}
    seen = set()
    used = {}
    for src in sources:
        section = src.get("section")
        if section not in sections:
            log("skip %s: unknown section %r" % (src.get("name"), section))
            continue
        try:
            entries = parse_feed(fetch(src["url"]))
        except Exception as e:                          # one bad feed is not fatal
            log("skip %s: %s" % (src.get("name"), e))
            continue
        taken = 0
        for title, summary in entries:
            if taken >= src.get("max", 4) or len(sections[section]) >= edition.MAX_ITEMS:
                break
            k = _key(title)
            if not k or k in seen:
                continue
            seen.add(k)
            sections[section].append({
                "title": edition.clean_text(title, edition.MAX_TITLE),
                "summary": edition.clean_text(summary, edition.MAX_SUMMARY)
                if src.get("summary", True) else "",
                "source": edition.clean_text(src.get("name", ""), edition.MAX_SOURCE)})
            taken += 1
        if taken:
            used.setdefault(section, []).append(src.get("name", ""))
        log("%s: %d stories from %s" % (section, taken, src.get("name")))
    data = {"format": edition.FORMAT, "generated": now,
            "id": time.strftime("%Y-%m-%dT%H%MZ", time.gmtime(now)),
            "sections": {k: v for k, v in sections.items() if v},
            "sources": used}
    edition.validate(data, now)                   # same checks as the Paper
    raw = json.dumps(data, separators=(",", ":")).encode()
    if len(raw) > edition.MAX_BYTES:
        raise ValueError("edition too large: %d bytes" % len(raw))
    return data


def http_fetch(url):
    import requests
    r = requests.get(url, timeout=30, headers={
        "User-Agent": "todays-adventure-edition/1 (+https://github.com/Matthewjg95/todays-adventure)"})
    r.raise_for_status()
    if len(r.content) > MAX_FEED_BYTES:
        raise ValueError("feed too large")
    return r.content


def main(argv):
    out = "edition.json"
    src_path = os.path.join(ROOT, "tools", "edition_sources.json")
    args = list(argv)
    use_gemini = "--gemini" in args
    if use_gemini:
        args.remove("--gemini")
    if "--sources" in args:
        i = args.index("--sources")
        src_path = args[i + 1]
        del args[i:i + 2]
    if args:
        out = args[0]
    with open(src_path) as f:
        sources = json.load(f)
    data = build(sources, http_fetch)
    if use_gemini:
        key = os.environ.get("GEMINI_API_KEY", "")
        if key:
            import gemini_editor
            data = gemini_editor.edit(data, key, os.environ.get("GEMINI_MODEL") or None)
        else:
            print("gemini: no GEMINI_API_KEY; publishing the feed edition")
    with open(out, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print("edition %s: %s -> %s" % (data["id"], {k: len(v) for k, v in data["sections"].items()}, out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
