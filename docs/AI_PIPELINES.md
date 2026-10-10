# AI pipelines: Gemini editions and notes catalogue

Status on October 10, 2026: **both are built, tested on the desktop and switched
off.** The Daily Paper runs on plain feed editions twice a day, and notes stay
only on the Paper. Nothing here has run against the real Gemini API, Google
Drive or Sheets.

## 1. Gemini editing of the Daily Paper (off)

```text
feeds -> build_edition.py -> [gemini_editor.py, only if switched on] -> edition.json
```

What Gemini may do: choose and order stories within each section, using the
story IDs it was given, and write a one- or two-sentence summary from the feed's
own text. Headlines stay exactly as the outlet wrote them, and stories cannot be
invented or moved between sections. Each Gemini summary ends with
"(Summary: Gemini)", which the current firmware already displays. If Gemini
errors, times out, returns bad JSON or unknown IDs, the edition is published from
the feeds as today. That fallback works section by section, so one bad section
does not discard the rest.

Cost: two requests a day on the free tier. The news is public, so free-tier data
use is not a concern here.

### Turning it on (when you are ready)

1. Create an API key at Google AI Studio (aistudio.google.com) in a project
   you keep for this.
2. GitHub -> repository Settings -> Secrets and variables -> Actions:
   - **Secret** `GEMINI_API_KEY` = the key.
   - **Variable** `GEMINI_EDITION` = `on`.
   - Optional **variable** `GEMINI_MODEL` = a current free-tier text model
     (code default `gemini-2.5-flash`; check AI Studio's model list, names
     change).
3. Actions -> "Daily Paper edition" -> Run workflow, then read the log for
   `gemini: edition edited with ...` or `gemini: skipped (...)`.

To turn it off, set `GEMINI_EDITION` to anything else or delete it. No firmware
change is involved either way.

Desktop trial: `GEMINI_API_KEY=... python tools/build_edition.py out.json --gemini`.

## 2. Notes pipeline (built, not wired)

```text
Paper (scheduled update, Wi-Fi up)                Your Google account
notes/nNNNN.json --notes_sync.py--> POST JSON --> Apps Script web app (Code.gs)
  strokes + PNG render (54 KB)       + token        |- Drive folder: nNNNN.png, nNNNN.strokes.json
  only notes changed since                          |- Gemini (free key): transcript, title,
  last upload; max 3 per wake                       |    tags, kind, proposed tasks (text only)
                                                    '- Sheet "notes": one catalogue row per note
                                     GET ?token= <-- catalogue JSON (for a future
                                                     "Your notes" Paper section)
```

Today: notes are saved only in `/flash/notes/` on the Paper. `notes_sync.py`
exists in the repository, but nothing imports it, it is not in the OTA payload,
and `main.py` has no hook (a test enforces all three).

Design points:

- The note on the Paper is never modified or deleted by syncing.
  `notes_sync.json` records the `updated` time last uploaded per note; an edited
  note uploads again.
- Upload happens only in the scheduled-update window, after the render, under the
  same battery gate as OTA. It stops at the first failure, so a dead link costs one
  request per wake.
- The Apps Script stores the files before calling Gemini. A transcription failure
  never loses a note; `retryPending()` can retry on a timer.
- The token is a shared secret checked in constant time. Payloads are size-capped.
  Page content is treated as text to transcribe, never as instructions.
- Proposed tasks are only listed in the Sheet. They never change a task's status
  (the task master rule still holds).
- **Not to GitHub:** this repository is public, so notes must never go here.
- **Free-tier privacy:** Google's terms allow free-tier prompts and outputs,
  including these handwriting images, to be used to improve its products. A
  billed project avoids that at a cost of pennies at this volume.

### Activation (later)

Google side (about 15 minutes):

1. Create a Drive folder and a Google Sheet; copy their IDs from the URLs.
2. script.google.com -> New project -> paste `companion/notes_apps_script/Code.gs`.
3. Project Settings -> Script properties: `NOTES_TOKEN` (a long random string),
   `FOLDER_ID`, `SHEET_ID`, `GEMINI_API_KEY`, optional `GEMINI_MODEL`.
4. Deploy -> New deployment -> Web app; Execute as **me**; Who has access
   **Anyone** (the token is the gate). Authorize, then copy the `/exec` URL.
5. Optional: Triggers -> add `retryPending`, time-driven, hourly.

Paper side (a firmware release):

1. Add `"notes_sync.py": "notes_sync.py"` to `DEVICE_FILES` in
   `tools/make_ota_manifest.py`, and `notes_sync` to the module list in
   `tools/m5link.py`.
2. In `config.py`: `NOTES_SYNC_URL = "<the /exec URL>"`; put
   `NOTES_SYNC_TOKEN = "<token>"` in the gitignored `wifi_secrets.py` (never
   commit it; config imports from there like the Wi-Fi password).
3. In `main.scheduled_cycle`, right after `_maybe_edition()`, add
   `_maybe_notes_sync()`, gated like `_maybe_edition`:

   ```python
   import notes_sync, notebook
   notes_sync.sync(notebook.NotebookStore(), config.NOTES_SYNC_URL,
                   config.NOTES_SYNC_TOKEN, notes_sync.device_post,
                   notes_sync.device_get, log=log_wake)
   ```

   Add a test like `test_fetched_on_completed_slot_before_ota`, then release
   as usual.
4. *Needs hardware:* whether UIFlow's `requests` exposes the 302 `Location`
   header (Apps Script answers POST with a redirect to the result); the upload
   duration of about 75 KB on battery; watchdog margin.

Tests: `tests/test_ai_pipelines.py` covers the Gemini merge rules and fallbacks
(with a fake API), the workflow gate, the PNG (decoded with Pillow, ink at the
right pixels), changed-only uploads, the redirect, stop-on-failure, and that
nothing is wired in. The PNG encoder also runs under MicroPython 1.24.1.
`Code.gs` passes a JavaScript syntax check only; it has not run in Apps Script.
