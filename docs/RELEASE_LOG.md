# Release and change record

## October 8, 2026 — real Daily Paper editions (branch feature/daily-paper-edition)

Owner reported the 0648514 interactive modules working on the Paper (hold
timing, wheel direction, page turns and ink all acceptable). This branch replaces
the sample newspaper with real editions: tools/build_edition.py builds a capped
edition.json from public feeds, .github/workflows/edition.yml publishes it to the
data-only `edition` branch three times a day, and the Paper downloads it at
scheduled updates (after the render, before OTA, same battery gate). Desktop
evidence: 151 tests, a live build from the five feeds (18 stories, 4.3 KB), a
Pillow preview of the live layout, and the device modules under the MicroPython
1.24.1 unix port. Not yet released over OTA; the workflow starts after merge.

## October 7, 2026 — interactive modules released over OTA (0648514)

At the owner's request the prototype below was merged to master and published
as OTA 0648514 (35 payloads: nine new modules/fixture plus changed main.py,
config.py and ui_renderer.py). The board installs it after its next completed
scheduled update with battery >= 30% (or charging); a button wake between slots
does not check OTA. Installation and on-panel behavior are not yet confirmed.
Rollback: BUTTON_WAKE_ACTION = "flashcard" in config.py and a new manifest.

## October 7, 2026 — interactive modules prototype (branch)

Branch feature/modular-companion adds the Home launcher (Today's Adventure,
Daily Paper, Notebook, Weather Flashcard), global hold-to-Home on the side
button with wake-press disarming, a fixed large newspaper with a viewport
route and minimap, handwriting capture with atomic local storage, and a
fixture-backed task master. The OTA manifest was deliberately left at 75a870a;
CI reports twelve pending payloads off master (nine new files; main.py,
config.py and ui_renderer.py changed). Desktop evidence only:
unit tests, a Pillow preview of the full test sequence, and the pure modules
run under the MicroPython 1.24.1 unix port. No serial connection, flash or
physical observation took place. See docs/INTERACTIVE_MODULES.md.

## September 27, 2026 — ten-second button interaction

OTA 75a870a: side-button wakes show the detail card for ten seconds after
rendering, then force the adventure display even at 100% battery. Scheduled
non-button renders still show the wave at full battery. The facts-card caption
now states ten seconds. E-ink refresh time is additional to the hold interval.
73 desktop tests passed; all 26 OTA hashes verified. Board installation was
verified over USB after its Wi-Fi OTA updater installed 75a870a. All 26 on-device
hashes matched. At reported 100% battery, the detail card, ten-second wait and
forced adventure render completed. The wave was restored and scheduled sleep
requested for the owner's physical-button recording. Evidence is saved in the
task workspace at outputs/wave-ota-2026-09-27_151448/verification.txt. To revert, restore the preceding main/renderer and regenerate OTA.

## September 27, 2026 — board installation verified

At about 1:47 p.m. Eastern, the identified M5Paper on COM9 was instructed
over USB to run its Wi-Fi OTA updater. Initial readback showed a31ed74;
the board then downloaded and verified two changed files and recorded
a22378c installed. All 26 on-device payload hashes matched the release.
Battery readback was 100%; the full-battery wave render returned successfully
and SHOW_LAST_UPDATED was False. The board was soft-reset and serial closed.
The owner subsequently confirmed the splash screen is live on the physical
display. Installation, render completion, and owner-observed appearance are
confirmed; contest photos and video are still pending.
Evidence: outputs/wave-ota-2026-09-27_134722/verification.txt in the task workspace.
The earlier capture also recorded a September 27 06:58 UTC watchdog recovery
at render on the preceding firmware; no root cause was established here.

## September 27, 2026 — full-battery wave splash

OTA a22378c restores the Great Wave screen only when the reported battery
percentage is at least 100. Charging below 100 keeps the adventure screen;
the next render below 100 restores it. A full battery may still report 100
after unplugging, so this is a battery-level trigger, not USB detection.
Weather/network work and OTA checks continue on scheduled updates. The time
and battery footer remain hidden. The detail card remains button-accessible.
Validation: 69 desktop tests passed, including 99/100 percent with both charging
states and the return below full; all 26 OTA hashes verified. Device installation
and physical appearance are not yet confirmed. To revert, restore main.py and
ui_renderer.py from the preceding release and generate a new OTA manifest.

## September 27, 2026 — hide diagnostic footer

OTA version a31ed74 disables SHOW_LAST_UPDATED in config.py, removing both
the update-time stamp and its battery telemetry from the main display footer.
Battery logging, protection, and the detail-card battery row remain available.
Validation: 68 desktop tests passed, a direct recording-canvas check drew no
footer with time and battery data present, and all 26 committed OTA payload
hashes verified. The first test attempt lacked requests; rerun passed after
installing desktop dependencies. Physical appearance and installed version
remain unconfirmed until the board refreshes after installing this release.
Rollback: restore SHOW_LAST_UPDATED=True and publish a freshly generated
manifest; retain shared history. This release is prepared for upstream master.

