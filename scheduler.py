"""Hourly update cadence, optimized for e-ink + battery.

On the M5Paper the best strategy is NOT time.sleep(): the M5Paper's
RTC (BM8563) can cut main power entirely and wake the ESP32 later —
the e-ink image persists with zero power. That takes battery life from
days to months.

Strategy (first that works wins):
  1. M5Paper RTC power-off wake  (UIFlow: M5.shutdown / power timer)
  2. machine.deepsleep
  3. plain time.sleep loop        (desktop / fallback; still fine on USB)
"""

import time

import config


def seconds_until_next_update():
    """Seconds until the top of the next interval (wakes on the hour)."""
    interval = config.UPDATE_INTERVAL_MINUTES * 60
    now = time.time()
    return int(interval - (now % interval)) or interval


def sleep_until_next_update():
    secs = seconds_until_next_update()
    # keep a sane range: at least 1 min, at most the full interval
    secs = max(60, min(secs, config.UPDATE_INTERVAL_MINUTES * 60))

    # 1a. Full power-off with RTC wake (UIFlow2 / M5Unified)
    try:
        import M5
        M5.Power.timerSleep(secs)  # does not return on battery power
        time.sleep(secs)           # on USB it may fall through; wait it out
        return
    except (ImportError, AttributeError):
        pass

    # 1b. Full power-off with RTC wake (legacy UIFlow 1.x)
    try:
        from m5stack import M5 as m5
        m5.shutdown(secs)
        time.sleep(secs)
        return
    except ImportError:
        pass

    # 2. ESP32 deep sleep
    try:
        import machine
        machine.deepsleep(secs * 1000)  # does not return; resets on wake
        return
    except ImportError:
        pass

    # 3. Desktop simulation / fallback
    time.sleep(secs)
