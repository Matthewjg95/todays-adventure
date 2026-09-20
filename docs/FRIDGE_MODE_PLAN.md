# Fridge-first scheduling and wake troubleshooting

Decision plan, September 20, 2026. No firmware changed or deployed.
Requested direction: no more than five scheduled daylight updates and two
scheduled night updates, with configurable battery and plugged-in modes.

## Contest scope and modularity

The official contest asks for a functional message/signal project, reproduction
steps, photographs/video, originality and technical merit. It does not require
universal hardware support or a Wi-Fi setup screen.
Source: https://community.element14.com/challenges-projects/project14/p/make-a-connection
Checked September 20.

Keep M5Paper v1.1 as the supported, demonstrated platform. Describe other boards
as future ports until each is tested. Separate these interfaces incrementally:
- Message logic: weather context, wonder, events and local recommendations.
- User settings: location, timezone, region catalog, schedule and display mode.
- Board adapter: drawing dimensions/fonts, sleep/wake, battery and external power.
- Policy: decide when to fetch/render from the settings and reported capabilities.

Board-specific retention, sleep current, wake sources and refresh waveforms mean
that “works on any e-ink display” and universal battery-life claims are inappropriate.
Optimize the measured device while preserving a portable message engine.

## Modes

| Mode | Proposed behavior |
|---|---|
| Fridge / battery default | Up to five daylight slots and two night slots; sleep directly between them; radio only for scheduled work |
| Plugged-in | Hourly by default, user-configurable within board refresh limits; keep the useful adventure screen, with artwork-only splash optional |
| Critical battery protection | Override either preference when supply is uncertain; no weather/OTA, minimize work, conservative recovery sleep |
| Manual interaction | Button opens cached facts; return without an unnecessary network fetch; record separately from scheduled wakes |

The current charging heuristic is not reliable external-power detection. An
explicit fridge/plugged-in preference should ship before automatic switching.
A plugged-in preference must not override battery protection. A board with a
reliable VBUS signal can later support auto mode with hysteresis/debounce;
this M5Paper should default to the conservative mode when supply is uncertain.
Plug/unplug changes may only be noticed at a scheduled or button wake unless
the board supplies a proven wake interrupt. Do not introduce polling wakes.

Seven is the scheduled-update budget, not a promise that the CPU can never boot
more often: power restoration, manual presses and watchdog recovery are separate
events. Count and report them rather than hiding them.

## Proposed default schedule

Use cached sunrise/sunset to distribute five updates across daylight: shortly
after sunrise, quarter-day, solar midpoint, three-quarter-day, and shortly before
sunset. Two night messages fall approximately one-third and two-thirds through
the sunset-to-next-sunrise interval. These are defaults for review, not deployed times.

For illustration only, a 07:00–19:00 day could have updates at 07:15, 10:08,
13:00, 15:52, 18:45, then 23:00 and 03:00. A wake “day” is the cycle from one
sunrise to the next. Allow fixed local times for people whose routine matters
more than solar alignment. Do not use clock-hour labels as unique event IDs.

Cache enough solar data to plan the following morning. For missing/invalid solar
data or polar day/night, use a documented fixed daily fallback with at most seven
deduplicated slots. Keep local date/timezone handling explicit across DST.

Each slot has a stable ID, target UTC timestamp and state:
pending, attempted, completed, failed. Persist an attempt before network work;
complete only after successful render. Do not retry an attempted slot after a
reset by starting another Wi-Fi/OTA loop. Recover using cached content when
appropriate and move to the next slot. Coalesce overdue slots into one current
update; never replay a backlog after charging.

An early wake within a tested tolerance (initial candidate: five minutes) may
consume the upcoming slot once, then schedule the following one. Larger drift
is logged for calibration. The scheduler must return one absolute target and
one actual sleep duration used by both logging and hardware. No hourly clamp
or intermediate “wake just to see if it is time” loop.

OTA checks piggyback on scheduled work. In fridge mode they can be limited to
the first daytime slot or a charging session to reduce network overhead.
Document that updates will no longer necessarily arrive within an hour.
An OTA reset resumes/completes its slot without recursively checking OTA again.

## Redundant-wake investigation

