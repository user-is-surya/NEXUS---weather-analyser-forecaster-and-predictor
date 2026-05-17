# Copyright (c) 2026 Surya
# Non-commercial use only

# ── Standard library ─────────────────────────────────────────────────────────
import time
import json
from datetime import datetime, timedelta

# ── Third-party ──────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium

# ── Local modules ─────────────────────────────────────────────────────────────
from fetch_weather import (
    geocode_city, ip_locate, reverse_geocode,
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


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG  (must be FIRST streamlit call)
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title  = "NEXUS | AI Weather Intelligence",
    page_icon   = "🌌",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)
init_db()


# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL CSS  —  Glassmorphism + Futuristic Dark UI
# ══════════════════════════════════════════════════════════════════════════════

def inject_css(bg_class: str = "bg-default"):
    st.markdown(f"""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Rajdhani:wght@300;400;600&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Root palette ── */
:root {{
    --neon-cyan:   #00e5ff;
    --neon-blue:   #2979ff;
    --neon-purple: #7c4dff;
    --neon-green:  #00ff88;
    --neon-pink:   #ff4081;
    --glass-bg:    rgba(10, 15, 30, 0.72);
    --glass-border:rgba(0, 229, 255, 0.18);
    --card-shadow: 0 8px 32px rgba(0, 229, 255, 0.12);
    --text-primary:#e8f4f8;
    --text-muted:  #7ecdc8;
}}

/* ── Full-page background ── */
.stApp {{
    background: #020810 !important;
    background-image:
        radial-gradient(ellipse at 20% 50%, rgba(41, 121, 255, 0.07) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 20%, rgba(124, 77, 255, 0.07) 0%, transparent 60%),
        radial-gradient(ellipse at 60% 80%, rgba(0, 229, 255, 0.05) 0%, transparent 60%);
    font-family: 'Rajdhani', sans-serif !important;
    color: var(--text-primary) !important;
}}

/* ── Background weather overlays ── */
.bg-rain {{
    background-image:
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cline x1='40' y1='0' x2='20' y2='200' stroke='%2300e5ff' stroke-width='1' opacity='0.06'/%3E%3Cline x1='90' y1='0' x2='70' y2='200' stroke='%2300e5ff' stroke-width='1' opacity='0.04'/%3E%3Cline x1='140' y1='0' x2='120' y2='200' stroke='%2300e5ff' stroke-width='1' opacity='0.06'/%3E%3Cline x1='180' y1='0' x2='160' y2='200' stroke='%2300e5ff' stroke-width='1' opacity='0.03'/%3E%3C/svg%3E"),
        radial-gradient(ellipse at 30% 30%, rgba(0,100,200,0.12) 0%, transparent 70%);
}}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 1rem 2rem 2rem 2rem !important; max-width: 100% !important; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: rgba(5, 10, 25, 0.95) !important;
    border-right: 1px solid var(--glass-border) !important;
}}
[data-testid="stSidebar"] * {{ color: var(--text-primary) !important; }}

/* ── Top header bar ── */
.nexus-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 2rem;
    background: rgba(0, 229, 255, 0.04);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(20px);
}}
.nexus-logo {{
    font-family: 'Orbitron', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--neon-cyan), var(--neon-blue), var(--neon-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 3px;
}}
.nexus-tagline {{
    font-family: 'Rajdhani', sans-serif;
    color: var(--text-muted);
    font-size: 0.85rem;
    letter-spacing: 2px;
    text-transform: uppercase;
}}
.nexus-clock {{
    font-family: 'JetBrains Mono', monospace;
    color: var(--neon-cyan);
    font-size: 1.1rem;
    opacity: 0.8;
}}

/* ── Glass card ── */
.glass-card {{
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1.4rem;
    backdrop-filter: blur(20px);
    box-shadow: var(--card-shadow);
    margin-bottom: 1rem;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}}
.glass-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
    opacity: 0.4;
}}
.glass-card:hover {{
    border-color: rgba(0, 229, 255, 0.35);
    box-shadow: 0 12px 40px rgba(0, 229, 255, 0.18);
    transform: translateY(-2px);
}}

/* ── Metric cards ── */
.metric-card {{
    background: linear-gradient(135deg, rgba(0,229,255,0.06) 0%, rgba(41,121,255,0.06) 100%);
    border: 1px solid rgba(0,229,255,0.15);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
    transition: all 0.3s ease;
    cursor: default;
}}
.metric-card:hover {{
    background: linear-gradient(135deg, rgba(0,229,255,0.12) 0%, rgba(41,121,255,0.12) 100%);
    border-color: rgba(0,229,255,0.35);
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,229,255,0.15);
}}
.metric-icon {{ font-size: 1.6rem; margin-bottom: 0.3rem; }}
.metric-label {{
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.2rem;
}}
.metric-value {{
    font-family: 'Orbitron', sans-serif;
    font-size: 1.4rem;
    font-weight: 600;
    color: var(--neon-cyan);
}}
.metric-sub {{
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 0.1rem;
}}

/* ── Big temperature display ── */
.temp-hero {{
    font-family: 'Orbitron', sans-serif;
    font-size: 5rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--neon-cyan), var(--neon-blue));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
    margin: 0.5rem 0;
    text-shadow: none;
    filter: drop-shadow(0 0 20px rgba(0,229,255,0.4));
}}
.condition-label {{
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.4rem;
    color: var(--text-muted);
    letter-spacing: 2px;
    text-transform: uppercase;
}}
.city-name {{
    font-family: 'Orbitron', sans-serif;
    font-size: 1.2rem;
    color: var(--neon-cyan);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}}
.weather-emoji-big {{ font-size: 4rem; filter: drop-shadow(0 0 12px rgba(0,229,255,0.5)); }}

/* ── Confidence badge ── */
.conf-badge {{
    display: inline-block;
    padding: 0.25rem 0.9rem;
    border-radius: 20px;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 2px;
    border: 1px solid currentColor;
    margin-top: 0.5rem;
}}

/* ── Section titles ── */
.section-title {{
    font-family: 'Orbitron', sans-serif;
    font-size: 0.8rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--neon-cyan);
    margin-bottom: 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--glass-border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}

/* ── Progress bars (custom) ── */
.gauge-container {{ margin: 0.4rem 0; }}
.gauge-label {{
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.2rem;
    font-family: 'Rajdhani', sans-serif;
    letter-spacing: 1px;
}}
.gauge-track {{
    background: rgba(255,255,255,0.06);
    border-radius: 99px;
    height: 6px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.04);
}}
.gauge-fill {{
    height: 100%;
    border-radius: 99px;
    transition: width 1s ease;
}}

/* ── Alert cards ── */
.alert-critical {{
    background: linear-gradient(135deg, rgba(255,50,50,0.12), rgba(255,100,50,0.08));
    border: 1px solid rgba(255,80,80,0.4);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
}}
.alert-warning {{
    background: linear-gradient(135deg, rgba(255,193,7,0.10), rgba(255,152,0,0.06));
    border: 1px solid rgba(255,193,7,0.3);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
}}
.alert-info {{
    background: linear-gradient(135deg, rgba(0,229,255,0.08), rgba(41,121,255,0.05));
    border: 1px solid rgba(0,229,255,0.2);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
}}

/* ── Chat bubbles ── */
.chat-user {{
    background: linear-gradient(135deg, rgba(41,121,255,0.2), rgba(124,77,255,0.1));
    border: 1px solid rgba(41,121,255,0.3);
    border-radius: 12px 12px 2px 12px;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
    max-width: 80%;
    margin-left: auto;
    font-family: 'Rajdhani', sans-serif;
}}
.chat-ai {{
    background: linear-gradient(135deg, rgba(0,229,255,0.08), rgba(0,255,136,0.05));
    border: 1px solid rgba(0,229,255,0.2);
    border-radius: 12px 12px 12px 2px;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
    max-width: 85%;
    font-family: 'Rajdhani', sans-serif;
}}

/* ── Status indicator ── */
.ai-status {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.75rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--neon-green);
}}
.ai-dot {{
    width: 8px;
    height: 8px;
    background: var(--neon-green);
    border-radius: 50%;
    animation: pulse 2s infinite;
    box-shadow: 0 0 8px var(--neon-green);
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.4; transform: scale(0.8); }}
}}

/* ── Greeting text ── */
.greeting {{
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    color: var(--text-muted);
    letter-spacing: 1px;
}}

/* ── Streamlit widget overrides ── */
.stTextInput input, .stSelectbox select {{
    background: rgba(0,229,255,0.04) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'Rajdhani', sans-serif !important;
}}
.stButton > button {{
    background: linear-gradient(135deg, var(--neon-blue), var(--neon-purple)) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.75rem !important;
    letter-spacing: 2px !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(41,121,255,0.3) !important;
}}
.stButton > button:hover {{
    box-shadow: 0 6px 25px rgba(0,229,255,0.5) !important;
    transform: translateY(-2px) !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.7rem !important;
    letter-spacing: 2px !important;
    color: var(--text-muted) !important;
}}
.stTabs [aria-selected="true"] {{
    color: var(--neon-cyan) !important;
    border-bottom-color: var(--neon-cyan) !important;
}}

/* ── Recommendation chips ── */
.rec-chip {{
    display: inline-block;
    background: rgba(0,229,255,0.08);
    border: 1px solid rgba(0,229,255,0.2);
    border-radius: 20px;
    padding: 0.2rem 0.7rem;
    font-size: 0.78rem;
    margin: 0.15rem;
    font-family: 'Rajdhani', sans-serif;
    color: var(--text-primary);
}}
.rec-chip-warn {{
    background: rgba(255,100,50,0.08);
    border-color: rgba(255,100,50,0.25);
}}

/* ── History table ── */
.stDataFrame {{ border-radius: 12px; overflow: hidden; }}

/* ── Weather score ring ── */
.score-ring {{
    width: 80px;
    height: 80px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Orbitron', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    box-shadow: 0 0 20px currentColor;
    margin: 0 auto;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: #020810; }}
::-webkit-scrollbar-thumb {{ background: var(--neon-blue); border-radius: 4px; }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE DEFAULTS
# ══════════════════════════════════════════════════════════════════════════════

def _init_state():
    defaults = {
        "city":          "",
        "lat":           None,
        "lon":           None,
        "weather":       None,   # aggregated weather dict
        "forecast":      None,   # {hourly, daily}
        "confidence":    0,
        "conf_label":    "LOW",
        "score":         0,
        "chat_history":  [],
        "alerts":        [],
        "last_refresh":  None,
        "unit":          "°C",
        "user_name":     get_pref("user_name", ""),
        "auto_refresh":  False,
        "error_msg":     "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _greeting() -> str:
    h = datetime.now().hour
    if h < 12:  return "Good Morning"
    if h < 17:  return "Good Afternoon"
    if h < 20:  return "Good Evening"
    return "Good Night"


def _temp_display(val, unit="°C") -> str:
    if val is None: return "—"
    if unit == "°F":
        return f"{val * 9/5 + 32:.1f}°F"
    return f"{val:.1f}°C"


def _uv_label(uv) -> str:
    if uv is None: return "Unknown"
    if uv >= 11: return "🔴 Extreme"
    if uv >= 8:  return "🟠 Very High"
    if uv >= 6:  return "🟡 High"
    if uv >= 3:  return "🟢 Moderate"
    return "🟢 Low"


def _aqi_label(aqi) -> str:
    if aqi is None: return "N/A"
    labels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor", 6: "Hazardous"}
    return labels.get(int(aqi), f"AQI {aqi}")


def _gauge_html(label: str, value: float, max_val: float, unit: str,
                gradient: str = "linear-gradient(90deg, #00e5ff, #2979ff)") -> str:
    pct = min(100, max(0, (value / max_val) * 100)) if max_val else 0
    return f"""
<div class="gauge-container">
    <div class="gauge-label"><span>{label}</span><span>{value:.0f} {unit}</span></div>
    <div class="gauge-track">
        <div class="gauge-fill" style="width:{pct:.0f}%;background:{gradient};"></div>
    </div>
</div>"""


def _conf_badge_html(label: str, color: str) -> str:
    return f'<span class="conf-badge" style="color:{color};border-color:{color};">{label}</span>'


# ══════════════════════════════════════════════════════════════════════════════
#  WEATHER FETCH + STORE
# ══════════════════════════════════════════════════════════════════════════════

def do_fetch(city_query: str):
    """Geocode city, fetch multi-API weather, compute AI analysis, store DB."""
    st.session_state["error_msg"] = ""
    try:
        with st.spinner("🛰️  Connecting to weather satellites…"):
            geo   = geocode_city(city_query)
            lat, lon = geo["lat"], geo["lon"]
            city_disp = city_query.strip().title()

            result   = aggregate_weather(lat, lon)
            forecast = fetch_open_meteo_forecast(lat, lon)

        data     = result["data"]
        conf     = result["confidence"]
        clabel   = result["confidence_label"]
        score    = compute_weather_score(data)
        alerts   = generate_alerts(data)

        # Persist
        save_search(
            city     = city_disp,
            country  = geo.get("country", ""),
            weather_data = data,
            confidence   = conf,
            score        = score,
        )

        # Update session
        st.session_state.update({
            "city":         city_disp,
            "lat":          lat,
            "lon":          lon,
            "weather":      data,
            "forecast":     forecast,
            "confidence":   conf,
            "conf_label":   clabel,
            "score":        score,
            "alerts":       alerts,
            "last_refresh": datetime.now(),
        })

    except ValueError as e:
        st.session_state["error_msg"] = f"🔍 {e}"
    except ConnectionError as e:
        st.session_state["error_msg"] = f"🌐 {e}"
    except Exception as e:
        st.session_state["error_msg"] = f"⚠️ Unexpected error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-DETECT LOCATION ON FIRST LOAD
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state["weather"] is None and not st.session_state.get("_auto_tried"):
    st.session_state["_auto_tried"] = True
    loc = ip_locate()
    if loc and loc.get("city"):
        do_fetch(loc["city"])


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-REFRESH  (5-minute timer)
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state["auto_refresh"] and st.session_state.get("last_refresh"):
    elapsed = (datetime.now() - st.session_state["last_refresh"]).seconds
    if elapsed >= 300 and st.session_state["city"]:
        do_fetch(st.session_state["city"])

# Inject CSS (with rain overlay if raining)
cond_css = ""
if st.session_state["weather"]:
    c = (st.session_state["weather"].get("condition") or "").lower()
    if any(k in c for k in ["rain", "drizzle", "shower"]): cond_css = "bg-rain"

inject_css(cond_css)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
<div style="text-align:center;margin-bottom:1.5rem;">
    <div style="font-family:'Orbitron',sans-serif;font-size:1.3rem;font-weight:800;
         background:linear-gradient(135deg,#00e5ff,#7c4dff);
         -webkit-background-clip:text;-webkit-text-fill-color:transparent;
         letter-spacing:3px;">NEXUS</div>
    <div style="font-size:0.65rem;letter-spacing:2px;color:#7ecdc8;
         text-transform:uppercase;margin-top:2px;">Weather Intelligence</div>
    <div class="ai-status" style="justify-content:center;margin-top:0.6rem;">
        <div class="ai-dot"></div> AI Online
    </div>
</div>
""", unsafe_allow_html=True)

    # ── City search ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🔍 Location</div>', unsafe_allow_html=True)
    city_input = st.text_input(
        "Search City",
        placeholder="e.g. Tokyo, Mumbai, New York…",
        label_visibility="collapsed",
    )
    if st.button("▶  FETCH WEATHER", use_container_width=True):
        if city_input.strip():
            do_fetch(city_input.strip())
        else:
            st.warning("Enter a city name first.")

    # ── Quick favourites ──────────────────────────────────────────────────────
    favs = get_favourites()
    if favs:
        st.markdown('<div class="section-title" style="margin-top:1rem;">⭐ Favourites</div>', unsafe_allow_html=True)
        for f in favs[:5]:
            col_a, col_b = st.columns([4, 1])
            if col_a.button(f["city"], key=f"fav_{f['id']}", use_container_width=True):
                do_fetch(f["city"])
            if col_b.button("✕", key=f"delfav_{f['id']}"):
                remove_favourite(f["city"])
                st.rerun()

    # ── Quick history ─────────────────────────────────────────────────────────
    hist = get_history(6)
    if hist:
        st.markdown('<div class="section-title" style="margin-top:1rem;">🕐 Recent</div>', unsafe_allow_html=True)
        for h in hist:
            if st.button(f"{h['city']}  {h['temperature']:.0f}°C" if h.get("temperature") else h["city"],
                         key=f"hst_{h['id']}", use_container_width=True):
                do_fetch(h["city"])

    st.divider()

    # ── Settings ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">⚙️ Settings</div>', unsafe_allow_html=True)

    user_name = st.text_input("Your Name (optional)", value=st.session_state["user_name"],
                               placeholder="e.g. Surya")
    if user_name != st.session_state["user_name"]:
        st.session_state["user_name"] = user_name
        set_pref("user_name", user_name)

    unit_choice = st.radio("Temperature Unit", ["°C", "°F"], horizontal=True,
                            index=0 if st.session_state["unit"] == "°C" else 1)
    st.session_state["unit"] = unit_choice

    auto_ref = st.toggle("Auto-Refresh (5 min)", value=st.session_state["auto_refresh"])
    st.session_state["auto_refresh"] = auto_ref

    if st.session_state["weather"] and st.session_state["city"]:
        if st.button("⭐ Add to Favourites", use_container_width=True):
            added = add_favourite(st.session_state["city"])
            if added:  st.success("Added!")
            else:      st.info("Already in favourites.")

    if st.button("🔄 Refresh Now", use_container_width=True):
        if st.session_state["city"]:
            do_fetch(st.session_state["city"])

    # ── Last refresh ─────────────────────────────────────────────────────────
    if st.session_state["last_refresh"]:
        elapsed = (datetime.now() - st.session_state["last_refresh"]).seconds
        st.markdown(
            f'<div style="font-size:0.7rem;color:#7ecdc8;text-align:center;margin-top:0.5rem;">'
            f'Updated {elapsed}s ago</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════

# ── Top header bar ───────────────────────────────────────────────────────────
greeting_name = f", {st.session_state['user_name']}" if st.session_state["user_name"] else ""
now_str = datetime.now().strftime("%a %d %b  %H:%M:%S")

st.markdown(f"""
<div class="nexus-header">
    <div>
        <div class="nexus-logo">NEXUS</div>
        <div class="nexus-tagline">AI Weather Intelligence Platform</div>
    </div>
    <div style="text-align:center;">
        <div class="greeting">{_greeting()}{greeting_name} 👋</div>
        <div class="ai-status" style="justify-content:center;margin-top:0.3rem;">
            <div class="ai-dot"></div> All Systems Nominal
        </div>
    </div>
    <div class="nexus-clock">{now_str}</div>
</div>
""", unsafe_allow_html=True)

# ── Error display ─────────────────────────────────────────────────────────────
if st.session_state["error_msg"]:
    st.markdown(f'<div class="alert-critical">{st.session_state["error_msg"]}</div>',
                unsafe_allow_html=True)

# ── No data yet ───────────────────────────────────────────────────────────────
if st.session_state["weather"] is None:
    st.markdown("""
<div class="glass-card" style="text-align:center;padding:4rem 2rem;">
    <div style="font-size:4rem;margin-bottom:1rem;">🌌</div>
    <div style="font-family:'Orbitron',sans-serif;font-size:1.4rem;
         color:#00e5ff;letter-spacing:3px;margin-bottom:0.8rem;">
        NEXUS WEATHER INTELLIGENCE
    </div>
    <div style="color:#7ecdc8;font-family:'Rajdhani',sans-serif;font-size:1.1rem;
         max-width:500px;margin:0 auto;">
        Search for any city using the sidebar to activate the AI weather analysis engine.
        Your location has been auto-detected — if data appears, you're ready to go.
    </div>
</div>
""", unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  DATA SHORTHANDS
# ══════════════════════════════════════════════════════════════════════════════

W       = st.session_state["weather"]
CITY    = st.session_state["city"]
UNIT    = st.session_state["unit"]
SCORE   = st.session_state["score"]
CONF    = st.session_state["confidence"]
CLABEL  = st.session_state["conf_label"]
ALERTS  = st.session_state["alerts"]
FCST    = st.session_state["forecast"] or {"hourly": [], "daily": []}
EMOJI   = condition_to_emoji(W.get("condition", "Clear"))
SLABEL, SCOLOR = score_label(SCORE)
CCOLOR  = confidence_color(CLABEL)


# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_now, tab_forecast, tab_map, tab_chat, tab_ai, tab_history = st.tabs([
    "🌡️  NOW",
    "📈  FORECAST",
    "🗺️  MAP",
    "💬  CHAT",
    "🤖  AI ANALYSIS",
    "📂  HISTORY",
])


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — CURRENT WEATHER
# ══════════════════════════════════════════════════════════════════════════════

