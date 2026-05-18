"""
=============================================================================
  NEXUS WEATHER INTELLIGENCE  —  dashboard.py  v2.1 (FIXED)
  Run with:  streamlit run dashboard.py

  INSTALL:
    pip install -r requirements.txt

  FREE API KEYS (Open-Meteo works with ZERO keys):
    • OpenWeatherMap → https://openweathermap.org/api
    • WeatherAPI     → https://www.weatherapi.com/
    Paste keys in multi_api_weather.py
=============================================================================
"""

# ── Standard library ─────────────────────────────────────────────────────────
import json
import requests as _req
from datetime import datetime

# ── Third-party ���─────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

# ── Local modules ─────────────────────────────────────────────────────────────
from fetch_weather import (
    geocode_city, ip_locate,
    fetch_open_meteo_forecast, condition_to_emoji,
)
from multi_api_weather import aggregate_weather, confidence_color
from ai_engine import (
    compute_weather_score, score_label, generate_alerts,
    generate_summary, get_recommendations, best_time_outside,
    chat_response, voice_summary,
)
from database import (
    init_db, save_search, get_history, search_history,
    clear_history, get_history_stats,
    add_favourite, remove_favourite, get_favourites,
    set_pref, get_pref,
)
from ui_theme import get_theme, inject_css

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG  — must be the very FIRST streamlit call
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="NEXUS | AI Weather Intelligence",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

def _init_state():
    defaults = dict(
        city="", lat=None, lon=None,
        weather=None, forecast=None,
        confidence=0, conf_label="LOW",
        score=0, chat_history=[], alerts=[],
        last_refresh=None, unit="°C",
        user_name=get_pref("user_name",""),
        auto_refresh=False, error_msg="",
        cached_weather=None, cached_city="",
        offline_mode=False,
        search_suggestions=[], _last_typed="",
        voice_active=False, _auto_tried=False,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ══════════════════════════════════════════════════════════════════════════════
#  PURE HELPER FUNCTIONS  (no Streamlit calls — safe to call anywhere)
# ══════════════════════════════════════════════════════════════════════════════

def _greeting() -> str:
    h = datetime.now().hour
    if h < 12:  return "Good Morning"
    if h < 17:  return "Good Afternoon"
    if h < 20:  return "Good Evening"
    return "Good Night"

def _temp(val, unit="°C") -> str:
    if val is None: return "—"
    return f"{val*9/5+32:.1f}°F" if unit == "°F" else f"{val:.1f}°C"

def _uv_label(uv) -> str:
    if uv is None: return "N/A"
    if uv >= 11: return "🔴 Extreme"
    if uv >= 8:  return "🟠 Very High"
    if uv >= 6:  return "🟡 High"
    if uv >= 3:  return "🟢 Moderate"
    return "🟢 Low"

def _aqi_label(v) -> str:
    if v is None: return "N/A"
    return {1:"Good",2:"Fair",3:"Moderate",4:"Poor",5:"Very Poor",6:"Hazardous"}.get(int(v),f"AQI {v}")

def _comfort_label(temp, feels) -> tuple:
    """Returns (label, hex_color)."""
    if temp is None or feels is None: return ("Unknown", "#aaa")
    diff = abs(feels - temp)
    if diff < 2:   return ("😊 Comfortable",          "#00ff88")
    if diff < 5:   return ("😐 Slightly Uncomfortable","#ffd166")
    return             ("😰 Extreme Discomfort",    "#ff6b6b")

def _gauge(label: str, value: float, max_val: float, unit: str, grad: str) -> str:
    pct = min(100, max(0, value / max_val * 100)) if max_val else 0
    return (f'<div class="gauge-container">'
            f'<div class="gauge-label"><span>{label}</span><span>{value:.0f} {unit}</span></div>'
            f'<div class="gauge-track"><div class="gauge-fill" style="width:{pct:.0f}%;background:{grad};"></div></div>'
            f'</div>')

def _badge(label: str, color: str) -> str:
    return f'<span class="conf-badge" style="color:{color};border-color:{color};">{label}</span>'

def _rgb(hex_color: str) -> str:
    """Convert '#rrggbb' → 'r,g,b' string for rgba() usage."""
    h = hex_color.lstrip('#')
    return ','.join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))

# ══════════════════════════════════════════════════════════════════════════════
#  WEATHER FETCH  (with offline fallback cache)
# ══════════════════════════════════════════════════════════════════════════════

