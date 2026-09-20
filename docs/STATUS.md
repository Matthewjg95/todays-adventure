# Status on September 18, 2026

## Baseline

- Upstream branch: master, commit c79de1f (contest planning documentation).
- OTA payload version: 80b4bd4, 25 files.
- Current firmware mitigation: repaint every update; watchdog stage breadcrumbs.
- Latest firmware commit reports field fading and approximately five hangs/day.
  No current device log was available to close either issue.
- Existing desktop suite: 43 tests passed during the baseline review.
- GitHub had no open PRs or issues and no Actions runs when inspected.
- The two remote experiment branches are ancestors of master.

## Prepared in docs/contest-readiness

Complete build and release documentation, a contest article and media package,
a hardware evidence checklist, desktop CI, and a read-only OTA manifest verifier.
Eight verifier tests cover intact releases and failures such as missing scenes,
changed payloads, wrong destinations and unreadable committed files.

No device-facing runtime file or OTA manifest was changed. Serial ports were not
opened, firmware was not installed, and no contest entry was submitted.

## Next work

1. Review the contest article; capture its required physical video when available.
2. Collect a 24–48-hour device run and classify watchdog stages.
3. Address the adventure/suggestion spacing on a separate firmware branch and
   verify the result with actual font metrics and a physical screen.
4. Revisit retention and charging classification based on the new evidence.
5. Treat interrupted OTA recovery as a separate engineering improvement.

See [contest package](contest/PACKAGE.md), [build guide](BUILD_GUIDE.md) and
[device validation](DEVICE_VALIDATION.md).