with tab_now:

    # ── Alert banners ─────────────────────────────────────────────────────────
    for alert in ALERTS:
        css_cls = {"critical": "alert-critical", "warning": "alert-warning",
                   "info": "alert-info"}.get(alert["severity"], "alert-info")
        st.markdown(
            f'<div class="{css_cls}"><b>{alert["icon"]} {alert["type"]}</b> — {alert["message"]}</div>',
            unsafe_allow_html=True,
        )

    # ── Hero row ──────────────────────────────────────────────────────────────
    hero_col, metrics_col = st.columns([1, 2], gap="large")

    with hero_col:
        st.markdown(f"""
<div class="glass-card" style="text-align:center;padding:2rem 1.5rem;">
    <div class="city-name">{CITY}</div>
    <div class="weather-emoji-big">{EMOJI}</div>
    <div class="temp-hero">{_temp_display(W.get('temperature'), UNIT)}</div>
    <div class="condition-label">{W.get('condition','—')}</div>
    <div style="color:#7ecdc8;font-size:0.9rem;margin-top:0.4rem;font-family:'Rajdhani',sans-serif;">
        Feels like {_temp_display(W.get('feels_like'), UNIT)}
    </div>
    {_conf_badge_html(CLABEL, CCOLOR)}
    <div style="margin-top:1rem;">
        <div class="score-ring" style="color:{SCOLOR};border:3px solid {SCOLOR};">
            {SCORE}
        </div>
        <div style="font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;
             color:#7ecdc8;margin-top:0.3rem;font-family:'Rajdhani',sans-serif;">
            Weather Score — {SLABEL}
        </div>
    </div>
    <div style="margin-top:1rem;font-size:0.75rem;color:#7ecdc8;font-family:'JetBrains Mono',monospace;">
        {W.get('sunrise','—')} ☀️ &nbsp;&nbsp;&nbsp; 🌙 {W.get('sunset','—')}
    </div>
</div>
""", unsafe_allow_html=True)

    with metrics_col:
        # Row 1 of metrics
        m1, m2, m3, m4 = st.columns(4)
        metrics_row1 = [
            (m1, "💧", "HUMIDITY",    W.get("humidity"),    "%",    "Moisture"),
            (m2, "💨", "WIND",        W.get("wind_speed"),  "km/h", f"{W.get('wind_direction','—')}°"),
            (m3, "🌡️", "PRESSURE",   W.get("pressure"),    "hPa",  "Atmospheric"),
            (m4, "👁️", "VISIBILITY", W.get("visibility"),  "km",   "Line of sight"),
        ]
        for col, icon, label, val, unit, sub in metrics_row1:
            with col:
                v_str = f"{val:.0f}" if val is not None else "—"
                st.markdown(f"""
<div class="metric-card">
    <div class="metric-icon">{icon}</div>
    <div class="metric-label">{label}</div>
    <div class="metric-value">{v_str}<span style="font-size:0.75rem;opacity:0.7;"> {unit}</span></div>
    <div class="metric-sub">{sub}</div>
</div>""", unsafe_allow_html=True)

        st.write("")

        # Row 2 of metrics
        m5, m6, m7, m8 = st.columns(4)
        metrics_row2 = [
            (m5, "☀️",  "UV INDEX",    W.get("uv_index"),    "",     _uv_label(W.get("uv_index"))),
            (m6, "☁️",  "CLOUD COVER", W.get("cloud_cover"), "%",    "Overcast level"),
            (m7, "🌧️", "RAINFALL",   W.get("rainfall_1h"), "mm/h", "1-hour total"),
            (m8, "😷",  "AQI",         W.get("aqi"),         "",     _aqi_label(W.get("aqi"))),
        ]
        for col, icon, label, val, unit, sub in metrics_row2:
            with col:
                v_str = f"{val:.1f}" if val is not None else "—"
                st.markdown(f"""
<div class="metric-card">
    <div class="metric-icon">{icon}</div>
    <div class="metric-label">{label}</div>
    <div class="metric-value">{v_str}<span style="font-size:0.75rem;opacity:0.7;"> {unit}</span></div>
    <div class="metric-sub">{sub}</div>
</div>""", unsafe_allow_html=True)

        st.write("")

        # Gauges
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📊 Live Gauges</div>', unsafe_allow_html=True)

        g1, g2 = st.columns(2)
        with g1:
            st.markdown(
                _gauge_html("Humidity", W.get("humidity", 0), 100, "%",
                            "linear-gradient(90deg,#00e5ff,#2979ff)"),
                unsafe_allow_html=True,
            )
            st.markdown(
                _gauge_html("Wind Speed", W.get("wind_speed", 0), 120, "km/h",
                            "linear-gradient(90deg,#7c4dff,#ff4081)"),
                unsafe_allow_html=True,
            )
        with g2:
            st.markdown(
                _gauge_html("Cloud Cover", W.get("cloud_cover", 0), 100, "%",
                            "linear-gradient(90deg,#7ecdc8,#7c4dff)"),
                unsafe_allow_html=True,
            )
            uv_val = W.get("uv_index", 0) or 0
            st.markdown(
                _gauge_html("UV Index", uv_val, 12, "",
                            "linear-gradient(90deg,#ffd166,#ff6b6b)"),
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Voice button ──────────────────────────────────────────────────────────
    st.markdown("---")
    col_v, col_s = st.columns([1, 3])
    with col_v:
        if st.button("🔊  SPEAK WEATHER"):
            vs = voice_summary(W, CITY)
            # Browser-safe TTS via JavaScript
            safe = vs.replace("'", "\\'").replace("\n", " ")
            st.components.v1.html(f"""
<script>
var u = new SpeechSynthesisUtterance('{safe}');
u.rate = 0.95; u.pitch = 1.05; u.volume = 1;
window.speechSynthesis.cancel();
window.speechSynthesis.speak(u);
</script>
""", height=0)
            st.success("🔊 Speaking…")

    # ── Data sources indicator ────────────────────────────────────────────────
    sources = st.session_state.get("weather", {})  # pull from last result
    # Show source chips (stored implicitly from last aggregate call)
    st.markdown(
        '<div style="font-size:0.72rem;color:#7ecdc8;font-family:\'Rajdhani\',sans-serif;letter-spacing:1px;">'
        '🛰️ Data sources: Open-Meteo (always) + OpenWeatherMap + WeatherAPI (if keys configured)'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — FORECAST
# ══════════════════════════════════════════════════════════════════════════════

with tab_forecast:
    hourly = FCST.get("hourly", [])
    daily  = FCST.get("daily",  [])

    if not hourly and not daily:
        st.info("Forecast data unavailable.")
    else:
        # ── 24-hour temperature chart ──────────────────────────────────────────
        st.markdown('<div class="section-title">📈 24-Hour Temperature Trend</div>',
                    unsafe_allow_html=True)

        h24 = hourly[:24]
        if h24:
            times  = [h["time"][11:16] for h in h24]
            temps  = [h.get("temperature") for h in h24]
            feels  = [h.get("feels_like") for h in h24]
            precip = [h.get("precip_prob", 0) or 0 for h in h24]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=times, y=temps, name="Temperature",
                line=dict(color="#00e5ff", width=2.5, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(0,229,255,0.06)",
                mode="lines",
            ))
            fig.add_trace(go.Scatter(
                x=times, y=feels, name="Feels Like",
                line=dict(color="#7c4dff", width=1.5, dash="dot", shape="spline"),
                mode="lines",
            ))
            fig.add_trace(go.Bar(
                x=times, y=precip, name="Rain Prob %",
                marker_color="rgba(41,121,255,0.25)",
                yaxis="y2",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Rajdhani", color="#7ecdc8", size=11),
                legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,229,255,0.2)"),
                yaxis=dict(title="°C", gridcolor="rgba(255,255,255,0.05)",
                           zeroline=False, tickfont=dict(color="#7ecdc8")),
                yaxis2=dict(title="Rain %", overlaying="y", side="right",
                            range=[0, 200], tickfont=dict(color="#7ecdc8"),
                            showgrid=False),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#7ecdc8")),
                margin=dict(l=10, r=10, t=10, b=10),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── 7-day daily forecast ──────────────────────────────────────────────
        st.markdown('<div class="section-title">📅 7-Day Forecast</div>', unsafe_allow_html=True)

        if daily:
            cols = st.columns(min(7, len(daily)))
            for i, (col, day) in enumerate(zip(cols, daily)):
                date_str = day["date"]
                try:
                    dt_obj  = datetime.strptime(date_str, "%Y-%m-%d")
                    day_lbl = "Today" if i == 0 else dt_obj.strftime("%a")
                    date_lbl= dt_obj.strftime("%d %b")
                except Exception:
                    day_lbl  = date_str
                    date_lbl = ""

                d_emoji = condition_to_emoji(day.get("condition", "Clear"))
                tmax = day.get("temp_max")
                tmin = day.get("temp_min")

                with col:
                    st.markdown(f"""
<div class="metric-card" style="padding:0.8rem 0.4rem;">
    <div style="font-family:'Orbitron',sans-serif;font-size:0.65rem;
         letter-spacing:2px;color:#7ecdc8;">{day_lbl}</div>
    <div style="font-size:0.6rem;color:#4a6a6a;margin-bottom:0.3rem;">{date_lbl}</div>
    <div style="font-size:1.8rem;">{d_emoji}</div>
    <div style="font-family:'Orbitron',sans-serif;font-size:0.9rem;
         color:#00e5ff;font-weight:600;">{tmax:.0f}°</div>
    <div style="font-size:0.75rem;color:#7ecdc8;">{tmin:.0f}°</div>
    <div style="font-size:0.65rem;color:#4a8a9a;margin-top:0.3rem;">
        🌧️ {day.get('precip_prob',0):.0f}%
    </div>
</div>""", unsafe_allow_html=True)

        # ── 7-day temperature range chart ─────────────────────────────────────
        if daily:
            dates    = [d["date"][5:] for d in daily]
            max_vals = [d.get("temp_max") for d in daily]
            min_vals = [d.get("temp_min") for d in daily]

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=dates, y=max_vals, name="Max °C",
                line=dict(color="#ff6b6b", width=2, shape="spline"),
                mode="lines+markers",
                marker=dict(size=6, color="#ff6b6b"),
            ))
            fig2.add_trace(go.Scatter(
                x=dates, y=min_vals, name="Min °C",
                line=dict(color="#00e5ff", width=2, shape="spline"),
                fill="tonexty", fillcolor="rgba(0,229,255,0.05)",
                mode="lines+markers",
                marker=dict(size=6, color="#00e5ff"),
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Rajdhani", color="#7ecdc8", size=11),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                margin=dict(l=10, r=10, t=10, b=10),
                hovermode="x unified",
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        # ── Best time outside ─────────────────────────────────────────────────
        st.markdown('<div class="section-title">🕐 Best Time to Go Outside</div>',
                    unsafe_allow_html=True)
        best = best_time_outside(hourly)
        st.markdown(f'<div class="glass-card">{best}</div>', unsafe_allow_html=True)

        # ── Precipitation heatmap (hourly rain prob) ──────────────────────────
        if hourly:
            st.markdown('<div class="section-title">🌧️ 48-Hour Precipitation Probability</div>',
                        unsafe_allow_html=True)
            h48 = hourly[:48]
            prob_vals = [h.get("precip_prob", 0) or 0 for h in h48]
            h48_times = [h["time"][11:16] for h in h48]

            fig3 = go.Figure(go.Bar(
                x=h48_times, y=prob_vals,
                marker=dict(
                    color=prob_vals,
                    colorscale=[[0,"rgba(0,229,255,0.2)"],[0.5,"rgba(41,121,255,0.5)"],
                                [1,"rgba(255,107,107,0.8)"]],
                    showscale=False,
                ),
            ))
            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(range=[0,100], gridcolor="rgba(255,255,255,0.05)"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)",
                           tickmode="array",
                           tickvals=h48_times[::3],
                           ticktext=h48_times[::3]),
                font=dict(family="Rajdhani", color="#7ecdc8"),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — MAP
# ══════════════════════════════════════════════════════════════════════════════

with tab_map:
    lat = st.session_state["lat"]
    lon = st.session_state["lon"]

    if lat is None or lon is None:
        st.info("Location not yet determined.")
    else:
        st.markdown('<div class="section-title">🗺️ Interactive Weather Map</div>',
                    unsafe_allow_html=True)

        # Build Folium map
        m = folium.Map(
            location=[lat, lon],
            zoom_start=10,
            tiles="CartoDB dark_matter",
        )

        # Main location marker
        temp_str = f"{W.get('temperature','?'):.0f}°C" if W.get("temperature") else "?"
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(
                f"<b>{CITY}</b><br>{EMOJI} {W.get('condition','—')}<br>"
                f"🌡️ {temp_str}<br>💧 {W.get('humidity','?')}%<br>"
                f"💨 {W.get('wind_speed','?'):.0f} km/h",
                max_width=200,
            ),
            tooltip=f"{CITY} — {temp_str}",
            icon=folium.Icon(color="blue", icon="cloud", prefix="fa"),
        ).add_to(m)

        # Simulated cloud/rainfall zone (circle overlay)
        cloud_pct = W.get("cloud_cover", 0) or 0
        rain_mm   = W.get("rainfall_1h", 0) or 0

        if cloud_pct > 40:
            folium.Circle(
                location=[lat, lon],
                radius=20000,
                color="#7ecdc8",
                fill=True,
                fill_color="#7ecdc8",
                fill_opacity=cloud_pct / 1000,
                tooltip=f"Cloud Cover: {cloud_pct}%",
            ).add_to(m)

        if rain_mm > 0.1:
            folium.Circle(
                location=[lat, lon],
                radius=15000,
                color="#2979ff",
                fill=True,
                fill_color="#2979ff",
                fill_opacity=min(0.35, rain_mm / 20),
                tooltip=f"Rainfall Zone: {rain_mm:.1f} mm/h",
            ).add_to(m)

        # Nearby cardinal direction markers (simulated radar)
        for dx, dy, lbl in [(0.3, 0, "N"), (-0.3, 0, "S"), (0, 0.4, "E"), (0, -0.4, "W")]:
            folium.CircleMarker(
                location=[lat + dx, lon + dy],
                radius=4,
                color="#00e5ff",
                fill=True,
                fill_color="#00e5ff",
                fill_opacity=0.3,
                tooltip=lbl,
            ).add_to(m)

        # OpenWeatherMap tile overlays (no key needed for some layers)
        folium.TileLayer(
            tiles="https://tile.openweathermap.org/map/clouds_new/{z}/{x}/{y}.png?appid=",
            attr="OpenWeatherMap",
            name="Clouds",
            opacity=0.4,
        ).add_to(m)

        folium.LayerControl().add_to(m)

        st_folium(m, width=None, height=520, returned_objects=[])

        # Map legend
        st.markdown("""
<div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:0.5rem;
     font-family:'Rajdhani',sans-serif;font-size:0.8rem;color:#7ecdc8;">
    <span>🔵 Your Location</span>
    <span>🩵 Cloud Cover Zone</span>
    <span>💙 Rainfall Zone</span>
    <span>⚪ Radar Points</span>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — CHAT ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════

with tab_chat:
    st.markdown("""
<div class="glass-card" style="margin-bottom:1rem;">
    <div class="section-title">💬 NEXUS Chat Assistant</div>
    <div style="font-family:'Rajdhani',sans-serif;font-size:0.9rem;color:#7ecdc8;">
        Ask me anything about the weather in <b style="color:#00e5ff;">{city}</b> —
        rain, UV, clothing, best time to go outside, and more.
    </div>
</div>
""".format(city=CITY), unsafe_allow_html=True)

    # Quick suggestion chips
    suggestions = [
        "Will it rain today?",
        "Should I carry an umbrella?",
        "Is it too hot outside?",
        "What should I wear?",
        "Is it safe to go jogging?",
        "How's the UV today?",
    ]
    chip_cols = st.columns(3)
    for i, sug in enumerate(suggestions):
        if chip_cols[i % 3].button(sug, key=f"chip_{i}", use_container_width=True):
            reply = chat_response(sug, W, CITY)
            st.session_state["chat_history"].append(("user", sug))
            st.session_state["chat_history"].append(("ai",   reply))

    st.divider()

    # Chat history
    if st.session_state["chat_history"]:
        for role, msg in st.session_state["chat_history"][-20:]:
            if role == "user":
                st.markdown(f'<div class="chat-user">🧑 {msg}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-ai">🤖 {msg}</div>', unsafe_allow_html=True)

    # Input
    user_q = st.text_input("Ask NEXUS…", placeholder="Type your question…",
                            label_visibility="collapsed", key="chat_input")
    col_send, col_clear = st.columns([3, 1])
    if col_send.button("Send ➤", use_container_width=True):
        if user_q.strip():
            reply = chat_response(user_q, W, CITY)
            st.session_state["chat_history"].append(("user", user_q))
            st.session_state["chat_history"].append(("ai",   reply))
            st.rerun()
    if col_clear.button("Clear", use_container_width=True):
        st.session_state["chat_history"] = []
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 5 — AI ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

with tab_ai:
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        # Summary
        st.markdown('<div class="section-title">🧠 AI Weather Summary</div>',
                    unsafe_allow_html=True)
        summary = generate_summary(W, CITY)
        st.markdown(f'<div class="glass-card" style="font-family:\'Rajdhani\',sans-serif;'
                    f'font-size:1.05rem;line-height:1.6;">{summary}</div>',
                    unsafe_allow_html=True)

        # Recommendations
        recs = get_recommendations(W)
        st.markdown('<div class="section-title" style="margin-top:1rem;">👕 Clothing & Activity</div>',
                    unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("**👔 What to Wear**")
        st.markdown(
            " ".join(f'<span class="rec-chip">{c}</span>' for c in recs["clothing"]),
            unsafe_allow_html=True,
        )
        st.write("")
        st.markdown("**🏃 Recommended Activities**")
        st.markdown(
            " ".join(f'<span class="rec-chip">{a}</span>' for a in recs["activities"]),
            unsafe_allow_html=True,
        )
        if recs["avoid"]:
            st.write("")
            st.markdown("**⚠️ Avoid**")
            st.markdown(
                " ".join(f'<span class="rec-chip rec-chip-warn">{a}</span>' for a in recs["avoid"]),
                unsafe_allow_html=True,
            )
        st.write("")
        st.markdown(f"**💧 Hydration Advisory**")
        st.markdown(recs["hydration"])
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        # Confidence breakdown
        st.markdown('<div class="section-title">📡 AI Confidence Engine</div>',
                    unsafe_allow_html=True)
        st.markdown(f"""
<div class="glass-card">
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">
        <div class="score-ring" style="color:{CCOLOR};border:3px solid {CCOLOR};width:60px;height:60px;font-size:1.1rem;">
            {CONF:.0f}%
        </div>
        <div>
            <div style="font-family:'Orbitron',sans-serif;font-size:0.9rem;
                 color:{CCOLOR};letter-spacing:2px;">{CLABEL}</div>
            <div style="font-size:0.75rem;color:#7ecdc8;margin-top:0.2rem;">
                Multi-source consensus confidence
            </div>
        </div>
    </div>
    <div style="font-size:0.8rem;color:#7ecdc8;font-family:'Rajdhani',sans-serif;line-height:1.6;">
        NEXUS aggregates weather data from up to 3 independent sources using 
        weighted mean fusion and outlier rejection. Higher confidence = 
        stronger inter-source agreement.
    </div>
</div>
""", unsafe_allow_html=True)

        # Radar/spider chart — weather dimensions
        st.markdown('<div class="section-title" style="margin-top:1rem;">🕸️ Condition Radar</div>',
                    unsafe_allow_html=True)

        temp_norm  = min(100, max(0, (W.get("temperature", 20) or 20) * 2))
        hum_norm   = W.get("humidity", 50) or 50
        wind_norm  = min(100, (W.get("wind_speed", 0) or 0) * 1.5)
        uv_norm    = min(100, (W.get("uv_index", 0) or 0) * 8)
        cloud_norm = W.get("cloud_cover", 0) or 0
        rain_norm  = min(100, (W.get("rainfall_1h", 0) or 0) * 10)

        categories = ["Temperature", "Humidity", "Wind", "UV Index", "Cloud Cover", "Rainfall"]
        values     = [temp_norm, hum_norm, wind_norm, uv_norm, cloud_norm, rain_norm]

        fig_radar = go.Figure(go.Scatterpolar(
            r     = values + [values[0]],
            theta = categories + [categories[0]],
            fill  = "toself",
            fillcolor = "rgba(0,229,255,0.1)",
            line  = dict(color="#00e5ff", width=2),
            name  = "Current",
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0,100],
                                gridcolor="rgba(255,255,255,0.08)",
                                tickfont=dict(color="#7ecdc8", size=9)),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.08)",
                                 tickfont=dict(color="#7ecdc8")),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(l=30, r=30, t=30, b=30),
        )
        st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

        # Weather score breakdown
        st.markdown('<div class="section-title">🏆 Weather Score Breakdown</div>',
                    unsafe_allow_html=True)

        score_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=SCORE,
            number={"font": {"family": "Orbitron", "color": SCOLOR}, "suffix": ""},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#7ecdc8"},
                "bar":  {"color": SCOLOR},
                "bgcolor": "rgba(0,0,0,0)",
                "bordercolor": "rgba(0,229,255,0.2)",
                "steps": [
                    {"range": [0,  35], "color": "rgba(255,107,107,0.15)"},
                    {"range": [35, 55], "color": "rgba(255,152,0,0.10)"},
                    {"range": [55, 70], "color": "rgba(255,209,102,0.10)"},
                    {"range": [70, 85], "color": "rgba(0,255,136,0.08)"},
                    {"range": [85,100], "color": "rgba(0,229,255,0.08)"},
                ],
                "threshold": {"line": {"color": SCOLOR, "width": 3}, "value": SCORE},
            },
        ))
        score_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Rajdhani", color="#7ecdc8"),
            margin=dict(l=10, r=10, t=10, b=10),
            height=200,
        )
        st.plotly_chart(score_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f'<div style="text-align:center;font-family:\'Orbitron\',sans-serif;'
            f'font-size:0.8rem;letter-spacing:2px;color:{SCOLOR};">{SLABEL} CONDITIONS</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 6 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════

with tab_history:
    stats = get_history_stats()
    s1, s2, s3, s4 = st.columns(4)
    for col, icon, label, val in [
        (s1, "🔍", "Total Searches",  stats["total_searches"]),
        (s2, "🏙️", "Unique Cities",  stats["unique_cities"]),
        (s3, "🌡️", "Avg Temperature", f"{stats['avg_temperature']:.1f}°C" if stats["avg_temperature"] else "—"),
        (s4, "📡", "Avg Confidence",  f"{stats['avg_confidence']:.0f}%" if stats["avg_confidence"] else "—"),
    ]:
        with col:
            st.markdown(f"""
<div class="metric-card">
    <div class="metric-icon">{icon}</div>
    <div class="metric-label">{label}</div>
    <div class="metric-value">{val}</div>
</div>""", unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="section-title">📋 Search History</div>', unsafe_allow_html=True)

    search_q = st.text_input("Search history…", placeholder="Filter by city…",
                              label_visibility="collapsed")

    if search_q.strip():
        rows = search_history(search_q.strip())
    else:
        rows = get_history(50)

    if rows:
        df = pd.DataFrame(rows)[[
            "searched_at", "city", "country", "temperature",
            "humidity", "wind_speed", "condition", "confidence", "weather_score",
        ]]
        df.columns = ["Time", "City", "Country", "Temp °C", "Humidity %",
                      "Wind km/h", "Condition", "Confidence %", "Score"]
        df["Temp °C"]      = df["Temp °C"].apply(lambda x: f"{x:.1f}" if x else "—")
        df["Wind km/h"]    = df["Wind km/h"].apply(lambda x: f"{x:.0f}" if x else "—")
        df["Confidence %"] = df["Confidence %"].apply(lambda x: f"{x:.0f}%" if x else "—")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No history records yet.")

    if st.button("🗑️ Clear All History", type="secondary"):
        clear_history()
        st.success("History cleared.")
# Copyright (c) 2026 Surya
# Non-commercial use only

"""
=============================================================================
  NEXUS WEATHER INTELLIGENCE  —  dashboard.py
  Production-grade futuristic AI Weather Dashboard
  Run with:  streamlit run dashboard.py
=============================================================================
  INSTALLATION (copy-paste into terminal):
    pip install streamlit requests folium streamlit-folium plotly pandas

  FREE API KEYS (optional — Open-Meteo works with ZERO keys):
    • OpenWeatherMap → https://openweathermap.org/api  (free tier)
    • WeatherAPI     → https://www.weatherapi.com/     (free tier)
    Paste your keys in multi_api_weather.py → OWM_API_KEY / WEATHERAPI_API_KEY
=============================================================================
"""

# ── Standard library ─────────────────────────────────────────────────────────
import time
import json
from datetime import datetime, timedelta

# ── Third-party ──────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium

# ── Local modules ─────────────────────────────────────────────────────────────
from fetch_weather import (
    geocode_city, ip_locate, reverse_geocode,
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


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG  (must be FIRST streamlit call)
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title  = "NEXUS | AI Weather Intelligence",
    page_icon   = "🌌",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)
init_db()


# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL CSS  —  Glassmorphism + Futuristic Dark UI
# ══════════════════════════════════════════════════════════════════════════════

def inject_css(bg_class: str = "bg-default"):
    st.markdown(f"""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Rajdhani:wght@300;400;600&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Root palette ── */
:root {{
    --neon-cyan:   #00e5ff;
    --neon-blue:   #2979ff;
    --neon-purple: #7c4dff;
    --neon-green:  #00ff88;
    --neon-pink:   #ff4081;
    --glass-bg:    rgba(10, 15, 30, 0.72);
    --glass-border:rgba(0, 229, 255, 0.18);
    --card-shadow: 0 8px 32px rgba(0, 229, 255, 0.12);
    --text-primary:#e8f4f8;
    --text-muted:  #7ecdc8;
}}

/* ── Full-page background ── */
.stApp {{
    background: #020810 !important;
    background-image:
        radial-gradient(ellipse at 20% 50%, rgba(41, 121, 255, 0.07) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 20%, rgba(124, 77, 255, 0.07) 0%, transparent 60%),
        radial-gradient(ellipse at 60% 80%, rgba(0, 229, 255, 0.05) 0%, transparent 60%);
    font-family: 'Rajdhani', sans-serif !important;
    color: var(--text-primary) !important;
}}

/* ── Background weather overlays ── */
.bg-rain {{
    background-image:
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cline x1='40' y1='0' x2='20' y2='200' stroke='%2300e5ff' stroke-width='1' opacity='0.06'/%3E%3Cline x1='90' y1='0' x2='70' y2='200' stroke='%2300e5ff' stroke-width='1' opacity='0.04'/%3E%3Cline x1='140' y1='0' x2='120' y2='200' stroke='%2300e5ff' stroke-width='1' opacity='0.06'/%3E%3Cline x1='180' y1='0' x2='160' y2='200' stroke='%2300e5ff' stroke-width='1' opacity='0.03'/%3E%3C/svg%3E"),
        radial-gradient(ellipse at 30% 30%, rgba(0,100,200,0.12) 0%, transparent 70%);
}}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 1rem 2rem 2rem 2rem !important; max-width: 100% !important; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: rgba(5, 10, 25, 0.95) !important;
    border-right: 1px solid var(--glass-border) !important;
}}
[data-testid="stSidebar"] * {{ color: var(--text-primary) !important; }}

