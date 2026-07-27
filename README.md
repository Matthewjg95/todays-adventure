# Today's Adventure

An ambient e-ink companion for the M5Stack M5Paper v1.1 that quietly
answers one question: **"What is worth noticing, appreciating, or
enjoying today?"**

Not a weather station. Weather data is only context — the product is
the *wonder*: one warm, human sentence about what makes today worth
noticing. There are no bad days; rainy days are different days. The
display updates itself every hour and never asks for a tap.

Design philosophy: facts first, wonder second, gratitude always.
Delight per glance. Zero guilt.

```
        SATURDAY, JULY 25

              99/100
         GO MAKE A MEMORY

           (weather art)
               76°

    ------------------------
     Only a few days each
       year are this nice.
    ------------------------

           Sunset Walk
       Stargazing Tonight
           Eat Outside

          SUNSET 8:34 PM
```

## Architecture

| Module | Responsibility |
|---|---|
| `config.py` | Location, WiFi, update cadence — the only file you must edit |
| `weather_service.py` | Open-Meteo fetch (free, no API key) → one "day context" dict; caches last good response; moon phase; first-snow memory |
| `scoring_engine.py` | Deterministic 1–100 day score + celebratory headline |
| `recommendation_engine.py` | Rule engine: context → up to 3 gentle suggestions |
| `wonder_engine.py` | Finds the one thing worth noticing today and says it like a human (the display's centerpiece) |
| `artwork.py` | Line-art weather glyphs drawn with primitives |
| `ui_renderer.py` | 540×960 portrait layout; M5Paper canvas + desktop text-mockup backends |
| `scheduler.py` | Hourly wake: RTC power-off → deep sleep → sleep-loop fallback |
| `main.py` | Boot → WiFi → fetch → score → render → sleep |

Everything downstream of `weather_service` consumes a plain dict, so the
engines are testable on a desktop with no hardware and no network.

## Setup

1. Edit `config.py`: set `LATITUDE`, `LONGITUDE`, `TIMEZONE`.
   Copy `wifi_secrets.example.py` to `wifi_secrets.py` and fill in
   your WiFi credentials (that file is gitignored).
2. Flash the M5Paper with UIFlow (MicroPython) firmware using
   [M5Burner](https://docs.m5stack.com/en/download).
3. Copy all `.py` files to the device filesystem (Thonny, `mpremote`,
   or `ampy`):
   ```
   mpremote cp config.py wifi_secrets.py weather_service.py scoring_engine.py recommendation_engine.py wonder_engine.py artwork.py ui_renderer.py scheduler.py main.py :
   ```
4. Reboot. MicroPython auto-runs `main.py`; the device fetches, renders,
   then powers itself off and lets the RTC wake it on the next hour.
   The e-ink image persists at zero power, so battery life is measured
   in weeks-to-months, not days.

## Desktop simulation (no hardware needed)

```bash
python main.py --demo     # fake perfect summer Saturday
python main.py --once     # real weather for your configured location
```

Requires `pip install requests` on desktop; on-device it uses the
built-in `urequests`.

## Extending it

- **New wonder** (the centerpiece sentence): append one `Wonder(...)`
  to `WONDERS` in `wonder_engine.py`. Highest matching priority wins;
  message variants rotate deterministically by date. Tone rules: warm,
  curious, never preachy, never guilt.
- **New activity rule**: append one `Rule(...)` to `RULES` in
  `recommendation_engine.py`. Higher `priority` places its activities
  first.
- **New headline**: add a `(predicate, text)` pair in
  `scoring_engine._headline_rules()` — first match wins.
- **New glyph**: add a draw function to `artwork.GLYPHS`.

## Design notes

- One full e-ink refresh per hour (clears ghosting; the flash is a
  non-issue at that cadence). Partial refresh is deliberately deferred
  to V2 — at 60-minute updates it buys nothing.
- Network failure never blanks the screen: the last good weather is
  cached, and the last rendered image persists on e-ink regardless.
- The score has a floor — no day is a zero. Every day is good for
  *something*.
