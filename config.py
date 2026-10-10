"""Today's Adventure — configuration.

Edit LATITUDE / LONGITUDE / TIMEZONE for your home, set your WiFi
credentials, and everything else should just work.
"""

# --- Location -------------------------------------------------------------
LATITUDE = 43.0481
LONGITUDE = -76.1474
TIMEZONE = "America/New_York"   # IANA name, passed to Open-Meteo
NORTHERN_HEMISPHERE = True      # flips season logic if False

# --- WiFi (device only; ignored in desktop simulation) --------------------
# Credentials live in wifi_secrets.py (gitignored); see the .example file.
try:
    from wifi_secrets import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    WIFI_SSID = "your-ssid"
    WIFI_PASSWORD = "your-password"

# --- Behavior -------------------------------------------------------------
UPDATE_INTERVAL_MINUTES = 60    # refresh cadence
USE_FAHRENHEIT = True
QUIET_START = 23                # no hourly updates from this local hour...
QUIET_END = 5                   # ...until this one (saves battery overnight)
NIGHT_WAKE_HOURS = (23, 1, 3)   # ...except these: night-watch renders
SHOW_LAST_UPDATED = False       # hide the update-time and battery footer
ALWAYS_RENDER = True            # repaint every wake. The 08-21
                                # "parked panel retains through sleep"
                                # result does NOT hold in the field:
                                # the image fades sporadically during
                                # rail-cut sleep, so a skipped refresh
                                # means a blank screen for an hour+.
                                # One GC16 flash per hour is the price.

# --- Battery survival -----------------------------------------------------
LOW_BATTERY_PCT = 20            # at/below: skip the glyph animation
CRITICAL_BATTERY_PCT = 8        # at/below: no radio at all, just coast
CRITICAL_SLEEP_MINUTES = 240    # how long to sleep while coasting
CUT_EPD_RAIL_IN_SLEEP = True    # power down the display rail during
                                # deep sleep (panel is parked first via
                                # powerSaveOn, so it should retain).
                                # UNDER TEST — flip False if the image
                                # fades between hourly renders.
BIG_TEXT = True                # experiment: every font one step bigger
GLYPH_ANIMATE_SECONDS = 0       # glyph movement after each render.
                                # 0 = one screen push per hour. The
                                # detailed scenes carry the visual
                                # interest now, and the animation was
                                # the longest awake stretch (30s of
                                # ~90s) on a 1.5-day battery.
SCENE_SET = "v3"                # which art set to draw: v1 | v2 | v3

# --- Interactive modules (side-button wake) --------------------------------
BUTTON_WAKE_ACTION = "home"     # "home": launcher + modules;
                                # "flashcard": the old 10-second facts card
HOME_HOLD_MS = 1000             # side-button hold that returns Home.
                                # Clamped to 400..1900 ms: the same
                                # button powers the board ON with a ~2 s
                                # press (M5Stack docs), so Home stays
                                # clearly shorter. See
                                # docs/INTERACTIVE_MODULES.md.
INTERACTIVE_IDLE_SECONDS = 180  # untouched this long: save, back to fridge
                                # (halved at/below LOW_BATTERY_PCT)
INTERACTIVE_EPD_MODE = 1        # page turns: 1 = GC16 (proven); 2 = text
                                # mode, less flash, unverified on panel
PAPER_PAN_FRAMES = 0            # 0 = clean stepped redraw (default);
                                # N = N fast intermediate pan frames
ROCKER_NEXT_PIN = 39            # wheel DOWN on the fridge-mounted Paper
ROCKER_BACK_PIN = 37            # wheel UP. Swapped Oct 2026 after the owner
                                # found 37/39 (M5Stack's "right/left")
                                # inverted in portrait use.
TOUCH_SWAP_XY = False           # GT911 orientation fixes, if the panel
TOUCH_FLIP_X = False            # rotation and touch disagree
TOUCH_FLIP_Y = False

# --- Daily Paper edition ----------------------------------------------------
# Built from public news feeds by tools/build_edition.py (GitHub Actions,
# .github/workflows/edition.yml) and published to the `edition` branch.
# Downloaded only at scheduled updates; None disables it (sample edition).
EDITION_URL = ("https://raw.githubusercontent.com/"
               "Matthewjg95/todays-adventure/edition/edition.json")
EDITION_MAX_AGE_HOURS = 3       # skip the download if the cached one is newer

# --- Weather API (Open-Meteo: free, no API key) ---------------------------
WEATHER_URL = (
    "http://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
    "precipitation,weather_code,cloud_cover,wind_speed_10m"
    "&daily=sunrise,sunset,precipitation_probability_max,"
    "temperature_2m_max,temperature_2m_min,weather_code"
    "&temperature_unit=fahrenheit&wind_speed_unit=mph"
    "&timezone={tz}&forecast_days=2"
)

# --- Files ----------------------------------------------------------------
STATE_FILE = "state.json"       # remembers things like "did it snow yet this year"
CACHE_FILE = "last_weather.json"

# OTA-excluded user preferences. No auto mode: charging inference is not VBUS.
POWER_MODE = "fridge"           # five daylight + two night updates
PLUGGED_INTERVAL_MINUTES = 60   # used only with an explicit plugged preference
try:
    import json as _json
    with open("user_settings.json") as _f:
        _prefs = _json.load(_f)
    if _prefs.get("power_mode") in ("fridge", "plugged"):
        POWER_MODE = _prefs["power_mode"]
    _hold = _prefs.get("home_hold_ms")
    if isinstance(_hold, int) and 400 <= _hold <= 1900:
        HOME_HOLD_MS = _hold        # survives OTA, unlike edits to this file
    _interval = _prefs.get("plugged_interval_minutes", 60)
    if isinstance(_interval, int) and _interval in (30, 60, 120, 180, 240):
        PLUGGED_INTERVAL_MINUTES = _interval
except (OSError, ValueError, TypeError, AttributeError):
    pass