def do_fetch(city_query: str, silent: bool = False):
    """Full weather fetch pipeline. On failure activates offline cache."""
    st.session_state.update(error_msg="", offline_mode=False)

    def _live():
        geo      = geocode_city(city_query)
        lat, lon = geo["lat"], geo["lon"]
        disp     = city_query.strip().title()
        result   = aggregate_weather(lat, lon)
        forecast = fetch_open_meteo_forecast(lat, lon)
        data     = result["data"]
        conf     = result["confidence"]
        clabel   = result["confidence_label"]
        score    = compute_weather_score(data)
        alerts   = generate_alerts(data)
        save_search(city=disp, country=geo.get("country",""),
                    weather_data=data, confidence=conf, score=score)
        st.session_state["cached_weather"] = data
        st.session_state["cached_city"]    = disp
        set_pref("cached_weather", data)
        set_pref("cached_city",    disp)
        return dict(city=disp, lat=lat, lon=lon, weather=data, forecast=forecast,
                    confidence=conf, conf_label=clabel, score=score,
                    alerts=alerts, last_refresh=datetime.now())

    try:
        if not silent:
            with st.spinner("🛰️  Connecting to weather satellites…"):
                payload = _live()
        else:
            payload = _live()
        st.session_state.update(payload)
    except ValueError as e:
        st.session_state["error_msg"] = f"🔍 {e}"
        _offline(city_query)
    except (ConnectionError, Exception) as e:
        st.session_state["error_msg"] = f"⚠️ {e}"
        _offline(city_query)

def _offline(city_query: str):
    cached = st.session_state.get("cached_weather") or get_pref("cached_weather")
    city_c = st.session_state.get("cached_city")    or get_pref("cached_city","")
    if cached:
        st.session_state.update(
            weather=cached, city=city_c or city_query,
            offline_mode=True, score=compute_weather_score(cached),
            alerts=generate_alerts(cached), conf_label="LOW", confidence=40,
        )

# ══════════════════════════════════════════════════════════════════════════════
#  SEARCH AUTOCOMPLETE  (Nominatim)
# ══════════════════════════════════════════════════════════════════════════════

def _suggestions(query: str) -> list:
    if len(query.strip()) < 2:
        return []
    try:
        r = _req.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 5, "addressdetails": 1},
            headers={"User-Agent": "NexusWeatherDashboard/2.0"},
            timeout=4,
        )
        results = []
        for d in r.json():
            addr  = d.get("address", {})
            city  = (addr.get("city") or addr.get("town") or addr.get("village")
                     or d.get("display_name","").split(",")[0])
            ctry  = addr.get("country","")
            label = f"{city}, {ctry}".strip(", ") if ctry else city
            if label not in results:
                results.append(label)
        return results[:5]
    except Exception:
        return []

# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-DETECT ON FIRST LOAD + AUTO-REFRESH
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state["_auto_tried"]:
    st.session_state["_auto_tried"] = True
    loc = ip_locate()
    city0 = loc.get("city","") if loc else ""
    do_fetch(city0 if city0 else "Chennai", silent=True)

if (st.session_state["auto_refresh"]
        and st.session_state.get("last_refresh")
        and st.session_state["city"]):
    elapsed = (datetime.now() - st.session_state["last_refresh"]).seconds
    if elapsed >= 300:
        do_fetch(st.session_state["city"], silent=True)

# ══════════════════════════════════════════════════════════════════════════════
#  INJECT CSS  (theme is derived from current weather)
# ══════════════════════════════════════════════════════════════════════════════