### Evidence already collected
- OTA 63f7e85 and renderer hash confirmed on the board September 20.
- Closely spaced daytime boots: 10:56/11:00 and 15:56/16:00 September 19 Eastern.
- Two night-watch updates in the same local hour: 01:07 and 01:59 September 20.
- Critical battery at 03:08; next retained boot at 12:46, despite a requested
  four-hour sleep. Cause unknown; investigate separately from scheduling.
- The retained log showed no WATCHDOG or FAILED entries.

### Reproduced code defect
At a synthetic time one minute before an hourly boundary,
seconds_until_next_update() returns 3660 seconds. sleep_until_next_update()
then clamps it to 3600. The app logs and records the former but sleeps for
the latter. This was reproduced offline with time and sleep mocked, with no
device access. It explains an intent/actual mismatch; it does not by itself
prove the cause of every observed duplicate.

Other candidates: the three-minute rollover threshold misses some observed
early wakes; the ten-minute minimum overshoots a nearby night slot; night-watch
eligibility uses hour membership without a completed-slot ledger.

### Work sequence
1. Preserve the current release and raw capture. Start implementation from fresh
   upstream master, retaining the spacing fix and other collaborators' work.
2. Add structured wake records: reset cause, slot ID, UTC/local time, time source,
   prior target, actual wake drift, requested sleep, mode, battery mV/percent,
   Wi-Fi/fetch/OTA/render durations and results. Save before long sleeps.
3. Replace the interval/quiet-hour branches with one pure next-slot planner and
   explicit budget. Apply the critical battery guard before clock-recovery
   Wi-Fi or button work where board initialization permits.
4. Run desktop simulations and fault-injection tests before generating OTA.
5. On the board, verify clock/wake behavior while powered. Then run a controlled
   battery observation. Record charging/serial interruptions and preserve logs.
6. Compare measured consumption and retention before publishing endurance claims.

## Required tests and acceptance

Desktop:
- At most five daytime and two night scheduled updates per configured cycle.
- No duplicate slot execution after early waking, reset or clock correction.
- No catch-up burst after a long outage.
- Log, recorded wake intent and hardware sleep argument agree exactly.
- Dawn/dusk, midnight, month/year rollover, DST changes, missing solar data.
- Button, OTA reset, Wi-Fi failure, critical battery and mode changes.
- Transition at a boundary does not duplicate a slot or leave an expired target.

Device:
- At least one full cycle with seven scheduled updates and no unintended
  scheduling boots; separately label manual/OTA/recovery boots.
- Confirm display readability immediately after refresh and before each next
  slot, including the longest sleep.
- Compare elapsed time and millivolts under comparable conditions; percentage
  swings make linear battery-life extrapolation unreliable.
- Verify safe recovery after charging without an update storm.

## Retention is the key release gate

The hourly repaint was added because the panel sometimes fades during sleep.
Longer intervals may increase time spent with a faded screen. Compare the
current parked-panel/rail-cut behavior with a controlled rail-retained variant,
changing one factor at a time and measuring both readability and power.

Use seven-update firmware only after this is understood well enough for the
intended placement. If retention remains unreliable, report the tradeoff and
choose the measured power/retention combination; silently adding extra refreshes
would defeat the user's schedule budget. Fewer wakes alone does not establish
a particular battery-life multiplier.

## Setup screen roadmap

Before broad setup UI: create OTA-excluded persistent settings for credentials,
coordinates, timezone, mode and local catalog choice. Validate and migrate
settings without erasing them on update. Keep sample defaults in Git.

A later explicit setup action can offer a temporary Wi-Fi access point and
phone browser form, with a time limit and return to normal operation. A phone
form is likely easier than typing on e-ink. City selection supplies weather
coordinates/timezone; it does not automatically provide curated outings.
Offer an editable local list and a generic fallback when no region pack exists.

For the contest deadline, prioritize a proven fridge mode and clear build steps.
Add setup UI only if enough time remains for an end-to-end test. Do not promise
additional board support without a second validated implementation.

## Versioning and release

Commit planner/tests separately from the generated OTA manifest; record both IDs.
Keep a release record for prepared, tested, published and device-confirmed states.
Integrate the local CI/verifier branch and run the combined suite before relying
on GitHub checks. Publish only a reviewed fast-forward update. Reversal is a new
release restoring prior code with a fresh manifest, not a force-reset of master.
