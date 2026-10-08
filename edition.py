"""Daily Paper edition: download, validate and cache (device + desktop).

A companion (tools/build_edition.py, run on a schedule by GitHub
Actions) turns public news feeds into one small JSON file and publishes
it to the repository's `edition` branch, apart from master and OTA. The
Paper downloads it only during scheduled updates, while Wi-Fi is up
anyway, and never while someone is reading.

Everything read from the file is re-validated here: unknown sections
are ignored, counts and lengths are capped and text is reduced to the
characters the panel fonts can show. A bad download never replaces a
good cached edition.
"""

import json
import os
import time

FORMAT = "ta-edition/1"
CACHE = "edition.json"
SECTIONS = ("top", "world", "tech", "local")
MAX_BYTES = 32 * 1024
MAX_ITEMS = 6
MAX_TITLE = 140
MAX_SUMMARY = 320
MAX_SOURCE = 40
STALE_SECONDS = 36 * 3600


class EditionError(ValueError):
    pass


_REPLACE = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": " - ", "…": "...", " ": " ",
    "′": "'", "″": '"', "´": "'",
}


def clean_text(value, limit):
    """Printable ASCII (plus the degree sign), collapsed spaces, capped
    at a word boundary with '...' when cut."""
    if not isinstance(value, str):
        return ""
    out = []
    for ch in value:
        ch = _REPLACE.get(ch, ch)
        for c in ch:
            o = ord(c)
            if 32 <= o < 127 or c == "\xb0":
                out.append(c)
            elif c in "\t\n\r":
                out.append(" ")
    text = " ".join("".join(out).split())
    if len(text) > limit:
        cut = text[:limit - 3]
        space = cut.rfind(" ")
        if space > limit // 2:
            cut = cut[:space]
        text = cut.rstrip(" ,;:-") + "..."
    return text


def validate(data, now=None):
    """Return a cleaned edition dict or raise EditionError."""
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise EditionError("not a %s edition" % FORMAT)
    generated = data.get("generated")
    if not isinstance(generated, int) or generated < 1700000000:
        raise EditionError("missing generation time")
    if now is not None and generated > now + 3600:
        raise EditionError("edition from the future")
    sections = data.get("sections")
    if not isinstance(sections, dict):
        raise EditionError("missing sections")
    clean = {}
    for name in SECTIONS:
        items = sections.get(name)
        if not isinstance(items, list):
            continue
        kept = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = clean_text(item.get("title"), MAX_TITLE)
            if not title:
                continue
            kept.append({"title": title,
                         "summary": clean_text(item.get("summary"), MAX_SUMMARY),
                         "source": clean_text(item.get("source"), MAX_SOURCE)})
            if len(kept) >= MAX_ITEMS:
                break
        if kept:
            clean[name] = kept
    if not clean:
        raise EditionError("edition has no stories")
    return {"format": FORMAT, "generated": generated,
            "id": clean_text(data.get("id"), 40), "sections": clean}


def is_stale(edition, now):
    return now - edition["generated"] > STALE_SECONDS


def load_cached(path=CACHE, now=None):
    """The cached edition, or None (missing or invalid: the Paper then
    shows its labelled sample edition)."""
    try:
        with open(path) as f:
            return validate(json.load(f), now)
    except (OSError, ValueError):
        return None


def _save(path, edition):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(edition, f)
    replace = getattr(os, "replace", None)
    if replace:
        replace(tmp, path)
    else:
        try:
            os.remove(path)
        except OSError:
            pass
        os.rename(tmp, path)


def needs_refresh(path=CACHE, now=None, max_age=3 * 3600):
    now = time.time() if now is None else now
    cached = load_cached(path, now)
    return cached is None or now - cached["generated"] >= max_age


def fetch_and_store(url, path=CACHE, get=None, now=None):
    """Download, validate and atomically cache. Returns the edition;
    raises (OSError / EditionError) and keeps the old cache on failure."""
    now = int(time.time()) if now is None else now
    if get is None:
        get = _http_get
    raw = get(url)
    if len(raw) > MAX_BYTES:
        raise EditionError("edition too large (%d bytes)" % len(raw))
    try:
        data = json.loads(raw)
    except ValueError:
        raise EditionError("edition is not JSON")
    edition = validate(data, now)
    cached = load_cached(path, now)
    if cached is not None and cached["generated"] >= edition["generated"]:
        return cached                      # nothing newer was published
    _save(path, edition)
    return edition


def _http_get(url, timeout=20):
    try:
        import urequests as requests
    except ImportError:
        import requests
    try:
        r = requests.get(url, timeout=timeout)
    except TypeError:
        r = requests.get(url)
    try:
        if r.status_code != 200:
            raise OSError("HTTP %d" % r.status_code)
        return r.content
    finally:
        r.close()
