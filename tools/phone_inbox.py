"""Phone -> desktop photo pipeline.

Drop photos into OneDrive/ClaudeInbox from your phone (share sheet ->
OneDrive -> ClaudeInbox). This pulls them into the repo's inbox/,
converts iPhone HEIC to JPEG, downscales for fast reading, and keeps
an index so Claude can find "the newest photo" instantly.

Usage:
    python tools/phone_inbox.py            # ingest new items, list them
    python tools/phone_inbox.py --list     # just show what's here
    python tools/phone_inbox.py --clean    # archive processed originals
"""

import json
import os
import shutil
import sys
import time

SRC = os.path.join(os.path.expanduser("~"), "OneDrive", "ClaudeInbox")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(REPO, "inbox")
ORIG = os.path.join(DST, "originals")
INDEX = os.path.join(DST, "index.json")
MAX_EDGE = 1568          # Claude reads this size efficiently
IMG_EXT = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif")
NOTE_EXT = (".txt", ".md")


def _load_index():
    try:
        with open(INDEX) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"items": []}


def _save_index(idx):
    with open(INDEX, "w") as f:
        json.dump(idx, f, indent=2)


def _open_image(path):
    from PIL import Image
    if path.lower().endswith((".heic", ".heif")):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            raise RuntimeError(
                "HEIC needs pillow-heif: pip install pillow-heif "
                "(or set iPhone Camera > Formats > Most Compatible)")
    return Image.open(path)


def ingest():
    os.makedirs(DST, exist_ok=True)
    os.makedirs(ORIG, exist_ok=True)
    if not os.path.isdir(SRC):
        os.makedirs(SRC, exist_ok=True)
        print("Created %s — share photos there from your phone." % SRC)
        return []

    idx = _load_index()
    seen = {i["source"] for i in idx["items"]}
    added = []

    for name in sorted(os.listdir(SRC)):
        path = os.path.join(SRC, name)
        if not os.path.isfile(path) or name in seen:
            continue
        low = name.lower()
        stamp = time.strftime("%Y%m%d-%H%M%S",
                              time.localtime(os.path.getmtime(path)))

        if low.endswith(IMG_EXT):
            out_name = "%s-%s.jpg" % (stamp, os.path.splitext(name)[0])
            out_name = out_name.replace(" ", "_")
            out = os.path.join(DST, out_name)
            try:
                img = _open_image(path)
                img = img.convert("RGB")
                if max(img.size) > MAX_EDGE:
                    scale = MAX_EDGE / max(img.size)
                    img = img.resize((int(img.width * scale),
                                      int(img.height * scale)))
                img.save(out, "JPEG", quality=88)
            except Exception as e:
                print("  ! %s: %s" % (name, e))
                continue
            kind = "image"
        elif low.endswith(NOTE_EXT):
            out_name = "%s-%s" % (stamp, name.replace(" ", "_"))
            out = os.path.join(DST, out_name)
            shutil.copy2(path, out)
            kind = "note"
        else:
            continue

        shutil.copy2(path, os.path.join(ORIG, name))
        item = {"source": name, "file": os.path.basename(out),
                "kind": kind, "added": stamp}
        idx["items"].append(item)
        added.append(item)

    _save_index(idx)
    return added


def show(items=None, limit=10):
    idx = _load_index()
    items = items if items is not None else idx["items"][-limit:]
    if not items:
        print("inbox empty")
        return
    for i in items:
        print("  [%s] %s  ->  inbox/%s"
              % (i["kind"], i["added"], i["file"]))
    newest = idx["items"][-1] if idx["items"] else None
    if newest:
        print("\nnewest: inbox/%s" % newest["file"])


def clean(keep_days=30):
    cutoff = time.time() - keep_days * 86400
    n = 0
    for name in os.listdir(ORIG):
        p = os.path.join(ORIG, name)
        if os.path.getmtime(p) < cutoff:
            os.remove(p)
            n += 1
    print("removed %d archived originals older than %d days"
          % (n, keep_days))


if __name__ == "__main__":
    if "--list" in sys.argv:
        show()
    elif "--clean" in sys.argv:
        clean()
    else:
        new = ingest()
        print("ingested %d new item(s) from %s" % (len(new), SRC))
        show(new if new else None)
