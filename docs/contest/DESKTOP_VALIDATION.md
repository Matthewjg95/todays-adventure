# Desktop validation on September 18, 2026

Baseline: upstream master at c79de1f. Review branch: docs/contest-readiness.
Environment: Windows, bundled CPython 3.12; requests 2.34.2 and Pillow 12.3.0.

| Check | Actual result |
|---|---|
| Existing logic and ASCII render tests | 43 passed |
| New manifest-verifier tests | 8 passed |
| Combined suite | 51 passed |
| Committed OTA payload check | All 25 files match version 80b4bd4 |
| Offline demo | Completed successfully |
| Live weather, main.py --once | Completed successfully; September 18, 67°F, “Open the windows today,” Chittenango Falls |
| Git whitespace check | Passed |
| Physical photograph review | Supplied September 18 HEIC decoded; complete screen visible |
| Diagram review | PNG visually checked; no clipped text |

The live run used the configured Syracuse location and produced a newly
written weather cache. Runtime state/cache files are ignored and excluded from
the package.

The GitHub Actions workflow is prepared but has not run on GitHub. These results
come from local commands. Tests use an ASCII canvas and do not establish
physical layout correctness, panel retention, battery endurance, charging
classification, watchdog frequency or on-device OTA behavior.

No serial port was opened. No device logs, installed firmware version or
fresh physical video were collected.
