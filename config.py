"""Today's Adventure — configuration.

Edit LATITUDE / LONGITUDE / TIMEZONE for your home, set your WiFi
credentials, and everything else should just work.
"""

# --- Location -------------------------------------------------------------
LATITUDE = 43.0481
LONGITUDE = -76.1474
TIMEZONE = "America/New_York"   # IANA name, passed to Open-Meteo
NORTHERN_HEMISPHERE = True      # flips season logic if False

# --- WiFi (device only; ignored in desktop simulation) --------------------
# Credentials live in wifi_secrets.py (gitignored); see the .example file.
try:
    from wifi_secrets import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    WIFI_SSID = "your-ssid"
    WIFI_PASSWORD = "your-password"

# --- Behavior -------------------------------------------------------------
UPDATE_INTERVAL_MINUTES = 60    # refresh cadence
USE_FAHRENHEIT = True
QUIET_START = 23                # no hourly updates from this local hour...
QUIET_END = 5                   # ...until this one (saves battery overnight)
NIGHT_WAKE_HOURS = (23, 1, 3)   # ...except these: night-watch renders
SHOW_LAST_UPDATED = True        # prototyping: render time, bottom right

# --- Weather API (Open-Meteo: free, no API key) ---------------------------
WEATHER_URL = (
    "http://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
    "precipitation,weather_code,cloud_cover,wind_speed_10m"
    "&daily=sunrise,sunset,precipitation_probability_max,"
    "temperature_2m_max,temperature_2m_min,weather_code"
    "&temperature_unit=fahrenheit&wind_speed_unit=mph"
    "&timezone={tz}&forecast_days=2"
)

# --- Files ----------------------------------------------------------------
STATE_FILE = "state.json"       # remembers things like "did it snow yet this year"
CACHE_FILE = "last_weather.json"
