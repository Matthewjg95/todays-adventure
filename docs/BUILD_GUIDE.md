# Build and run Today's Adventure

This guide includes the September 20 seven-slot scheduling release.
See [operating modes](OPERATING_MODES.md) for schedule and power preferences.

## Hardware and software

- M5Stack M5Paper v1.1 with its battery and a USB data cable.
- A Wi-Fi network the board can join.
- UIFlow2 firmware; the project README records testing with v2.4.9.
- A desktop computer with Git and Python 3.12 for the verified desktop workflow.
- M5Burner for initial firmware installation: https://docs.m5stack.com/en/download.

The integrated board supplies the display, processor, radio, RTC and power circuitry.
This build needs no additional sensor wiring. A new hardware revision or firmware
version needs its own device validation.

## Get the source and run desktop checks

Run from a terminal:

```text
git clone https://github.com/Matthewjg95/todays-adventure.git
cd todays-adventure
python -m pip install -r requirements-dev.txt
python -m unittest discover tests -v
python tools/verify_ota_manifest.py
python main.py --demo
```

The demo prints an ASCII approximation with synthetic weather. It is not a
photograph or a pixel-accurate e-ink preview. `python main.py --once` fetches
real weather and prints one desktop frame; it needs internet access.
Desktop runs may write `state.json` and `last_weather.json`, both ignored by Git.

For serial uploads, also install `python -m pip install pyserial`.
For optional HEIC phone-photo tooling, install `python -m pip install pillow-heif`.

## Configure the project

1. Set latitude, longitude, timezone and hemisphere in `config.py`.
2. Copy `wifi_secrets.example.py` to `wifi_secrets.py` and enter Wi-Fi credentials.
   That file is ignored by Git.
3. Customize `adventures.py` and `events.py` if outside the Syracuse area:
   changing coordinates alone does not replace the local destinations or events.
4. Keep the current Fahrenheit/mph configuration for this validated build.
   The API URL explicitly requests those units; the configuration flag alone
   should not be treated as a verified unit conversion.
5. Review OTA before connecting a personalized build. `ota.py` follows this
   repository's `master` branch, includes `config.py`, and can replace local
   customizations. For an independent build, fork the repository, change the
   `RAW` URL in `ota.py` to your fork and branch, and maintain its manifest.

## Install on the board when its port is available

These steps open the serial connection, interrupt the running app, and eventually
reset it. They were deliberately not executed during the September 18 desktop review.

1. Flash the UIFlow2 firmware with M5Burner, selecting the M5Paper v1.1.
2. Close any other program using the board's serial connection. The uploader
   automatically selects the first CH9102 VID 0x1A86 device; ensure that identifies
   the intended board before using it.
3. Open PowerShell in the repository root. Create scene directories:

```powershell
python tools/m5link.py exec "import os; [os.mkdir(p) for p in ('/flash/scenes','/flash/scenes/v3','/flash/scenes/special') if p.rsplit('/',1)[-1] not in os.listdir(p.rsplit('/',1)[0])]"
```

4. Upload every runtime module, credentials, boot entry and current scene assets
   in one upload session:

```powershell
$modules = @('main.py','config.py','scheduler.py','wake_plan.py','ui_renderer.py','weather_service.py','scoring_engine.py','recommendation_engine.py','wonder_engine.py','adventures.py','events.py','artwork.py','ota.py','wifi_secrets.py')
$uploadPairs = @()
foreach ($name in $modules) { $uploadPairs += @($name, "/flash/$name") }
$uploadPairs += @('boot_device.py', '/flash/boot.py')
foreach ($dir in @('scenes/v3', 'scenes/special')) {
    foreach ($file in Get-ChildItem -LiteralPath $dir -Filter '*.png' -File) {
        $relative = "$dir/$($file.Name)"
        $uploadPairs += @($relative, "/flash/$relative")
    }
}
python tools/m5link.py put @uploadPairs
```

The uploader verifies each transfer's size. It does not create parent directories,
which is why step 3 is separate. If using another scene set, upload that directory
too and set `SCENE_SET` accordingly. Current OTA includes v3 and special scenes only.

5. Start the application:

```text
python tools/m5link.py reset
```

6. Check the actual screen, next scheduled wake, night behavior and plug/unplug
   behavior using [the device checklist](DEVICE_VALIDATION.md). A desktop test
   result does not establish physical display or battery performance.

## What the current firmware actually does

- Uses ESP32 `machine.deepsleep` with timer wake and an attempted wheel-button
  wake configuration. The older RTC power-off helper is not the active sleep path.
- Composes the display offscreen and performs one full GC16 refresh.
- Repaints each scheduled slot; five daylight and two nighttime slots are the
  default. Retention is being observed during normal use, not treated as a
  proven limitation. Explicit plugged-in mode defaults to hourly updates.
- Uses a voltage/trend heuristic for charging; it is not a direct USB-present signal.
- Records wake history and watchdog stage breadcrumbs on flash.
- Attempts OTA after completed scheduled renders when the battery gate allows it; updates below
  30% are skipped unless charging is inferred. Critical-battery handling requests
  a longer sleep. The critical guard now precedes clock-recovery networking.
- Does not guarantee interruption-safe OTA rollback: downloads are hash-checked
  before installation, but replacement is per file and has no multi-file rollback.

## Release workflow

Pushing firmware and its manifest to upstream `master` can update a running
device on its next eligible wake. Keep review work on a branch until release.

1. Run tests and review all device-facing edits.
2. Commit the device code.
3. Run `python tools/make_ota_manifest.py`; it hashes **committed HEAD bytes**,
   not uncommitted working-tree changes.
4. Run `python tools/verify_ota_manifest.py`.
5. Commit the regenerated manifest and review the full release before publishing.

For documentation/tooling-only changes, leave the firmware version and manifest
unchanged. The verifier checks payload hashes and coverage; it intentionally
does not require the manifest version to equal a later documentation commit.

## Troubleshooting

| Symptom | First check |
|---|---|
| Import failure immediately after boot | Confirm all thirteen runtime modules, including wake_plan, adventures, events and ota, were uploaded. |
| Missing scene art or splash | Confirm both scene directories and their files exist on flash. |
| Device stays on the Wave after unplugging | Inspect voltage trend and charging classification in the wake log. |
| Screen fades between wakes | Record time since render and rail-cut setting; repainting is a mitigation. |
| Watchdog recovery | Look for the last recorded stage in the following boot line. |
| Incorrect local adventures | Edit the destination and event catalogs, not just coordinates. |
| Personal settings revert | Check which repository/branch OTA follows and the manifest's config entry. |

Local `FIELD_NOTES.md` is deliberately untracked and was unavailable for this
review. This guide records what is supported by tracked code and commit history.
