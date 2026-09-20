"""Pure, UTC-based update slots. No hardware, files or network access."""
import time

EARLY_SECONDS = 300


def _date(day):
    t = time.gmtime(day * 86400)
    return "%04d-%02d-%02d" % (t[0], t[1], t[2])


def _minutes(value):
    h, m = value.split("T")[1].split(":")[:2]
    return int(h) * 60 + int(m)


def solar_minutes(raw, day):
    """Use this date's cached solar data; otherwise a fixed 07:00–19:00 day."""
    daily = (raw or {}).get("daily", {})
    try:
        index = daily["time"].index(_date(day))
        rise = _minutes(daily["sunrise"][index])
        setting = _minutes(daily["sunset"][index])
        if 60 <= setting - rise <= 1380:
            return rise, setting
    except (KeyError, ValueError, IndexError, TypeError, AttributeError):
        pass
    return 420, 1140


def slots(now, raw=None, mode="fridge", interval=60):
    offset = int((raw or {}).get("utc_offset_seconds", 0))
    day = int((now + offset) // 86400)
    result = []
    for d in range(day - 2, day + 3):
        midnight = d * 86400 - offset
        if mode == "plugged":
            for minute in range(0, 1440, interval):
                result.append(("%s-p%d" % (_date(d), minute),
                               midnight + minute * 60, minute < 300 or minute >= 1380))
            continue
        rise, setting = solar_minutes(raw, d)
        start, end = rise + 15, setting - 15
        for i in range(5):
            minute = start + (end - start) * i // 4
            result.append(("%s-d%d" % (_date(d), i), midnight + minute * 60, False))
        tomorrow_rise, _ = solar_minutes(raw, d + 1)
        night = 1440 + tomorrow_rise - setting
        for i in (1, 2):
            minute = setting + night * i // 3
            result.append(("%s-n%d" % (_date(d), i), midnight + minute * 60, True))
    return sorted(result, key=lambda s: s[1])


def choose(now, raw=None, mode="fridge", interval=60, attempted=()):
    """Coalesce overdue work, accept early wake once, and return next future slot."""
    schedule = slots(now, raw, mode, interval)
    past = [s for s in schedule if s[1] <= now + EARLY_SECONDS]
    latest = past[-1] if past else None
    due = latest if latest and latest[0] not in attempted else None
    future = next(s for s in schedule if s[1] > now + EARLY_SECONDS)
    return due, future
