# Operating modes — September 20 release

The default is **fridge**: five scheduled updates from sunrise +15 minutes to
sunset −15 minutes, and two updates one-third and two-thirds through the night.
The device sleeps directly between slots. Missing or invalid solar dates use
a 07:00–19:00 fallback. Five daytime and two night slots belong to one
sunrise-to-sunrise cycle.

For a 07:00–19:00 day, example local times are 07:15, 10:07, 13:00, 15:52,
18:45, 23:00 and 03:00. Actual times follow cached solar data. There is no
background polling. Manual, OTA and watchdog boots are additional to the
scheduled-update count.

To choose another mode, create /flash/user_settings.json with:
{"power_mode": "plugged", "plugged_interval_minutes": 60}

Allowed intervals are 30, 60, 120, 180 or 240 minutes. Fridge mode can be selected
with {"power_mode": "fridge"}. This optional file is ignored by Git and excluded
from OTA. It currently stores schedule preferences only; Wi-Fi credentials
remain in wifi_secrets.py and location remains in config.py.

Plugged mode is an explicit preference, not an automatic power measurement.
Battery below 30% falls back to fridge scheduling; at or below 8%, radio and
render work are skipped even when the charging heuristic claims charging.
The useful main display stays visible on external power. Artwork-only charging
mode is not part of the new loop.

Each slot is recorded before network work, then marked completed after rendering.
A failed slot waits for the next scheduled slot rather than retrying repeatedly.
Waking up to five minutes early consumes that slot once. Overdue work coalesces
into one update. OTA checks use the existing connection after a completed render;
an OTA reboot does not repeat that slot. Updates can take several hours to arrive.

The device uses the API's cached UTC offset. It is refreshed when weather is
fetched; there is no onboard timezone database. Near a DST change or after a
location change, a pending wake can be shifted until the next successful fetch.
Stable local-date slot IDs prevent re-execution when that offset changes.

Logs now include slot ID, mode, target drift, completion duration and the exact
sleep duration passed to hardware. Battery percentage is still an estimate.
Readability and endurance over the longer intervals require normal-use
observation; historical retention concerns are not treated as a deployment gate.

Initial uploads must include wake_plan.py alongside the other runtime modules.
The OTA manifest includes thirteen runtime modules and thirteen scene files
(26 payloads).
