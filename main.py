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
    """NTP-set the system clock, then mirror it into the BM8563 so the
    next cold boot has the time before WiFi is even up."""
    if not MICROPYTHON:
        return False
    try:
        import ntptime
        ntptime.settime()
    except Exception:
        return False           # external RTC may still carry us
    scheduler.rtc_set(time.gmtime())
    return True


def establish_time():
    """Make the system clock trustworthy BEFORE any decision depends
    on it. Returns the source used.

    Critical for overnight: timerSleep cuts main power, so every RTC
    wake is a cold boot with the ESP32 clock at zero. Deciding quiet
    hours or night watch from that clock silently disables both.
    """
    if not MICROPYTHON:
        return "desktop"
    if time.localtime()[0] >= 2024:
        return "system"
    stamp = scheduler.rtc_get()          # survives power-off
    if stamp:
        try:
            import machine
            machine.RTC().datetime((stamp[0], stamp[1], stamp[2], 0,
                                    stamp[3], stamp[4], stamp[5], 0))
            if time.localtime()[0] >= 2024:
                return "rtc"
        except Exception:
            pass
    try:                                  # last resort: network time
        connect_wifi()
    except Exception:
        return "none"
    return "ntp" if sync_clock() else "none"


WAKE_LOG = "wake_log.txt"
WAKE_LOG_MAX = 5000       # bytes; trimmed to the recent tail


def log_wake(msg):
    """Append one line to a flash log. On battery there is no serial,
    so this is the only record of what happened overnight."""
    if not MICROPYTHON:
        return
    try:
        t = time.localtime()
        line = "%04d-%02d-%02d %02d:%02d %s\n" % (
            t[0], t[1], t[2], t[3], t[4], msg)
        try:
            if os_size(WAKE_LOG) > WAKE_LOG_MAX:
                with open(WAKE_LOG) as f:
                    tail = f.read()[-WAKE_LOG_MAX // 2:]
                with open(WAKE_LOG, "w") as f:
                    f.write(tail)
        except OSError:
            pass
        with open(WAKE_LOG, "a") as f:
            f.write(line)
    except Exception:
        pass


def os_size(path):
    import os
    return os.stat(path)[6]


def _fingerprint(ctx, head, activities, wonder_text):
    """What the screen would show, minus noise. Temp is bucketed to
    3 degrees so a slow drift doesn't trigger e-ink refreshes."""
    return "|".join((
        "%d-%d" % (ctx["month"], ctx["day"]),
        head, ",".join(activities), wonder_text,
        ctx["condition"],
        str(int(round(ctx["temp"] / 3.0))),
        # after midnight counts as night too, not just after sunset
        "day" if ctx["sunrise_minutes"] <= ctx["now_minutes"]
        <= ctx["sunset_minutes"] else "night",
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
    wonder_text = wonder_engine.wonder(ctx)
    activities = recommendation_engine.recommend(
        ctx, avoid=head + " " + wonder_text)

    # Only touch the e-ink when something meaningful changed.
    fp = _fingerprint(ctx, head, activities, wonder_text)
    state = weather_service._load_json(config.STATE_FILE) or {}
    if not force and state.get("last_render") == fp:
        print("unchanged: skipping refresh")
        log_wake("  unchanged, no refresh")
        return ctx, score, head, activities, wonder_text
    state["last_render"] = fp

    cv = ui_renderer.make_canvas()
    ui_renderer.render(cv, ctx, head, activities, wonder_text)
    weather_service._save_json(config.STATE_FILE, state)
    print("rendered: %s | %s | %s"
          % (head, ", ".join(activities), wonder_text))

    # A few seconds of glyph motion — rain falls, rays breathe.
    secs = getattr(config, "GLYPH_ANIMATE_SECONDS", 0)
    if MICROPYTHON and secs:
        try:
            ui_renderer.animate_glyph(cv, ctx, secs)
        except Exception as e:
            print("animate failed:", e)

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
        "time_str": "9:00 AM",
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


FLASHCARD_SECONDS = 60


def show_flashcard():
    """The side button woke us: show the facts card for a minute,
    then fall through to the normal adventure render.

    Uses cached weather when possible so the card appears seconds
    after the button press — hour-old numbers are fine here, and the
    flip-back render fetches fresh data anyway."""
    try:
        raw = weather_service._load_json(config.CACHE_FILE)
        if raw is None or local_hour() is None:
            connect_wifi()
            sync_clock()
            raw = None      # build_context fetches fresh
        ctx = weather_service.build_context(raw=raw)
        ctx["score"] = scoring_engine.score_day(ctx)
        cv = ui_renderer.make_canvas()
        ui_renderer.render_facts(cv, ctx)
        print("flashcard shown")
        time.sleep(FLASHCARD_SECONDS)
    except Exception as e:
        print("flashcard failed:", e)
    # Make sure the follow-up render isn't skipped as "unchanged".
    state = weather_service._load_json(config.STATE_FILE) or {}
    state["last_render"] = None
    weather_service._save_json(config.STATE_FILE, state)


def run_forever():
    # Clock first: every battery wake is a cold boot, and the wake
    # cause, quiet hours and night watch are all decided from it.
    boot_source = establish_time()
    button_wake = MICROPYTHON and not scheduler.woke_by_timer()
    log_wake("boot (%s) [%s, clock=%s]"
             % ("button" if button_wake else "timer",
                scheduler.WAKE_DETAIL, boot_source))
    print("wake:", "button" if button_wake else "timer",
          scheduler.WAKE_DETAIL)
    if button_wake:
        show_flashcard()
    while True:
        try:
            source = establish_time()
            hour = local_hour()
            if hour is None:
                # Clock unknowable (no RTC, no WiFi). Render anyway
                # rather than sit dark all night.
                log_wake("clock unknown (%s): rendering daytime" % source)
                update_display()
            elif is_quiet_hour(hour):
                # button_wake: always flip back off the flashcard,
                # even mid-night
                if hour in config.NIGHT_WAKE_HOURS or button_wake:
                    log_wake("night watch %02d:00 (%s)" % (hour, source))
                    update_display(night_watch=True)
                else:
                    log_wake("quiet skip %02d:00 (%s)" % (hour, source))
                    print("quiet hours: skipping update")
            else:
                log_wake("update %02d:00 (%s)" % (hour, source))
                update_display()
        except Exception as e:
            # Never brick the loop: leave the last good image on the
            # e-ink (it persists unpowered) and try again next hour.
            print("update failed:", e)
            log_wake("FAILED: %r" % (e,))
        button_wake = False
        secs = scheduler.seconds_until_next_update()
        log_wake("sleeping %ds" % secs)
        scheduler.note_expected_wake(secs)
        scheduler.sleep_until_next_update()


if __name__ == "__main__":
    if "--demo" in sys.argv:
        update_display(demo_context(), force=True)
    elif "--once" in sys.argv:
        update_display(force=True)
    else:
        run_forever()
