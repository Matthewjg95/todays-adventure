# Device validation when the serial port is free

Status on September 18, 2026: **not run in this review**.
Desktop tests and the supplied photo are separate evidence.

## Capture a baseline

Record installed OTA version, firmware version, configuration, start time,
battery percent/mV, power source and Wi-Fi conditions. Preserve the existing
logs before changing firmware. The serial helper interrupts the device, so
collect logs between observation windows rather than throughout a timed run.

Once the M5Paper is available:

```text
python tools/m5link.py cat /flash/ota_version.txt
python tools/m5link.py cat /flash/wake_log.txt
python tools/m5link.py cat /flash/stage.txt
python tools/m5link.py reset
```

Save each capture with its date and time in an ignored `logs/` folder. The
wake log trims near 5 KB, so collect it often enough to preserve the needed
window. Collection may perturb the run; record every interruption.

## Observe for 24 to 48 hours

| Check | Evidence to record | Desired outcome |
|---|---|---|
| Normal wake | Before/after photo, visible update stamp, log | Updates at expected cadence and returns to sleep |
| Display retention | Photos immediately after render and before next wake | Image remains readable for the entire interval |
| Overnight | Logs and representative night screen | Night-watch and morning transitions occur |
| Charging to battery | Cable state, voltage, next rendered screen | Charging splash gives way to normal content |
| Button | Video of press and return | Facts card appears and returns after about a minute |
| Network loss | Planned short outage, restoration, logs | Recoverable failure and later successful update |
| Watchdog | Count and last-stage strings | No unexplained resets; any failure has useful evidence |
| Battery | Start/end readings and elapsed time | Report measured drain, not an extrapolation as proven runtime |

Use `python tools/battery_report.py logs/<capture>.txt` as an exploratory aid.
Its projected full-charge runtime is not a measured discharge duration. Its
gap label can mistake scheduled quiet/critical sleeps for downtime; reconcile
gaps with the actual scheduler and log context.

Do not deliberately drain the cell or interrupt an OTA apply for this contest
evidence pass. Low-battery gates and interrupted updates need a separate,
controlled test plan with recovery access.

## Layout follow-up

The supplied September 18 photo shows the adventure name close to the first
suggestion. In `ui_renderer.render`, the next row may start only 32 pixels
after a 40-point adventure line. Prepare a font-aware spacing fix on a firmware
branch, check two-line wonders and long names against the sun arc, then inspect
on the panel before release. ASCII smoke tests cannot establish text bounds.

## Results template

- Observation start/end:
- Installed OTA version and UIFlow version:
- Relevant configuration:
- Total scheduled / observed updates:
- Watchdog resets by stage:
- Display fade incidents and elapsed time after refresh:
- Starting / ending battery percent and millivolts:
- Charging and serial interruptions:
- Photo/video filenames:
- Findings and remaining questions:
