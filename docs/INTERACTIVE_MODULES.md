# Interactive modules — first prototype (October 7, 2026)

Branch `feature/modular-companion`. **Not released over OTA and not installed
on the board.** Everything below marked *desktop* was verified without hardware;
everything marked *needs hardware* has not been observed on a physical M5Paper.

## What it does

Pressing the side wheel while the Paper sleeps on the fridge now opens a
**Home launcher** instead of the 10-second facts card:

| Tile | Behavior |
|---|---|
| Today's Adventure | Leaves the session; `main.py` resumes the fridge cycle exactly as before (render from cache or the due slot, OTA check if a slot ran, deep sleep). |
| Daily Paper | A 1460 × 2380 px sample newspaper seen through a 540 × 860 window, nine-stop reading route, position map. |
| Notebook | Handwriting/sketch capture with New, Undo, Save, Clear (confirmed); stored on flash. |
| Weather Flashcard | The existing facts card from cached weather, with the update time it came from. Press refreshes. |

**Hold the side button anywhere to return Home.** Handwriting is saved and the
paper position is stored first. After `INTERACTIVE_IDLE_SECONDS` (180 s, halved
at or below `LOW_BATTERY_PCT`) without input, the session saves and resumes the
fridge cycle; a pen held on the glass never idles out.

`BUTTON_WAKE_ACTION = "flashcard"` in `config.py` restores the previous wake
behavior.

## Controls

| Input | Home | Paper | Notebook | Weather |
|---|---|---|---|---|
| Side button short press | — | next stop | save | refresh (network) |
| Side button hold (≥ `HOME_HOLD_MS`) | — | Home | save, Home | Home |
| Wheel rocked right / left (G37 / G39) | — | next / back | — | — |
| Tap | open module | right half next, left half back | toolbar; a tap in the page is a dot | — |
| Drag | — | — | ink | — |

## Side button: wiring, threshold, limitation

