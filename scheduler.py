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


BM8563_ADDR = 0x51


def _i2c():
    from machine import I2C, Pin
    return I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)


def _bcd2int(v):
    return (v >> 4) * 10 + (v & 0x0F)


def _int2bcd(v):
    return ((v // 10) << 4) | (v % 10)


def rtc_get():
    """Read UTC time from the BM8563, which keeps running while the
    board is fully powered off. Returns a time tuple or None.

    This is the piece that makes overnight work: after timerSleep cuts
    main power, the ESP32 cold-boots with its internal clock at zero,
    so the only trustworthy time source before WiFi is this chip.
    """
    try:
        i2c = _i2c()
        d = i2c.readfrom_mem(BM8563_ADDR, 0x02, 7)
        if d[0] & 0x80:          # VL flag: RTC lost power, time is junk
            return None
        second = _bcd2int(d[0] & 0x7F)
        minute = _bcd2int(d[1] & 0x7F)
        hour = _bcd2int(d[2] & 0x3F)
        day = _bcd2int(d[3] & 0x3F)
        month = _bcd2int(d[5] & 0x1F)
        year = _bcd2int(d[6]) + (1900 if d[5] & 0x80 else 2000)
        if not (2024 <= year <= 2099 and 1 <= month <= 12
                and 1 <= day <= 31):
            return None
        return (year, month, day, hour, minute, second, 0, 0)
    except Exception:
        return None


def rtc_set(t):
    """Store UTC time into the BM8563 so the next cold boot knows the
    time without needing WiFi. `t` is a localtime-style tuple."""
    try:
        i2c = _i2c()
        year, month, day, hour, minute, second = t[0], t[1], t[2], \
            t[3], t[4], t[5]
        century = 0x80 if year < 2000 else 0x00
        i2c.writeto_mem(BM8563_ADDR, 0x02, bytes([
            _int2bcd(second), _int2bcd(minute), _int2bcd(hour),
            _int2bcd(day), 0x00,
            _int2bcd(month) | century, _int2bcd(year % 100),
        ]))
        return True
    except Exception:
        return False


def woke_by_timer():
    """True if this boot was the hourly RTC alarm; False if a human
    pressed the side button.

    The BM8563 RTC raises its timer flag (TF, bit 2 of Control/Status2)
    when its alarm powers the board on; a button power-on leaves it
    clear. We read the flag over I2C and clear it for next time.
    """
    try:
        i2c = _i2c()
        val = i2c.readfrom_mem(BM8563_ADDR, 0x01, 1)[0]
        i2c.writeto_mem(BM8563_ADDR, 0x01, bytes([val & 0x7B]))
        return bool(val & 0x04)
    except Exception:
        # Fallback: timer wakes land on the hour. Only trust this if
        # the clock is actually set — an unsynced clock reads 2000.
        t = time.localtime()
        if t[0] < 2024:
            return True         # assume timer; never strand a battery wake
        return t[4] <= 1


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
