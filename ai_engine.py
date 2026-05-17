# Copyright (c) 2026 Surya
# Non-commercial use only

"""
=============================================================================
  NEXUS WEATHER INTELLIGENCE — ai_engine.py
  Rule-based AI analysis layer:
    • Human-like weather summaries
    • Smart alert generation
    • Weather score (0–100)
    • Chat assistant responses
    • Clothing & activity recommendations
    • "Best time to go outside" advisor
=============================================================================
"""

from __future__ import annotations
import math
from datetime import datetime
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
#  WEATHER SCORE  (0 – 100)
# ══════════════════════════════════════════════════════════════════════════════

def compute_weather_score(data: dict) -> int:
    """
    Composite pleasantness score out of 100.
    High score = ideal outdoor conditions.
    """
    score = 100
    temp = data.get("temperature")
    humidity = data.get("humidity", 50)
    wind = data.get("wind_speed", 0)
    uv = data.get("uv_index", 0)
    rain = data.get("rainfall_1h", 0)
    cloud = data.get("cloud_cover", 0)

    # Temperature comfort (ideal: 18–26°C)
    if temp is not None:
        if temp < 0:          score -= 40
        elif temp < 10:       score -= 20
        elif temp < 15:       score -= 8
        elif 18 <= temp <= 26: score += 5
        elif temp > 35:       score -= 30
        elif temp > 30:       score -= 15
        elif temp > 28:       score -= 5

    # Humidity comfort (ideal: 30–60%)
    if humidity > 85:   score -= 15
    elif humidity > 70: score -= 8
    elif humidity < 20: score -= 5

    # Wind comfort
    if wind > 60:   score -= 25
    elif wind > 40: score -= 15
    elif wind > 25: score -= 5

    # UV
    if uv and uv >= 11: score -= 20
    elif uv and uv >= 8:  score -= 10
    elif uv and uv >= 6:  score -= 5

    # Rainfall
    if rain and rain > 10: score -= 30
    elif rain and rain > 5:  score -= 20
    elif rain and rain > 1:  score -= 10
    elif rain and rain > 0:  score -= 5

    # Overcast
    if cloud and cloud > 90: score -= 5

    return max(0, min(100, score))


def score_label(score: int) -> tuple[str, str]:
    """Returns (label, color) for a weather score."""
    if score >= 85: return ("Excellent", "#00ff88")
    if score >= 70: return ("Good",      "#7dffb3")
    if score >= 55: return ("Fair",      "#ffd166")
    if score >= 35: return ("Poor",      "#ff9f43")
    return              ("Severe",   "#ff6b6b")


