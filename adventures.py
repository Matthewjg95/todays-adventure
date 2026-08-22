"""The daily local adventure: one real place or outing near home,
picked deterministically per day, shown ALL day — rain or shine, cold
or gray — and suppressed only when the weather is genuinely inclement.

The suggestions above it are moods; this line is a plan.

Editing: add entries to ADVENTURES. Fields:
  name          what shows on screen (keep it under ~26 chars)
  seasons       tuple of seasons it makes sense in (or ALL)
  weekend_only  True if it only works on Sat/Sun (markets, day trips)
  min_high      skip unless the day's high reaches this (swimming)
  max_high      skip when hotter than this (strenuous hikes)
"""

ALL = ("winter", "spring", "summer", "autumn")
WARM = ("spring", "summer", "autumn")

ADVENTURES = [
    # --- big classics -------------------------------------------------
    {"name": "Green Lakes loop", "seasons": ALL},
    {"name": "Onondaga Lake Park loop", "seasons": ALL},
    {"name": "Creekwalk to the lake", "seasons": WARM},
    {"name": "Clark Reservation cliffs", "seasons": WARM},
    {"name": "Beaver Lake boardwalk", "seasons": ALL},
    {"name": "Tinker Falls walk", "seasons": WARM},
    {"name": "Chittenango Falls", "seasons": WARM},
    {"name": "Pratt's Falls", "seasons": WARM},
    {"name": "Labrador Hollow boardwalk", "seasons": WARM},
    {"name": "Highland Forest trails", "seasons": ALL},
    {"name": "Erie Canalway ride", "seasons": WARM, "min_high": 55},
    # --- water days ---------------------------------------------------
    {"name": "Jamesville Beach swim", "seasons": ("summer",),
     "min_high": 78},
    {"name": "Oneida Shores swim", "seasons": ("summer",),
     "min_high": 78},
    {"name": "Skaneateles pier walk", "seasons": WARM},
    {"name": "Sylvan Beach sunset", "seasons": ("summer",),
     "weekend_only": True},
    # --- town ---------------------------------------------------------
    {"name": "Regional Market morning", "seasons": ALL,
     "weekend_only": True},
    {"name": "Westcott street wander", "seasons": ALL},
    {"name": "Thornden rose garden", "seasons": ("spring", "summer")},
    {"name": "Everson plaza + a coffee", "seasons": ALL},
    {"name": "Rosamond Gifford Zoo", "seasons": ALL},
    {"name": "Little Italy bakery run", "seasons": ALL},
    # --- winter-specific ----------------------------------------------
    {"name": "Highland Forest ski trails", "seasons": ("winter",)},
    {"name": "Green Lakes on snowshoes", "seasons": ("winter",)},
    {"name": "Long Branch winter walk", "seasons": ("winter",),
     "max_high": 40},
]


def _inclement(ctx):
    """The ONLY thing that hides the adventure. Cold and gray are not
    inclement; dangerous or truly miserable is."""
    return (ctx["condition"] == "severe"
            or ctx["condition"] in ("storm", "rain")
            or (ctx["condition"] == "snow" and ctx["wind"] >= 15)
            or ctx["rain_prob"] >= 70
            or ctx["feels_like"] <= 10
            or ctx["feels_like"] >= 98)


def _eligible(a, ctx):
    if ctx["season"] not in a["seasons"]:
        return False
    if a.get("weekend_only") and not ctx["is_weekend"]:
        return False
    if "min_high" in a and ctx["high"] < a["min_high"]:
        return False
    if "max_high" in a and ctx["high"] > a["max_high"]:
        return False
    return True


def today(ctx):
    """The day's adventure name, or None (night watch / inclement /
    nothing eligible). Same answer all day: seeded by the date, not
    the hour, so the plan survives every hourly refresh."""
    if ctx.get("is_night_watch"):
        return None
    if _inclement(ctx):
        return None
    pool = [a for a in ADVENTURES if _eligible(a, ctx)]
    if not pool:
        return None
    seed = ctx["year"] * 10000 + ctx["month"] * 100 + ctx["day"]
    return pool[seed % len(pool)]["name"]
