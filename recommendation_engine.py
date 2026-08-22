"""Deterministic rule engine: day context -> activities + footer message.

Adding a rule = appending one Rule(...) to RULES. Each rule has:
  when      - predicate over the day context
  gives     - activities it suggests
  priority  - higher priority rules place their activities first
  special   - if True, its `banner` can appear as the footer message

The engine collects activities from every matching rule (highest
priority first), de-duplicates, and returns at most MAX_ACTIVITIES.
"""

MAX_ACTIVITIES = 3


class Rule:
    def __init__(self, name, when, gives, priority=0,
                 special=False, banner=None, hours=None):
        self.name = name
        self.when = when
        self.gives = gives
        self.priority = priority
        self.special = special
        self.banner = banner
        self.hours = hours          # (start, end) local hours, else always

    def active(self, ctx):
        if self.hours is not None:
            start, end = self.hours
            h = ctx["hour"]
            if start <= end:
                inside = start <= h < end
            else:                       # window wraps midnight
                inside = h >= start or h < end
            if not inside:
                return False
        return self.when(ctx)


def _mild(c):
    return 55 <= c["feels_like"] <= 85


def _golden_sunset(c):
    """Broken clouds + calm air = photogenic sunset."""
    return (15 <= c["cloud_cover"] <= 60 and c["rain_prob"] < 30
            and c["wind"] < 15)


def _stargazing(c):
    dark_moon = c["moon_phase"] < 0.25 or c["moon_phase"] > 0.75
    return c["cloud_cover"] < 25 and c["rain_prob"] < 20 and dark_moon


RULES = [
    # ---- Severe weather --------------------------------------------------
    Rule("severe weather",
         when=lambda c: c["condition"] == "severe",
         gives=["Stay In", "Check On Someone", "Charge Your Devices"],
         priority=300),

    # ---- Night watch -----------------------------------------------------
    Rule("night watch",
         when=lambda c: c.get("is_night_watch"),
         gives=["A Glass Of Water", "One More Chapter", "Back To Bed"],
         priority=200),

    # ---- Special events (footer banners) --------------------------------
    Rule("first snow",
         when=lambda c: c["is_first_snow"],
         gives=["Watch The Snowfall", "Hot Chocolate"],
         priority=100, special=True,
         banner="FIRST SNOW OF THE YEAR"),
    Rule("rare perfect day",
         when=lambda c: c["score"] >= 96,
         gives=[],
         priority=95, special=True,
         banner="ONLY A FEW DAYS ARE THIS NICE"),
    Rule("perfect weekend day",
         when=lambda c: c["score"] >= 88 and c["is_weekend"],
         gives=[],
         priority=90, special=True,
         banner="GO MAKE A MEMORY"),
    Rule("great sunset tonight",
         when=lambda c: _golden_sunset(c),
         gives=["Sunset Walk"],
         priority=60, special=True,
         banner="DON'T MISS TONIGHT'S SUNSET"),
    Rule("stargazing",
         when=lambda c: _stargazing(c),
         gives=["Stargazing Tonight"],
         priority=55, special=True,
         banner="EXCELLENT STARGAZING TONIGHT"),
    Rule("peak autumn",
         when=lambda c: c["season"] == "autumn" and c["month"] == 10
         and c["condition"] in ("clear", "partly") and _mild(c),
         gives=["Walk In The Leaves"],
         priority=70, special=True,
         banner="PEAK AUTUMN HAS ARRIVED"),
    Rule("window weather",
         when=lambda c: 62 <= c["temp"] <= 78 and c["humidity"] < 65
         and c["rain_prob"] < 25,
         gives=["Open The Windows"],
         priority=40, special=True,
         banner="PERFECT WINDOW OPENING WEATHER"),

    # ---- Beautiful days -------------------------------------------------
    Rule("perfect warm day",
         when=lambda c: 68 <= c["feels_like"] <= 84 and c["rain_prob"] < 25
         and c["wind"] < 12 and c["condition"] in ("clear", "partly"),
         gives=["Eat Outside", "Go For A Hike", "Sunset Walk"],
         priority=50, hours=(6, 19)),
    Rule("mild day any sky",
         when=lambda c: _mild(c) and c["rain_prob"] < 30 and c["wind"] < 15
         and c["condition"] not in ("rain", "storm", "snow"),
         gives=["Go For A Walk", "Eat Outside"],
         priority=42),
    Rule("weekend adventure",
         when=lambda c: c["is_weekend"] and _mild(c)
         and c["rain_prob"] < 35,
         gives=["Farmers Market", "Take A Day Trip", "Picnic"],
         priority=45, hours=(6, 15)),
    Rule("golden evening",
         when=lambda c: _mild(c) and c["rain_prob"] < 35
         and c["condition"] not in ("rain", "storm", "snow"),
         gives=["Sunset Walk", "Eat Dinner Outside", "Evening Stroll"],
         priority=55, hours=(17, 22)),
    Rule("hot day",
         when=lambda c: c["feels_like"] > 85,
         gives=["Go Swimming", "Ice Cream Run", "Find Some Shade"],
         priority=40, hours=(8, 19)),
    Rule("crisp day",
         when=lambda c: 40 <= c["feels_like"] < 58
         and c["condition"] not in ("rain", "storm"),
         gives=["Brisk Walk", "Coffee Outside", "Take Photos"],
         priority=35, hours=(6, 18)),
    Rule("spring gardening",
         when=lambda c: c["season"] == "spring" and _mild(c)
         and c["rain_prob"] < 40,
         gives=["Great Day For Gardening"],
         priority=30, hours=(7, 18)),

    # ---- Rain -----------------------------------------------------------
    Rule("cozy rain",
         when=lambda c: c["condition"] in ("rain", "storm")
         and c["temp"] < 65,
         gives=["Read A Book", "Make Soup", "Movie Night",
                "Coffee Shop Weather"],
         priority=40),
    Rule("warm rain",
         when=lambda c: c["condition"] in ("rain", "storm")
         and c["temp"] >= 65,
         gives=["Listen To The Rain", "Bake Something", "Read A Book"],
         priority=40),
    Rule("rain later",
         when=lambda c: c["condition"] not in ("rain", "storm", "snow")
         and c["rain_prob"] >= 60 and c["temp"] > 36,
         gives=["Walk Before The Rain"],
         priority=38, special=True,
         banner="RAIN IS COMING"),

    # ---- Snow -----------------------------------------------------------
    Rule("snow day",
         when=lambda c: c["condition"] == "snow",
         gives=["Play In The Snow", "Hot Chocolate",
                "Watch The Snowfall"],
         priority=45),
    Rule("weekend snow",
         when=lambda c: c["condition"] == "snow" and c["is_weekend"],
         gives=["Build A Snowman"],
         priority=50),

    # ---- Cold / gray ----------------------------------------------------
    Rule("deep cold",
         when=lambda c: c["feels_like"] < 25,
         gives=["Stay Cozy", "Bake Something", "Call Someone You Love"],
         priority=35),
    Rule("gray day",
         when=lambda c: c["condition"] in ("cloudy", "fog")
         and not c["is_weekend"] and c["score"] < 65,
         gives=["Light A Candle", "Make Tea", "Read A Book"],
         priority=20),

    # ---- Fallback (always matches) --------------------------------------
    Rule("any day",
         when=lambda c: True,
         gives=["Take A Short Walk", "Make A Good Meal",
                "Call Someone You Love"],
         priority=0),
]