# ══════════════════════════════════════════════════════════════════════════════
#  ALERT ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def generate_alerts(data: dict) -> list[dict]:
    """
    Generate a list of alert dicts: {type, severity, icon, message}.
    Severity: "critical" | "warning" | "info"
    """
    alerts = []
    temp    = data.get("temperature")
    feels   = data.get("feels_like", temp)
    humidity= data.get("humidity", 50)
    wind    = data.get("wind_speed", 0)
    rain    = data.get("rainfall_1h", 0)
    uv      = data.get("uv_index", 0)
    cond    = (data.get("condition") or "").lower()
    aqi     = data.get("aqi")

    # Heat / Cold alerts
    if temp is not None:
        if temp >= 42:
            alerts.append({"type": "Heat Emergency", "severity": "critical",
                           "icon": "🔥",
                           "message": f"Extreme heat {temp:.1f}°C — dangerous. Stay indoors with AC."})
        elif temp >= 38 or (feels and feels >= 40):
            alerts.append({"type": "Heat Warning", "severity": "warning",
                           "icon": "♨️",
                           "message": f"Feels like {feels:.1f}°C — heat stress risk. Stay hydrated."})
        elif temp <= -10:
            alerts.append({"type": "Severe Cold", "severity": "critical",
                           "icon": "🧊",
                           "message": f"Dangerously cold at {temp:.1f}°C. Frostbite risk in minutes."})
        elif temp <= 0:
            alerts.append({"type": "Freezing Warning", "severity": "warning",
                           "icon": "❄️",
                           "message": f"Temperature at freezing ({temp:.1f}°C). Icy surfaces likely."})

    # Rain / Storm
    if any(k in cond for k in ["thunder", "storm"]):
        alerts.append({"type": "Storm Alert", "severity": "critical",
                       "icon": "⛈️",
                       "message": "Thunderstorm detected. Avoid open areas and elevated ground."})
    elif rain and rain > 10:
        alerts.append({"type": "Heavy Rain", "severity": "warning",
                       "icon": "🌧️",
                       "message": f"{rain:.1f} mm/h rainfall — flooding possible. Avoid low-lying areas."})
    elif rain and rain > 2:
        alerts.append({"type": "Rain Alert", "severity": "info",
                       "icon": "🌦️",
                       "message": f"Light rain ({rain:.1f} mm/h). Carry an umbrella."})

    # Wind
    if wind and wind > 80:
        alerts.append({"type": "Extreme Wind", "severity": "critical",
                       "icon": "💨",
                       "message": f"Wind speed {wind:.0f} km/h — structural damage possible. Stay indoors."})
    elif wind and wind > 50:
        alerts.append({"type": "High Wind", "severity": "warning",
                       "icon": "🌬️",
                       "message": f"Strong wind {wind:.0f} km/h. Secure loose objects."})

    # UV
    if uv and uv >= 11:
        alerts.append({"type": "Extreme UV", "severity": "critical",
                       "icon": "☀️",
                       "message": f"UV Index {uv:.0f} — extreme. Outdoor exposure dangerous without protection."})
    elif uv and uv >= 8:
        alerts.append({"type": "High UV", "severity": "warning",
                       "icon": "🌞",
                       "message": f"UV Index {uv:.0f} — high. SPF 50+ and hat essential."})

    # Humidity discomfort
    if humidity and humidity > 90:
        alerts.append({"type": "Humidity Alert", "severity": "warning",
                       "icon": "💧",
                       "message": f"Humidity {humidity}% — very uncomfortable. Heat index significantly elevated."})

    # AQI (WeatherAPI returns 1–6 EPA index)
    if aqi and aqi >= 4:
        alerts.append({"type": "Air Quality Alert", "severity": "warning",
                       "icon": "😷",
                       "message": "Air quality is unhealthy. Limit prolonged outdoor exertion."})

    return alerts


# ══════════════════════════════════════════════════════════════════════════════
#  HUMAN-LIKE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def generate_summary(data: dict, city: str = "your city") -> str:
    """
    Generate a 3–4 sentence natural language weather summary.
    Dynamically adapts to all conditions.
    """
    temp    = data.get("temperature")
    feels   = data.get("feels_like", temp)
    humidity= data.get("humidity", 50)
    wind    = data.get("wind_speed", 0)
    rain    = data.get("rainfall_1h", 0)
    uv      = data.get("uv_index")
    cond    = data.get("condition", "Clear")
    cloud   = data.get("cloud_cover", 0)
    cond_l  = cond.lower()

    # Time of day greeting
    hour = datetime.now().hour
    if hour < 12:   period = "morning"
    elif hour < 17: period = "afternoon"
    elif hour < 20: period = "evening"
    else:           period = "night"

    # Temperature description
    if temp is None:
        temp_desc = "temperatures unknown"
    elif temp >= 38:
        temp_desc = f"scorching {temp:.1f}°C"
    elif temp >= 30:
        temp_desc = f"hot {temp:.1f}°C"
    elif temp >= 22:
        temp_desc = f"warm {temp:.1f}°C"
    elif temp >= 15:
        temp_desc = f"mild {temp:.1f}°C"
    elif temp >= 5:
        temp_desc = f"cool {temp:.1f}°C"
    else:
        temp_desc = f"cold {temp:.1f}°C"

    # Feels-like note
    if feels and temp and abs(feels - temp) >= 3:
        fl_note = f", though it feels like {feels:.1f}°C due to {'humidity' if humidity > 65 else 'wind chill'}"
    else:
        fl_note = ""

    # Precipitation description
    if any(k in cond_l for k in ["thunder", "storm"]):
        precip_line = "Active thunderstorms are in the area — stay indoors and away from windows."
    elif rain and rain > 5:
        precip_line = f"Heavy rainfall of {rain:.1f} mm/h is occurring; flooding in low areas is possible."
    elif rain and rain > 0.5:
        precip_line = f"Light rain is falling at {rain:.1f} mm/h — an umbrella is advisable."
    elif "drizzle" in cond_l:
        precip_line = "A light drizzle is present — keep a jacket handy."
    elif cloud and cloud > 80:
        precip_line = "Overcast skies dominate, though rainfall is not currently detected."
    else:
        precip_line = "No precipitation is currently observed."

    # Wind note
    if wind and wind > 50:
        wind_note = f" Gusty winds at {wind:.0f} km/h add to the discomfort."
    elif wind and wind > 25:
        wind_note = f" A noticeable breeze at {wind:.0f} km/h keeps things moving."
    else:
        wind_note = ""

    # UV note
    uv_note = ""
    if uv and uv >= 8:
        uv_note = f" UV index is high at {uv:.0f} — apply SPF 50+ before stepping outside."
    elif uv and uv >= 6:
        uv_note = f" UV index of {uv:.0f} warrants sunscreen."

    # Humidity comfort
    if humidity and humidity > 80:
        hum_note = f" High humidity of {humidity}% makes the air feel heavy and sticky."
    elif humidity and humidity < 25:
        hum_note = " Air is very dry — stay hydrated."
    else:
        hum_note = ""

    summary = (
        f"Good {period} from {city}! "
        f"Currently experiencing {cond.lower()} with {temp_desc}{fl_note}. "
        f"{precip_line}{wind_note}{uv_note}{hum_note}"
    )
    return summary.strip()


