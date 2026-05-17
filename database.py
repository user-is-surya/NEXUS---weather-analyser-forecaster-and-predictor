"""
=============================================================================
  NEXUS WEATHER INTELLIGENCE — database.py
  SQLite persistence layer: search history, cache, and user preferences.
=============================================================================
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "nexus_weather.db"


# ══════════════════════════════════════════════════════════════════════════════
#  INITIALISATION
# ══════════════════════════════════════════════════════════════════════════════

def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # Weather search history ───────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weather_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                city        TEXT    NOT NULL,
                country     TEXT,
                temperature REAL,
                feels_like  REAL,
                humidity    INTEGER,
                wind_speed  REAL,
                condition   TEXT,
                confidence  REAL,
                weather_score INTEGER,
                raw_json    TEXT,
                searched_at TEXT    NOT NULL
            )
        """)

        # Favourite cities ─────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS favourites (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                city      TEXT UNIQUE NOT NULL,
                country   TEXT,
                added_at  TEXT NOT NULL
            )
        """)

        # App preferences ──────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORY  CRUD
# ══════════════════════════════════════════════════════════════════════════════

def save_search(city: str, country: str, weather_data: dict, confidence: float, score: int) -> None:
    """Persist a weather search result to history."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO weather_history
                (city, country, temperature, feels_like, humidity,
                 wind_speed, condition, confidence, weather_score, raw_json, searched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city,
            country,
            weather_data.get("temperature"),
            weather_data.get("feels_like"),
            weather_data.get("humidity"),
            weather_data.get("wind_speed"),
            weather_data.get("condition", "Unknown"),
            round(confidence, 2),
            score,
            json.dumps(weather_data),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()


def get_history(limit: int = 50) -> list[dict]:
    """Return the most recent searches as a list of dicts."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM weather_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def search_history(query: str) -> list[dict]:
    """Full-text search over city names in history."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM weather_history
            WHERE city LIKE ?
            ORDER BY id DESC
            LIMIT 100
        """, (f"%{query}%",)).fetchall()
    return [dict(r) for r in rows]


def clear_history() -> None:
    """Wipe all history rows (used from settings panel)."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM weather_history")
        conn.commit()


def get_history_stats() -> dict:
    """Aggregate stats for the history panel."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        total   = conn.execute("SELECT COUNT(*) FROM weather_history").fetchone()[0]
        cities  = conn.execute("SELECT COUNT(DISTINCT city) FROM weather_history").fetchone()[0]
        avg_tmp = conn.execute("SELECT AVG(temperature) FROM weather_history").fetchone()[0]
        avg_con = conn.execute("SELECT AVG(confidence) FROM weather_history").fetchone()[0]
    return {
        "total_searches": total,
        "unique_cities":  cities,
        "avg_temperature": round(avg_tmp, 1) if avg_tmp else None,
        "avg_confidence":  round(avg_con, 1) if avg_con else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  FAVOURITES
# ══════════════════════════════════════════════════════════════════════════════

def add_favourite(city: str, country: str = "") -> bool:
    """Add a city to favourites. Returns False if already present."""
    init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO favourites (city, country, added_at) VALUES (?, ?, ?)",
                (city, country, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def remove_favourite(city: str) -> None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM favourites WHERE city = ?", (city,))
        conn.commit()


def get_favourites() -> list[dict]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM favourites ORDER BY added_at DESC").fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
#  PREFERENCES
# ══════════════════════════════════════════════════════════════════════════════

def set_pref(key: str, value) -> None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
        conn.commit()


def get_pref(key: str, default=None):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        ).fetchone()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return row[0]
    return default