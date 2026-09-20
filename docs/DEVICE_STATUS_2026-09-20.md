# M5Paper status — September 20, 2026

Captured at 12:50 p.m. America/New_York from COM9, CH9102 serial 5B1F012386.
Device log timestamps are UTC; times below are converted to Eastern.

## Confirmed
- Installed OTA version: 63f7e85.
- Renderer SHA-256: a84d1f4e87794ba7f8af928b44a2e603cfd02ec0e2d9bf1c26a8dd0650f93754, matching the published spacing fix.
- OTA installed September 19 at 9:57 a.m.; one changed payload was staged and verified.
- Last saved stage before this inspection: sleep.
- Latest retained update: September 20 at 12:47–12:48 p.m.
- Cached weather time: 12:45 p.m.; cloudy, 60.3°F.
- Direct battery reading while connected: 100%, 4142 mV. Treat percentage as an estimate; the firmware already documents unreliable battery/charging telemetry.
- MicroPython 1.27.0, M5STACK_Paper build; this does not identify a UIFlow release number.
- A soft-reset command was sent after capture and COM9 was closed. Post-reset rendering was not observed in this capture.

## Retained history
The ring-buffer log begins mid-line. Its complete entries cover September 19
8:57 a.m. through September 20 12:48 p.m. There are 26 boot entries, 20 normal
update entries, three night-watch entries, no WATCHDOG entries, and no FAILED
entries. This is not proof of uninterrupted operation or of every render succeeding.

Battery readings changed from 50% / 3724 mV on September 19 at 8:57 a.m.
to 8% / 3374 mV on September 20 at 3:08 a.m. (about 18 hours). This is a
partial discharge observation, not a full-charge runtime measurement.
Percent readings fluctuate substantially between wakes.

At 3:08 a.m. the critical-battery guard skipped the update and requested a
four-hour sleep. No further retained entry appears until 12:46 p.m., a gap
of 9 hours 38 minutes. That return is logged as a button boot with NTP clock
recovery. Power depletion or loss is plausible, but the log alone cannot
establish the cause of the missing expected wake.

## Follow-up priorities
1. Measure discharge and critical-battery recovery; record when USB is attached.
2. Investigate redundant wakes: 10:56/11:00 a.m. and 3:56/4:00 p.m. on
   September 19; night watch also ran at 1:07 and 1:59 a.m. September 20.
3. Check the scheduler's three-minute rollover threshold and quiet-hour
   ten-minute minimum against observed early waking. These are candidates,
   not confirmed root causes.
4. Increase or export log retention for a complete controlled observation window.

No firmware or configuration was changed by this inspection.
