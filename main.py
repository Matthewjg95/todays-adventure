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


def _charging_from(mv, prev_mv):
    """Charging detection from cell voltage + trend.

    isCharging() lies and getVBUSVoltage() is unimplemented (-1) on
    this board, so the cell itself is the only witness. Voltage alone
    is ambiguous: a freshly-unplugged full cell RESTS at 4150-4200mV
    for hours (which kept the charging splash up after unplugging).
    A charger either holds the cell clearly high (>=4230) or drives
    it upward; a resting cell sags. When ambiguous, say battery —
    the weather screen is the useful default."""
    if mv is None:
        return None
    if mv >= 4230:
        return True
    if mv >= 4150:
        if prev_mv is None:
            return True             # no history yet: old behavior
        return mv > prev_mv + 1     # rising = charger at work
    return False


_BATT_CACHE = None
_BATT_MV_FILE = "batt_mv.txt"


def battery_info():
    """{'pct', 'mv', 'charging'} or None. Computed once per boot
    (multiple callers per wake must see one consistent reading and
    the mv-trend file must be written exactly once)."""
    global _BATT_CACHE
    if _BATT_CACHE is not None:
        return _BATT_CACHE
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
        prev = None
        try:
            with open(_BATT_MV_FILE) as f:
                prev = int(f.read().strip())
        except Exception:
            pass
        if info["mv"]:
            try:
                with open(_BATT_MV_FILE, "w") as f:
                    f.write(str(info["mv"]))
            except Exception:
                pass
        info["charging"] = _charging_from(info["mv"], prev)
        _BATT_CACHE = info
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
            # force a repaint after the reset: new code may render
            # differently, and a stale SPLASH/fingerprint marker
            # would skip the redraw
            state = weather_service._load_json(config.STATE_FILE) or {}
            state["last_render"] = None
            weather_service._save_json(config.STATE_FILE, state)
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


STAGE_FILE = "stage.txt"


def _stage(name):
    """Breadcrumb for the watchdog. A hung wake ends in a silent
    4-min WDT reset; the next boot logs the last stage reached so
    the log says WHERE it hung, not just that it did."""
    if not MICROPYTHON:
        return
    try:
        with open(STAGE_FILE, "w") as f:
            f.write(name)
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


def update_display(ctx=None, force=False, night_watch=False, keep_wifi=False):
    if ctx is None:
        _stage("wifi")
        connect_wifi()
        _stage("ntp")
        sync_clock()
        _stage("fetch")
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

    _stage("render")
    cv = ui_renderer.make_canvas()
    ui_renderer.render(cv, ctx, head, activities, wonder_text)
    weather_service._save_json(config.STATE_FILE, state)
    print("rendered: %s | %s | %s"
          % (head, ", ".join(activities), wonder_text))

    # Network work is done; drop the radio before the slow part.
    if not keep_wifi:
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



SCHEDULE_STATE = "schedule_state.json"


def _save_schedule(state):
    """Persist before expensive work so a reset cannot repeat a slot."""
    import json
    import os
    temporary = SCHEDULE_STATE + ".tmp"
    with open(temporary, "w") as f:
        json.dump(state, f)
    replace = getattr(os, "replace", os.rename)
    replace(temporary, SCHEDULE_STATE)


def _sleep_to(target, label):
    """One computed duration for telemetry, intent, and actual hardware sleep."""
    secs = max(60, int(target - time.time()))
    wifi_off()
    _stage("sleep")
    log_wake("sleep target=%d slot=%s seconds=%d" % (target, label, secs))
    scheduler.note_expected_wake(secs)
    scheduler.sleep_for(secs)


def _critical(b):
    # A noisy charging heuristic must not override a critically low cell.
    return bool(b and b["pct"] <= getattr(config, "CRITICAL_BATTERY_PCT", 8))


def scheduled_cycle(button_wake=False):
    import wake_plan
    now = time.time()
    b = battery_info()
    if _critical(b):
        log_wake("CRITICAL battery %s; skipping radio/render" % battery_log_str(b))
        _sleep_to(now + config.CRITICAL_SLEEP_MINUTES * 60, "critical")
        return
    if time.gmtime(now)[0] < 2024:
        log_wake("clock unknown; deferring scheduled work")
        _sleep_to(now + 4 * 3600, "clock-recovery")
        return
    raw = weather_service._load_json(config.CACHE_FILE) or {}
    state = weather_service._load_json(SCHEDULE_STATE) or {}
    if not isinstance(state, dict):
        state = {}
    attempted = state.get("attempted", [])
    if not isinstance(attempted, list):
        attempted = []
    mode = getattr(config, "POWER_MODE", "fridge")
    # Explicit plugged preference is not evidence that external power is present.
    if b and b["pct"] < 30:
        mode = "fridge"
    interval = getattr(config, "PLUGGED_INTERVAL_MINUTES", 60)
    due, future = wake_plan.choose(now, raw, mode, interval, attempted)
    try:
        if due:
            slot, target, night = due
            state["attempted"] = (attempted + [slot])[-64:]
            state["last"] = {"slot": slot, "target": target, "status": "attempted"}
            _save_schedule(state)
            started = time.time()
            log_wake("slot=%s mode=%s drift=%ds batt=%s" %
                     (slot, mode, int(now - target), battery_log_str(b)))
            update_display(force=True, night_watch=night, keep_wifi=True)
            state["last"]["status"] = "completed"
            _save_schedule(state)
            log_wake("slot=%s completed duration=%ds" %
                     (slot, int(time.time() - started)))
            # Already connected. Claim/completion survives the OTA reset.
            _stage("ota")
            _maybe_ota()
        elif button_wake:
            # Restore the normal screen from cache after the facts card.
            if raw:
                ctx = weather_service.build_context(raw=raw)
                update_display(ctx, force=True, night_watch=is_quiet_hour(local_hour()))
        else:
            log_wake("no unattempted slot; skipping network and render")
    except Exception as e:
        log_wake("FAILED slot=%s: %r" % (due[0] if due else "manual", e))
        if due:
            state["last"]["status"] = "failed"
            try:
                _save_schedule(state)
            except Exception:
                pass
    # A fetch may update solar times/UTC offset. Re-plan once; no polling boots.
    raw = weather_service._load_json(config.CACHE_FILE) or raw
    _, future = wake_plan.choose(time.time(), raw, mode, interval,
                                 state.get("attempted", attempted))
    _sleep_to(future[1], future[0])


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

    # Protect a depleted cell before clock recovery can enable Wi-Fi.
    if _critical(battery_info()):
        log_wake("CRITICAL battery at boot; deferring clock/network")
        _sleep_to(time.time() + config.CRITICAL_SLEEP_MINUTES * 60, "critical")
        return
    boot_source = establish_time()
    button_wake = MICROPYTHON and not scheduler.woke_by_timer()
    hung = ""
    if "WATCHDOG" in scheduler.WAKE_DETAIL or "WDT" in scheduler.WAKE_DETAIL:
        try:
            with open(STAGE_FILE) as f:
                hung = ", hung at " + f.read().strip()
        except OSError:
            pass
    log_wake("boot (%s) [%s%s, clock=%s, batt=%s]" %
             ("button" if button_wake else "timer", scheduler.WAKE_DETAIL,
              hung, boot_source, battery_log_str()))
    if button_wake:
        show_flashcard()
    while True:
        if wdt:
            wdt.feed()
        scheduled_cycle(button_wake)
        button_wake = False


if __name__ == "__main__":
    if "--demo" in sys.argv:
        update_display(demo_context(), force=True)
    elif "--once" in sys.argv:
        update_display(force=True)
    else:
        run_forever()