# Words too generic to count as a repeated concept.
_STOP = {"a", "an", "and", "the", "for", "of", "to", "in", "on", "is",
         "it", "its", "at", "day", "days", "today", "tonight", "this",
         "go", "take", "make", "some", "one", "more", "great",
         "perfect", "good", "nice", "weather", "time", "now", "later",
         "arrives", "while", "world", "your", "you", "out", "get"}


def _tokens(text):
    out = []
    for word in text.lower().replace("'", " ").split():
        word = "".join(ch for ch in word if ch.isalpha())
        if len(word) >= 3 and word not in _STOP:
            out.append(word)
    return out


def _same_concept(a, b):
    """'walk'/'walking', 'read'/'reading', 'stars'/'stargazing' all
    match: equal words, or equal 4-letter stems."""
    for x in a:
        for y in b:
            if x == y or (len(x) >= 4 and len(y) >= 4
                          and x[:4] == y[:4]):
                return True
    return False


def recommend(ctx, avoid=None):
    """Returns up to MAX_ACTIVITIES gentle suggestions for today.

    ctx must already contain ctx["score"]. `avoid` is text already on
    screen (headline + wonder): suggestions repeating one of its
    concepts — "GREAT DAY FOR A WALK" then "Take A Short Walk" — are
    passed over, as are suggestions repeating each other. If that
    leaves too few, the repeats fill back in rather than showing a
    sparse list.
    """
    matched = [r for r in RULES if r.active(ctx)]
    matched.sort(key=lambda r: -r.priority)

    candidates = []
    for rule in matched:
        for act in rule.gives:
            if act not in candidates:
                candidates.append(act)

    avoid_tokens = _tokens(avoid) if avoid else []
    chosen, chosen_tokens = [], []

    def try_add(act, respect_avoid):
        toks = _tokens(act)
        if respect_avoid and _same_concept(toks, avoid_tokens):
            return
        for prior in chosen_tokens:
            if _same_concept(toks, prior):
                return
        chosen.append(act)
        chosen_tokens.append(toks)

    for act in candidates:
        if len(chosen) >= MAX_ACTIVITIES:
            break
        try_add(act, respect_avoid=True)
    for act in candidates:          # refill pass: allow avoid-repeats
        if len(chosen) >= MAX_ACTIVITIES:
            break
        if act not in chosen:
            try_add(act, respect_avoid=False)

    return chosen[:MAX_ACTIVITIES]