# ══════════════════════════════════════════════════════════════════════════════
#  CLOTHING & ACTIVITY RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_recommendations(data: dict) -> dict:
    """
    Returns {clothing: [...], activities: [...], avoid: [...], hydration: str}.
    """
    temp    = data.get("temperature", 22)
    feels   = data.get("feels_like",  temp)
    rain    = data.get("rainfall_1h",  0)
    wind    = data.get("wind_speed",   0)
    uv      = data.get("uv_index",     0)
    humidity= data.get("humidity",    50)
    cond_l  = (data.get("condition") or "").lower()

    clothing  = []
    activities= []
    avoid     = []

    # Clothing
    if feels is not None:
        if feels < 0:
            clothing += ["Heavy winter coat", "Thermal underlayer", "Insulated gloves", "Warm boots", "Scarf & beanie"]
        elif feels < 10:
            clothing += ["Warm jacket", "Sweater", "Gloves", "Closed shoes"]
        elif feels < 18:
            clothing += ["Light jacket", "Long-sleeve shirt", "Comfortable trousers"]
        elif feels < 28:
            clothing += ["T-shirt & shorts/light trousers", "Comfortable footwear"]
        else:
            clothing += ["Lightweight breathable clothing", "Loose cotton wear"]

    if rain and rain > 0.5 or "rain" in cond_l or "drizzle" in cond_l:
        clothing += ["Waterproof jacket / raincoat", "Carry an umbrella", "Water-resistant footwear"]

    if uv and uv >= 6:
        clothing += ["Wide-brim hat", "UV-blocking sunglasses", "SPF 50+ sunscreen"]

    if wind and wind > 25:
        clothing += ["Windbreaker or shell jacket"]

    # Activities
    score = compute_weather_score(data)
    if score >= 80:
        activities += ["Outdoor jogging / cycling", "Picnic in the park", "Beach or hiking trail", "Outdoor sports"]
    elif score >= 60:
        activities += ["Short outdoor walk", "Light gardening", "Casual outdoor dining"]
    elif score >= 40:
        activities += ["Indoor café visit", "Museum or gallery", "Home workout"]
    else:
        activities += ["Stay indoors", "Indoor fitness", "WFH / home activities"]

    # Avoid
    if any(k in cond_l for k in ["thunder", "storm"]):
        avoid += ["Open fields", "Tall trees", "Swimming outdoors", "Elevated structures"]
    if temp is not None and temp >= 38:
        avoid += ["Strenuous outdoor exercise", "Direct sun exposure 10 AM–4 PM"]
    if rain and rain > 5:
        avoid += ["Low-lying flood-prone areas", "Driving through waterlogged roads"]
    if wind and wind > 50:
        avoid += ["Motorcycling", "Outdoor events", "Scaffolding or elevated work"]

    # Hydration
    if temp is not None and temp >= 35:
        hydration = "🚨 Drink at least 3–4 litres of water today. Heat increases sweat loss significantly."
    elif temp is not None and temp >= 28:
        hydration = "💧 Drink 2.5–3 litres of water. Stay hydrated in the warm weather."
    elif humidity and humidity > 80:
        hydration = "💧 High humidity reduces sweat evaporation — keep drinking water steadily."
    else:
        hydration = "✅ Normal hydration: 2 litres of water throughout the day is sufficient."

    return {
        "clothing":   clothing[:6],
        "activities": activities[:4],
        "avoid":      avoid[:4],
        "hydration":  hydration,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  BEST TIME TO GO OUTSIDE (from hourly forecast)
# ══════════════════════════════════════════════════════════════════════════════

def best_time_outside(hourly: list[dict]) -> str:
    """Given a list of hourly forecast dicts, return the best 2-hour window."""
    if not hourly:
        return "Forecast data unavailable."

    scored = []
    for h in hourly[:24]:  # next 24 hours only
        temp  = h.get("temperature", 22)
        rain  = h.get("precip_prob", 0) or 0
        uv    = h.get("uv_index", 0) or 0
        wind  = h.get("wind_speed", 0) or 0
        s = 100
        if temp < 15 or temp > 33: s -= 20
        if rain > 60: s -= 30
        elif rain > 30: s -= 15
        if uv > 8: s -= 15
        if wind > 40: s -= 15
        scored.append((h["time"], s))

    best_time, best_score = max(scored, key=lambda x: x[1])
    try:
        t = best_time[11:16]  # HH:MM from ISO string
    except Exception:
        t = best_time

    if best_score >= 75:
        verdict = "great"
    elif best_score >= 55:
        verdict = "acceptable"
    else:
        verdict = "poor (consider rescheduling)"

    return f"🕐 Best window: **{t}** — conditions are {verdict} (score {best_score}/100)."


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════

def chat_response(user_msg: str, data: dict, city: str = "your city") -> str:
    """
    Rule-based conversational weather chatbot.
    Matches common user intents and replies naturally.
    """
    msg = user_msg.lower().strip()
    temp    = data.get("temperature")
    feels   = data.get("feels_like", temp)
    humidity= data.get("humidity", 50)
    wind    = data.get("wind_speed", 0)
    rain    = data.get("rainfall_1h", 0)
    uv      = data.get("uv_index", 0)
    cond    = (data.get("condition") or "Clear")
    cond_l  = cond.lower()

    # ── Intent matching ────────────────────────────────────────────────────────

    # Umbrella / rain questions
    if any(k in msg for k in ["umbrella", "rain", "raining", "wet", "drizzle"]):
        if any(k in cond_l for k in ["rain", "drizzle", "storm", "shower"]) or (rain and rain > 0.5):
            return f"🌧️ Yes, definitely carry an umbrella! It's currently {cond.lower()} in {city} with {rain:.1f} mm/h of rainfall."
        else:
            return f"☀️ No umbrella needed right now — {city} is seeing {cond.lower()} skies with no rainfall detected."

    # Hot / temperature
    if any(k in msg for k in ["hot", "warm", "heat", "temperature", "temp", "degree"]):
        if temp is None:
            return "Temperature data is currently unavailable."
        if temp >= 35:
            return f"🔥 Yes, it's very hot in {city} — {temp:.1f}°C (feels like {feels:.1f}°C). Stay hydrated and avoid direct sun."
        elif temp >= 28:
            return f"☀️ It's quite warm in {city} at {temp:.1f}°C. Comfortable for outdoors if you stay hydrated."
        elif temp >= 18:
            return f"🌤️ Pleasant weather in {city} — {temp:.1f}°C, ideal for most activities."
        else:
            return f"🧥 It's cool in {city} at {temp:.1f}°C. A jacket would be a good idea."

    # Cold
    if any(k in msg for k in ["cold", "freeze", "freezing", "chilly"]):
        if temp is not None and temp <= 10:
            return f"🥶 Yes, it's cold in {city} — {temp:.1f}°C. Wear layers and a warm jacket."
        elif temp is not None:
            return f"It's {temp:.1f}°C in {city} — not particularly cold, though a light layer wouldn't hurt."
        return "Temperature data unavailable at the moment."

    # Wind
    if any(k in msg for k in ["wind", "windy", "breeze", "gust"]):
        if wind and wind > 50:
            return f"💨 Very windy in {city}! Gusts up to {wind:.0f} km/h — secure loose items and avoid motorcycling."
        elif wind and wind > 20:
            return f"🌬️ Moderate breeze in {city} at {wind:.0f} km/h — pleasant but hold onto your hat!"
        else:
            return f"Calm conditions in {city} — wind speed is just {wind:.0f} km/h."

    # UV / sunscreen
    if any(k in msg for k in ["uv", "sun", "sunscreen", "spf", "sunburn"]):
        if uv and uv >= 8:
            return f"☀️ UV index is high at {uv:.0f} in {city} — apply SPF 50+ and wear a hat before going outside."
        elif uv and uv >= 5:
            return f"🌞 UV index is moderate ({uv:.0f}). Sunscreen is recommended if you'll be outside for long."
        else:
            return f"UV index is low ({uv:.0f}) — minimal sun protection needed today."

    # Outdoor / go outside / exercise
    if any(k in msg for k in ["outside", "outdoor", "go out", "exercise", "run", "jog", "walk", "play"]):
        score = compute_weather_score(data)
        if score >= 75:
            return f"🏃 Great time to go outside in {city}! Weather score is {score}/100 — enjoy the {cond.lower()}."
        elif score >= 55:
            return f"🚶 Conditions are fair (score {score}/100). A short walk is fine but be prepared for {cond.lower()}."
        else:
            return f"🏠 I'd suggest staying indoors — weather score is {score}/100. {cond} conditions with {wind:.0f} km/h winds."

    # Humidity / comfort
    if any(k in msg for k in ["humid", "humidity", "sticky", "muggy", "comfort"]):
        if humidity and humidity > 80:
            return f"💧 Humidity is very high in {city} at {humidity}% — it'll feel much hotter than the thermometer reads."
        elif humidity and humidity > 60:
            return f"Humidity is moderate at {humidity}%. Slightly sticky but manageable."
        else:
            return f"Humidity is comfortable at {humidity}% — pleasant outdoor conditions."

    # Storm / thunder
    if any(k in msg for k in ["storm", "thunder", "lightning", "tornado", "cyclone"]):
        if any(k in cond_l for k in ["thunder", "storm"]):
            return f"⛈️ Yes! There's a thunderstorm in {city} right now. Avoid open areas, tall trees, and stay indoors."
        else:
            return f"No storm activity detected in {city} at the moment. Conditions are {cond.lower()}."

    # Summary / general
    if any(k in msg for k in ["summary", "overview", "how is", "how's the weather", "what's the weather", "tell me"]):
        return generate_summary(data, city)

    # Greeting
    if any(k in msg for k in ["hello", "hi", "hey", "greet", "good"]):
        return f"👋 Hello! I'm NEXUS, your AI weather assistant. Currently in {city}: {cond}, {temp:.1f}°C. Ask me anything about today's weather!"

    # Default fallback
    return (
        f"I detected '{user_msg}' — here's a quick status for {city}: "
        f"{cond}, {temp:.1f}°C, humidity {humidity}%, wind {wind:.0f} km/h. "
        "Ask me about rain, UV, clothing, best time to go outside, and more!"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  VOICE SUMMARY  (used by the TTS JavaScript bridge in dashboard.py)
# ══════════════════════════════════════════════════════════════════════════════

def voice_summary(data: dict, city: str) -> str:
    """
    Short, spoken-word optimised weather summary (no markdown, plain text).
    """
    temp   = data.get("temperature")
    cond   = data.get("condition", "Clear")
    wind   = data.get("wind_speed", 0)
    rain   = data.get("rainfall_1h", 0)
    uv     = data.get("uv_index", 0)

    parts = [f"Current weather in {city}."]

    if temp is not None:
        parts.append(f"Temperature is {temp:.0f} degrees Celsius.")

    parts.append(f"Conditions: {cond}.")

    if wind and wind > 20:
        parts.append(f"Wind speed is {wind:.0f} kilometres per hour.")

    if rain and rain > 0.5:
        parts.append(f"Rainfall of {rain:.1f} millimetres per hour is occurring. Carry an umbrella.")

    if uv and uv >= 6:
        parts.append(f"UV index is {uv:.0f}. Sunscreen is recommended.")

    alerts = generate_alerts(data)
    if alerts:
        parts.append(f"Alert: {alerts[0]['message']}")

    return " ".join(parts)