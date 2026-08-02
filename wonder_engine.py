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
    def __init__(self, name, when, messages, priority=0, night=False):
        self.name = name
        self.when = when
        self.messages = messages    # variants; picked by date
        self.priority = priority
        self.night = night          # night-watch renders only


def _day_seed(ctx):
    seed = ctx["year"] * 366 + ctx["month"] * 31 + ctx["day"]
    if ctx.get("is_night_watch"):
        # night wakes each get their own variant, not one all night
        seed += ctx["hour"] * 7
    return seed


def _tomorrow(ctx):
    return ctx.get("tomorrow") or {}


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


# Annual meteor showers: (month, day) of peak -> name. Peaks drift a
# day either way year to year; we celebrate a two-night window.
_METEORS = {
    (1, 3): "Quadrantid", (1, 4): "Quadrantid",
    (4, 22): "Lyrid", (4, 23): "Lyrid",
    (5, 5): "Eta Aquariid", (5, 6): "Eta Aquariid",
    (8, 11): "Perseid", (8, 12): "Perseid", (8, 13): "Perseid",
    (10, 21): "Orionid", (10, 22): "Orionid",
    (11, 17): "Leonid", (11, 18): "Leonid",
    (12, 13): "Geminid", (12, 14): "Geminid",
}


def _meteor_shower(c):
    return _METEORS.get((c["month"], c["day"]))


def _daylight_minutes(c):
    return c.get("sunset_minutes", 0) - c.get("sunrise_minutes", 0)


def _warmer_than_yesterday(c, degrees):
    d = c.get("temp_delta")
    return d is not None and d >= degrees


def _cooler_than_yesterday(c, degrees):
    d = c.get("temp_delta")
    return d is not None and d <= -degrees


