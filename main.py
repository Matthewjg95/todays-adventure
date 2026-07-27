"""Today's Adventure — entry point.

MicroPython auto-runs main.py at boot, so the device wakes, connects,
fetches, scores, renders, and powers back off — no interaction ever.

Desktop simulation:  python main.py --once      (real weather, one render)
                     python main.py --demo      (fake perfect summer day)
"""

import sys
import time

import config
import weather_service
import scoring_engine
import recommendation_engine
import wonder_engine
import ui_renderer
import scheduler

MICROPYTHON = weather_service.MICROPYTHON


def connect_wifi():
    if not MICROPYTHON:
        return
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    for _ in range(30):
        if wlan.isconnected():
            return
        time.sleep(1)
    raise OSError("WiFi connect failed")


def sync_clock():
    if not MICROPYTHON:
        return
    try:
        import ntptime
        ntptime.settime()
    except Exception:
        pass  # RTC keeps time between wakes; a failed sync is fine


def _fingerprint(ctx, score, head, activities, wonder_text):
    """What the screen would show, minus noise. Temp is bucketed to
    3 degrees so a slow drift doesn't trigger e-ink refreshes."""
    return "|".join((
        "%d-%d" % (ctx["month"], ctx["day"]),
        str(score), head, ",".join(activities), wonder_text,
        ctx["condition"],
        str(int(round(ctx["temp"] / 3.0))),
        "day" if ctx["now_minutes"] < ctx["sunset_minutes"] else "night",
        "nw%d" % ctx["hour"] if ctx.get("is_night_watch") else "",
    ))


def update_display(ctx=None, force=False, night_watch=False):
    if ctx is None:
        connect_wifi()
        sync_clock()
        ctx = weather_service.build_context()
    if night_watch:
        ctx["is_night_watch"] = True

    score = scoring_engine.score_day(ctx)
    ctx["score"] = score
    head = scoring_engine.headline(ctx, score)
    activities = recommendation_engine.recommend(ctx)
    wonder_text = wonder_engine.wonder(ctx)

    # Only touch the e-ink when something meaningful changed.
    fp = _fingerprint(ctx, score, head, activities, wonder_text)
    state = weather_service._load_json(config.STATE_FILE) or {}
    if not force and state.get("last_render") == fp:
        print("unchanged: skipping refresh")
        return ctx, score, head, activities, wonder_text
    state["last_render"] = fp

    cv = ui_renderer.make_canvas()
    ui_renderer.render(cv, ctx, score, head, activities, wonder_text)
    weather_service._save_json(config.STATE_FILE, state)
    print("rendered: %d/100 | %s | %s | %s"
          % (score, head, ", ".join(activities), wonder_text))
    return ctx, score, head, activities, wonder_text


def local_hour():
    """Best-effort local hour; None if the clock isn't trustworthy."""
    if MICROPYTHON:
        raw = weather_service._load_json(config.CACHE_FILE)
        offset = raw.get("utc_offset_seconds", 0) if raw else 0
        t = time.localtime(time.time() + offset)
    else:
        t = time.localtime()
    if t[0] < 2024:      # clock not set yet; don't trust it
        return None
    return t[3]


def is_quiet_hour(hour):
    if hour is None:
        return False
    if config.QUIET_START > config.QUIET_END:
        return hour >= config.QUIET_START or hour < config.QUIET_END
    return config.QUIET_START <= hour < config.QUIET_END


def demo_context():
    """A fake perfect summer Saturday, for testing without a network."""
    ctx = {
        "temp": 76.0, "feels_like": 75.0, "humidity": 40,
        "cloud_cover": 20, "wind": 4.0, "precip_now": 0.0,
        "rain_prob": 5, "condition": "clear",
        "high": 81.0, "low": 62.0,
        "sunrise": "5:52 AM", "sunset": "8:34 PM",
        "sunrise_minutes": 5 * 60 + 52,
        "sunset_minutes": 20 * 60 + 34, "now_minutes": 9 * 60,
        "year": 2026, "month": 7, "day": 25, "hour": 9,
        "weekday": 5, "weekday_name": "Saturday", "month_name": "July",
        "is_weekend": True, "season": "summer",
        "moon_phase": 0.9, "moon_name": "Waning Crescent",
        "is_first_snow": False, "is_night_watch": False,
        "tomorrow": {"high": 82.0, "low": 61.0, "rain_prob": 10,
                     "condition": "clear"},
    }
    return ctx


def run_forever():
    while True:
        try:
            hour = local_hour()
            if is_quiet_hour(hour):
                if hour in config.NIGHT_WAKE_HOURS:
                    update_display(night_watch=True)
                else:
                    print("quiet hours: skipping update")
            else:
                update_display()
        except Exception as e:
            # Never brick the loop: leave the last good image on the
            # e-ink (it persists unpowered) and try again next hour.
            print("update failed:", e)
        scheduler.sleep_until_next_update()


if __name__ == "__main__":
    if "--demo" in sys.argv:
        update_display(demo_context(), force=True)
    elif "--once" in sys.argv:
        update_display(force=True)
    else:
        run_forever()
