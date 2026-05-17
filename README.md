# 🌌 NEXUS Weather Intelligence Dashboard

A production-grade futuristic AI Weather Dashboard built with Python + Streamlit.

---

## 📁 File Structure

```
weather_dashboard/
├── dashboard.py          ← Main app (run this)
├── fetch_weather.py      ← Geocoding + per-API fetch functions
├── multi_api_weather.py  ← Multi-source aggregation + confidence engine
├── ai_engine.py          ← AI analysis, alerts, chat, recommendations
├── database.py           ← SQLite history + favourites + preferences
├── requirements.txt      ← Python dependencies
└── nexus_weather.db      ← Auto-created on first run (SQLite)
```

---

## ⚡ Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

Or individually:
```bash
pip install streamlit requests folium streamlit-folium plotly pandas
```

### 2. (Optional but recommended) Add free API keys

Open `multi_api_weather.py` and paste your keys:

```python
OWM_API_KEY        = "your_key_here"   # https://openweathermap.org/api
WEATHERAPI_API_KEY = "your_key_here"   # https://www.weatherapi.com/
```

**The dashboard works with ZERO keys** using Open-Meteo only.  
Adding keys enables: AQI data, better accuracy, higher confidence scores.

### 3. Run the dashboard
```bash
streamlit run dashboard.py
```

---

## 🔑 Free API Keys — How to Get Them

| API | Free Tier | Key Required | Get Key |
|-----|-----------|--------------|---------|
| **Open-Meteo** | Unlimited | ❌ No | Built-in |
| **OpenWeatherMap** | 1,000 calls/day | ✅ Yes | https://openweathermap.org/api |
| **WeatherAPI** | 1,000,000 calls/month | ✅ Yes | https://www.weatherapi.com/ |
| **Nominatim (OSM)** | Unlimited (fair use) | ❌ No | Built-in |
| **ipapi.co** | 1,000 calls/day | ❌ No | Built-in |

---

## 🎛️ Features Overview

### 🌡️ NOW Tab
- Real-time temperature, feels like, humidity, wind, pressure, visibility
- UV index, cloud cover, rainfall, AQI
- Sunrise/sunset times
- Weather score (0–100) with gauge
- AI confidence badge (VERY HIGH / HIGH / MEDIUM / LOW)
- Live animated gauges
- Alert banners (heat, storm, UV, wind, rain)
- 🔊 Voice assistant via browser TTS (no pyttsx3 crashes)

### 📈 FORECAST Tab
- 24-hour temperature + feels-like + rain probability chart
- 7-day daily forecast cards
- 7-day temperature range chart (min/max)
- 48-hour precipitation probability bar chart
- Best time to go outside (AI-scored)

### 🗺️ MAP Tab
- Interactive Folium map (dark theme)
- Location marker with weather popup
- Cloud cover zone overlay
- Rainfall zone overlay
- Simulated radar points

### 💬 CHAT Tab
- Rule-based AI chat assistant
- Quick suggestion chips
- Questions: rain, UV, clothing, outdoor safety, temperature, storm, humidity
- Conversational, contextual responses

### 🤖 AI ANALYSIS Tab
- 3–4 sentence human-like weather summary
- Clothing recommendations (dynamically generated)
- Activity suggestions
- Items to avoid
- Hydration advisory
- Confidence engine panel
- Radar/spider chart (6 weather dimensions)
- Weather score gauge

### 📂 HISTORY Tab
- SQLite-backed search history
- Stats: total searches, unique cities, avg temperature, avg confidence
- Searchable/filterable history table
- Clear history button

### 🗂️ Sidebar
- City search
- Favourites (add/remove/one-click fetch)
- Recent searches
- Name personalisation (stored in DB)
- Temperature unit toggle (°C / °F)
- Auto-refresh toggle (5-minute interval)
- Manual refresh button

---

## 🛠️ Customisation

| What | Where |
|------|-------|
| API keys | `multi_api_weather.py` → top of file |
| Source trust weights | `multi_api_weather.py` → `SOURCE_WEIGHTS` dict |
| Alert thresholds | `ai_engine.py` → `generate_alerts()` |
| Colour scheme | `dashboard.py` → `:root` CSS variables |
| Chat responses | `ai_engine.py` → `chat_response()` |
| Score formula | `ai_engine.py` → `compute_weather_score()` |

---

## 🐛 Troubleshooting

**"City not found"** → Check spelling; Nominatim needs recognisable city names.  
**Map not rendering** → `pip install streamlit-folium --upgrade`  
**No AQI data** → Add OWM or WeatherAPI key in `multi_api_weather.py`  
**Voice not working** → Browser must support Web Speech API (Chrome/Edge recommended)  
**Low confidence score** → Only 1 API source active; add API keys for multi-source fusion  

---

## 📜 Licence
MIT — free for personal and commercial use.