_cond = (st.session_state.get("weather") or {}).get("condition","")
T     = get_theme(_cond)
st.markdown(inject_css(T), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    theme_pill = f'<div class="theme-pill" style="margin-top:.5rem;">{T["label"]}</div>' if T["label"] else ""
    st.markdown(f"""
<div style="text-align:center;margin-bottom:1.5rem;">
  <div style="font-family:'Orbitron',sans-serif;font-size:1.3rem;font-weight:800;
       background:{T['hero']};-webkit-background-clip:text;-webkit-text-fill-color:transparent;
       letter-spacing:3px;">NEXUS</div>
  <div style="font-size:.65rem;letter-spacing:2px;color:#7ecdc8;text-transform:uppercase;margin-top:2px;">
    Weather Intelligence v2.1</div>
  {theme_pill}
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">🔍 Smart Search</div>', unsafe_allow_html=True)
    city_input = st.text_input("City", placeholder="Type a city name…",
                               label_visibility="collapsed", key="city_search_input")

    if city_input and city_input != st.session_state["_last_typed"]:
        st.session_state["_last_typed"]        = city_input
        st.session_state["search_suggestions"] = _suggestions(city_input)
    elif not city_input:
        st.session_state["search_suggestions"] = []

    for sug in st.session_state.get("search_suggestions", []):
        if st.button(f"📍 {sug}", key=f"sug_{sug}", use_container_width=True):
            st.session_state["search_suggestions"] = []
            st.session_state["_last_typed"]         = ""
            do_fetch(sug.split(",")[0].strip())
            st.rerun()

    c1, c2 = st.columns([3, 1])
    if c1.button("▶ SEARCH", use_container_width=True, key="btn_search"):
        if city_input.strip():
            st.session_state["search_suggestions"] = []
            do_fetch(city_input.strip())
        else:
            st.warning("Enter a city name.")
    if c2.button("📍", key="btn_gps", help="Auto-detect my location"):
        loc = ip_locate()
        if loc and loc.get("city"):
            do_fetch(loc["city"])
        else:
            st.warning("Auto-detect failed — try Chennai.")
            do_fetch("Chennai")

    favs = get_favourites()
    if favs:
        st.markdown('<div class="section-title" style="margin-top:1rem;">⭐ Favourites</div>',
                    unsafe_allow_html=True)
        for f in favs[:6]:
            ca, cb = st.columns([4, 1])
            if ca.button(f["city"], key=f"fav_{f['id']}", use_container_width=True):
                do_fetch(f["city"])
            if cb.button("✕", key=f"dfav_{f['id']}"):
                remove_favourite(f["city"])
                st.rerun()

    hist = get_history(6)
    if hist:
        st.markdown('<div class="section-title" style="margin-top:1rem;">🕐 Recent</div>',
                    unsafe_allow_html=True)
        for h in hist:
            lbl = f"{h['city']}  {h['temperature']:.0f}°" if h.get("temperature") else h["city"]
            if st.button(lbl, key=f"hst_{h['id']}", use_container_width=True):
                do_fetch(h["city"])

    st.divider()
    st.markdown('<div class="section-title">⚙️ Settings</div>', unsafe_allow_html=True)

    uname = st.text_input("Your Name", value=st.session_state["user_name"],
                           placeholder="e.g. Surya")
    if uname != st.session_state["user_name"]:
        st.session_state["user_name"] = uname
        set_pref("user_name", uname)

    unit_c = st.radio("Unit", ["°C","°F"], horizontal=True,
                       index=0 if st.session_state["unit"]=="°C" else 1)
    st.session_state["unit"] = unit_c

    auto_r = st.toggle("Auto-Refresh (5 min)", value=st.session_state["auto_refresh"])
    st.session_state["auto_refresh"] = auto_r

    if st.session_state.get("weather") and st.session_state.get("city"):
        if st.button("⭐ Save to Favourites", use_container_width=True):
            ok = add_favourite(st.session_state["city"])
            st.success("Saved!") if ok else st.info("Already saved.")

    if st.button("🔄 Refresh Now", use_container_width=True):
        if st.session_state["city"]:
            do_fetch(st.session_state["city"])

    if st.session_state.get("last_refresh"):
        e = (datetime.now() - st.session_state["last_refresh"]).seconds
        offline_pfx = "🟠 OFFLINE · " if st.session_state["offline_mode"] else ""
        st.markdown(
            f'<div style="font-size:.7rem;color:#7ecdc8;text-align:center;margin-top:.4rem;">'
            f'{offline_pfx}Updated {e}s ago</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN HEADER
# ══════════════════════════════════════════════════════════════════════════════

gname   = f", {st.session_state['user_name']}" if st.session_state["user_name"] else ""
now_str = datetime.now().strftime("%a %d %b  %H:%M:%S")

st.markdown(f"""
<div class="nexus-header">
  <div>
    <div class="nexus-logo">NEXUS</div>
    <div class="nexus-tagline">AI Weather Intelligence Platform</div>
  </div>
  <div style="text-align:center;">
    <div class="greeting">{_greeting()}{gname} 👋</div>
  </div>
  <div style="font-family:'JetBrains Mono',monospace;color:var(--a1);font-size:1.1rem;opacity:.85;">{now_str}</div>
</div>""", unsafe_allow_html=True)

if st.session_state.get("offline_mode"):
    st.markdown(
        '<div class="offline-banner"><span style="display:inline-block;width:8px;height:8px;background:#ff9f43;border-radius:50%;margin-right:4px;animation:pulse 1.5s infinite;"></span>'
        ' OFFLINE MODE — Showing last cached data. Check your internet connection.</div>',
        unsafe_allow_html=True,
    )

if st.session_state["error_msg"] and not st.session_state["offline_mode"]:
    st.markdown(f'<div class="alert-warning">⚠️ {st.session_state["error_msg"]}</div>',
                unsafe_allow_html=True)

if st.session_state["weather"] is None:
    st.markdown("""
<div class="glass-card" style="text-align:center;padding:4rem 2rem;">
  <div style="font-size:4rem;margin-bottom:1rem;">🌌</div>
  <div style="font-family:'Orbitron',sans-serif;font-size:1.4rem;color:var(--a1);
       letter-spacing:3px;margin-bottom:.8rem;">NEXUS WEATHER INTELLIGENCE</div>
  <div style="color:var(--text-muted);font-family:'Rajdhani',sans-serif;font-size:1.1rem;max-width:480px;margin:0 auto;">
    Detecting your location… or type a city in the sidebar to begin.
  </div>
</div>""", unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  DATA SHORTHANDS
# ══════════════════════════════════════════════════════════════════════════════

W      = st.session_state["weather"]
CITY   = st.session_state["city"]
UNIT   = st.session_state["unit"]
SCORE  = st.session_state["score"]
CONF   = st.session_state["confidence"]
CLABEL = st.session_state["conf_label"]
ALERTS = st.session_state["alerts"]
FCST   = st.session_state.get("forecast") or {"hourly":[], "daily":[]}
EMOJI  = condition_to_emoji(W.get("condition","Clear"))
SLABEL, SCOLOR = score_label(SCORE)
CCOLOR = confidence_color(CLABEL)

# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_now, tab_forecast, tab_map, tab_chat, tab_ai, tab_history = st.tabs([
    "🌡️  NOW","📈  FORECAST","🗺️  MAP","💬  CHAT","🤖  AI ANALYSIS","📂  HISTORY",
])

# ──────────────────────────────────────────────────────────────────────────────
#  TAB 1 — NOW
# ──────────────────────────────────────────────────────────────────────────────
with tab_now:

    for alert in ALERTS:
        cls = {"critical":"alert-critical","warning":"alert-warning","info":"alert-info"}.get(alert["severity"],"alert-info")
        st.markdown(f'<div class="{cls}"><b>{alert["icon"]} {alert["type"]}</b> — {alert["message"]}</div>',
                    unsafe_allow_html=True)

    hero_col, metrics_col = st.columns([1,2], gap="large")

    with hero_col:
        fl_label, fl_color = _comfort_label(W.get("temperature"), W.get("feels_like"))
        fl_rgb = _rgb(fl_color)
        st.markdown(f"""
<div class="glass-card" style="text-align:center;padding:2rem 1.5rem;">
  <div class="city-name">{CITY}</div>
  <div class="weather-emoji-big">{EMOJI}</div>
  <div class="temp-hero">{_temp(W.get('temperature'), UNIT)}</div>
  <div class="condition-label">{W.get('condition','—')}</div>
  <div style="color:var(--text-muted);font-size:.9rem;margin-top:.3rem;font-family:'Rajdhani',sans-serif;">
    Feels like {_temp(W.get('feels_like'), UNIT)}
  </div>
  <div class="comfort-badge" style="background:rgba({fl_rgb},.12);border:1px solid {fl_color};color:{fl_color};">
    {fl_label}
  </div>
  <div style="margin-top:.6rem;">{_badge(CLABEL, CCOLOR)}</div>
  <div style="margin-top:1rem;">
    <div class="score-ring" style="color:{SCOLOR};border:3px solid {SCOLOR};width:80px;height:80px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Orbitron',sans-serif;font-size:1.4rem;font-weight:800;margin:0 auto;">{SCORE}</div>
    <div style="font-size:.7rem;letter-spacing:2px;text-transform:uppercase;color:var(--text-muted);margin-top:.3rem;font-family:'Rajdhani',sans-serif;">
      Weather Score — {SLABEL}
    </div>
  </div>
  <div style="margin-top:1rem;font-size:.75rem;color:var(--text-muted);font-family:'JetBrains Mono',monospace;">
    {W.get('sunrise','—')} ☀️ &nbsp;&nbsp; 🌙 {W.get('sunset','—')}
  </div>
</div>""", unsafe_allow_html=True)

    with metrics_col:
        m1,m2,m3,m4 = st.columns(4)
        for col,icon,lbl,val,unt,sub in [
            (m1,"💧","HUMIDITY",   W.get("humidity"),   "%",   "Moisture"),
            (m2,"💨","WIND",       W.get("wind_speed"), "km/h",f"Dir {W.get('wind_direction','—')}°"),
            (m3,"🌡️","PRESSURE",  W.get("pressure"),   "hPa", "Atmospheric"),
            (m4,"👁️","VISIBILITY",W.get("visibility"), "km",  "Sight range"),
        ]:
            with col:
                v = f"{val:.0f}" if val is not None else "—"
                st.markdown(f"""
<div class="metric-card">
  <div class="metric-icon">{icon}</div>
  <div class="metric-label">{lbl}</div>
  <div class="metric-value">{v}<span style="font-size:.75rem;opacity:.7;"> {unt}</span></div>
  <div class="metric-sub">{sub}</div>
</div>""", unsafe_allow_html=True)

        st.write("")
        m5,m6,m7,m8 = st.columns(4)
        for col,icon,lbl,val,unt,sub in [
            (m5,"☀️","UV INDEX",  W.get("uv_index"),   "",    _uv_label(W.get("uv_index"))),
            (m6,"☁️","CLOUD",     W.get("cloud_cover"),"%",   "Cover"),
            (m7,"🌧️","RAINFALL", W.get("rainfall_1h"),"mm/h","1h total"),
            (m8,"😷","AQI",       W.get("aqi"),        "",    _aqi_label(W.get("aqi"))),
        ]:
            with col:
                v = f"{val:.1f}" if val is not None else "—"
                st.markdown(f"""
<div class="metric-card">
  <div class="metric-icon">{icon}</div>
  <div class="metric-label">{lbl}</div>
  <div class="metric-value">{v}<span style="font-size:.75rem;opacity:.7;"> {unt}</span></div>
  <div class="metric-sub">{sub}</div>
</div>""", unsafe_allow_html=True)

        st.write("")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📊 Live Gauges</div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(_gauge("Humidity",   W.get("humidity",0),  100,"%" ,"linear-gradient(90deg,var(--a1),var(--a2))"), unsafe_allow_html=True)
            st.markdown(_gauge("Wind Speed", W.get("wind_speed",0),120,"km/h","linear-gradient(90deg,#7c4dff,#ff4081)"),  unsafe_allow_html=True)
        with g2:
            st.markdown(_gauge("Cloud Cover",W.get("cloud_cover",0),100,"%","linear-gradient(90deg,#7ecdc8,#7c4dff)"),   unsafe_allow_html=True)
            st.markdown(_gauge("UV Index",   W.get("uv_index",0) or 0,12,"","linear-gradient(90deg,#ffd166,#ff6b6b)"),  unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    vc1, vc2, vc3 = st.columns([1,1,4])
    with vc1:
        if st.button("🔊 SPEAK", key="speak_btn"):
            vs   = voice_summary(W, CITY)
            safe = vs.replace("'","\\'").replace("\n"," ").replace('"','\\"')
            st.components.v1.html(f"""
<script>
(function(){{
  window.speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance('{safe}');
  u.rate=0.95; u.pitch=1.05; u.volume=1;
  var voices=window.speechSynthesis.getVoices();
  var en=voices.find(function(v){{return v.lang.startsWith('en')}});
  if(en) u.voice=en;
  window.speechSynthesis.speak(u);
}})();
</script>""", height=0)
            st.success("🔊 NEXUS speaking…")
    with vc2:
        if st.button("⏹ STOP", key="stop_btn"):
            st.components.v1.html("<script>window.speechSynthesis.cancel();</script>", height=0)
    with vc3:
        preview = voice_summary(W, CITY)
        st.markdown(
            f'<div style="font-size:.78rem;color:var(--text-muted);font-family:\'Rajdhani\',sans-serif;padding-top:.5rem;">'
            f'💬 <i>{preview[:130]}{"…" if len(preview)>130 else ""}</i></div>',
            unsafe_allow_html=True,
        )

# ──────────────────────────────────────────────────────────────────────────────
#  TAB 2 — FORECAST
# ──────────────────────────────────────────────────────────────────────────────
with tab_forecast:
    hourly = FCST.get("hourly",[])
    daily  = FCST.get("daily", [])
    r1a    = _rgb(T["a1"])
    r2a    = _rgb(T["a2"])

    if not hourly and not daily:
        st.info("Forecast unavailable — check internet connection.")
    else:
        st.markdown('<div class="section-title">📈 24-Hour Temperature Trend</div>', unsafe_allow_html=True)
        h24 = hourly[:24]
        if h24:
            times  = [h["time"][11:16] for h in h24]
            temps  = [h.get("temperature") for h in h24]
            feels  = [h.get("feels_like")  for h in h24]
            precip = [h.get("precip_prob",0) or 0 for h in h24]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=times,y=temps,name="Temperature",
                line=dict(color=T["a1"],width=2.5,shape="spline"),
                fill="tozeroy",fillcolor=f"rgba({r1a},.06)",mode="lines"))
            fig.add_trace(go.Scatter(x=times,y=feels,name="Feels Like",
                line=dict(color=T["a2"],width=1.5,dash="dot",shape="spline"),mode="lines"))
            fig.add_trace(go.Bar(x=times,y=precip,name="Rain Prob %",
                marker_color=f"rgba({r2a},.22)",yaxis="y2"))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Rajdhani",color="#7ecdc8",size=11),
                legend=dict(bgcolor="rgba(0,0,0,0)",bordercolor="rgba(255,255,255,.1)"),
                yaxis=dict(title="°C",gridcolor="rgba(255,255,255,.05)",zeroline=False),
                yaxis2=dict(title="Rain %",overlaying="y",side="right",range=[0,200],showgrid=False),
                xaxis=dict(gridcolor="rgba(255,255,255,.05)"),
                margin=dict(l=10,r=10,t=10,b=10),hovermode="x unified")
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

        st.markdown('<div class="section-title">📅 7-Day Forecast</div>', unsafe_allow_html=True)
        if daily:
            cols = st.columns(min(7,len(daily)))
            for i,(col,day) in enumerate(zip(cols,daily)):
                try:
                    dt  = datetime.strptime(day["date"],"%Y-%m-%d")
                    dlbl= "Today" if i==0 else dt.strftime("%a")
                    ddt = dt.strftime("%d %b")
                except Exception:
                    dlbl,ddt = day["date"],""
                de   = condition_to_emoji(day.get("condition","Clear"))
                tmax = day.get("temp_max"); tmin=day.get("temp_min")
                with col:
                    st.markdown(f"""
<div class="metric-card" style="padding:.8rem .4rem;">
  <div style="font-family:'Orbitron',sans-serif;font-size:.65rem;letter-spacing:2px;color:var(--text-muted);">{dlbl}</div>
  <div style="font-size:.6rem;color:#4a6a6a;margin-bottom:.3rem;">{ddt}</div>
  <div style="font-size:1.8rem;">{de}</div>
  <div style="font-family:'Orbitron',sans-serif;font-size:.9rem;color:var(--a1);font-weight:600;">{tmax:.0f}°</div>
  <div style="font-size:.75rem;color:var(--text-muted);">{tmin:.0f}°</div>
  <div style="font-size:.65rem;color:#4a8a9a;margin-top:.3rem;">🌧️ {day.get('precip_prob',0):.0f}%</div>
</div>""", unsafe_allow_html=True)

        if daily:
            dates    = [d["date"][5:] for d in daily]
            max_vals = [d.get("temp_max") for d in daily]
            min_vals = [d.get("temp_min") for d in daily]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=dates,y=max_vals,name="Max °C",
                line=dict(color="#ff6b6b",width=2,shape="spline"),mode="lines+markers",
                marker=dict(size=6,color="#ff6b6b")))
            fig2.add_trace(go.Scatter(x=dates,y=min_vals,name="Min °C",
                line=dict(color=T["a1"],width=2,shape="spline"),
                fill="tonexty",fillcolor=f"rgba({r1a},.05)",mode="lines+markers",
                marker=dict(size=6,color=T["a1"])))
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Rajdhani",color="#7ecdc8",size=11),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                yaxis=dict(gridcolor="rgba(255,255,255,.05)",zeroline=False),
                xaxis=dict(gridcolor="rgba(255,255,255,.05)"),
                margin=dict(l=10,r=10,t=10,b=10),hovermode="x unified")
            st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})

        st.markdown('<div class="section-title">🕐 Best Time to Go Outside</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="glass-card">{best_time_outside(hourly)}</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
#  TAB 3 — MAP
# ──────────────────────────────────────────────────────────────────────────────
with tab_map:
    lat = st.session_state.get("lat")
    lon = st.session_state.get("lon")
    if lat is None:
        st.info("No location resolved yet — search a city first.")
    else:
        st.markdown('<div class="section-title">🗺️ Interactive Weather Map</div>', unsafe_allow_html=True)
        m = folium.Map(location=[lat,lon], zoom_start=10, tiles="CartoDB dark_matter")
        tstr = f"{W.get('temperature','?'):.0f}°C" if W.get("temperature") else "?"
        folium.Marker(location=[lat,lon],
            popup=folium.Popup(
                f"<b>{CITY}</b><br>{EMOJI} {W.get('condition','—')}<br>"
                f"🌡️{tstr} 💧{W.get('humidity','?')}% 💨{W.get('wind_speed','?'):.0f}km/h",
                max_width=220),
            tooltip=f"📍 {CITY} — {tstr}",
            icon=folium.Icon(color="blue",icon="cloud",prefix="fa")).add_to(m)
        st_folium(m, width=None, height=520, returned_objects=[])

# ──────────────────────────────────────────────────────────────────────────────
#  TAB 4 — CHAT
# ──────────────────────────────────────────────────────────────────────────────
with tab_chat:
    st.markdown(f"""
<div class="glass-card" style="margin-bottom:1rem;">
  <div class="section-title">💬 NEXUS Chat — AI Weather Assistant</div>
  <div style="font-family:'Rajdhani',sans-serif;font-size:.9rem;color:var(--text-muted);">
    Ask anything about weather in <b style="color:var(--a1);">{CITY}</b>
  </div>
</div>""", unsafe_allow_html=True)

    chips = ["Will it rain?","Umbrella needed?","Too hot outside?",
             "What to wear?","Safe to jog?","UV levels?","Windy today?","Best time to go out?"]
    r1c,r2c = st.columns(4),st.columns(4)
    for i,chip in enumerate(chips):
        row = r1c if i<4 else r2c
        if row[i%4].button(chip, key=f"chip_{i}", use_container_width=True):
            reply = chat_response(chip, W, CITY)
            st.session_state["chat_history"] += [("user",chip),("ai",reply)]
            st.rerun()

    st.divider()
    for role,msg in st.session_state["chat_history"][-24:]:
        css = "chat-user" if role=="user" else "chat-ai"
        pfx = "🧑" if role=="user" else "🤖"
        st.markdown(f'<div class="{css}">{pfx} {msg}</div>', unsafe_allow_html=True)

    ci1,ci2,ci3 = st.columns([6,1,1])
    uq = ci1.text_input("Ask…", placeholder="Type your question…",
                         label_visibility="collapsed", key="chat_input_key")
    if ci2.button("Send", use_container_width=True, key="chat_send_btn"):
        if uq.strip():
            reply = chat_response(uq, W, CITY)
            st.session_state["chat_history"] += [("user",uq),("ai",reply)]
            st.rerun()
    if ci3.button("Clear", use_container_width=True, key="chat_clear_btn"):
        st.session_state["chat_history"] = []
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
#  TAB 5 — AI ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────
with tab_ai:
    col_l, col_r = st.columns([1,1], gap="large")

    with col_l:
        st.markdown('<div class="section-title">🧠 AI Weather Summary</div>', unsafe_allow_html=True)
        summary = generate_summary(W, CITY)
        st.markdown(
            f'<div class="glass-card" style="font-family:\'Rajdhani\',sans-serif;font-size:1.05rem;line-height:1.6;">{summary}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title" style="margin-top:1rem;">🌡️ Feels-Like Intelligence</div>',
                    unsafe_allow_html=True)
        temp  = W.get("temperature",0) or 0
        feels = W.get("feels_like",  temp)
        hum   = W.get("humidity",   50) or 50
        wind  = W.get("wind_speed",  0) or 0
        fl_lbl, fl_col = _comfort_label(temp, feels)
        fl_rgb2 = _rgb(fl_col)

        hi = None
        if temp >= 27 and hum >= 40:
            hi = (-8.784 + 1.611*temp + 2.339*hum - 0.146*temp*hum
                  - 0.01231*temp**2 - 0.01642*hum**2
                  + 0.00221*temp**2*hum + 0.000726*temp*hum**2
                  - 0.00000358*temp**2*hum**2)
        
        wc = None
        if temp <= 10 and wind > 5:
            wc = 13.12 + 0.6215*temp - 11.37*(wind**0.16) + 0.3965*temp*(wind**0.16)

        heat_index_html = ""
        if hi:
            heat_index_html = f"<div style='font-size:.75rem;color:#ffd166;margin-top:.3rem;'>🔥 Heat Index: {hi:.1f}°C</div>"
        
        windchill_html = ""
        if wc:
            windchill_html = f"<div style='font-size:.75rem;color:#90caf9;margin-top:.2rem;'>❄️ Wind Chill: {wc:.1f}°C</div>"

        st.markdown(f"""
<div class="glass-card">
  <div style="display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap;">
    <div style="text-align:center;">
      <div style="font-size:.7rem;letter-spacing:2px;color:var(--text-muted);font-family:'Rajdhani',sans-serif;">ACTUAL</div>
      <div style="font-family:'Orbitron',sans-serif;font-size:2rem;color:var(--a1);">{temp:.0f}°</div>
    </div>
    <div style="font-size:1.5rem;color:var(--text-muted);">→</div>
    <div style="text-align:center;">
      <div style="font-size:.7rem;letter-spacing:2px;color:var(--text-muted);font-family:'Rajdhani',sans-serif;">FEELS LIKE</div>
      <div style="font-family:'Orbitron',sans-serif;font-size:2rem;color:{fl_col};">{feels:.0f}°</div>
    </div>
    <div style="flex:1;min-width:130px;">
      <div class="comfort-badge" style="background:rgba({fl_rgb2},.10);border:1px solid {fl_col};color:{fl_col};">{fl_lbl}</div>
      {heat_index_html}
      {windchill_html}
      <div style="font-size:.72rem;color:var(--text-muted);margin-top:.3rem;">
        Humidity: {hum}% · Wind: {wind:.0f} km/h
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        recs = get_recommendations(W)
        st.markdown('<div class="section-title" style="margin-top:1rem;">👕 Recommendations</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("**👔 Clothing**")
        st.markdown(" ".join(f'<span class="rec-chip">{c}</span>' for c in recs["clothing"]),
                    unsafe_allow_html=True)
        st.write("")
        st.markdown("**🏃 Activities**")
        st.markdown(" ".join(f'<span class="rec-chip">{a}</span>' for a in recs["activities"]),
                    unsafe_allow_html=True)
        if recs["avoid"]:
            st.write("")
            st.markdown("**⚠️ Avoid**")
            st.markdown(" ".join(f'<span class="rec-chip rec-chip-warn">{a}</span>' for a in recs["avoid"]),
                        unsafe_allow_html=True)
        st.write("")
        st.markdown(f"**💧 Hydration** — {recs['hydration']}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="section-title">📡 AI Confidence Engine</div>', unsafe_allow_html=True)
        st.markdown(f"""
<div class="glass-card">
  <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">
    <div style="width:60px;height:60px;border-radius:50%;border:3px solid {CCOLOR};display:flex;align-items:center;justify-content:center;font-family:'Orbitron',sans-serif;font-size:1.1rem;font-weight:800;color:{CCOLOR};">{CONF:.0f}%</div>
    <div>
      <div style="font-family:'Orbitron',sans-serif;font-size:.9rem;color:{CCOLOR};letter-spacing:2px;">{CLABEL}</div>
      <div style="font-size:.75rem;color:var(--text-muted);margin-top:.2rem;">Multi-source consensus</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-title" style="margin-top:1rem;">🏆 Weather Score</div>', unsafe_allow_html=True)
        sfig = go.Figure(go.Indicator(
            mode="gauge+number", value=SCORE,
            number={"font":{"family":"Orbitron","color":SCOLOR}},
            gauge={
                "axis":{"range":[0,100],"tickcolor":"#7ecdc8"},
                "bar":{"color":SCOLOR},
                "bgcolor":"rgba(0,0,0,0)","bordercolor":"rgba(255,255,255,.1)",
                "steps":[
                    {"range":[0,35],"color":"rgba(255,107,107,.15)"},
                    {"range":[35,55],"color":"rgba(255,152,0,.10)"},
                    {"range":[55,70],"color":"rgba(255,209,102,.10)"},
                    {"range":[70,85],"color":"rgba(0,255,136,.08)"},
                    {"range":[85,100],"color":"rgba(0,229,255,.08)"},
                ],
                "threshold":{"line":{"color":SCOLOR,"width":3},"value":SCORE},
            }))
        sfig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Rajdhani",color="#7ecdc8"),
            margin=dict(l=10,r=10,t=10,b=10),height=200)
        st.plotly_chart(sfig,use_container_width=True,config={"displayModeBar":False})

# ──────────────────────────────────────────────────────────────────────────────
#  TAB 6 — HISTORY
# ──────────────────────────────────────────────────────────────────────────────
with tab_history:
    stats = get_history_stats()
    s1,s2,s3,s4 = st.columns(4)
    for col,icon,lbl,val in [
        (s1,"🔍","Total Searches",stats["total_searches"]),
        (s2,"🏙️","Unique Cities",stats["unique_cities"]),
        (s3,"🌡️","Avg Temp",f"{stats['avg_temperature']:.1f}°C" if stats["avg_temperature"] else "—"),
        (s4,"📡","Avg Confidence",f"{stats['avg_confidence']:.0f}%" if stats["avg_confidence"] else "—"),
    ]:
        with col:
            st.markdown(f"""
<div class="metric-card">
  <div class="metric-icon">{icon}</div>
  <div class="metric-label">{lbl}</div>
  <div class="metric-value">{val}</div>
</div>""", unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="section-title">📋 Search History</div>', unsafe_allow_html=True)
    sq = st.text_input("Filter…", placeholder="Filter by city…", label_visibility="collapsed")
    rows = search_history(sq.strip()) if sq.strip() else get_history(50)

    if rows:
        df = pd.DataFrame(rows)[["searched_at","city","country","temperature",
                                   "humidity","wind_speed","condition","confidence","weather_score"]]
        df.columns = ["Time","City","Country","Temp °C","Humidity %",
                      "Wind km/h","Condition","Confidence %","Score"]
        df["Temp °C"]      = df["Temp °C"].apply(lambda x: f"{x:.1f}" if x else "—")
        df["Wind km/h"]    = df["Wind km/h"].apply(lambda x: f"{x:.0f}" if x else "—")
        df["Confidence %"] = df["Confidence %"].apply(lambda x: f"{x:.0f}%" if x else "—")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No history yet.")

    if st.button("🗑️ Clear History", type="secondary"):
        clear_history()
        st.success("Cleared.")
        st.rerun()