WONDERS = [
    # ---- Night watch (only during the 3 scheduled night wakes) --------
    Wonder("umbrella warning",
           when=lambda c: c.get("is_night_watch")
           and _tomorrow(c).get("rain_prob", 0) >= 60,
           messages=["Rain before breakfast. Leave the "
                     "umbrella by the door.",
                     "Tomorrow arrives wet. Plan a slow morning."],
           priority=78, night=True),
    Wonder("frost warning",
           when=lambda c: c.get("is_night_watch")
           and _tomorrow(c).get("low", 99) <= 34,
           messages=["Frost by morning. The plants would "
                     "appreciate a blanket.",
                     "Cold night ahead. Warm socks are advised."],
           priority=78, night=True),
    Wonder("tomorrow snow",
           when=lambda c: c.get("is_night_watch")
           and _tomorrow(c).get("condition") == "snow",
           messages=["Snow is coming while you sleep. "
                     "Morning will look different.",
                     "Tonight the sky is wrapping presents. "
                     "Open the curtains first thing."],
           priority=79, night=True),
    Wonder("tomorrow beauty",
           when=lambda c: c.get("is_night_watch")
           and _tomorrow(c).get("rain_prob", 100) < 20
           and 58 <= _tomorrow(c).get("high", 0) <= 86,
           messages=["Tomorrow looks like a beauty. Sleep well.",
                     "Rest up. Tomorrow is worth waking for."],
           priority=76, night=True),
    Wonder("night full moon",
           when=lambda c: c.get("is_night_watch") and _full_moon(c),
           messages=["The moon is out doing its best work "
                     "right now."],
           priority=74, night=True),
    Wonder("night watch",
           when=lambda c: c.get("is_night_watch"),
           messages=["Still awake? So is the moon.",
                     "The night has its own kind of quiet.",
                     "Even the birds are asleep. "
                     "You made it further than they did.",
                     "Nothing needs you right now. That's rare."],
           priority=70, night=True),

    # ---- Meteor showers (night wake, or the evening before) ----------
    Wonder("meteor shower night",
           when=lambda c: c.get("is_night_watch")
           and _meteor_shower(c) and c["cloud_cover"] < 50,
           messages=["Meteors are falling right now. Go outside.",
                     "Look up, be patient, and you'll see one."],
           priority=88, night=True),
    Wonder("meteor shower evening",
           when=lambda c: _meteor_shower(c) and c["cloud_cover"] < 50
           and c["hour"] >= 16,
           messages=["Meteor shower tonight. Set an alarm for "
                     "after midnight.",
                     "Tonight the sky puts on a show. "
                     "Meteors after dark."],
           priority=88),

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
                     "Whatever you postponed: today is the day for it."],
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

    # ---- Yesterday's memory -------------------------------------------
    Wonder("heat broke",
           when=lambda c: _cooler_than_yesterday(c, 12)
           and c["high"] < 85,
           messages=["The heat finally broke.",
                     "Cooler than yesterday. You'll feel it "
                     "the moment you step out."],
           priority=63),
    Wonder("big warm up",
           when=lambda c: _warmer_than_yesterday(c, 12),
           messages=["Much warmer than yesterday. "
                     "The day opened up.",
                     "Yesterday's coat can stay inside."],
           priority=63),
    Wonder("cold snap",
           when=lambda c: _cooler_than_yesterday(c, 15),
           messages=["A proper cold snap. Yesterday feels "
                     "far away.",
                     "The cold arrived overnight. Dress like "
                     "you mean it."],
           priority=64),
    Wonder("sun returns",
           when=lambda c: c["condition"] in ("clear", "partly")
           and (c.get("yesterday") or {}).get("condition")
           in ("rain", "storm", "snow", "fog"),
           messages=["The sun came back.",
                     "After yesterday, this light feels earned."],
           priority=62),

    # ---- Daylight milestones -------------------------------------------
    Wonder("long evenings",
           when=lambda c: _daylight_minutes(c) >= 14 * 60
           and c["month"] in (5, 6, 7),
           messages=["Fourteen hours of daylight today. "
                     "Use the long end of it.",
                     "The evening goes on and on right now."],
           priority=30),
    Wonder("short days",
           when=lambda c: _daylight_minutes(c) <= 9 * 60 + 30
           and c["month"] in (11, 12, 1),
           messages=["Barely nine hours of daylight. "
                     "Catch what there is.",
                     "The light is scarce today. That makes it "
                     "worth more."],
           priority=30),
    Wonder("sunset past eight",
           when=lambda c: c.get("sunset_minutes", 0) >= 20 * 60
           and c.get("sunset_minutes", 0) < 20 * 60 + 10
           and c["month"] in (4, 5),
           messages=["The sun sets after eight now. "
                     "Summer is close."],
           priority=68),

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

    # ---- Seasonal texture ----------------------------------------------
    Wonder("deep summer",
           when=lambda c: c["month"] in (7, 8) and c["high"] >= 85,
           messages=["Deep summer. The kind of heat you'll "
                     "describe fondly in February.",
                     "Find some shade and stay a while."],
           priority=25),
    Wonder("early spring thaw",
           when=lambda c: c["month"] in (3, 4) and c["high"] >= 55
           and c["season"] == "spring",
           messages=["The ground is waking up.",
                     "Mud season. It means everything is thawing."],
           priority=25),
    Wonder("bare november",
           when=lambda c: c["month"] == 11,
           messages=["The trees are showing their bones.",
                     "November light is low and gold and brief."],
           priority=20),

    # ---- Seasonal defaults (always something worth noticing) ----------
    Wonder("summer default",
           when=lambda c: c["season"] == "summer",
           messages=["Take the long way home today.",
                     "The evenings are long right now. Use one.",
                     "Somewhere nearby, the water is warm.",
                     "Eat something outside today.",
                     "Summer is short. This is the middle of it."],
           priority=0),
    Wonder("autumn default",
           when=lambda c: c["season"] == "autumn",
           messages=["Autumn only does this once a year.",
                     "A good day to notice the trees.",
                     "The air smells different this month.",
                     "Sweater weather has its own quiet luxury.",
                     "Everything is turning. Watch it happen."],
           priority=0),
    Wonder("winter default",
           when=lambda c: c["season"] == "winter",
           messages=["Winter light is the softest light.",
                     "Warm drinks taste better on days like this.",
                     "The world is resting. You're allowed to, too.",
                     "Long nights make small lights matter more.",
                     "Cold air is good for the head."],
           priority=0),
    Wonder("spring default",
           when=lambda c: c["season"] == "spring",
           messages=["Something new bloomed today. Find it.",
                     "Everything outside is busy growing.",
                     "The birds started early this morning.",
                     "Green is coming back, a little each day.",
                     "Open a window for ten minutes."],
           priority=0),
]


def wonder(ctx):
    """Return today's one sentence worth reading. Night-watch renders
    draw only from the night pool, and vice versa."""
    at_night = bool(ctx.get("is_night_watch"))
    best = None
    for w in WONDERS:
        if w.night != at_night:
            continue
        if w.when(ctx) and (best is None or w.priority > best.priority):
            best = w
    if best is None:
        return "Today only happens once."
    return best.messages[_day_seed(ctx) % len(best.messages)]
