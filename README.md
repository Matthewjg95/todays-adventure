# Today's Adventure

An ambient e-ink companion for the M5Stack M5Paper v1.1 that quietly
answers one question: **"What is worth noticing, appreciating, or
enjoying today?"**

Not a weather station. Weather data is only context — the product is
the *wonder*: one warm, human sentence about what makes today worth
noticing, over an illustrated landscape that changes with the sky.
There are no bad days and there is no score; every day has a reason
to be beautiful. Fridge mode schedules five daylight updates and two
night updates; an explicit plugged-in preference supports more frequent updates.

The screen, top to bottom: an agent-drawn landscape scene for the
current weather (with the date floating in its sky), a headline, the
temperature and how it compares to yesterday, the wonder sentence,
up to three gentle suggestions, and a dotted horizon arc showing the
sun's real position (the moon phase takes over at night). Around
two points through the night it wakes for "night watch": quiet messages, some
playful, some genuinely useful — an umbrella warning built from
tomorrow's forecast, a frost alert for the plants.

Press the side wheel and the display flips to a facts flashcard
(temperature, humidity, wind, sun times, moon, tomorrow, battery)
for a minute, then returns on its own.

## Architecture

| Module | Responsibility |
|---|---|
| `config.py` | Location, cadence, quiet hours, scene set — the knobs |
| `wifi_secrets.py` | WiFi credentials (gitignored; copy the `.example`) |
| `weather_service.py` | Open-Meteo fetch (free, no key) → one "day context" dict; caching, moon phase, yesterday's memory, first-snow/first-warm-day state |
| `scoring_engine.py` | Headlines (an internal ease-number routes them; it is never displayed) |
| `recommendation_engine.py` | Rule engine → up to 3 suggestions, time-of-day aware, with concept-dedup against the headline and wonder |
| `wonder_engine.py` | The centerpiece sentence: ~40 wonders (meteor showers, solstices, first snow, yesterday comparisons), day/night pools, date-deterministic variants |
| `adventures.py` / `events.py` | Local destinations and calendar events; customize these for another area |
| `ota.py` | Manifest-based self-update from the configured GitHub branch |
| `artwork.py` | Vector weather glyphs (drawn over the scene art) |
| `ui_renderer.py` | Full-frame offscreen compose → ONE absolute GC16 push (the only render that survives deep-sleep wakes); scene PNG compositing; flashcard |
| `scheduler.py` | Deep sleep with panel parked and display rail cut; wake-cause detection; the only wake path that provably works on this hardware |
| `main.py` | Wake → clock → fetch → render → sleep, with watchdog, battery guards, wake log |

Reliability machinery, all earned the hard way: a 4-minute hardware
watchdog, fetch timeouts, a persistent `wake_log.txt` on flash with
battery telemetry per wake, low-battery animation cuts and a
critical-battery coast mode, and watchdog stage breadcrumbs. Current
configuration repaints each scheduled update. Historical blank-screen reports
did not establish rail-cut fading; the owner reports good retention.
Change fingerprinting remains
available, but unchanged-frame skipping is disabled. Battery endurance
and display retention still need current device measurements.

## Scene art

Landscapes are generated Python (Pillow) — every image is
reproducible from `tools/`. Three sets ship (`scenes/v1|v2|v3`,
chosen by `config.SCENE_SET`); v3 was drawn by a team of agents with
visual self-critique loops. `scenes/special/` holds the showpieces,
including a portrait recomposition of Hokusai's Great Wave.

Contract for new scenes: 540x320 grayscale, the glyph zone
(x 160–380, y 30–220) and date strip (y 0–28) stay near-white, tones
spaced ≥25 apart (the panel shows 16 gray levels — verify by
quantizing: `img.point(lambda v: (v//17)*17)`), light shapes get
dark keylines. `tools/make_sheets.py` builds all-8-at-once judging
screens.

## Setup

See [current operating modes](docs/OPERATING_MODES.md). The default is fridge
mode. An optional ignored `user_settings.json` selects plugged-in mode and its
interval without being replaced by OTA. Automatic charger detection does not
select the schedule, and plugging in no longer replaces the main screen with art.

Use the [complete build guide](docs/BUILD_GUIDE.md) for dependencies,
configuration, directory creation, all runtime modules, scene uploads,
and the OTA release procedure. Customize the local destination/event
catalogs as well as the coordinates. OTA currently follows upstream
`master` and can replace `config.py`; use your own fork for an
independent personalized installation.

1. Flash UIFlow2.0 firmware (tested: v2.4.9) with
   [M5Burner](https://docs.m5stack.com/en/download).
2. Edit `config.py` (lat/long/timezone); copy
   `wifi_secrets.example.py` → `wifi_secrets.py` and fill it in.
3. Deploy with the bundled uploader (**standard `mpremote` cannot
   talk to this firmware** — its startup swallows the interrupt):

   ```bash
   python tools/m5link.py put main.py /flash/main.py config.py /flash/config.py wifi_secrets.py /flash/wifi_secrets.py scheduler.py /flash/scheduler.py ui_renderer.py /flash/ui_renderer.py weather_service.py /flash/weather_service.py scoring_engine.py /flash/scoring_engine.py recommendation_engine.py /flash/recommendation_engine.py wonder_engine.py /flash/wonder_engine.py adventures.py /flash/adventures.py events.py /flash/events.py artwork.py /flash/artwork.py ota.py /flash/ota.py boot_device.py /flash/boot.py
   ```

   Create the directories and upload the active scene set to
   `/flash/scenes/<set>/`, plus `/flash/scenes/special/`, then reboot.
   The build guide includes complete PowerShell commands.
   `tools/m5link.py` finds the board by USB VID (CH9102) and
   also offers `exec`, `cat` and `reset`.

## Desktop development (no hardware needed)

```bash
python -m pip install -r requirements-dev.txt
python main.py --demo      # fake perfect summer Saturday, ASCII mockup
python main.py --once      # real weather for your configured location
python -m unittest discover tests
python tools/verify_ota_manifest.py
```

Install `pyserial` for the serial uploader and `pillow-heif` for the
optional phone-photo inbox. The desktop tests use an ASCII canvas;
they do not verify physical typography, sleep current or panel retention.
GitHub Actions runs tests, the demo and committed-payload OTA checks.

## Contest and validation

- [Contest package and outstanding evidence](docs/contest/PACKAGE.md)
- [Project blog draft](docs/contest/PROJECT_BLOG.md)
- [Device validation checklist](docs/DEVICE_VALIDATION.md)
- [Current status](docs/STATUS.md)

## Extending it

- **New wonder**: append a `Wonder(...)` in `wonder_engine.py`
  (day or night pool; variants rotate deterministically by date).
- **New suggestion rule**: append a `Rule(...)` in
  `recommendation_engine.py` (priority, optional active-hours window).
- **New scene set**: generate into `scenes/<name>/` per the contract
  above and point `config.SCENE_SET` at it.

## Field notes

The hard-won hardware knowledge (why the RTC wake can't work, the
display controller's sync trap, the pad-hold footgun, battery
telemetry honesty) lives in a local, deliberately untracked
`FIELD_NOTES.md`. If you are debugging this hardware: read it first.

## Success metric

If someone walks past the display while grabbing their coffee and
smiles because of what it says, the project is successful.
