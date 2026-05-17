# Copyright (c) 2026 Surya
# Non-commercial use only

"""
=============================================================================
  NEXUS WEATHER INTELLIGENCE — fetch_weather.py
  Single-source weather fetch per API with unified schema output.
  Each function returns a dict or raises a descriptive exception.
=============================================================================
"""

import requests
import json
from datetime import datetime, timezone
from typing import Optional

# ── Timeouts (seconds) ────────────────────────────────────────────────────────
TIMEOUT = 8


# ══════════════════════════════════════════════════════════════════════════════
#  GEOCODING  (Nominatim — completely free, no key required)
# ══════════════════════════════════════════════════════════════════════════════

def geocode_city(city_name: str) -> dict:
    """
    Convert a city name → {lat, lon, display_name, country, country_code}.
    Uses OpenStreetMap Nominatim. Raises ValueError on unknown city.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q":      city_name,
        "format": "json",
        "limit":  1,
    }
    headers = {"User-Agent": "NexusWeatherDashboard/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise ConnectionError(f"Geocoding network error: {e}")

    if not data:
        raise ValueError(f"City '{city_name}' not found. Please check the spelling.")

    result = data[0]
    return {
        "lat":          float(result["lat"]),
        "lon":          float(result["lon"]),
        "display_name": result.get("display_name", city_name),
        "country":      result.get("display_name", "").split(", ")[-1],
        "country_code": result.get("country_code", "").upper(),
    }


def reverse_geocode(lat: float, lon: float) -> str:
    """Return the city name for a lat/lon pair."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json"}
    headers = {"User-Agent": "NexusWeatherDashboard/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        data = resp.json()
        address = data.get("address", {})
        return (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("county")
            or "Unknown Location"
        )
    except Exception:
        return "Unknown Location"


def ip_locate() -> Optional[dict]:
    """
    Attempt to detect user's approximate location from their public IP.
    Returns {lat, lon, city} or None on failure.
    """
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=TIMEOUT)
        data = resp.json()
        return {
            "lat":  float(data.get("latitude", 0)),
            "lon":  float(data.get("longitude", 0)),
            "city": data.get("city", ""),
        }
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  UNIFIED WEATHER SCHEMA
# ══════════════════════════════════════════════════════════════════════════════
# Every fetch function must return a dict that conforms (missing keys = None):
#
#   temperature     float  °C
#   feels_like      float  °C
#   humidity        int    %
#   wind_speed      float  km/h
#   wind_direction  int    degrees
#   pressure        float  hPa
#   visibility      float  km
#   uv_index        float
#   cloud_cover     int    %
#   rainfall_1h     float  mm
#   condition       str    e.g. "Partly Cloudy"
#   condition_code  int    (API-specific; mapped to emoji later)
#   sunrise         str    HH:MM local
#   sunset          str    HH:MM local
#   aqi             int    (1–5 scale or raw µg/m³)
#   source          str    API name


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 1 — Open-Meteo  (100% free, no API key)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_open_meteo(lat: float, lon: float) -> dict:
    """Fetch current weather from Open-Meteo (free, no key needed)."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "current":    (
            "temperature_2m,apparent_temperature,relative_humidity_2m,"
            "precipitation,weather_code,cloud_cover,wind_speed_10m,"
            "wind_direction_10m,surface_pressure,visibility,uv_index"
        ),
        "daily": "sunrise,sunset,uv_index_max",
        "timezone": "auto",
        "forecast_days": 1,
    }
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise ConnectionError(f"Open-Meteo fetch failed: {e}")

    cur = data.get("current", {})
    daily = data.get("daily", {})

    # Map WMO weather code → human label
    wmo_code = cur.get("weather_code", 0)
    condition = _wmo_to_label(wmo_code)

    # Parse sunrise/sunset
    sunrise_raw = (daily.get("sunrise") or [""])[0]
    sunset_raw  = (daily.get("sunset")  or [""])[0]
    sunrise = sunrise_raw[11:16] if len(sunrise_raw) > 10 else None
    sunset  = sunset_raw[11:16]  if len(sunset_raw)  > 10 else None

    return {
        "temperature":    cur.get("temperature_2m"),
        "feels_like":     cur.get("apparent_temperature"),
        "humidity":       cur.get("relative_humidity_2m"),
        "wind_speed":     cur.get("wind_speed_10m"),           # km/h
        "wind_direction": cur.get("wind_direction_10m"),
        "pressure":       cur.get("surface_pressure"),
        "visibility":     (cur.get("visibility") or 0) / 1000, # m → km
        "uv_index":       cur.get("uv_index"),
        "cloud_cover":    cur.get("cloud_cover"),
        "rainfall_1h":    cur.get("precipitation"),
        "condition":      condition,
        "condition_code": wmo_code,
        "sunrise":        sunrise,
        "sunset":         sunset,
        "aqi":            None,
        "source":         "Open-Meteo",
    }


def fetch_open_meteo_forecast(lat: float, lon: float) -> dict:
    """
    Fetch hourly (48h) + daily (7-day) forecast from Open-Meteo.
    Returns {hourly: [...], daily: [...]}.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":  lat,
        "longitude": lon,
        "hourly": (
            "temperature_2m,apparent_temperature,precipitation_probability,"
            "precipitation,weather_code,cloud_cover,wind_speed_10m,uv_index"
        ),
        "daily": (
            "temperature_2m_max,temperature_2m_min,sunrise,sunset,"
            "precipitation_sum,precipitation_probability_max,"
            "weather_code,wind_speed_10m_max,uv_index_max"
        ),
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        raw = resp.json()
    except requests.RequestException as e:
        raise ConnectionError(f"Open-Meteo forecast failed: {e}")

    hourly_times = raw.get("hourly", {}).get("time", [])
    daily_dates  = raw.get("daily",  {}).get("time", [])

    hourly = []
    for i, t in enumerate(hourly_times[:48]):
        hourly.append({
            "time":         t,
            "temperature":  _safe(raw["hourly"]["temperature_2m"], i),
            "feels_like":   _safe(raw["hourly"]["apparent_temperature"], i),
            "precip_prob":  _safe(raw["hourly"]["precipitation_probability"], i),
            "precipitation":_safe(raw["hourly"]["precipitation"], i),
            "condition":    _wmo_to_label(_safe(raw["hourly"]["weather_code"], i) or 0),
            "cloud_cover":  _safe(raw["hourly"]["cloud_cover"], i),
            "wind_speed":   _safe(raw["hourly"]["wind_speed_10m"], i),
            "uv_index":     _safe(raw["hourly"]["uv_index"], i),
        })

    daily = []
    for i, d in enumerate(daily_dates):
        daily.append({
            "date":          d,
            "temp_max":      _safe(raw["daily"]["temperature_2m_max"], i),
            "temp_min":      _safe(raw["daily"]["temperature_2m_min"], i),
            "sunrise":       (_safe(raw["daily"]["sunrise"], i) or "")[-5:],
            "sunset":        (_safe(raw["daily"]["sunset"], i) or "")[-5:],
            "precip_sum":    _safe(raw["daily"]["precipitation_sum"], i),
            "precip_prob":   _safe(raw["daily"]["precipitation_probability_max"], i),
            "condition":     _wmo_to_label(_safe(raw["daily"]["weather_code"], i) or 0),
            "wind_max":      _safe(raw["daily"]["wind_speed_10m_max"], i),
            "uv_max":        _safe(raw["daily"]["uv_index_max"], i),
        })

    return {"hourly": hourly, "daily": daily}


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 2 — OpenWeatherMap  (free tier — 1 000 calls/day)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_openweathermap(lat: float, lon: float, api_key: str) -> Optional[dict]:
    """
    Fetch current weather + AQI from OpenWeatherMap free tier.
    Returns None (not an exception) if the key is empty or the call fails
    so the multi-API engine can degrade gracefully.
    """
    if not api_key or api_key.strip() in ("", "YOUR_OWM_KEY"):
        return None

    try:
        # Current weather
        w_url = "https://api.openweathermap.org/data/2.5/weather"
        w_resp = requests.get(
            w_url,
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=TIMEOUT,
        )
        w_resp.raise_for_status()
        wd = w_resp.json()

        # Air Quality
        aqi_val = None
        try:
            a_url = "https://api.openweathermap.org/data/2.5/air_pollution"
            a_resp = requests.get(
                a_url,
                params={"lat": lat, "lon": lon, "appid": api_key},
                timeout=TIMEOUT,
            )
            a_resp.raise_for_status()
            aqi_val = a_resp.json()["list"][0]["main"]["aqi"]  # 1–5
        except Exception:
            pass

        # Sunrise/sunset from sys block
        sys_block = wd.get("sys", {})
        tz_offset = wd.get("timezone", 0)  # seconds offset from UTC

        def _unix_to_local(ts: int) -> str:
            if not ts:
                return ""
            dt = datetime.fromtimestamp(ts + tz_offset, tz=timezone.utc)
            return dt.strftime("%H:%M")

        return {
            "temperature":    wd["main"].get("temp"),
            "feels_like":     wd["main"].get("feels_like"),
            "humidity":       wd["main"].get("humidity"),
            "wind_speed":     (wd.get("wind", {}).get("speed") or 0) * 3.6,  # m/s → km/h
            "wind_direction": wd.get("wind", {}).get("deg"),
            "pressure":       wd["main"].get("pressure"),
            "visibility":     (wd.get("visibility") or 0) / 1000,
            "uv_index":       None,  # needs separate One Call call
            "cloud_cover":    wd.get("clouds", {}).get("all"),
            "rainfall_1h":    wd.get("rain", {}).get("1h", 0),
            "condition":      wd["weather"][0].get("description", "").title() if wd.get("weather") else "Unknown",
            "condition_code": wd["weather"][0].get("id", 0) if wd.get("weather") else 0,
            "sunrise":        _unix_to_local(sys_block.get("sunrise", 0)),
            "sunset":         _unix_to_local(sys_block.get("sunset", 0)),
            "aqi":            aqi_val,
            "source":         "OpenWeatherMap",
        }
    except Exception as e:
        print(f"[OWM] fetch failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 3 — WeatherAPI.com  (free tier — 1 000 000 calls/month)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_weatherapi(lat: float, lon: float, api_key: str) -> Optional[dict]:
    """
    Fetch current weather from WeatherAPI.com free tier.
    Returns None if key is absent or the call fails.
    """
    if not api_key or api_key.strip() in ("", "YOUR_WEATHERAPI_KEY"):
        return None

    try:
        url = "https://api.weatherapi.com/v1/current.json"
        params = {"key": api_key, "q": f"{lat},{lon}", "aqi": "yes"}
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        cur   = data.get("current", {})
        astro = data.get("forecast", {}).get("forecastday", [{}])[0].get("astro", {})
        aqi_block = cur.get("air_quality", {})
        aqi_val = None
        us_epa = aqi_block.get("us-epa-index")
        if us_epa:
            aqi_val = int(us_epa)  # 1–6 scale

        # WeatherAPI gives wind in kph already
        return {
            "temperature":    cur.get("temp_c"),
            "feels_like":     cur.get("feelslike_c"),
            "humidity":       cur.get("humidity"),
            "wind_speed":     cur.get("wind_kph"),
            "wind_direction": cur.get("wind_degree"),
            "pressure":       cur.get("pressure_mb"),
            "visibility":     cur.get("vis_km"),
            "uv_index":       cur.get("uv"),
            "cloud_cover":    cur.get("cloud"),
            "rainfall_1h":    cur.get("precip_mm"),
            "condition":      (cur.get("condition") or {}).get("text", "Unknown"),
            "condition_code": (cur.get("condition") or {}).get("code", 0),
            "sunrise":        astro.get("sunrise", "").replace(" ", "").lstrip("0") or None,
            "sunset":         astro.get("sunset",  "").replace(" ", "").lstrip("0") or None,
            "aqi":            aqi_val,
            "source":         "WeatherAPI",
        }
    except Exception as e:
        print(f"[WeatherAPI] fetch failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _safe(lst: list, idx: int):
    """Safe list indexer that returns None instead of raising."""
    try:
        return lst[idx]
    except (IndexError, TypeError):
        return None


def _wmo_to_label(code: int) -> str:
    """Map WMO weather interpretation code → human-readable label."""
    mapping = {
        0: "Clear Sky",
        1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
        45: "Foggy", 48: "Icy Fog",
        51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
        56: "Freezing Drizzle", 57: "Heavy Freezing Drizzle",
        61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
        66: "Freezing Rain", 67: "Heavy Freezing Rain",
        71: "Slight Snow", 73: "Moderate Snow", 75: "Heavy Snow",
        77: "Snow Grains",
        80: "Slight Rain Showers", 81: "Moderate Rain Showers", 82: "Violent Rain Showers",
        85: "Slight Snow Showers", 86: "Heavy Snow Showers",
        95: "Thunderstorm", 96: "Thunderstorm with Hail", 99: "Thunderstorm with Heavy Hail",
    }
    return mapping.get(code, f"Weather Code {code}")


def condition_to_emoji(condition: str) -> str:
    """Map a condition string → weather emoji."""
    c = condition.lower()
    if any(k in c for k in ["thunder", "storm", "lightning"]): return "⛈️"
    if any(k in c for k in ["heavy rain", "violent rain"]):     return "🌧️"
    if any(k in c for k in ["rain", "shower", "drizzle"]):      return "🌦️"
    if any(k in c for k in ["snow", "blizzard", "sleet"]):      return "❄️"
    if any(k in c for k in ["fog", "mist", "haze"]):            return "🌫️"
    if any(k in c for k in ["overcast", "cloud"]):              return "☁️"
    if "partly" in c:                                            return "⛅"
    if any(k in c for k in ["clear", "sunny", "fair"]):         return "☀️"
    return "🌡️"