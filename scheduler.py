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


_BUS = None


def _i2c():
    """I2C handle for the RTC, retried because the bus is not ready
    in the first moments of boot — exactly when we need to ask why we
    woke. Without the retry every RTC wake looked like a button press.
    """
    global _BUS
    if _BUS is not None:
        return _BUS
    from machine import I2C, Pin
    last = None
    for attempt in range(4):
        try:
            bus = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
            bus.readfrom_mem(BM8563_ADDR, 0x02, 1)   # prove it answers
            _BUS = bus
            return bus
        except Exception as e:
            last = e
            if attempt == 0:
                try:            # bring the board's hardware up, then retry
                    import M5
                    M5.begin()
                except Exception:
                    pass
            time.sleep(0.2)
    raise last


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


WAKE_DETAIL = "?"       # why woke_by_timer decided what it did
INTENT_FILE = "wake_intent.txt"
WAKE_SLACK = 300        # seconds of tolerance around the expected wake


def note_expected_wake(secs):
    """Record when the RTC alarm should bring us back, so the next
    boot can tell an alarm from a human."""
    try:
        with open(INTENT_FILE, "w") as f:
            f.write("%d" % (int(time.time()) + int(secs)))
    except Exception:
        pass


def woke_by_timer():
    """True if the RTC alarm woke us, False if a human pressed the
    side button.

    The obvious approach — the BM8563's timer flag — does not work
    here: the UIFlow2 firmware initialises the RTC during boot and
    clears its interrupt flags before any Python runs, so the flag
    always reads zero. Instead we compare the clock against the wake
    time we recorded before sleeping. Requires the clock to be
    established first.
    """
    global WAKE_DETAIL
    # Strongest signal first: on a deep-sleep reset the chip records
    # WHY it woke — its timer, or the armed wheel-press pin.
    try:
        import machine
        cause = machine.reset_cause()
        if cause == machine.DEEPSLEEP_RESET:
            try:
                reason = machine.wake_reason()
                pin_wakes = []
                for name in ("PIN_WAKE", "EXT0_WAKE", "EXT1_WAKE"):
                    v = getattr(machine, name, None)
                    if v is not None:
                        pin_wakes.append(v)
                if reason in pin_wakes:
                    WAKE_DETAIL = "wheel press (ext0)"
                    return False           # a human! show the card
            except Exception:
                pass
            WAKE_DETAIL = "deepsleep reset"
            return True
        if cause == machine.WDT_RESET:
            WAKE_DETAIL = "WATCHDOG reset (hang recovered)"
            return True      # not a human; skip the flashcard
    except Exception:
        pass
    now = time.time()
    if time.localtime()[0] < 2024:
        WAKE_DETAIL = "clock unset; assuming timer"
        return True
    try:
        with open(INTENT_FILE) as f:
            expected = int(f.read().strip())
    except Exception:
        WAKE_DETAIL = "no intent file; assuming timer"
        return True
    drift = now - expected
    on_time = -WAKE_SLACK <= drift <= WAKE_SLACK
    WAKE_DETAIL = "drift=%ds -> %s" % (drift,
                                       "timer" if on_time else "button")
    return on_time


def seconds_until_next_update():
    """Seconds until the top of the next interval (wakes on the hour)."""
    interval = config.UPDATE_INTERVAL_MINUTES * 60
    now = time.time()
    return int(interval - (now % interval)) or interval


MAIN_PWR_PIN = 2        # M5Paper power latch (M5EPD_MAIN_PWR_PIN)
WHEEL_PUSH_PIN = 38     # side wheel press (M5EPD key push, active low)


