"""Analyze a downloaded wake_log.txt: drain curve, runtime, anomalies.

Usage: python tools/battery_report.py logs/wake_log_YYYY-MM-DD.txt
"""

import datetime
import re
import sys

LINE = re.compile(r"(\d{4}-\d\d-\d\d \d\d:\d\d)\s+(.*)")
BATT = re.compile(r"batt=(\d+)%\s+(\d+)mV")
CHG = re.compile(r"batt=chg\s+(\d+)mV")


def parse(path):
    rows, events = [], []
    for raw in open(path, encoding="utf-8", errors="replace"):
        m = LINE.search(raw)
        if not m:
            continue
        when = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
        rest = m.group(2).strip()
        b = BATT.search(rest)
        if b:
            rows.append((when, int(b.group(1)), int(b.group(2))))
        if ("FAILED" in rest or "WATCHDOG" in rest
                or "clock unknown" in rest):
            events.append((when, rest))
    return rows, events


def main():
    path = sys.argv[1]
    rows, events = parse(path)
    if not rows:
        print("no battery readings found")
        return

    print("=" * 62)
    print("BATTERY READINGS: %d" % len(rows))
    print("=" * 62)
    prev = None
    for when, pct, mv in rows:
        gap = ""
        if prev and (when - prev).total_seconds() > 7200:
            gap = "   <-- GAP %.1f h (device was down)" % (
                (when - prev).total_seconds() / 3600.0)
        print("  %s  %3d%%  %4dmV%s"
              % (when.strftime("%a %m-%d %H:%M"), pct, mv, gap))
        prev = when

    # longest continuous discharge run (percent monotonically falling)
    best = cur = [rows[0]]
    for r in rows[1:]:
        if r[1] <= cur[-1][1] and (r[0] - cur[-1][0]).total_seconds() < 7200:
            cur.append(r)
        else:
            if len(cur) > len(best):
                best = cur
            cur = [r]
    if len(cur) > len(best):
        best = cur

    t0, p0, v0 = best[0]
    t1, p1, v1 = best[-1]
    hours = (t1 - t0).total_seconds() / 3600.0
    print()
    print("=" * 62)
    print("LONGEST DISCHARGE RUN")
    print("=" * 62)
    print("  from %s  %3d%% %4dmV" % (t0.strftime("%a %m-%d %H:%M"), p0, v0))
    print("  to   %s  %3d%% %4dmV" % (t1.strftime("%a %m-%d %H:%M"), p1, v1))
    print("  duration: %.1f h (%.1f days) over %d wakes"
          % (hours, hours / 24.0, len(best)))
    if hours > 0 and p0 > p1:
        rate = (p0 - p1) / hours
        print("  drain: %.2f %%/h  |  %.1f mV/h"
              % (rate, (v0 - v1) / hours))
        print("  => full charge (100%% -> 0%%) projects to %.1f h "
              "(%.1f days)" % (100.0 / rate, 100.0 / rate / 24.0))

    if events:
        print()
        print("=" * 62)
        print("ANOMALIES")
        print("=" * 62)
        for when, rest in events:
            print("  %s  %s" % (when.strftime("%a %m-%d %H:%M"), rest))


if __name__ == "__main__":
    main()
