# Release and change record

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
