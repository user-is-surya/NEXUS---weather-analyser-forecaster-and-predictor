# Copyright (c) 2026 Surya
# Non-commercial use only

"""
=============================================================================
  NEXUS WEATHER INTELLIGENCE — multi_api_weather.py
  Aggregates data from Open-Meteo, OWM, WeatherAPI.
  Performs outlier detection, confidence scoring, and unified output.
=============================================================================
"""

import statistics
from typing import Optional
from fetch_weather import (
    fetch_open_meteo,
    fetch_openweathermap,
    fetch_weatherapi,
)


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — paste your free API keys here (Open-Meteo needs NO key)
# ══════════════════════════════════════════════════════════════════════════════

OWM_API_KEY        = "5a4852c34d238740b2972557c0e4c9cb"   # Get free at https://openweathermap.org/api
WEATHERAPI_API_KEY = "37641bafddc546b28f772306261605"   # Get free at https://www.weatherapi.com/


# ══════════════════════════════════════════════════════════════════════════════
#  OUTLIER DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def _remove_outliers(values: list[float], threshold: float = 1.8) -> list[float]:
    """
    Remove values that deviate more than `threshold` standard deviations
    from the mean. Works on lists of 2+ items; returns original list otherwise.
    """
    if len(values) < 2:
        return values
    try:
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        if stdev == 0:
            return values
        return [v for v in values if abs(v - mean) <= threshold * stdev]
    except Exception:
        return values


def _weighted_mean(values: list[Optional[float]], weights: list[float]) -> Optional[float]:
    """
    Compute a weighted mean, skipping None values and their corresponding weights.
    """
    valid_pairs = [(v, w) for v, w in zip(values, weights) if v is not None]
    if not valid_pairs:
        return None
    total_weight = sum(w for _, w in valid_pairs)
    if total_weight == 0:
        return None
    return sum(v * w for v, w in valid_pairs) / total_weight


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════

# Reliability weights per source (higher = more trusted for this project)
SOURCE_WEIGHTS = {
    "Open-Meteo":     1.0,   # Excellent free accuracy, European ECMWF model
    "OpenWeatherMap": 0.85,  # Large network, good global coverage
    "WeatherAPI":     0.95,  # Very good accuracy
}


def aggregate_weather(lat: float, lon: float) -> dict:
    """
    Fetch from all configured sources, remove outliers per field,
    produce a unified best-estimate with confidence metadata.

    Returns:
    {
        "data":          dict  — unified weather data (unified schema),
        "confidence":    float — 0–100,
        "confidence_label": str,
        "sources_used":  list[str],
        "sources_raw":   list[dict],
        "agreement":     dict  — per-field std-deviation summary,
    }
    """
    # ── 1. Fetch from each source ─────────────────────────────────────────────
    sources_raw: list[dict] = []
    errors: list[str] = []

    # Open-Meteo (always attempted — no key needed)
    try:
        om = fetch_open_meteo(lat, lon)
        sources_raw.append(om)
    except Exception as e:
        errors.append(f"Open-Meteo: {e}")

    # OpenWeatherMap (skipped silently if key absent)
    owm = fetch_openweathermap(lat, lon, OWM_API_KEY)
    if owm:
        sources_raw.append(owm)

    # WeatherAPI (skipped silently if key absent)
    wapi = fetch_weatherapi(lat, lon, WEATHERAPI_API_KEY)
    if wapi:
        sources_raw.append(wapi)

    if not sources_raw:
        raise RuntimeError(
            "All weather sources failed. Check your internet connection.\n"
            + "\n".join(errors)
        )

    sources_used = [s["source"] for s in sources_raw]

    # ── 2. Aggregate numeric fields with outlier removal ──────────────────────
    NUMERIC_FIELDS = [
        "temperature", "feels_like", "humidity", "wind_speed",
        "pressure", "visibility", "uv_index", "cloud_cover", "rainfall_1h",
    ]

    merged: dict = {}
    agreement: dict = {}  # per-field std-dev

    for field in NUMERIC_FIELDS:
        raw_vals = [s.get(field) for s in sources_raw]
        float_vals = [float(v) for v in raw_vals if v is not None]
        cleaned    = _remove_outliers(float_vals)

        # Get weights for the cleaned values (match by position in sources_raw)
        weights = []
        for s, rv in zip(sources_raw, raw_vals):
            if rv is not None and float(rv) in cleaned:
                weights.append(SOURCE_WEIGHTS.get(s["source"], 1.0))

        merged[field] = _weighted_mean(cleaned, weights if weights else [1.0] * len(cleaned))

        # Agreement metric
        if len(cleaned) >= 2:
            try:
                agreement[field] = round(statistics.stdev(cleaned), 2)
            except Exception:
                agreement[field] = None
        else:
            agreement[field] = None

    # ── 3. Non-numeric fields: pick from most trusted available source ─────────
    preferred_order = ["Open-Meteo", "WeatherAPI", "OpenWeatherMap"]
    source_map = {s["source"]: s for s in sources_raw}

    def _pick_text(field: str):
        for pref in preferred_order:
            val = source_map.get(pref, {}).get(field)
            if val:
                return val
        return None

    merged["condition"]      = _pick_text("condition") or "Unknown"
    merged["condition_code"] = _pick_text("condition_code")
    merged["sunrise"]        = _pick_text("sunrise")
    merged["sunset"]         = _pick_text("sunset")
    merged["aqi"]            = _pick_text("aqi")

    # ── 4. Round numeric fields sensibly ─────────────────────────────────────
    for field in ["temperature", "feels_like", "pressure", "visibility", "uv_index", "rainfall_1h"]:
        if merged.get(field) is not None:
            merged[field] = round(merged[field], 1)
    for field in ["humidity", "cloud_cover", "wind_speed"]:
        if merged.get(field) is not None:
            merged[field] = round(merged[field], 1)

    # ── 5. Confidence scoring ─────────────────────────────────────────────────
    confidence = _compute_confidence(sources_raw, agreement)

    return {
        "data":              merged,
        "confidence":        confidence,
        "confidence_label":  _confidence_label(confidence),
        "sources_used":      sources_used,
        "sources_raw":       sources_raw,
        "agreement":         agreement,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIDENCE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _compute_confidence(sources: list[dict], agreement: dict) -> float:
    """
    Produce a 0–100 confidence score based on:
      • Number of sources that agreed
      • Standard deviation of key fields (temperature is most important)
    """
    n = len(sources)

    # Base score by source count
    base = {1: 60, 2: 78, 3: 90}.get(n, 60)

    # Deduct for high temperature disagreement
    temp_std = agreement.get("temperature")
    if temp_std is not None:
        if temp_std < 0.5:
            adjustment = +5
        elif temp_std < 1.5:
            adjustment = 0
        elif temp_std < 3.0:
            adjustment = -8
        else:
            adjustment = -18
    else:
        adjustment = -5  # only one source, slight penalty

    score = min(98, max(40, base + adjustment))
    return round(score, 1)


def _confidence_label(score: float) -> str:
    if score >= 90: return "VERY HIGH"
    if score >= 78: return "HIGH"
    if score >= 65: return "MEDIUM"
    return "LOW"


def confidence_color(label: str) -> str:
    """Return a CSS hex color for a confidence badge."""
    return {
        "VERY HIGH": "#00ff88",
        "HIGH":      "#7dffb3",
        "MEDIUM":    "#ffd166",
        "LOW":       "#ff6b6b",
    }.get(label, "#aaa")