/* ── Top header bar ── */
.nexus-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 2rem;
    background: rgba(0, 229, 255, 0.04);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(20px);
}}
.nexus-logo {{
    font-family: 'Orbitron', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--neon-cyan), var(--neon-blue), var(--neon-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 3px;
}}
.nexus-tagline {{
    font-family: 'Rajdhani', sans-serif;
    color: var(--text-muted);
    font-size: 0.85rem;
    letter-spacing: 2px;
    text-transform: uppercase;
}}
.nexus-clock {{
    font-family: 'JetBrains Mono', monospace;
    color: var(--neon-cyan);
    font-size: 1.1rem;
    opacity: 0.8;
}}

/* ── Glass card ── */
.glass-card {{
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1.4rem;
    backdrop-filter: blur(20px);
    box-shadow: var(--card-shadow);
    margin-bottom: 1rem;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}}
.glass-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
    opacity: 0.4;
}}
.glass-card:hover {{
    border-color: rgba(0, 229, 255, 0.35);
    box-shadow: 0 12px 40px rgba(0, 229, 255, 0.18);
    transform: translateY(-2px);
}}

/* ── Metric cards ── */
.metric-card {{
    background: linear-gradient(135deg, rgba(0,229,255,0.06) 0%, rgba(41,121,255,0.06) 100%);
    border: 1px solid rgba(0,229,255,0.15);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
    transition: all 0.3s ease;
    cursor: default;
}}
.metric-card:hover {{
    background: linear-gradient(135deg, rgba(0,229,255,0.12) 0%, rgba(41,121,255,0.12) 100%);
    border-color: rgba(0,229,255,0.35);
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,229,255,0.15);
}}
.metric-icon {{ font-size: 1.6rem; margin-bottom: 0.3rem; }}
.metric-label {{
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.2rem;
}}
.metric-value {{
    font-family: 'Orbitron', sans-serif;
    font-size: 1.4rem;
    font-weight: 600;
    color: var(--neon-cyan);
}}
.metric-sub {{
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 0.1rem;
}}

