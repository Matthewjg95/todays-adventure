"""Today's Adventure — entry point.

MicroPython auto-runs main.py at boot, so the device wakes, connects,
fetches, scores, renders, and powers back off — no interaction ever.

Desktop simulation:  python main.py --once      (real weather, one render)
                     python main.py --demo      (fake perfect summer day)
"""

import sys
import time

import config
import adventures
import events
import weather_service
import scoring_engine
import recommendation_engine
import wonder_engine
import ui_renderer
import scheduler

MICROPYTHON = weather_service.MICROPYTHON


def battery_info():
    """{'pct', 'mv', 'charging'} or None.

    The gauge is a voltmeter, not a fuel gauge: while charging it
    reads the charger's ~4.2V and reports ~100% regardless of true
    charge. Only on-battery readings mean anything — so log raw
    millivolts and flag charging readings as untrustworthy."""
    if not MICROPYTHON:
        return None
    try:
        import M5
        try:
            pct = int(M5.Power.getBatteryLevel())
        except Exception:
            M5.begin()
            pct = int(M5.Power.getBatteryLevel())
        info = {"pct": pct, "mv": None, "charging": None}
        try:
            info["mv"] = int(M5.Power.getBatteryVoltage())
        except Exception:
            pass
        # Charging detection, the hard way. isCharging() lies (returns
        # True on battery) and getVBUSVoltage() returns -1 on this
        # board — unimplemented. What does not lie is the cell itself:
        # under load a 1S li-ion cannot sit above ~4.15V unless a
        # charger is holding it there. Measured: battery max ever
        # logged 3718mV; plugged readings 4184-4274mV.
        if info["mv"]:
            info["charging"] = info["mv"] >= 4150
        return info
    except Exception:
        return None


def battery_pct():
    b = battery_info()
    return b["pct"] if b else None


def battery_log_str(b=None):
    """One battery string, used EVERYWHERE it appears — the log, the
    corner stamp, the flashcard — so screen and log always agree."""
    if b is None:
        b = battery_info()
    if not b:
        return "?"
    if b["charging"]:
        return "chg %smV" % b["mv"]      # charger voltage, not charge
    return "%d%% %smV" % (b["pct"], b["mv"])


def connect_wifi():
    if not MICROPYTHON:
        return
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        # Cap TX power: full-power bursts on battery are the prime
        # suspect for the rare mid-update hard deaths (brownout).
        wlan.config(txpower=11)
    except Exception:
        pass
    if wlan.isconnected():
        return
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    for _ in range(30):
        if wlan.isconnected():
            return
        time.sleep(1)
    raise OSError("WiFi connect failed")


def _maybe_ota():
    """Self-update from GitHub when power allows. An applied update
    resets the device; the next boot runs the new code."""
    if not MICROPYTHON:
        return
    b = battery_info()
    if b and not b["charging"] and b["pct"] < 30:
        return                      # not on a weak battery
    try:
        import ota
        if ota.check_and_apply(log_wake):
            wifi_off()
            import machine
            log_wake("OTA applied; resetting")
            machine.reset()
    except Exception as e:
        log_wake("OTA check failed: %r" % (e,))


def wifi_off():
    """Shut the radio down the moment we're done with it.

    It used to stay active for the whole wake — including the 30s
    animation — and through deep sleep. On battery that is pure waste.
    """
    if not MICROPYTHON:
        return
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        if wlan.active():
            wlan.disconnect()
            wlan.active(False)
    except Exception:
        pass


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
        ctx.get("adventure") or "",
        "nw%d" % ctx["hour"] if ctx.get("is_night_watch") else "",
    ))


def update_display(ctx=None, force=False, night_watch=False):
    if ctx is None:
        connect_wifi()
        sync_clock()
        _maybe_ota()
        ctx = weather_service.build_context()
    if night_watch:
        ctx["is_night_watch"] = True
    b = battery_info()
    ctx["battery_pct"] = b["pct"] if b else None
    ctx["battery_charging"] = bool(b and b["charging"])
    ctx["battery_str"] = battery_log_str(b)

    score = scoring_engine.score_day(ctx)
    ctx["score"] = score
    head = scoring_engine.headline(ctx, score)
    wonder_text = wonder_engine.wonder(ctx)
    if not ctx.get("is_night_watch"):
        ev = events.today(ctx)
        if ev:
            wonder_text = ev        # a worthy day outranks the weather
    ctx["adventure"] = adventures.today(ctx)
    activities = recommendation_engine.recommend(
        ctx, avoid=" ".join((head, wonder_text, ctx["adventure"] or "")))
    if ctx["adventure"]:
        activities = activities[:2]     # the adventure line is the star

    # Only touch the e-ink when something meaningful changed.
    fp = _fingerprint(ctx, head, activities, wonder_text)
    state = weather_service._load_json(config.STATE_FILE) or {}
    if not force and state.get("last_render") == fp \
            and not getattr(config, "ALWAYS_RENDER", True):
        # Skipping is only safe if the panel provably still shows the
        # last render — it faded during sleep, so default is repaint.
        # No stamp repaint either: it was differential post-reboot
        # (unreliable) and cost a display power-up per skipped wake.
        # The upd stamp shows the last RENDER; wake_log.txt is the
        # proof of life.
        print("unchanged: skipping refresh")
        log_wake("  unchanged, no refresh")
        return ctx, score, head, activities, wonder_text
    state["last_render"] = fp

    cv = ui_renderer.make_canvas()
    ui_renderer.render(cv, ctx, head, activities, wonder_text)
    weather_service._save_json(config.STATE_FILE, state)
    print("rendered: %s | %s | %s"
          % (head, ", ".join(activities), wonder_text))

    # Network work is done; drop the radio before the slow part.
    wifi_off()

    # A few seconds of glyph motion — rain falls, rays breathe.
    # Skipped on a low battery: it is the single longest awake stretch.
    secs = getattr(config, "GLYPH_ANIMATE_SECONDS", 0)
    pct = ctx.get("battery_pct")
    if (pct is not None and not ctx.get("battery_charging")
            and pct <= getattr(config, "LOW_BATTERY_PCT", 20)):
        secs = 0
        log_wake("  low battery: animation skipped")
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
        b = battery_info()
        ctx["battery_pct"] = b["pct"] if b else None
        ctx["battery_charging"] = bool(b and b["charging"])
        ctx["battery_str"] = battery_log_str(b)
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


