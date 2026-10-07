"""Interactive session host for the M5Paper (device only).

Entered when the side button wakes the board (BUTTON_WAKE_ACTION =
"home"). Runs the Home launcher until the user chooses Today's
Adventure or stops touching it for the idle timeout, then returns so
main.py resumes the established fridge cycle (render from cache or the
due slot, then deep sleep).

While this loop runs nothing schedules a sleep: the ambient cycle only
resumes after run() returns. The hardware watchdog is fed every pass.
"""

import time

import config
import home_app
import input_events as ie
import notebook
import tasks
import ui_renderer
import weather_service


def _local_now():
    raw = weather_service._load_json(config.CACHE_FILE) or {}
    t = time.localtime(time.time() + raw.get("utc_offset_seconds", 0))
    return t if t[0] >= 2024 else None


def date_str():
    t = _local_now()
    if t is None:
        return None
    return "%s, %s %d" % (weather_service._WEEKDAYS[t[6]],
                          weather_service._MONTHS[t[1] - 1], t[2])


def wall_time():
    return int(time.time()) if time.gmtime()[0] >= 2024 else None


def cached_weather(battery_str=None):
    """(ctx, wonder, adventure) from the cache only; (None, None, None)
    when nothing is cached. Never invents values."""
    raw = weather_service._load_json(config.CACHE_FILE)
    if not raw:
        return None, None, None
    try:
        import adventures
        import scoring_engine
        import wonder_engine
        ctx = weather_service.build_context(raw=raw)
        ctx["score"] = scoring_engine.score_day(ctx)
        stamp = (raw.get("current") or {}).get("time")
        if stamp and "T" in stamp:
            h, m = weather_service._parse_hhmm(stamp)
            ctx["time_str"] = weather_service._fmt_12h(h, m)
        else:
            ctx["time_str"] = "unknown time"
        if battery_str:
            ctx["battery_str"] = battery_str()
        return ctx, wonder_engine.wonder(ctx), adventures.today(ctx)
    except Exception:
        return None, None, None


def refresh_weather(host, sampler):
    """Fetch now, abandoning the attempt if the user holds for Home.
    The hold itself stays queued so the main loop still acts on it."""
    def home_requested():
        return any(e[0] == "button" and e[1] == ie.HOLD for e in sampler.queue)

    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        if not wlan.isconnected():
            wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            deadline = time.ticks_add(time.ticks_ms(), 30000)
            while not wlan.isconnected():
                if home_requested() or time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                    return False
                if sampler._timer is None:
                    sampler.sample()
                host["feed"]()
                time.sleep_ms(100)
        host["sync_clock"]()
        if home_requested():
            return False
        # A blocking HTTP read (<=30 s timeout); samples resume after it.
        weather_service._save_json(config.CACHE_FILE, weather_service.fetch_raw())
        return True
    finally:
        host["wifi_off"]()


def _draw(app, cv, first):
    frames = app.frames or [None]
    app.frames = []
    for origin in frames[:-1]:
        cv.reset()
        app.render(cv, origin)
        cv.show(4)                       # fastest mode for pan intermediates
    cv.reset()
    app.render(cv, frames[-1])
    cv.show(1 if first else getattr(config, "INTERACTIVE_EPD_MODE", 1))


def run(host):
    """host: dict of callables from main.py: feed, log, stage, wifi_off,
    sync_clock, battery (-> info dict or None), battery_str."""
    import device_io
    host["stage"]("session")
    sampler = device_io.Sampler()
    sampler.start()
    idle_ms = int(getattr(config, "INTERACTIVE_IDLE_SECONDS", 180)) * 1000
    b = host["battery"]()
    if b and not b.get("charging") and b["pct"] <= getattr(config, "LOW_BATTERY_PCT", 20):
        idle_ms //= 2
    env = home_app.Env(
        store=notebook.NotebookStore(),
        tasks=tasks.TaskMaster(),
        weather=lambda: cached_weather(host["battery_str"]),
        refresh_weather=lambda: refresh_weather(host, sampler),
        date_str=date_str, wall_time=wall_time, idle_ms=idle_ms,
        pan_frames=getattr(config, "PAPER_PAN_FRAMES", 0), log=host["log"])
    app = home_app.App(env)
    cv = ui_renderer.make_canvas()
    host["log"]("session start (hold=%dms idle=%ds)"
                % (sampler.side_tracker.hold_ms, idle_ms // 1000))
    try:
        app.open(sampler.now_ms())
        first = True
        while app.exit_reason is None:
            host["feed"]()
            for kind, payload, t in sampler.drain():
                if kind == "button":
                    app.button(payload, t)
                elif kind == "rocker":
                    app.rocker(payload, t)
                elif kind == "touch":
                    app.touch(payload, t)
                if app.exit_reason:
                    break
            if app.exit_reason:
                break
            if app.needs_frame:
                host["stage"]("session-render")
                _draw(app, cv, first)
                first = False
                host["stage"]("session")
            else:
                ink = app.take_ink()
                if ink:
                    cv.ink_segments(ink)
            app.tick(sampler.now_ms())
            time.sleep_ms(20)
    except Exception as e:
        host["log"]("session error: %r" % (e,))
        try:
            app.close("error")
        except Exception:
            pass
    finally:
        sampler.stop()
        if sampler.dropped:
            host["log"]("session input queue overflow: %d dropped" % sampler.dropped)
    return app.exit_reason or "error"