/* ── Big temperature display ── */
.temp-hero {{
    font-family: 'Orbitron', sans-serif;
    font-size: 5rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--neon-cyan), var(--neon-blue));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
    margin: 0.5rem 0;
    text-shadow: none;
    filter: drop-shadow(0 0 20px rgba(0,229,255,0.4));
}}
.condition-label {{
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.4rem;
    color: var(--text-muted);
    letter-spacing: 2px;
    text-transform: uppercase;
}}
.city-name {{
    font-family: 'Orbitron', sans-serif;
    font-size: 1.2rem;
    color: var(--neon-cyan);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}}
.weather-emoji-big {{ font-size: 4rem; filter: drop-shadow(0 0 12px rgba(0,229,255,0.5)); }}

/* ── Confidence badge ── */
.conf-badge {{
    display: inline-block;
    padding: 0.25rem 0.9rem;
    border-radius: 20px;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 2px;
    border: 1px solid currentColor;
    margin-top: 0.5rem;
}}

/* ── Section titles ── */
.section-title {{
    font-family: 'Orbitron', sans-serif;
    font-size: 0.8rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--neon-cyan);
    margin-bottom: 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--glass-border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}

/* ── Progress bars (custom) ── */
.gauge-container {{ margin: 0.4rem 0; }}
.gauge-label {{
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.2rem;
    font-family: 'Rajdhani', sans-serif;
    letter-spacing: 1px;
}}
.gauge-track {{
    background: rgba(255,255,255,0.06);
    border-radius: 99px;
    height: 6px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.04);
}}
.gauge-fill {{
    height: 100%;
    border-radius: 99px;
    transition: width 1s ease;
}}

