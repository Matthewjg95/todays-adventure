# M5Paper v1.1 — Power & Display Architecture

Why the device kept going blank, what the hardware actually is, and
the design that works. Written after three failed overnight attempts;
read this before touching scheduler.py or the render path.

## The hardware, mapped

```
 BATTERY/USB ─► power latch ◄─ GPIO2 (must stay high; hold through sleep)
                    │
      ┌─────────────┼──────────────┐
      ▼             ▼              ▼
   ESP32        IT8951 EPD      BM8563 RTC (always powered,
 (main CPU)     controller       keeps UTC through everything)
                    │
                    ▼
              e-ink panel (image persists with NO power)
```

Three separate state holders, and they do not stay in sync by
themselves:

| Component | Survives deep sleep? | Survives power-off? |
|---|---|---|
| ESP32 RAM/clock | no (wake = cold boot) | no |
| IT8951 internal framebuffer | only if its rail stays powered | no |
| Panel (visible image) | yes | yes |
| BM8563 RTC time | yes | yes |

## The display pipeline trap (the blank screen)

The IT8951 has quality modes (GC16 — absolute, writes every pixel,
one flash) and differential modes (DU/DU4 — fast, quiet, but they
only flip pixels that differ from the **controller's internal
buffer**, not from what's visibly on the panel).

After every deep-sleep wake the ESP32 cold-boots and reattaches to
the controller. M5GFX `Panel_IT8951::init()` does **not** reset or
clear anything — whatever sync existed between controller buffer and
panel is gone. From the driver's own semantics: differential updates
against a desynced buffer *produce nothing visible until a full
refresh resynchronizes*.

Our old render did an absolute white wipe (works from any state →
screen blanks) then drew all content differentially (desynced → shows
nothing). Result: a reliably blank screen after every battery wake,
while identical code looked perfect on USB where no reboot ever broke
the sync.

**Rule: after a reboot, the first thing the panel receives must be an
absolute (GC16) full frame. Differential updates are only valid
against a frame pushed during the same boot.**

## The render path that works

1. Compose the ENTIRE screen into an offscreen full-size canvas
   (`Lcd.newCanvas(540, 960, 8bpp)` in PSRAM — we have 4 MB free).
2. Push it once in quality mode: one GC16 flash, every pixel
   absolute, correct from any prior state.
3. Animation may then use differential region pushes — they reference
   the frame from step 2, same boot, so they are in sync.
4. The stamp-corner repaint on unchanged wakes is differential and
   post-reboot, so it is best-effort only (may not develop; cosmetic).

## Sleep path (scheduler.py)

- `machine.deepsleep(ms)` — the ONLY wake that fires on this
  board/firmware. Proven: two full nights of hourly wakes.
  - RTC-latch wake (`M5.Power.timerSleep`, and the raw BM8563
    TIE+GPIO2 sequence) powers off and never returns. Proven dead
    twice on battery. Do not retry without new information.
- Before sleeping: quiesce the display (waitDisplay + panel sleep if
  the binding exposes them). Do NOT cut the EPD power rail (pin 23):
  an uncontrolled cut can discharge the panel (fades the image) and
  guarantees a desynced controller. Pin 5 (external port) may be cut.
- `Pin(2, OUT, value=1, hold=True)` — GPIO2 is RTC-capable, so the
  individual hold survives deep sleep and the power latch stays up.
- 4-minute hardware WDT while awake: the 5 AM DNS hang recurs
  (first WiFi use after quiet hours); the WDT reset recovers it and
  is logged as `WATCHDOG reset`.

## Failure history (so nobody re-walks this road)

| Night | Sleep method | Result |
|---|---|---|
| Aug 3 | M5.Power.timerSleep | froze at first battery sleep — no wake |
| Aug 4 | raw BM8563 TIE + GPIO2 low | same: powered off, never woke |
| Aug 5 | deepsleep + EPD rail cut | woke perfectly all night; renders invisible → "blank" |
| Aug 6 | deepsleep + EPD rail kept | still blank: reboot desyncs controller buffer; differential draws develop nothing |
| Fix | deepsleep + full-frame GC16 compose-and-push | absolute updates need no sync |

## Power budget

Deep sleep with EPD rail powered: days-to-~2 weeks per charge
(measure when stable). The zero-power months-long dream requires the
RTC-latch wake that provably does not work here. If it ever matters:
first verify sleep current with a meter, then consider cutting the
EPD rail again — safe now ONLY because every render is an absolute
full frame, but re-test panel fade before trusting it.

Sources: M5GFX `Panel_IT8951.cpp`; M5Unified issue #91 (display
quiesce before sleep); m5stack community threads on M5Paper
shutdown/deep-sleep power architecture.
