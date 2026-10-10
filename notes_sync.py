"""Notes upload to your own Google Drive (device side, NOT WIRED IN YET).

Nothing imports this module today: notes stay only on the Paper. To switch it
on later, follow docs/AI_PIPELINES.md ("Notes pipeline: activation"): deploy
companion/notes_apps_script, add this file to the OTA payload, set
NOTES_SYNC_URL and the token, and add the one-line hook to main.py.

Flow once enabled: during a scheduled update (Wi-Fi already up, battery
gate passed) each saved note whose `updated` time changed since its last
upload is sent as JSON (original strokes + a PNG render) to a Google Apps
Script web app you own. The script stores it in a Drive folder, asks Gemini
to transcribe and tag it, and catalogues it in a Google Sheet. Upload state
is kept in notes_sync.json; a failure leaves the note pending for the next
update, and the note on the Paper is never modified or deleted.
"""

import json
import os

import notebook

FORMAT = "ta-note-upload/1"
STATE_FILE = "notes_sync.json"
MAX_PER_WAKE = 3


# --- PNG render (Gemini reads PNG; it does not read PBM) -------------------

def _crc32(data, crc=0):
    try:
        import binascii
        return binascii.crc32(data, crc) & 0xFFFFFFFF
    except (ImportError, AttributeError):
        crc ^= 0xFFFFFFFF
        for b in data:
            crc ^= b
            for _ in range(8):
                crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
        return crc ^ 0xFFFFFFFF


def _adler32(data):
    a, b = 1, 0
    for i in range(0, len(data), 3800):         # stay below the modulo overflow
        for byte in data[i:i + 3800]:
            a += byte
            b += a
        a %= 65521
        b %= 65521
    return (b << 16) | a


def _chunk(kind, data):
    body = kind + data
    return (len(data).to_bytes(4, "big") + body
            + _crc32(body).to_bytes(4, "big"))


def rasterize_png(note, thickness=1):
    """1-bit grayscale PNG of the note (black ink on white). Uses stored
    (uncompressed) deflate blocks, so no zlib compressor is needed on the
    ESP32; about 55 KB for a full page."""
    pbm = notebook.rasterize_pbm(note, thickness)
    header_end = pbm.index(b"\n", pbm.index(b"\n") + 1) + 1
    bits = pbm[header_end:]
    w, h = note.width, note.height
    stride = (w + 7) // 8
    raw = bytearray()
    for y in range(h):
        raw.append(0)                           # filter: none
        row = bits[y * stride:(y + 1) * stride]
        raw.extend(bytes((~b) & 0xFF for b in row))   # PBM 1=ink, PNG 0=black
    z = bytearray(b"\x78\x01")
    for i in range(0, len(raw), 65535):
        block = raw[i:i + 65535]
        final = 1 if i + 65535 >= len(raw) else 0
        n = len(block)
        z.append(final)
        z.extend(n.to_bytes(2, "little"))
        z.extend((n ^ 0xFFFF).to_bytes(2, "little"))
        z.extend(block)
    z.extend(_adler32(raw).to_bytes(4, "big"))
    ihdr = (w.to_bytes(4, "big") + h.to_bytes(4, "big")
            + bytes((1, 0, 0, 0, 0)))           # 1-bit grayscale
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", bytes(z)) + _chunk(b"IEND", b""))


# --- upload state ------------------------------------------------------------

def load_state(path=STATE_FILE):
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state, path=STATE_FILE):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    try:
        os.remove(path)
    except OSError:
        pass
    os.rename(tmp, path)


def pending(store, state):
    """Saved notes whose content changed since they were last uploaded."""
    out = []
    for nid in store.list_ids():
        try:
            note = store.load(nid)
        except notebook.NotebookError:
            continue
        if note.strokes and state.get(nid) != note.updated:
            out.append(note)
    return out


def payload(note, token):
    import binascii
    png = rasterize_png(note)
    return json.dumps({
        "format": FORMAT,
        "token": token,
        "note": notebook.export_bundle(note),
        "png_base64": binascii.b2a_base64(png).decode().strip(),
    })


def _accepted(post, get, url, body):
    """Apps Script answers a POST with 302 to a one-time result URL; the
    script has already run by then. Follow it with GET to read the result."""
    status, headers, text = post(url, body)
    if status in (301, 302, 303) and get is not None:
        location = (headers or {}).get("Location") or (headers or {}).get("location")
        if location:
            status, headers, text = get(location)
    if status != 200:
        return False, "HTTP %s" % status
    try:
        reply = json.loads(text)
    except ValueError:
        return False, "reply is not JSON"
    if not reply.get("ok"):
        return False, str(reply.get("error", "rejected"))[:60]
    return True, reply.get("title", "")


def sync(store, url, token, post, get=None, state_path=STATE_FILE,
         max_notes=MAX_PER_WAKE, log=print):
    """Upload up to max_notes changed notes. Returns the number uploaded.
    Stops at the first failure so a dead link costs one request per wake."""
    state = load_state(state_path)
    sent = 0
    for note in pending(store, state)[:max_notes]:
        ok, info = _accepted(post, get, url, payload(note, token))
        if not ok:
            log("notes sync: %s not uploaded (%s)" % (note.id, info))
            break
        state[note.id] = note.updated
        save_state(state, state_path)
        sent += 1
        log("notes sync: %s uploaded %s" % (note.id, info))
    return sent


def device_post(url, body, timeout=30):
    """(status, headers, text) with urequests/requests; no redirect following."""
    try:
        import urequests as requests
    except ImportError:
        import requests
    r = requests.post(url, data=body, headers={"Content-Type": "application/json"})
    try:
        return r.status_code, getattr(r, "headers", None), r.text
    finally:
        r.close()


def device_get(url):
    try:
        import urequests as requests
    except ImportError:
        import requests
    r = requests.get(url)
    try:
        return r.status_code, getattr(r, "headers", None), r.text
    finally:
        r.close()