/* ── Alert cards ── */
.alert-critical {{
    background: linear-gradient(135deg, rgba(255,50,50,0.12), rgba(255,100,50,0.08));
    border: 1px solid rgba(255,80,80,0.4);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
}}
.alert-warning {{
    background: linear-gradient(135deg, rgba(255,193,7,0.10), rgba(255,152,0,0.06));
    border: 1px solid rgba(255,193,7,0.3);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
}}
.alert-info {{
    background: linear-gradient(135deg, rgba(0,229,255,0.08), rgba(41,121,255,0.05));
    border: 1px solid rgba(0,229,255,0.2);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
}}

/* ── Chat bubbles ── */
.chat-user {{
    background: linear-gradient(135deg, rgba(41,121,255,0.2), rgba(124,77,255,0.1));
    border: 1px solid rgba(41,121,255,0.3);
    border-radius: 12px 12px 2px 12px;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
    max-width: 80%;
    margin-left: auto;
    font-family: 'Rajdhani', sans-serif;
}}
.chat-ai {{
    background: linear-gradient(135deg, rgba(0,229,255,0.08), rgba(0,255,136,0.05));
    border: 1px solid rgba(0,229,255,0.2);
    border-radius: 12px 12px 12px 2px;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
    max-width: 85%;
    font-family: 'Rajdhani', sans-serif;
}}

/* ── Status indicator ── */
.ai-status {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.75rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--neon-green);
}}
.ai-dot {{
    width: 8px;
    height: 8px;
    background: var(--neon-green);
    border-radius: 50%;
    animation: pulse 2s infinite;
    box-shadow: 0 0 8px var(--neon-green);
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.4; transform: scale(0.8); }}
}}

/* ── Greeting text ── */
.greeting {{
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    color: var(--text-muted);
    letter-spacing: 1px;
}}

/* ── Streamlit widget overrides ── */
.stTextInput input, .stSelectbox select {{
    background: rgba(0,229,255,0.04) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'Rajdhani', sans-serif !important;
}}
.stButton > button {{
    background: linear-gradient(135deg, var(--neon-blue), var(--neon-purple)) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.75rem !important;
    letter-spacing: 2px !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(41,121,255,0.3) !important;
}}
.stButton > button:hover {{
    box-shadow: 0 6px 25px rgba(0,229,255,0.5) !important;
    transform: translateY(-2px) !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.7rem !important;
    letter-spacing: 2px !important;
    color: var(--text-muted) !important;
}}
.stTabs [aria-selected="true"] {{
    color: var(--neon-cyan) !important;
    border-bottom-color: var(--neon-cyan) !important;
}}

/* ── Recommendation chips ── */
.rec-chip {{
    display: inline-block;
    background: rgba(0,229,255,0.08);
    border: 1px solid rgba(0,229,255,0.2);
    border-radius: 20px;
    padding: 0.2rem 0.7rem;
    font-size: 0.78rem;
    margin: 0.15rem;
    font-family: 'Rajdhani', sans-serif;
    color: var(--text-primary);
}}
.rec-chip-warn {{
    background: rgba(255,100,50,0.08);
    border-color: rgba(255,100,50,0.25);
}}

/* ── History table ── */
.stDataFrame {{ border-radius: 12px; overflow: hidden; }}

