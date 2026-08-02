"""Headlines, and the internal "ease" number that helps pick them.

Philosophy: the score is NOT shown — every day has a reason to be
beautiful, and ranking days 1-100 quietly contradicts that. The number
survives only as an internal signal for how easy it is to be outside,
which helps route between headlines and rules. Nothing user-facing
should ever print it.
"""


def _temp_points(feels_like):
    """0-40 points. Peak comfort around 72F, gentle falloff."""
    ideal = 72.0
    diff = abs(feels_like - ideal)
    pts = 40.0 - diff * 1.1
    return max(0.0, pts)


def _sky_points(cloud_cover, condition):
    """0-20 points for pleasant skies."""
    if condition in ("rain", "storm"):
        return 2.0
    if condition == "snow":
        return 8.0   # snow is pretty!
    if condition == "fog":
        return 5.0
    return 20.0 - (cloud_cover / 100.0) * 12.0


def _rain_points(rain_prob, condition):
    """0-20 points for staying dry."""
    if condition in ("rain", "storm"):
        return 0.0
    return 20.0 - (rain_prob / 100.0) * 18.0


def _wind_points(wind):
    """0-10 points for calm air."""
    if wind <= 5:
        return 10.0
    if wind >= 25:
        return 0.0
    return 10.0 * (25.0 - wind) / 20.0


def score_day(ctx):
    pts = 12.0  # floor: no day scores near zero
    pts += _temp_points(ctx["feels_like"])
    pts += _sky_points(ctx["cloud_cover"], ctx["condition"])
    pts += _rain_points(ctx["rain_prob"], ctx["condition"])
    pts += _wind_points(ctx["wind"])
    if ctx["is_weekend"]:
        pts += 4.0
    return max(1, min(100, int(round(pts))))


# --- Headline -------------------------------------------------------------
# Ordered rules; first match wins. Each: (predicate, headline).

def _perfect_outdoor(ctx, score):
    return score >= 92


def _headline_rules():
    return (
        (lambda c, s: c.get("is_night_watch"),
         "WHILE THE WORLD SLEEPS"),
        (lambda c, s: c["is_first_snow"],
         "FIRST SNOW OF THE YEAR"),
        (lambda c, s: s >= 96,
         "GO MAKE A MEMORY"),
        (lambda c, s: s >= 92 and c["season"] == "summer",
         "PERFECT SUMMER DAY"),
        (lambda c, s: s >= 92 and c["season"] == "spring",
         "PERFECT SPRING DAY"),
        (lambda c, s: s >= 92 and c["season"] == "autumn",
         "PERFECT AUTUMN DAY"),
        (lambda c, s: s >= 92,
         "PERFECT OUTDOOR WEATHER"),
        (lambda c, s: s >= 84,
         "GREAT DAY FOR A WALK"),
        (lambda c, s: s >= 74 and c["temp"] >= 62 and c["temp"] <= 78
            and c["condition"] not in ("rain", "storm"),
         "OPEN THE WINDOWS TODAY"),
        (lambda c, s: s >= 74,
         "GET OUTSIDE TODAY"),
        (lambda c, s: c["feels_like"] > 85
            and c["condition"] in ("clear", "partly"),
         "PERFECT POOL WEATHER"),
        (lambda c, s: c["condition"] == "snow",
         "A SNOW DAY IS A GIFT"),
        (lambda c, s: c["condition"] in ("rain", "storm") and s >= 55,
         "PERFECT READING WEATHER"),
        (lambda c, s: c["condition"] in ("rain", "storm"),
         "MOVIE NIGHT WEATHER"),
        (lambda c, s: s >= 60,
         "PERFECT READING WEATHER"),
        (lambda c, s: s >= 48,
         "SLOW DOWN AND ENJOY IT"),
        (lambda c, s: c["feels_like"] < 25,
         "BUNDLE UP, IT'S BEAUTIFUL"),
        (lambda c, s: True,
         "STAY COZY TODAY"),
    )


def headline(ctx, score):
    for predicate, text in _headline_rules():
        if predicate(ctx, score):
            return text
    return "ENJOY TODAY"  # unreachable; last rule always matches
