"""Worthy life events: the days the display should honor above all
weather. Three pools — custom (yours), celestial (the sky's), and
local (the city's) — merged and ranked; the top event of the day takes
over the wonder line.

This file is OTA-delivered: edit it, push to GitHub, and the wall
knows within the hour. That IS the pipeline.

Fields:
  month/day     when (year optional: one-shot events like an eclipse)
  name          short label (internal)
  message       what the display says — warm, human, one line-ish
  span          extra days after month/day the event stays live
  priority      higher wins the day (customs default above the rest)
"""

CUSTOM = [
    # --- yours: birthdays, anniversaries, traditions -----------------
    # {"month": 5, "day": 14, "name": "mom's birthday",
    #  "message": "Call your mom. It's her day."},
]

CELESTIAL = [
    {"month": 8, "day": 12, "span": 1, "name": "perseids",
     "message": "The Perseids peak tonight. Look up after midnight."},
    {"month": 12, "day": 13, "span": 1, "name": "geminids",
     "message": "The Geminids peak tonight — winter's best meteors."},
    {"month": 1, "day": 3, "span": 1, "name": "quadrantids",
     "message": "The Quadrantid meteors peak tonight."},
    {"month": 4, "day": 22, "span": 1, "name": "lyrids",
     "message": "The Lyrid meteors peak tonight."},
    {"month": 10, "day": 21, "span": 1, "name": "orionids",
     "message": "The Orionids peak tonight — dust from Halley's Comet."},
    # one-shots worth marking years ahead
    {"year": 2026, "month": 8, "day": 12, "name": "total eclipse europe",
     "message": "A total solar eclipse crosses Spain today."},
    {"year": 2029, "month": 4, "day": 13, "name": "apophis",
     "message": "Asteroid Apophis passes closer than our satellites today."},
]

LOCAL = [
    # --- Syracuse rhythms --------------------------------------------
    {"month": 8, "day": 26, "span": 13, "name": "nys fair",
     "message": "The Great New York State Fair is on. Go once, at least."},
    {"month": 6, "day": 14, "span": 2, "name": "taste of syracuse",
     "message": "Taste of Syracuse weekend — eat downtown."},
    {"month": 9, "day": 12, "span": 1, "name": "westcott fair",
     "message": "Westcott Street Fair — the neighborhood at its best."},
    {"month": 12, "day": 1, "span": 30, "name": "lights on the lake",
     "message": "Lights on the Lake is glowing at Onondaga Lake Park."},
]


def _live(e, ctx):
    if "year" in e and e["year"] != ctx["year"]:
        return False
    span = e.get("span", 0)
    m, d = ctx["month"], ctx["day"]
    # walk each day of the window (handles month boundaries)
    em, ed = e["month"], e["day"]
    _mdays = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    for _ in range(span + 1):
        if (em, ed) == (m, d):
            return True
        ed += 1
        if ed > _mdays[em - 1]:
            ed, em = 1, em % 12 + 1
    return False


def today(ctx):
    """The day's top event message, or None. Customs outrank
    celestial outrank local, unless a priority says otherwise."""
    best, best_rank = None, -1
    for rank, pool in ((3, CUSTOM), (2, CELESTIAL), (1, LOCAL)):
        for e in pool:
            if _live(e, ctx):
                r = e.get("priority", rank)
                if r > best_rank:
                    best, best_rank = e, r
    return best["message"] if best else None