def _seconds_to_next_night_event(hour):
    """Seconds from now (top-of-hour wake) to the next hour that has
    work: a night-watch render or the end of quiet hours. Clamped to
    4h as a safety net against clock math surprises."""
    events = set(config.NIGHT_WAKE_HOURS) | {config.QUIET_END}
    for ahead in range(1, 25):
        if (hour + ahead) % 24 in events:
            break
    else:
        ahead = 1
    # align to the top of that hour using the current minute
    minute = time.localtime()[4]
    secs = ahead * 3600 - minute * 60
    return max(600, min(secs, 4 * 3600))


def run_forever():
    # Hardware watchdog: if ANYTHING hangs (a dead socket, a wedged
    # panel), the chip resets and the next boot recovers. Deep sleep
    # resets the chip anyway, so the WDT only has to cover awake time.
    wdt = None
    if MICROPYTHON:
        try:
            from machine import WDT
            wdt = WDT(timeout=240000)      # 4 min >> longest good cycle
        except Exception:
            pass
        try:
            # Release the pad holds sleep left behind (held pads would
            # silently break the display bus), but keep the rails up.
            import esp32
            esp32.gpio_deep_sleep_hold(False)
            from machine import Pin
            Pin(scheduler.EPD_PWR_EN_PIN, Pin.OUT, value=1, hold=False)
        except Exception:
            pass

    # Clock first: every battery wake is a cold boot, and the wake
    # cause, quiet hours and night watch are all decided from it.
    boot_source = establish_time()
    button_wake = MICROPYTHON and not scheduler.woke_by_timer()
    log_wake("boot (%s) [%s, clock=%s, batt=%s]"
             % ("button" if button_wake else "timer",
                scheduler.WAKE_DETAIL, boot_source,
                battery_log_str()))
    print("wake:", "button" if button_wake else "timer",
          scheduler.WAKE_DETAIL)
    if button_wake:
        show_flashcard()
    while True:
        if wdt:
            wdt.feed()
        try:
            # Critical battery: do NOT touch the radio. The device
            # died on 2026-08-18 because the 5 AM update hung at 0%,
            # the watchdog retried, and the WiFi burst collapsed the
            # rail to 2848mV. Coast on the last image instead.
            b = battery_info()
            crit = getattr(config, "CRITICAL_BATTERY_PCT", 8)
            if b and not b["charging"] and b["pct"] <= crit:
                log_wake("CRITICAL battery %s — skipping update, "
                         "long sleep" % battery_log_str(b))
                print("critical battery: coasting")
                wifi_off()
                scheduler.note_expected_wake(
                    config.CRITICAL_SLEEP_MINUTES * 60)
                scheduler.sleep_for(
                    config.CRITICAL_SLEEP_MINUTES * 60)
                continue

            # Docked and charging: show the Wave as a splash screen.
            # Power is free, so this is also the ideal OTA moment.
            if b and b["charging"]:
                try:
                    connect_wifi()
                    sync_clock()
                    _maybe_ota()
                except Exception as e:
                    log_wake("charging net: %r" % (e,))
                wifi_off()
                state = weather_service._load_json(
                    config.STATE_FILE) or {}
                if state.get("last_render") != "SPLASH":
                    ui_renderer.render_splash()
                    state["last_render"] = "SPLASH"
                    weather_service._save_json(config.STATE_FILE, state)
                    log_wake("charging: splash shown")
                else:
                    log_wake("charging: splash already up")
                button_wake = False
                scheduler.note_expected_wake(3600)
                scheduler.sleep_for(3600)
                continue

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
                    # Sleep STRAIGHT to the next event hour instead of
                    # booting every hour just to decide to skip — each
                    # pointless boot costs ~10s awake.
                    secs = _seconds_to_next_night_event(hour)
                    log_wake("quiet %02d:00 (%s): sleeping %dm to "
                             "next event" % (hour, source, secs // 60))
                    print("quiet hours: long sleep %ds" % secs)
                    button_wake = False
                    scheduler.note_expected_wake(secs)
                    scheduler.sleep_for(secs)
                    continue
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