def _shutdown_with_rtc_wake(secs):
    """M5EPD-style shutdown, done directly over I2C.

    UIFlow2's M5.Power.timerSleep powers the board off but its wake
    never fires — the device froze at its first battery sleep. What
    Arduino's proven M5.shutdown() actually does: arm the BM8563
    countdown timer, enable its interrupt output (wired to the power
    latch), then release main power on GPIO2. The RTC's INT line
    re-latches power when the timer fires.

    On battery this function does not return. On USB the board stays
    powered; the caller waits out the interval instead.
    """
    from machine import Pin
    i2c = _i2c()
    if secs >= 60:
        src = 0x83                              # 1/60 Hz clock: minutes
        count = min(255, max(1, (secs + 30) // 60))
    else:
        src = 0x82                              # 1 Hz clock: seconds
        count = min(255, max(1, secs))
    i2c.writeto_mem(BM8563_ADDR, 0x01, bytes([0x01]))  # TIE on, flags clear
    i2c.writeto_mem(BM8563_ADDR, 0x0E, bytes([0x00]))  # stop timer
    i2c.writeto_mem(BM8563_ADDR, 0x0F, bytes([count]))
    i2c.writeto_mem(BM8563_ADDR, 0x0E, bytes([src]))   # start countdown
    Pin(MAIN_PWR_PIN, Pin.OUT).value(0)         # release the power latch


def _restore_power_latch():
    """After a USB-powered sleep, re-assert the latch so a later USB
    unplug doesn't kill the board mid-cycle, and quiet the timer."""
    try:
        from machine import Pin
        Pin(MAIN_PWR_PIN, Pin.OUT).value(1)
        i2c = _i2c()
        i2c.writeto_mem(BM8563_ADDR, 0x0E, bytes([0x00]))
        i2c.writeto_mem(BM8563_ADDR, 0x01, bytes([0x00]))
    except Exception:
        pass


EPD_PWR_EN_PIN = 23     # e-ink panel power (image persists unpowered)
EXT_PWR_EN_PIN = 5      # external port power


def _peripherals_off():
    """Park the panel, then trim rails.

    powerSaveOn = IT8951 standby: parks the source/gate drivers so the
    panel retains its image without active power — the same sequence
    Arduino's proven shutdown uses. This replaces the pad-hold
    approach: holding pin 23 required the GLOBAL digital-pad hold,
    which freezes the SPI flash pins through sleep and the chip
    (intermittently) cannot boot at wake — two lost days."""
    try:
        import M5
        fn = getattr(M5.Lcd, "powerSaveOn", None)
        if fn:
            fn()
    except Exception:
        pass
    try:
        from machine import Pin
        Pin(EXT_PWR_EN_PIN, Pin.OUT).value(0)
    except Exception:
        pass
    # The big battery lever: with the panel PARKED (powerSaveOn above),
    # drive the EPD rail firmly low before sleeping. This is the
    # Arduino-shutdown order (park, then cut) — distinct from the old
    # failure, where the rail floated under an *unparked* panel and
    # the image discharged. During deep sleep the pin floats anyway,
    # but from 0V with parked drivers, not from sagging mid-rail.
    if getattr(config, "CUT_EPD_RAIL_IN_SLEEP", False):
        try:
            import time as _t
            _t.sleep(0.3)          # let the standby command settle
            from machine import Pin
            Pin(EPD_PWR_EN_PIN, Pin.OUT).value(0)
        except Exception:
            pass


def sleep_until_next_update():
    secs = seconds_until_next_update()
    # keep a sane range: at least 1 min, at most the full interval
    secs = max(60, min(secs, config.UPDATE_INTERVAL_MINUTES * 60))
    sleep_for(secs)


def sleep_for(secs):
    secs = max(60, int(secs))

    # ESP32 deep sleep: the wake timer is inside the chip, so it fires
    # regardless of firmware or the RTC-to-power-latch circuit — which
    # never restored power on this board (tested twice: UIFlow2's
    # timerSleep AND the Arduino-style BM8563 sequence in
    # _shutdown_with_rtc_wake, kept below for a future revisit).
    # Wake = reset -> boot.py -> main.py, same as a cold boot.
    try:
        import machine
        # ONLY the main power latch is held: GPIO2 is an RTC pad, its
        # individual hold survives deep sleep without the global
        # digital-pad hold. NEVER enable esp32.gpio_deep_sleep_hold —
        # it freezes the SPI flash pins and the chip cannot reliably
        # boot at wake (Aug 8-9: two sleeps never woke).
        machine.Pin(MAIN_PWR_PIN, machine.Pin.OUT, value=1, hold=True)
        try:
            # Arm the wheel-press (G38, active low, external pull-up)
            # as a deep-sleep wake source — without this the side
            # button is dead while the device sleeps, i.e. ~59
            # minutes of every hour.
            import esp32
            esp32.wake_on_ext0(machine.Pin(WHEEL_PUSH_PIN,
                                           machine.Pin.IN), 0)
        except Exception:
            pass
        _peripherals_off()
        machine.deepsleep(secs * 1000)  # does not return
        return
    except ImportError:
        pass

    # Desktop simulation / fallback
    time.sleep(secs)
