"""Fetch weather + build the "day context" that every other module consumes.

The day context is a plain dict so the scoring and recommendation engines
stay decoupled from the API. Runs on MicroPython (urequests) and on
desktop CPython (requests) for simulation.
"""

import json
import sys
import time

import config

MICROPYTHON = sys.implementation.name == "micropython"

try:
    import urequests as requests  # older MicroPython firmwares
except ImportError:
    import requests               # UIFlow2 and desktop both have this

# Open-Meteo WMO weather codes -> simple condition buckets
_CODE_MAP = {
    "clear":  (0, 1),
    "partly": (2,),
    "cloudy": (3,),
    "fog":    (45, 48),
    "rain":   (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82),
    "snow":   (71, 73, 75, 77, 85, 86),
    "storm":  (95, 96, 99),
}


def _condition_from_code(code):
    for name, codes in _CODE_MAP.items():
        if code in codes:
            return name
    return "cloudy"


def _parse_hhmm(iso_string):
    """'2026-07-22T05:52' -> (5, 52)"""
    t = iso_string.split("T")[1]
    h, m = t.split(":")[:2]
    return int(h), int(m)


def _fmt_12h(h, m):
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return "%d:%02d %s" % (h12, m, suffix)


def _season(month):
    if config.NORTHERN_HEMISPHERE:
        table = {12: "winter", 1: "winter", 2: "winter",
                 3: "spring", 4: "spring", 5: "spring",
                 6: "summer", 7: "summer", 8: "summer",
                 9: "autumn", 10: "autumn", 11: "autumn"}
    else:
        table = {12: "summer", 1: "summer", 2: "summer",
                 3: "autumn", 4: "autumn", 5: "autumn",
                 6: "winter", 7: "winter", 8: "winter",
                 9: "spring", 10: "spring", 11: "spring"}
    return table[month]


def moon_phase(year, month, day):
    """Approximate moon phase, 0.0=new .. 0.5=full .. ~1.0=new again.

    Simple synodic-month arithmetic; accurate to about a day, which is
    plenty for "great stargazing tonight".
    """
    if month < 3:
        year -= 1
        month += 12
    a = year // 100
    b = a // 4
    jd = (int(365.25 * (year + 4716)) + int(30.6001 * (month + 1))
          + day + (2 - a + b) - 1524.5)
    days_since_new = (jd - 2451549.5) % 29.53058867
    return days_since_new / 29.53058867


def moon_name(phase):
    if phase < 0.03 or phase > 0.97:
        return "New Moon"
    if phase < 0.22:
        return "Waxing Crescent"
    if phase < 0.28:
        return "First Quarter"
    if phase < 0.47:
        return "Waxing Gibbous"
    if phase < 0.53:
        return "Full Moon"
    if phase < 0.72:
        return "Waning Gibbous"
    if phase < 0.78:
        return "Last Quarter"
    return "Waning Crescent"


_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def fetch_raw():
    url = config.WEATHER_URL.format(
        lat=config.LATITUDE, lon=config.LONGITUDE, tz=config.TIMEZONE)
    resp = requests.get(url)
    try:
        return resp.json()
    finally:
        resp.close()


def _load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


def build_context(now=None, raw=None):
    """Return the day-context dict. `now` is a time.localtime() tuple.

    Falls back to cached weather if the network fails; raises only if
    there is no cache either.
    """
    if raw is None:
        try:
            raw = fetch_raw()
            _save_json(config.CACHE_FILE, raw)
        except Exception:
            raw = _load_json(config.CACHE_FILE)
            if raw is None:
                raise

    if now is None:
        if MICROPYTHON:
            # Device RTC runs UTC (ntptime); Open-Meteo tells us the
            # local offset for the configured location.
            now = time.localtime(time.time()
                                 + raw.get("utc_offset_seconds", 0))
        else:
            now = time.localtime()
    year, month, day, hour, minute = now[0], now[1], now[2], now[3], now[4]
    weekday = now[6]  # 0 = Monday

    cur = raw["current"]
    daily = raw["daily"]

    sr_h, sr_m = _parse_hhmm(daily["sunrise"][0])
    ss_h, ss_m = _parse_hhmm(daily["sunset"][0])

    rain_prob = daily["precipitation_probability_max"][0]
    if rain_prob is None:
        rain_prob = 0

    phase = moon_phase(year, month, day)

    ctx = {
        # weather
        "temp": cur["temperature_2m"],
        "feels_like": cur["apparent_temperature"],
        "humidity": cur["relative_humidity_2m"],
        "cloud_cover": cur["cloud_cover"],
        "wind": cur["wind_speed_10m"],
        "precip_now": cur["precipitation"],
        "rain_prob": rain_prob,
        "condition": _condition_from_code(cur["weather_code"]),
        "high": daily["temperature_2m_max"][0],
        "low": daily["temperature_2m_min"][0],
        # sun
        "sunrise": _fmt_12h(sr_h, sr_m),
        "sunset": _fmt_12h(ss_h, ss_m),
        "sunrise_minutes": sr_h * 60 + sr_m,
        "sunset_minutes": ss_h * 60 + ss_m,
        "now_minutes": hour * 60 + minute,
        # calendar
        "year": year, "month": month, "day": day, "hour": hour,
        "weekday": weekday,
        "weekday_name": _WEEKDAYS[weekday],
        "month_name": _MONTHS[month - 1],
        "is_weekend": weekday >= 5,
        "season": _season(month),
        # moon
        "moon_phase": phase,
        "moon_name": moon_name(phase),
        # set True by main.py during night-watch renders
        "is_night_watch": False,
    }

    # Tomorrow's outlook (for useful night messages)
    if len(daily["temperature_2m_max"]) > 1:
        t_rain = daily["precipitation_probability_max"][1]
        ctx["tomorrow"] = {
            "high": daily["temperature_2m_max"][1],
            "low": daily["temperature_2m_min"][1],
            "rain_prob": t_rain if t_rain is not None else 0,
            "condition": _condition_from_code(daily["weather_code"][1]),
        }

    _apply_memory(ctx)
    return ctx


def _apply_memory(ctx):
    """Stateful "first time this year" facts, remembered across wakes."""
    state = _load_json(config.STATE_FILE) or {}
    dirty = False

    # Snow seasons span new year; key them by the year they start in.
    season_year = ctx["year"] if ctx["month"] >= 7 else ctx["year"] - 1
    snow_key = "first_snow_%d" % season_year

    ctx["is_first_snow"] = False
    if ctx["condition"] == "snow" and not state.get(snow_key):
        state[snow_key] = "%d-%d" % (ctx["month"], ctx["day"])
        ctx["is_first_snow"] = True
        dirty = True

    # First genuinely warm day of the calendar year (spring only, so a
    # January freak doesn't spend it early).
    warm_key = "first_warm_%d" % ctx["year"]
    ctx["is_first_warm_day"] = False
    if (ctx["temp"] >= 68 and ctx["month"] in (2, 3, 4, 5)
            and not state.get(warm_key)):
        state[warm_key] = "%d-%d" % (ctx["month"], ctx["day"])
        ctx["is_first_warm_day"] = True
        dirty = True

    if dirty:
        _save_json(config.STATE_FILE, state)