Evidence used (M5Stack M5Paper v1.1 documentation and this repository's code):

- The wheel's middle push is **G38** and is also the board's **power button**.
  M5Stack documents a ~2 s long press to power on; power-off is the software
  API (releasing the G2 hold) or the rear reset button. "When powered via USB,
  the device cannot be turned off." The rocker is G37 (right) / G39 (left).
- This firmware never releases G2 in normal operation: it deep-sleeps with G2
  held high (`scheduler.sleep_for`) and arms G38 as the ext0 wake source. While
  the program runs, holding G38 therefore does not change power; it is an
  ordinary active-low input.
- The stock UIFlow `boot.py` treats a button held at startup as "enter the setup
  menu". This project replaces it with `boot_device.py`; **if the stock boot.py
  is ever restored, a hold during wake can enter UIFlow setup instead.**

Design that follows from this:

- **Default hold = 1000 ms**, configurable via `config.HOME_HOLD_MS` or, to
  survive OTA, `{"home_hold_ms": 1200}` in `/flash/user_settings.json`. Values
  are clamped to **400–1900 ms** so a Home hold always stays clearly shorter than
  the documented ~2 s power-on press.
- The hold fires the moment the threshold is reached (feedback without letting
  go) and suppresses the short press on release. A release that is still
  debouncing when the threshold passes counts as a short press.
- The tracker is **disarmed until it sees the button released**: the press that
  woke the board (often still held while MicroPython boots) can never register
  as a hold or a press.
- If the board is fully off (G2 released by a rear-reset or flat cell), pressing
  the button is a power-on, not Home. That is a hardware property, not a bug.

*Needs hardware:* the actual feel of 1000 ms, whether a hold during the 2–4 s
boot is reliably ignored, and debounce adequacy for this switch.

## Input capture and refresh

`device_io.Sampler` samples G38/G37/G39 and the GT911 touch panel every 15 ms
from a `machine.Timer` into a bounded queue (512 events, overflows logged). Pen
points are appended to the note model as soon as they are drained, before any
pixel is drawn; ink is then drawn incrementally in the fastest e-ink mode, and
full frames are composed in one reused 540 × 960 buffer.

**Limitation:** ESP32 MicroPython timer callbacks are *soft*; they run between
bytecodes. While one long C call blocks (a full-frame push, a socket read during
weather refresh), sampling pauses and resumes afterwards. Strokes in progress are
not discarded by a redraw, but a contact made and lifted entirely within one
blocking call can be missed, and point density drops during it. The Weather
refresh polls for a Home hold while connecting; the HTTP read itself blocks for up
to 30 s. *Needs hardware:* measure push duration and stroke continuity.

Touch orientation flags (`TOUCH_SWAP_XY`, `TOUCH_FLIP_X/Y`) and rocker pins are
in `config.py` in case the panel disagrees with the portrait rotation.

## Daily Paper

- One fixed layout (`newspaper.build_edition`): masthead band across the full
  width, then a 3 × 3 grid of article cells. Block positions never depend on
  content (tested).
- The route is serpentine: front page → engineering → project desk ↓ adventure &
  weather → engineering (continued) → notes ↓ waiting & later → field sketch →
  about. Every step shares an overlap band (80 px sideways, 100 px down), so the
  edge of the previous article and the head of the next stay visible.
- Only blocks intersecting the window are typeset and drawn; nothing paper-sized
  is allocated. A minimap in the bottom bar shows the window's position.
- Position persists in `app_state.json` on every turn and survives restarts;
  corrupt values are clamped back onto the route.
- `PAPER_PAN_FRAMES = 0` (default) gives a clean stepped redraw. Setting it to N
  draws N fastest-mode intermediate frames; this is *unverified on the panel*
  and likely to cost latency and ghosting.
- Content is a labelled **sample edition**. Priorities and Waiting/Later read the
  task snapshot (a fixture, labelled as such). The weather panel shows only
  cached weather with its update time, or says nothing is cached.

## Daily Paper editions (real news)

```text
tools/edition_sources.json --> tools/build_edition.py --> edition.json
   (public RSS/Atom feeds)        (GitHub Actions,          on the `edition`
                                   3x daily, or any PC)     branch (data only)
                                                                 |
   Paper: scheduled update, Wi-Fi already up, battery >= 30% ----+
          -> edition.py validates, caps, caches edition.json
   Daily Paper module: reads the cache only (no network while reading)
```

- **Sources** (`tools/edition_sources.json`): NPR top stories, BBC World,
  Hacker News + NPR Technology, Syracuse.com local. Edit the file to change them;
  sections are `top`, `world`, `tech`, `local`.
- **Builder**: headline and short summary only, HTML stripped, accents folded,
  duplicates dropped across sections, at most 6 stories per section, 140-character
  titles, 320-character summaries, 32 KB total. One failing feed is skipped; if
  all fail nothing is published, so the Paper keeps its previous edition.
- **Publishing**: `.github/workflows/edition.yml` runs at about 6:17 AM,
  12:17 PM and 5:17 PM Eastern (GitHub may start scheduled runs late) and on
  demand (Actions -> Daily Paper edition -> Run workflow). It force-replaces the
  single commit on the `edition` branch; desktop CI ignores that branch.
  Scheduled workflows only run from the default branch, so this starts after
  merge to master.
- **Device**: `main._maybe_edition()` runs after a completed scheduled render,
  before the OTA check, only if the cached edition is older than
  `EDITION_MAX_AGE_HOURS` (3). Every field is validated again on the Paper; a bad,
  oversized or older download never replaces the cache. Failures are logged as
  `edition fetch failed` and do not affect the adventure screen.
  `EDITION_URL = None` disables downloads.
- **Layout**: the same fixed grid and route. Top story (lead), More top stories,
  World (lead + briefs), Technology and Local fill the news cells; priorities,
  notes, waiting/later and adventure & weather stay local. Text that does not fit
  is cut at a whole line with "..." or a whole headline; it never runs into the
  next article. The masthead says TODAY'S EDITION with its time, OLDER EDITION
  after 36 hours without a newer one, and SAMPLE EDITION when nothing has been
  downloaded yet.
- Feed text is shown as headline + summary with the source name; full stories
  remain at the source.

## Notebook storage

- `notes/nNNNN.json`, format `ta-notebook/1`: strokes in order, each with its
  wall-clock start (when the clock is valid) and `(x, y, dt_ms)` points.
- Saves check free flash (`os.statvfs`, 16 KB margin), write a temp file and
  rename it (MicroPython has no `os.replace`, so the old file is removed first;
  a crash between the two leaves a `.tmp` that is recovered on next open).
- Any failure shows an inverted message ("STORAGE FULL", "SAVE FAILED") on the
  notebook or on Home, the page stays in memory, and New refuses to discard it.
- `notebook.CompanionExporter` defines the later-phase seam: original strokes
  (`export_bundle`) plus a 1-bit PBM render (`rasterize_pbm`). No account or
  network is needed; the default sink writes two local files.

## Tasks

`tasks.TaskMaster` is the single authority; views read an immutable `Snapshot`.
IDs are stable strings; statuses are `inbox, next, active, waiting, later, done,
dropped`. `propose()` appends to `task_proposals.json` and never changes a
status. The master is `tasks_fixture.json` for now.

## Desktop verification (done)

```text
python -m unittest discover tests -v        # 151 tests
python tools/verify_ota_manifest.py --pending
python main.py --demo
python tools/preview.py [--edition edition.json]  # PNG frames into preview/
python tools/build_edition.py edition.json   # build a real edition locally
micropython tools/mp_smoke.py <repo> <empty-dir>   # optional, unix port
```

Focused tests: `tests/test_input_events.py` (press/hold separation, wake-press
disarm, debounce, threshold clamp, stroke point retention),
`tests/test_newspaper.py` (bounds, route overlap, stable layout, typography fit
with DejaVu metrics and the conservative estimate, honest empty weather),
`tests/test_companion.py` (hold to Home from every module, viewport resume across
restart, note save/reopen with order and timing, storage-full visibility, clear
confirmation, idle exit, task proposals, device loop never sleeping, button wake
order in `main.run_forever`).

`tools/preview.py` drives the real controller through the physical test sequence
and writes frames plus `sequence.png` and `paper_overview.png`; copies are in
`docs/prototype/`. They use DejaVu Sans (the firmware's font family) quantized to
16 grays. **They are not photographs of the panel.**

## Physical test sequence (needs hardware)

Preconditions: board on battery, last screen is the fridge adventure, a wake
log captured (`python tools/m5link.py cat /flash/wake_log.txt`).

1. **Launcher.** Short-press the side wheel. Expect the Home launcher within a
   few seconds. Record the time from press to visible Home. Keep holding the
   wake press for 3 s on a second try: Home must still appear and nothing else
   must happen.
2. **Newspaper.** Tap *Daily Paper*. Expect "SAMPLE EDITION – 1 OF 9". Advance
   with a short press, rock the wheel right, tap the right half; go back with the
   left rocker and a left-half tap. Check the minimap rectangle moves, the overlap
   edges are visible, and record the refresh time and any ghosting per turn.
   Stop at stop 5.
3. **Handwriting.** Hold to Home, tap *Notebook*, write a word and sketch a
   circle quickly. Check the ink follows the pen, note any missing segments,
   then tap UNDO once and redraw. Tap CLEAR and confirm KEEP leaves the page.
4. **Hold to Home.** Hold the side wheel ~1 s. Expect Home without letting go;
   the footer must not show a save error. Release: nothing further happens.
5. **Reopen note.** Tap *Notebook*: the same strokes are back. For restart
   evidence, press the rear reset, wake with the side button, open Notebook and
   confirm the note again; then open Daily Paper and confirm it returns to stop 5.
6. **Adventure fridge cycle.** Hold to Home, tap *Today's Adventure*. Expect the
   normal adventure screen and then deep sleep. Capture the wake log: it should
   show `session start`, `note n0001 saved`, `session exit: adventure`,
   `session ended (adventure); resuming fridge cycle`, and a `sleep target=...`
   line for the next scheduled slot. Confirm the next scheduled wake happens.
7. Leave a module untouched for 3 minutes: expect the same return to the fridge
   screen with `session exit: idle`.

Record photos/video and the captured log in `logs/` (ignored by Git).

## Deployment (deliberate, separate from this branch)

Nothing here updates devices. The OTA manifest on this branch still describes
release 75a870a; CI runs the verifier in `--pending` mode off master and strict
on master. Merging without regenerating the manifest changes no device, because
devices only act on a new manifest version.

**Bench install (USB, recommended for the first hardware run):** upload the new
modules alongside the existing ones (see BUILD_GUIDE step 4; the module list now
includes `input_events.py device_io.py home_app.py screens.py newspaper.py
notebook.py tasks.py session.py tasks_fixture.json`), then
`python tools/m5link.py reset`.

**OTA release (only after the bench run passes):** on master, commit the code,
run `python tools/make_ota_manifest.py`, `python tools/verify_ota_manifest.py`,
commit the manifest and push. The manifest now covers 35 payloads.

Rollback: set `BUTTON_WAKE_ACTION = "flashcard"` (or restore the previous
main.py) and publish a new manifest; the extra modules are then simply unused.