/* ── Weather score ring ── */
.score-ring {{
    width: 80px;
    height: 80px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Orbitron', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    box-shadow: 0 0 20px currentColor;
    margin: 0 auto;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: #020810; }}
::-webkit-scrollbar-thumb {{ background: var(--neon-blue); border-radius: 4px; }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE DEFAULTS
# ══════════════════════════════════════════════════════════════════════════════

def _init_state():
    defaults = {
        "city":          "",
        "lat":           None,
        "lon":           None,
        "weather":       None,   # aggregated weather dict
        "forecast":      None,   # {hourly, daily}
        "confidence":    0,
        "conf_label":    "LOW",
        "score":         0,
        "chat_history":  [],
        "alerts":        [],
        "last_refresh":  None,
        "unit":          "°C",
        "user_name":     get_pref("user_name", ""),
        "auto_refresh":  False,
        "error_msg":     "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _greeting() -> str:
    h = datetime.now().hour
    if h < 12:  return "Good Morning"
    if h < 17:  return "Good Afternoon"
    if h < 20:  return "Good Evening"
    return "Good Night"


def _temp_display(val, unit="°C") -> str:
    if val is None: return "—"
    if unit == "°F":
        return f"{val * 9/5 + 32:.1f}°F"
    return f"{val:.1f}°C"


def _uv_label(uv) -> str:
    if uv is None: return "Unknown"
    if uv >= 11: return "🔴 Extreme"
    if uv >= 8:  return "🟠 Very High"
    if uv >= 6:  return "🟡 High"
    if uv >= 3:  return "🟢 Moderate"
    return "🟢 Low"


def _aqi_label(aqi) -> str:
    if aqi is None: return "N/A"
    labels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor", 6: "Hazardous"}
    return labels.get(int(aqi), f"AQI {aqi}")


def _gauge_html(label: str, value: float, max_val: float, unit: str,
                gradient: str = "linear-gradient(90deg, #00e5ff, #2979ff)") -> str:
    pct = min(100, max(0, (value / max_val) * 100)) if max_val else 0
    return f"""
<div class="gauge-container">
    <div class="gauge-label"><span>{label}</span><span>{value:.0f} {unit}</span></div>
    <div class="gauge-track">
        <div class="gauge-fill" style="width:{pct:.0f}%;background:{gradient};"></div>
    </div>
</div>"""


def _conf_badge_html(label: str, color: str) -> str:
    return f'<span class="conf-badge" style="color:{color};border-color:{color};">{label}</span>'


# ══════════════════════════════════════════════════════════════════════════════
#  WEATHER FETCH + STORE
# ══════════════════════════════════════════════════════════════════════════════

def do_fetch(city_query: str):
    """Geocode city, fetch multi-API weather, compute AI analysis, store DB."""
    st.session_state["error_msg"] = ""
    try:
        with st.spinner("🛰️  Connecting to weather satellites…"):
            geo   = geocode_city(city_query)
            lat, lon = geo["lat"], geo["lon"]
            city_disp = city_query.strip().title()

            result   = aggregate_weather(lat, lon)
            forecast = fetch_open_meteo_forecast(lat, lon)

        data     = result["data"]
        conf     = result["confidence"]
        clabel   = result["confidence_label"]
        score    = compute_weather_score(data)
        alerts   = generate_alerts(data)

        # Persist
        save_search(
            city     = city_disp,
            country  = geo.get("country", ""),
            weather_data = data,
            confidence   = conf,
            score        = score,
        )

        # Update session
        st.session_state.update({
            "city":         city_disp,
            "lat":          lat,
            "lon":          lon,
            "weather":      data,
            "forecast":     forecast,
            "confidence":   conf,
            "conf_label":   clabel,
            "score":        score,
            "alerts":       alerts,
            "last_refresh": datetime.now(),
        })

    except ValueError as e:
        st.session_state["error_msg"] = f"🔍 {e}"
    except ConnectionError as e:
        st.session_state["error_msg"] = f"🌐 {e}"
    except Exception as e:
        st.session_state["error_msg"] = f"⚠️ Unexpected error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-DETECT LOCATION ON FIRST LOAD
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state["weather"] is None and not st.session_state.get("_auto_tried"):
    st.session_state["_auto_tried"] = True
    loc = ip_locate()
    if loc and loc.get("city"):
        do_fetch(loc["city"])


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-REFRESH  (5-minute timer)
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state["auto_refresh"] and st.session_state.get("last_refresh"):
    elapsed = (datetime.now() - st.session_state["last_refresh"]).seconds
    if elapsed >= 300 and st.session_state["city"]:
        do_fetch(st.session_state["city"])

# Inject CSS (with rain overlay if raining)
cond_css = ""
if st.session_state["weather"]:
    c = (st.session_state["weather"].get("condition") or "").lower()
    if any(k in c for k in ["rain", "drizzle", "shower"]): cond_css = "bg-rain"

inject_css(cond_css)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
<div style="text-align:center;margin-bottom:1.5rem;">
    <div style="font-family:'Orbitron',sans-serif;font-size:1.3rem;font-weight:800;
         background:linear-gradient(135deg,#00e5ff,#7c4dff);
         -webkit-background-clip:text;-webkit-text-fill-color:transparent;
         letter-spacing:3px;">NEXUS</div>
    <div style="font-size:0.65rem;letter-spacing:2px;color:#7ecdc8;
         text-transform:uppercase;margin-top:2px;">Weather Intelligence</div>
    <div class="ai-status" style="justify-content:center;margin-top:0.6rem;">
        <div class="ai-dot"></div> AI Online
    </div>
</div>
""", unsafe_allow_html=True)

    # ── City search ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🔍 Location</div>', unsafe_allow_html=True)
    city_input = st.text_input(
        "Search City",
        placeholder="e.g. Tokyo, Mumbai, New York…",
        label_visibility="collapsed",
    )
    if st.button("▶  FETCH WEATHER", use_container_width=True):
        if city_input.strip():
            do_fetch(city_input.strip())
        else:
            st.warning("Enter a city name first.")

    # ── Quick favourites ──────────────────────────────────────────────────────
    favs = get_favourites()
    if favs:
        st.markdown('<div class="section-title" style="margin-top:1rem;">⭐ Favourites</div>', unsafe_allow_html=True)
        for f in favs[:5]:
            col_a, col_b = st.columns([4, 1])
            if col_a.button(f["city"], key=f"fav_{f['id']}", use_container_width=True):
                do_fetch(f["city"])
            if col_b.button("✕", key=f"delfav_{f['id']}"):
                remove_favourite(f["city"])
                st.rerun()

    # ── Quick history ─────────────────────────────────────────────────────────
    hist = get_history(6)
    if hist:
        st.markdown('<div class="section-title" style="margin-top:1rem;">🕐 Recent</div>', unsafe_allow_html=True)
        for h in hist:
            if st.button(f"{h['city']}  {h['temperature']:.0f}°C" if h.get("temperature") else h["city"],
                         key=f"hst_{h['id']}", use_container_width=True):
                do_fetch(h["city"])

    st.divider()

    # ── Settings ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">⚙️ Settings</div>', unsafe_allow_html=True)

    user_name = st.text_input("Your Name (optional)", value=st.session_state["user_name"],
                               placeholder="e.g. Surya")
    if user_name != st.session_state["user_name"]:
        st.session_state["user_name"] = user_name
        set_pref("user_name", user_name)

    unit_choice = st.radio("Temperature Unit", ["°C", "°F"], horizontal=True,
                            index=0 if st.session_state["unit"] == "°C" else 1)
    st.session_state["unit"] = unit_choice

    auto_ref = st.toggle("Auto-Refresh (5 min)", value=st.session_state["auto_refresh"])
    st.session_state["auto_refresh"] = auto_ref

    if st.session_state["weather"] and st.session_state["city"]:
        if st.button("⭐ Add to Favourites", use_container_width=True):
            added = add_favourite(st.session_state["city"])
            if added:  st.success("Added!")
            else:      st.info("Already in favourites.")

    if st.button("🔄 Refresh Now", use_container_width=True):
        if st.session_state["city"]:
            do_fetch(st.session_state["city"])

    # ── Last refresh ─────────────────────────────────────────────────────────
    if st.session_state["last_refresh"]:
        elapsed = (datetime.now() - st.session_state["last_refresh"]).seconds
        st.markdown(
            f'<div style="font-size:0.7rem;color:#7ecdc8;text-align:center;margin-top:0.5rem;">'
            f'Updated {elapsed}s ago</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════

# ── Top header bar ───────────────────────────────────────────────────────────
greeting_name = f", {st.session_state['user_name']}" if st.session_state["user_name"] else ""
now_str = datetime.now().strftime("%a %d %b  %H:%M:%S")

st.markdown(f"""
<div class="nexus-header">
    <div>
        <div class="nexus-logo">NEXUS</div>
        <div class="nexus-tagline">AI Weather Intelligence Platform</div>
    </div>
    <div style="text-align:center;">
        <div class="greeting">{_greeting()}{greeting_name} 👋</div>
        <div class="ai-status" style="justify-content:center;margin-top:0.3rem;">
            <div class="ai-dot"></div> All Systems Nominal
        </div>
    </div>
    <div class="nexus-clock">{now_str}</div>
</div>
""", unsafe_allow_html=True)

# ── Error display ─────────────────────────────────────────────────────────────
if st.session_state["error_msg"]:
    st.markdown(f'<div class="alert-critical">{st.session_state["error_msg"]}</div>',
                unsafe_allow_html=True)

# ── No data yet ───────────────────────────────────────────────────────────────
if st.session_state["weather"] is None:
    st.markdown("""
<div class="glass-card" style="text-align:center;padding:4rem 2rem;">
    <div style="font-size:4rem;margin-bottom:1rem;">🌌</div>
    <div style="font-family:'Orbitron',sans-serif;font-size:1.4rem;
         color:#00e5ff;letter-spacing:3px;margin-bottom:0.8rem;">
        NEXUS WEATHER INTELLIGENCE
    </div>
    <div style="color:#7ecdc8;font-family:'Rajdhani',sans-serif;font-size:1.1rem;
         max-width:500px;margin:0 auto;">
        Search for any city using the sidebar to activate the AI weather analysis engine.
        Your location has been auto-detected — if data appears, you're ready to go.
    </div>
</div>
""", unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  DATA SHORTHANDS
# ══════════════════════════════════════════════════════════════════════════════

W       = st.session_state["weather"]
CITY    = st.session_state["city"]
UNIT    = st.session_state["unit"]
SCORE   = st.session_state["score"]
CONF    = st.session_state["confidence"]
CLABEL  = st.session_state["conf_label"]
ALERTS  = st.session_state["alerts"]
FCST    = st.session_state["forecast"] or {"hourly": [], "daily": []}
EMOJI   = condition_to_emoji(W.get("condition", "Clear"))
SLABEL, SCOLOR = score_label(SCORE)
CCOLOR  = confidence_color(CLABEL)


# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_now, tab_forecast, tab_map, tab_chat, tab_ai, tab_history = st.tabs([
    "🌡️  NOW",
    "📈  FORECAST",
    "🗺️  MAP",
    "💬  CHAT",
    "🤖  AI ANALYSIS",
    "📂  HISTORY",
])


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — CURRENT WEATHER
# ══════════════════════════════════════════════════════════════════════════════

with tab_now:

    # ── Alert banners ─────────────────────────────────────────────────────────
    for alert in ALERTS:
        css_cls = {"critical": "alert-critical", "warning": "alert-warning",
                   "info": "alert-info"}.get(alert["severity"], "alert-info")
        st.markdown(
            f'<div class="{css_cls}"><b>{alert["icon"]} {alert["type"]}</b> — {alert["message"]}</div>',
            unsafe_allow_html=True,
        )

    # ── Hero row ──────────────────────────────────────────────────────────────
    hero_col, metrics_col = st.columns([1, 2], gap="large")

    with hero_col:
        st.markdown(f"""
<div class="glass-card" style="text-align:center;padding:2rem 1.5rem;">
    <div class="city-name">{CITY}</div>
    <div class="weather-emoji-big">{EMOJI}</div>
    <div class="temp-hero">{_temp_display(W.get('temperature'), UNIT)}</div>
    <div class="condition-label">{W.get('condition','—')}</div>
    <div style="color:#7ecdc8;font-size:0.9rem;margin-top:0.4rem;font-family:'Rajdhani',sans-serif;">
        Feels like {_temp_display(W.get('feels_like'), UNIT)}
    </div>
    {_conf_badge_html(CLABEL, CCOLOR)}
    <div style="margin-top:1rem;">
        <div class="score-ring" style="color:{SCOLOR};border:3px solid {SCOLOR};">
            {SCORE}
        </div>
        <div style="font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;
             color:#7ecdc8;margin-top:0.3rem;font-family:'Rajdhani',sans-serif;">
            Weather Score — {SLABEL}
        </div>
    </div>
    <div style="margin-top:1rem;font-size:0.75rem;color:#7ecdc8;font-family:'JetBrains Mono',monospace;">
        {W.get('sunrise','—')} ☀️ &nbsp;&nbsp;&nbsp; 🌙 {W.get('sunset','—')}
    </div>
</div>
""", unsafe_allow_html=True)

    with metrics_col:
        # Row 1 of metrics
        m1, m2, m3, m4 = st.columns(4)
        metrics_row1 = [
            (m1, "💧", "HUMIDITY",    W.get("humidity"),    "%",    "Moisture"),
            (m2, "💨", "WIND",        W.get("wind_speed"),  "km/h", f"{W.get('wind_direction','—')}°"),
            (m3, "🌡️", "PRESSURE",   W.get("pressure"),    "hPa",  "Atmospheric"),
            (m4, "👁️", "VISIBILITY", W.get("visibility"),  "km",   "Line of sight"),
        ]
        for col, icon, label, val, unit, sub in metrics_row1:
            with col:
                v_str = f"{val:.0f}" if val is not None else "—"
                st.markdown(f"""
<div class="metric-card">
    <div class="metric-icon">{icon}</div>
    <div class="metric-label">{label}</div>
    <div class="metric-value">{v_str}<span style="font-size:0.75rem;opacity:0.7;"> {unit}</span></div>
    <div class="metric-sub">{sub}</div>
</div>""", unsafe_allow_html=True)

        st.write("")

        # Row 2 of metrics
        m5, m6, m7, m8 = st.columns(4)
        metrics_row2 = [
            (m5, "☀️",  "UV INDEX",    W.get("uv_index"),    "",     _uv_label(W.get("uv_index"))),
            (m6, "☁️",  "CLOUD COVER", W.get("cloud_cover"), "%",    "Overcast level"),
            (m7, "🌧️", "RAINFALL",   W.get("rainfall_1h"), "mm/h", "1-hour total"),
            (m8, "😷",  "AQI",         W.get("aqi"),         "",     _aqi_label(W.get("aqi"))),
        ]
        for col, icon, label, val, unit, sub in metrics_row2:
            with col:
                v_str = f"{val:.1f}" if val is not None else "—"
                st.markdown(f"""
<div class="metric-card">
    <div class="metric-icon">{icon}</div>
    <div class="metric-label">{label}</div>
    <div class="metric-value">{v_str}<span style="font-size:0.75rem;opacity:0.7;"> {unit}</span></div>
    <div class="metric-sub">{sub}</div>
</div>""", unsafe_allow_html=True)

        st.write("")

        # Gauges
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📊 Live Gauges</div>', unsafe_allow_html=True)

        g1, g2 = st.columns(2)
        with g1:
            st.markdown(
                _gauge_html("Humidity", W.get("humidity", 0), 100, "%",
                            "linear-gradient(90deg,#00e5ff,#2979ff)"),
                unsafe_allow_html=True,
            )
            st.markdown(
                _gauge_html("Wind Speed", W.get("wind_speed", 0), 120, "km/h",
                            "linear-gradient(90deg,#7c4dff,#ff4081)"),
                unsafe_allow_html=True,
            )
        with g2:
            st.markdown(
                _gauge_html("Cloud Cover", W.get("cloud_cover", 0), 100, "%",
                            "linear-gradient(90deg,#7ecdc8,#7c4dff)"),
                unsafe_allow_html=True,
            )
            uv_val = W.get("uv_index", 0) or 0
            st.markdown(
                _gauge_html("UV Index", uv_val, 12, "",
                            "linear-gradient(90deg,#ffd166,#ff6b6b)"),
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Voice button ──────────────────────────────────────────────────────────
    st.markdown("---")
    col_v, col_s = st.columns([1, 3])
    with col_v:
        if st.button("🔊  SPEAK WEATHER"):
            vs = voice_summary(W, CITY)
            # Browser-safe TTS via JavaScript
            safe = vs.replace("'", "\\'").replace("\n", " ")
            st.components.v1.html(f"""
<script>
var u = new SpeechSynthesisUtterance('{safe}');
u.rate = 0.95; u.pitch = 1.05; u.volume = 1;
window.speechSynthesis.cancel();
window.speechSynthesis.speak(u);
</script>
""", height=0)
            st.success("🔊 Speaking…")

    # ── Data sources indicator ────────────────────────────────────────────────
    sources = st.session_state.get("weather", {})  # pull from last result
    # Show source chips (stored implicitly from last aggregate call)
    st.markdown(
        '<div style="font-size:0.72rem;color:#7ecdc8;font-family:\'Rajdhani\',sans-serif;letter-spacing:1px;">'
        '🛰️ Data sources: Open-Meteo (always) + OpenWeatherMap + WeatherAPI (if keys configured)'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — FORECAST
# ══════════════════════════════════════════════════════════════════════════════

with tab_forecast:
    hourly = FCST.get("hourly", [])
    daily  = FCST.get("daily",  [])

    if not hourly and not daily:
        st.info("Forecast data unavailable.")
    else:
        # ── 24-hour temperature chart ──────────────────────────────────────────
        st.markdown('<div class="section-title">📈 24-Hour Temperature Trend</div>',
                    unsafe_allow_html=True)

        h24 = hourly[:24]
        if h24:
            times  = [h["time"][11:16] for h in h24]
            temps  = [h.get("temperature") for h in h24]
            feels  = [h.get("feels_like") for h in h24]
            precip = [h.get("precip_prob", 0) or 0 for h in h24]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=times, y=temps, name="Temperature",
                line=dict(color="#00e5ff", width=2.5, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(0,229,255,0.06)",
                mode="lines",
            ))
            fig.add_trace(go.Scatter(
                x=times, y=feels, name="Feels Like",
                line=dict(color="#7c4dff", width=1.5, dash="dot", shape="spline"),
                mode="lines",
            ))
            fig.add_trace(go.Bar(
                x=times, y=precip, name="Rain Prob %",
                marker_color="rgba(41,121,255,0.25)",
                yaxis="y2",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Rajdhani", color="#7ecdc8", size=11),
                legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,229,255,0.2)"),
                yaxis=dict(title="°C", gridcolor="rgba(255,255,255,0.05)",
                           zeroline=False, tickfont=dict(color="#7ecdc8")),
                yaxis2=dict(title="Rain %", overlaying="y", side="right",
                            range=[0, 200], tickfont=dict(color="#7ecdc8"),
                            showgrid=False),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#7ecdc8")),
                margin=dict(l=10, r=10, t=10, b=10),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── 7-day daily forecast ──────────────────────────────────────────────
        st.markdown('<div class="section-title">📅 7-Day Forecast</div>', unsafe_allow_html=True)

        if daily:
            cols = st.columns(min(7, len(daily)))
            for i, (col, day) in enumerate(zip(cols, daily)):
                date_str = day["date"]
                try:
                    dt_obj  = datetime.strptime(date_str, "%Y-%m-%d")
                    day_lbl = "Today" if i == 0 else dt_obj.strftime("%a")
                    date_lbl= dt_obj.strftime("%d %b")
                except Exception:
                    day_lbl  = date_str
                    date_lbl = ""

                d_emoji = condition_to_emoji(day.get("condition", "Clear"))
                tmax = day.get("temp_max")
                tmin = day.get("temp_min")

                with col:
                    st.markdown(f"""
<div class="metric-card" style="padding:0.8rem 0.4rem;">
    <div style="font-family:'Orbitron',sans-serif;font-size:0.65rem;
         letter-spacing:2px;color:#7ecdc8;">{day_lbl}</div>
    <div style="font-size:0.6rem;color:#4a6a6a;margin-bottom:0.3rem;">{date_lbl}</div>
    <div style="font-size:1.8rem;">{d_emoji}</div>
    <div style="font-family:'Orbitron',sans-serif;font-size:0.9rem;
         color:#00e5ff;font-weight:600;">{tmax:.0f}°</div>
    <div style="font-size:0.75rem;color:#7ecdc8;">{tmin:.0f}°</div>
    <div style="font-size:0.65rem;color:#4a8a9a;margin-top:0.3rem;">
        🌧️ {day.get('precip_prob',0):.0f}%
    </div>
</div>""", unsafe_allow_html=True)

        # ── 7-day temperature range chart ─────────────────────────────────────
        if daily:
            dates    = [d["date"][5:] for d in daily]
            max_vals = [d.get("temp_max") for d in daily]
            min_vals = [d.get("temp_min") for d in daily]

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=dates, y=max_vals, name="Max °C",
                line=dict(color="#ff6b6b", width=2, shape="spline"),
                mode="lines+markers",
                marker=dict(size=6, color="#ff6b6b"),
            ))
            fig2.add_trace(go.Scatter(
                x=dates, y=min_vals, name="Min °C",
                line=dict(color="#00e5ff", width=2, shape="spline"),
                fill="tonexty", fillcolor="rgba(0,229,255,0.05)",
                mode="lines+markers",
                marker=dict(size=6, color="#00e5ff"),
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Rajdhani", color="#7ecdc8", size=11),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                margin=dict(l=10, r=10, t=10, b=10),
                hovermode="x unified",
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        # ── Best time outside ─────────────────────────────────────────────────
        st.markdown('<div class="section-title">🕐 Best Time to Go Outside</div>',
                    unsafe_allow_html=True)
        best = best_time_outside(hourly)
        st.markdown(f'<div class="glass-card">{best}</div>', unsafe_allow_html=True)

        # ── Precipitation heatmap (hourly rain prob) ──────────────────────────
        if hourly:
            st.markdown('<div class="section-title">🌧️ 48-Hour Precipitation Probability</div>',
                        unsafe_allow_html=True)
            h48 = hourly[:48]
            prob_vals = [h.get("precip_prob", 0) or 0 for h in h48]
            h48_times = [h["time"][11:16] for h in h48]

            fig3 = go.Figure(go.Bar(
                x=h48_times, y=prob_vals,
                marker=dict(
                    color=prob_vals,
                    colorscale=[[0,"rgba(0,229,255,0.2)"],[0.5,"rgba(41,121,255,0.5)"],
                                [1,"rgba(255,107,107,0.8)"]],
                    showscale=False,
                ),
            ))
            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(range=[0,100], gridcolor="rgba(255,255,255,0.05)"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)",
                           tickmode="array",
                           tickvals=h48_times[::3],
                           ticktext=h48_times[::3]),
                font=dict(family="Rajdhani", color="#7ecdc8"),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — MAP
# ══════════════════════════════════════════════════════════════════════════════

with tab_map:
    lat = st.session_state["lat"]
    lon = st.session_state["lon"]

    if lat is None or lon is None:
        st.info("Location not yet determined.")
    else:
        st.markdown('<div class="section-title">🗺️ Interactive Weather Map</div>',
                    unsafe_allow_html=True)

        # Build Folium map
        m = folium.Map(
            location=[lat, lon],
            zoom_start=10,
            tiles="CartoDB dark_matter",
        )

        # Main location marker
        temp_str = f"{W.get('temperature','?'):.0f}°C" if W.get("temperature") else "?"
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(
                f"<b>{CITY}</b><br>{EMOJI} {W.get('condition','—')}<br>"
                f"🌡️ {temp_str}<br>💧 {W.get('humidity','?')}%<br>"
                f"💨 {W.get('wind_speed','?'):.0f} km/h",
                max_width=200,
            ),
            tooltip=f"{CITY} — {temp_str}",
            icon=folium.Icon(color="blue", icon="cloud", prefix="fa"),
        ).add_to(m)

        # Simulated cloud/rainfall zone (circle overlay)
        cloud_pct = W.get("cloud_cover", 0) or 0
        rain_mm   = W.get("rainfall_1h", 0) or 0

        if cloud_pct > 40:
            folium.Circle(
                location=[lat, lon],
                radius=20000,
                color="#7ecdc8",
                fill=True,
                fill_color="#7ecdc8",
                fill_opacity=cloud_pct / 1000,
                tooltip=f"Cloud Cover: {cloud_pct}%",
            ).add_to(m)

        if rain_mm > 0.1:
            folium.Circle(
                location=[lat, lon],
                radius=15000,
                color="#2979ff",
                fill=True,
                fill_color="#2979ff",
                fill_opacity=min(0.35, rain_mm / 20),
                tooltip=f"Rainfall Zone: {rain_mm:.1f} mm/h",
            ).add_to(m)

        # Nearby cardinal direction markers (simulated radar)
        for dx, dy, lbl in [(0.3, 0, "N"), (-0.3, 0, "S"), (0, 0.4, "E"), (0, -0.4, "W")]:
            folium.CircleMarker(
                location=[lat + dx, lon + dy],
                radius=4,
                color="#00e5ff",
                fill=True,
                fill_color="#00e5ff",
                fill_opacity=0.3,
                tooltip=lbl,
            ).add_to(m)

        # OpenWeatherMap tile overlays (no key needed for some layers)
        folium.TileLayer(
            tiles="https://tile.openweathermap.org/map/clouds_new/{z}/{x}/{y}.png?appid=",
            attr="OpenWeatherMap",
            name="Clouds",
            opacity=0.4,
        ).add_to(m)

        folium.LayerControl().add_to(m)

        st_folium(m, width=None, height=520, returned_objects=[])

        # Map legend
        st.markdown("""
<div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:0.5rem;
     font-family:'Rajdhani',sans-serif;font-size:0.8rem;color:#7ecdc8;">
    <span>🔵 Your Location</span>
    <span>🩵 Cloud Cover Zone</span>
    <span>💙 Rainfall Zone</span>
    <span>⚪ Radar Points</span>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — CHAT ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════

with tab_chat:
    st.markdown("""
<div class="glass-card" style="margin-bottom:1rem;">
    <div class="section-title">💬 NEXUS Chat Assistant</div>
    <div style="font-family:'Rajdhani',sans-serif;font-size:0.9rem;color:#7ecdc8;">
        Ask me anything about the weather in <b style="color:#00e5ff;">{city}</b> —
        rain, UV, clothing, best time to go outside, and more.
    </div>
</div>
""".format(city=CITY), unsafe_allow_html=True)

    # Quick suggestion chips
    suggestions = [
        "Will it rain today?",
        "Should I carry an umbrella?",
        "Is it too hot outside?",
        "What should I wear?",
        "Is it safe to go jogging?",
        "How's the UV today?",
    ]
    chip_cols = st.columns(3)
    for i, sug in enumerate(suggestions):
        if chip_cols[i % 3].button(sug, key=f"chip_{i}", use_container_width=True):
            reply = chat_response(sug, W, CITY)
            st.session_state["chat_history"].append(("user", sug))
            st.session_state["chat_history"].append(("ai",   reply))

    st.divider()

    # Chat history
    if st.session_state["chat_history"]:
        for role, msg in st.session_state["chat_history"][-20:]:
            if role == "user":
                st.markdown(f'<div class="chat-user">🧑 {msg}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-ai">🤖 {msg}</div>', unsafe_allow_html=True)

    # Input
    user_q = st.text_input("Ask NEXUS…", placeholder="Type your question…",
                            label_visibility="collapsed", key="chat_input")
    col_send, col_clear = st.columns([3, 1])
    if col_send.button("Send ➤", use_container_width=True):
        if user_q.strip():
            reply = chat_response(user_q, W, CITY)
            st.session_state["chat_history"].append(("user", user_q))
            st.session_state["chat_history"].append(("ai",   reply))
            st.rerun()
    if col_clear.button("Clear", use_container_width=True):
        st.session_state["chat_history"] = []
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 5 — AI ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

with tab_ai:
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        # Summary
        st.markdown('<div class="section-title">🧠 AI Weather Summary</div>',
                    unsafe_allow_html=True)
        summary = generate_summary(W, CITY)
        st.markdown(f'<div class="glass-card" style="font-family:\'Rajdhani\',sans-serif;'
                    f'font-size:1.05rem;line-height:1.6;">{summary}</div>',
                    unsafe_allow_html=True)

        # Recommendations
        recs = get_recommendations(W)
        st.markdown('<div class="section-title" style="margin-top:1rem;">👕 Clothing & Activity</div>',
                    unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("**👔 What to Wear**")
        st.markdown(
            " ".join(f'<span class="rec-chip">{c}</span>' for c in recs["clothing"]),
            unsafe_allow_html=True,
        )
        st.write("")
        st.markdown("**🏃 Recommended Activities**")
        st.markdown(
            " ".join(f'<span class="rec-chip">{a}</span>' for a in recs["activities"]),
            unsafe_allow_html=True,
        )
        if recs["avoid"]:
            st.write("")
            st.markdown("**⚠️ Avoid**")
            st.markdown(
                " ".join(f'<span class="rec-chip rec-chip-warn">{a}</span>' for a in recs["avoid"]),
                unsafe_allow_html=True,
            )
        st.write("")
        st.markdown(f"**💧 Hydration Advisory**")
        st.markdown(recs["hydration"])
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        # Confidence breakdown
        st.markdown('<div class="section-title">📡 AI Confidence Engine</div>',
                    unsafe_allow_html=True)
        st.markdown(f"""
<div class="glass-card">
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">
        <div class="score-ring" style="color:{CCOLOR};border:3px solid {CCOLOR};width:60px;height:60px;font-size:1.1rem;">
            {CONF:.0f}%
        </div>
        <div>
            <div style="font-family:'Orbitron',sans-serif;font-size:0.9rem;
                 color:{CCOLOR};letter-spacing:2px;">{CLABEL}</div>
            <div style="font-size:0.75rem;color:#7ecdc8;margin-top:0.2rem;">
                Multi-source consensus confidence
            </div>
        </div>
    </div>
    <div style="font-size:0.8rem;color:#7ecdc8;font-family:'Rajdhani',sans-serif;line-height:1.6;">
        NEXUS aggregates weather data from up to 3 independent sources using 
        weighted mean fusion and outlier rejection. Higher confidence = 
        stronger inter-source agreement.
    </div>
</div>
""", unsafe_allow_html=True)

        # Radar/spider chart — weather dimensions
        st.markdown('<div class="section-title" style="margin-top:1rem;">🕸️ Condition Radar</div>',
                    unsafe_allow_html=True)

        temp_norm  = min(100, max(0, (W.get("temperature", 20) or 20) * 2))
        hum_norm   = W.get("humidity", 50) or 50
        wind_norm  = min(100, (W.get("wind_speed", 0) or 0) * 1.5)
        uv_norm    = min(100, (W.get("uv_index", 0) or 0) * 8)
        cloud_norm = W.get("cloud_cover", 0) or 0
        rain_norm  = min(100, (W.get("rainfall_1h", 0) or 0) * 10)

        categories = ["Temperature", "Humidity", "Wind", "UV Index", "Cloud Cover", "Rainfall"]
        values     = [temp_norm, hum_norm, wind_norm, uv_norm, cloud_norm, rain_norm]

        fig_radar = go.Figure(go.Scatterpolar(
            r     = values + [values[0]],
            theta = categories + [categories[0]],
            fill  = "toself",
            fillcolor = "rgba(0,229,255,0.1)",
            line  = dict(color="#00e5ff", width=2),
            name  = "Current",
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0,100],
                                gridcolor="rgba(255,255,255,0.08)",
                                tickfont=dict(color="#7ecdc8", size=9)),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.08)",
                                 tickfont=dict(color="#7ecdc8")),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(l=30, r=30, t=30, b=30),
        )
        st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

        # Weather score breakdown
        st.markdown('<div class="section-title">🏆 Weather Score Breakdown</div>',
                    unsafe_allow_html=True)

        score_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=SCORE,
            number={"font": {"family": "Orbitron", "color": SCOLOR}, "suffix": ""},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#7ecdc8"},
                "bar":  {"color": SCOLOR},
                "bgcolor": "rgba(0,0,0,0)",
                "bordercolor": "rgba(0,229,255,0.2)",
                "steps": [
                    {"range": [0,  35], "color": "rgba(255,107,107,0.15)"},
                    {"range": [35, 55], "color": "rgba(255,152,0,0.10)"},
                    {"range": [55, 70], "color": "rgba(255,209,102,0.10)"},
                    {"range": [70, 85], "color": "rgba(0,255,136,0.08)"},
                    {"range": [85,100], "color": "rgba(0,229,255,0.08)"},
                ],
                "threshold": {"line": {"color": SCOLOR, "width": 3}, "value": SCORE},
            },
        ))
        score_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Rajdhani", color="#7ecdc8"),
            margin=dict(l=10, r=10, t=10, b=10),
            height=200,
        )
        st.plotly_chart(score_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f'<div style="text-align:center;font-family:\'Orbitron\',sans-serif;'
            f'font-size:0.8rem;letter-spacing:2px;color:{SCOLOR};">{SLABEL} CONDITIONS</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 6 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════

with tab_history:
    stats = get_history_stats()
    s1, s2, s3, s4 = st.columns(4)
    for col, icon, label, val in [
        (s1, "🔍", "Total Searches",  stats["total_searches"]),
        (s2, "🏙️", "Unique Cities",  stats["unique_cities"]),
        (s3, "🌡️", "Avg Temperature", f"{stats['avg_temperature']:.1f}°C" if stats["avg_temperature"] else "—"),
        (s4, "📡", "Avg Confidence",  f"{stats['avg_confidence']:.0f}%" if stats["avg_confidence"] else "—"),
    ]:
        with col:
            st.markdown(f"""
<div class="metric-card">
    <div class="metric-icon">{icon}</div>
    <div class="metric-label">{label}</div>
    <div class="metric-value">{val}</div>
</div>""", unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="section-title">📋 Search History</div>', unsafe_allow_html=True)

    search_q = st.text_input("Search history…", placeholder="Filter by city…",
                              label_visibility="collapsed")

    if search_q.strip():
        rows = search_history(search_q.strip())
    else:
        rows = get_history(50)

    if rows:
        df = pd.DataFrame(rows)[[
            "searched_at", "city", "country", "temperature",
            "humidity", "wind_speed", "condition", "confidence", "weather_score",
        ]]
        df.columns = ["Time", "City", "Country", "Temp °C", "Humidity %",
                      "Wind km/h", "Condition", "Confidence %", "Score"]
        df["Temp °C"]      = df["Temp °C"].apply(lambda x: f"{x:.1f}" if x else "—")
        df["Wind km/h"]    = df["Wind km/h"].apply(lambda x: f"{x:.0f}" if x else "—")
        df["Confidence %"] = df["Confidence %"].apply(lambda x: f"{x:.0f}%" if x else "—")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No history records yet.")

    if st.button("🗑️ Clear All History", type="secondary"):
        clear_history()
        st.success("History cleared.")
        st.rerun()