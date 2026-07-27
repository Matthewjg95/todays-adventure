"""The Wonder Engine: finds the one thing worth noticing about today
and says it like a human would.

Output is a single warm sentence — the centerpiece of the display.
Deterministic: the same day always produces the same message (variants
are picked by date, not randomness, so the screen doesn't churn
between hourly refreshes).

Adding a wonder = appending one Wonder(...) to WONDERS.
Tone rules: warm, curious, occasionally playful. Never preachy,
never guilt. "The lake will be beautiful tonight", not "You should
exercise today."
"""


class Wonder:
    def __init__(self, name, when, messages, priority=0):
        self.name = name
        self.when = when
        self.messages = messages    # variants; picked by date
        self.priority = priority


def _day_seed(ctx):
    return ctx["year"] * 366 + ctx["month"] * 31 + ctx["day"]


def _clear_evening(c):
    return c["cloud_cover"] < 30 and c["rain_prob"] < 25


def _golden_sunset(c):
    return (15 <= c["cloud_cover"] <= 60 and c["rain_prob"] < 30
            and c["wind"] < 15)


def _full_moon(c):
    return 0.47 <= c["moon_phase"] <= 0.53


def _solstice_equinox(c):
    dates = {(3, 20): "spring begins",
             (6, 21): "longest day",
             (9, 22): "autumn begins",
             (12, 21): "longest night"}
    return dates.get((c["month"], c["day"]))


WONDERS = [
    Wonder("first snow",
           when=lambda c: c["is_first_snow"],
           messages=["The first snow is here.",
                     "It finally snowed. Go look."],
           priority=100),

    Wonder("longest day",
           when=lambda c: _solstice_equinox(c) == "longest day",
           messages=["Today is the longest day of the year."],
           priority=90),
    Wonder("longest night",
           when=lambda c: _solstice_equinox(c) == "longest night",
           messages=["Tonight is the longest night of the year. "
                     "The light returns tomorrow."],
           priority=90),
    Wonder("spring begins",
           when=lambda c: _solstice_equinox(c) == "spring begins",
           messages=["Spring officially arrives today."],
           priority=90),
    Wonder("autumn begins",
           when=lambda c: _solstice_equinox(c) == "autumn begins",
           messages=["Autumn officially arrives today."],
           priority=90),

    Wonder("first warm day",
           when=lambda c: c.get("is_first_warm_day"),
           messages=["The warm days are back.",
                     "First truly warm day of the year. It's here."],
           priority=85),

    Wonder("rare perfect day",
           when=lambda c: c["score"] >= 96,
           messages=["Only a few days each year are this nice.",
                     "Whatever you postponed — today is the day for it."],
           priority=80),

    Wonder("perfect summer day",
           when=lambda c: c["score"] >= 90 and c["season"] == "summer",
           messages=["Summer won't wait.",
                     "This is the kind of day you remember in January."],
           priority=70),

    Wonder("full moon tonight",
           when=lambda c: _full_moon(c) and _clear_evening(c),
           messages=["The moon is beautiful tonight.",
                     "Look up after dark. The moon is full."],
           priority=65),

    Wonder("great sunset",
           when=lambda c: _golden_sunset(c),
           messages=["It's difficult to waste a sunset like this one.",
                     "Tonight's sunset deserves a witness."],
           priority=60),

    Wonder("stargazing",
           when=lambda c: _clear_evening(c)
           and (c["moon_phase"] < 0.25 or c["moon_phase"] > 0.75),
           messages=["The stars will be out tonight.",
                     "A dark sky, no clouds. Look up tonight."],
           priority=55),

    Wonder("window weather",
           when=lambda c: 62 <= c["temp"] <= 78 and c["humidity"] < 65
           and c["rain_prob"] < 25,
           messages=["Perfect window opening weather.",
                     "Let a little of today inside."],
           priority=50),

    Wonder("snowing now",
           when=lambda c: c["condition"] == "snow",
           messages=["The world is quieter when it snows.",
                     "Snow is falling right now. Watch it for a minute."],
           priority=48),

    Wonder("rain coming",
           when=lambda c: c["condition"] not in ("rain", "storm", "snow")
           and c["rain_prob"] >= 60 and c["temp"] > 36,
           messages=["Rain is on its way. The air smells like it.",
                     "Walk now. The rain arrives later."],
           priority=45),

    Wonder("cozy rain",
           when=lambda c: c["condition"] in ("rain", "storm"),
           messages=["The rain is doing the hard work of "
                     "making today cozy.",
                     "Listen to the rain for a minute."],
           priority=40),

    Wonder("crisp autumn",
           when=lambda c: c["season"] == "autumn"
           and 40 <= c["feels_like"] <= 60
           and c["condition"] in ("clear", "partly"),
           messages=["The air is exactly as crisp as it should be.",
                     "The leaves are doing something worth seeing."],
           priority=35),

    Wonder("fog",
           when=lambda c: c["condition"] == "fog",
           messages=["The fog makes everything look like a memory."],
           priority=35),

    # ---- Seasonal defaults (always something worth noticing) ----------
    Wonder("summer default",
           when=lambda c: c["season"] == "summer",
           messages=["Take the long way home today.",
                     "The evenings are long right now. Use one."],
           priority=0),
    Wonder("autumn default",
           when=lambda c: c["season"] == "autumn",
           messages=["Autumn only does this once a year.",
                     "A good day to notice the trees."],
           priority=0),
    Wonder("winter default",
           when=lambda c: c["season"] == "winter",
           messages=["Winter light is the softest light.",
                     "Warm drinks taste better on days like this."],
           priority=0),
    Wonder("spring default",
           when=lambda c: c["season"] == "spring",
           messages=["Something new bloomed today. Find it.",
                     "Everything outside is busy growing."],
           priority=0),
]


def wonder(ctx):
    """Return today's one sentence worth reading."""
    best = None
    for w in WONDERS:
        if w.when(ctx) and (best is None or w.priority > best.priority):
            best = w
    if best is None:
        return "Today only happens once."
    return best.messages[_day_seed(ctx) % len(best.messages)]