## September 20, 2026 — seven-slot fridge schedule

Firmware payload version: 8ec6ad1 (local source commit). The release includes
five solar daylight slots and two night slots, persistent attempt/completion
records, an explicit plugged-in mode, early critical-battery protection, and
one shared sleep duration for telemetry and hardware. The spacing fix remains.

The integrated desktop suite passed 68 tests. All 26 manifest payloads matched
committed bytes. Tests include early/reset duplicate prevention, two-day slot
counts, failure handling, year rollover and UTC-offset changes. Historical
retention concerns are no longer a deployment gate, per owner observation.

Documentation, contest materials and the CI/verifier workflow are included in
this release rather than remaining local-only. Earlier entries below describe
their status at the time. The board is on the fridge: no serial connection or
new installed-version readback was performed. Device installation and endurance
under the new cadence remain pending after publication.

OTA remains a per-file update without transactional rollback. To undo this
schedule, restore the previous main/config/scheduler, remove wake_plan from the
manifest, and generate a fresh manifest version. Do not force-reset shared master.

## September 19, 2026 — device feedback and editorial revision

The owner reported that spacing on the physical device is now much better.
This is user-observed confirmation of the improvement, not a serial readback
of the installed version. It supersedes the earlier appearance-unconfirmed
status below. Battery endurance and retention remain unmeasured here.

The contest article was shortened to remove repeated product framing and
module-by-module detail. Build commands and audit detail remain in supporting
documents. The new draft includes the observed spacing improvement and calls
for an updated physical photo. This editorial change is local and not submitted.

## September 19, 2026 — adventure spacing OTA

- Previous upstream baseline: c79de1fe3ac811d50df32460c548696b570bf1d6.
- Firmware change: 63f7e85a8dfa266bdca1f8e84f0cfeac38f5201a.
- Manifest/release commit: 71698513eb0cbe908afbf106c80893da2df27b72.
- Published OTA version: 63f7e85.
- Changed runtime file: ui_renderer.py. Added tests/test_layout_spacing.py.
- Behavior: reserve the full adventure text height before suggestions; reduce
  font size on crowded layouts to keep suggestions above the sun region.
- Validation during preparation: 47 desktop tests passed; before/after desktop
  preview visually inspected. Preview uses Arial, not exact panel font metrics.
- A September 19 rerun was blocked by a local dependency PermissionError; that
  attempt was not a passing test run. The published source matches the earlier
  tested source. The Git tree SHA was identical on both publication attempts.
- Publication: initial attempt was interrupted before master advanced. On
  September 19, both commits were created and master advanced in one non-forced
  ref update. Raw GitHub renderer content and manifest version were read back
  and matched the intended release.
- Device installation: NOT CONFIRMED. No serial connection, device logs or
  installed-version readback were obtained. Availability on GitHub is distinct
  from successful installation on the device.
- Physical appearance after update: NOT CONFIRMED.

## September 18–19, 2026 — documentation and desktop tooling

Prepared on docs/contest-readiness from c79de1f. This work includes the build
guide, contest draft and media, validation plans, GitHub Actions workflow,
manifest verifier and eight verifier tests. The 51-test documentation branch
suite passed on September 18. These eight tests and the four spacing tests
were run on separate branches; a combined 55-test suite has not been run.

This work was initially staged but uncommitted. The September 19 audit
checkpoints it in local Git history. It has NOT been pushed to GitHub, so
the new CI workflow is NOT active upstream. Exported ZIP/HTML/patch files
are deliverables, not a substitute for a Git commit or remote backup.

The contest materials describe the September 18 baseline. Their statements
about pending spacing work and unchanged runtime apply to that preparation,
not to the September 19 OTA release above.

## Rollback procedure

Use a new release; do not force-reset shared master or rewrite history.

1. Fetch current master and inspect intervening changes from every collaborator.
2. On a rollback branch, revert firmware commit 63f7e85, resolving any overlap
   with later work. Keep unrelated changes. Commit the restored renderer.
3. Run the relevant tests. Adjust the regression expectations explicitly if
   intentionally restoring the prior overlapping behavior.
4. Regenerate ota_manifest.json from that committed code with
   tools/make_ota_manifest.py. This gives the rollback a new version and hashes.
5. Verify all manifest payloads and commit the manifest.
6. Publish the reviewed rollback release to master without forcing history.
7. Confirm OTA availability separately from device installation and appearance.

Git preserves earlier source versions. The current device updater does not
provide automatic transactional rollback during a failed installation; a
device unable to boot or connect may need serial recovery.

## Change record standard for future work

Record the reason, affected files, test results and limitations, commit IDs,
OTA version, publication state, device confirmation, and rollback path for each
release. Keep documentation work separate from firmware releases. Before
publishing, check current upstream state so another agent's changes are not
overwritten. Do not mark a release installed based only on a successful push.
