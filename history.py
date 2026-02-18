"""
Rollover AI Backend — Pick History Endpoints (Flask)

Adds cloud-synced pick history so new users see the last 7 days
of predictions on first install.

Storage: SQLite file (pick_history.db) — lightweight, no extra infra.
Cleanup: Auto-prunes entries older than 7 days on every write.
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from contextlib import contextmanager
from flask import request, jsonify

# ─── Database Setup ───────────────────────────────────────────

DB_PATH = os.environ.get("HISTORY_DB_PATH", "pick_history.db")
MAX_DAYS = 7


@contextmanager
def get_db():
    """Thread-safe SQLite connection context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_history_db():
    """Create the picks table if it doesn't exist."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pick_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                pick_index INTEGER NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                market TEXT NOT NULL,
                odds REAL NOT NULL,
                confidence REAL NOT NULL,
                result TEXT NOT NULL DEFAULT 'pending',
                league TEXT NOT NULL DEFAULT '',
                home_logo TEXT,
                away_logo TEXT,
                league_logo TEXT,
                home_short_code TEXT,
                away_short_code TEXT,
                kickoff TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ph_date ON pick_history(date)
        """)


def _prune_old_entries(conn):
    """Delete entries older than MAX_DAYS."""
    cutoff = (datetime.utcnow() - timedelta(days=MAX_DAYS)).strftime("%Y-%m-%d")
    conn.execute("DELETE FROM pick_history WHERE date < ?", (cutoff,))


def _date_str(dt=None):
    return (dt or datetime.utcnow()).strftime("%Y-%m-%d")


# ─── CRUD Operations ─────────────────────────────────────────

def get_history():
    cutoff = (datetime.utcnow() - timedelta(days=MAX_DAYS)).strftime("%Y-%m-%d")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM pick_history WHERE date >= ? ORDER BY date DESC, pick_index ASC",
            (cutoff,),
        ).fetchall()

    history = {}
    for row in rows:
        date = row["date"]
        if date not in history:
            history[date] = []
        history[date].append({
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "market": row["market"],
            "odds": row["odds"],
            "confidence": row["confidence"],
            "result": row["result"],
            "league": row["league"],
            "home_logo": row["home_logo"],
            "away_logo": row["away_logo"],
            "league_logo": row["league_logo"],
            "home_short_code": row["home_short_code"],
            "away_short_code": row["away_short_code"],
            "kickoff": row["kickoff"],
        })
    return history


def save_daily_picks(date_str, picks):
    with get_db() as conn:
        conn.execute("DELETE FROM pick_history WHERE date = ?", (date_str,))
        now = datetime.utcnow().isoformat()
        for i, pick in enumerate(picks):
            conn.execute(
                """INSERT INTO pick_history
                   (date, pick_index, home_team, away_team, market, odds, confidence,
                    result, league, home_logo, away_logo, league_logo,
                    home_short_code, away_short_code, kickoff, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    date_str, i,
                    pick.get("home_team", ""),
                    pick.get("away_team", ""),
                    pick.get("market", ""),
                    float(pick.get("odds", 0)),
                    float(pick.get("confidence", 0)),
                    pick.get("result", "pending"),
                    pick.get("league", ""),
                    pick.get("home_logo"),
                    pick.get("away_logo"),
                    pick.get("league_logo"),
                    pick.get("home_short_code"),
                    pick.get("away_short_code"),
                    pick.get("kickoff"),
                    now,
                ),
            )
        _prune_old_entries(conn)
    return len(picks)


def update_pick_result(date_str, index, result):
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE pick_history SET result = ? WHERE date = ? AND pick_index = ?",
            (result, date_str, index),
        )
        return cursor.rowcount > 0


# ─── Flask Route Registration ────────────────────────────────

def register_history_routes(app):
    """
    Call from your main app.py:
        from history import register_history_routes, init_history_db
        init_history_db()
        register_history_routes(app)
    """

    @app.route("/api/history", methods=["GET"])
    def api_get_history():
        return jsonify(get_history())

    @app.route("/api/history/seed", methods=["GET"])
    def api_seed_history():
        """Fetch today's slip from self and save to history DB."""
        base = os.environ.get("SELF_URL", "http://localhost:8000")
        try:
            resp = requests.get(
                f"{base}/api/today?max_matches=4&max_odds=2.60",
                timeout=120,
            )
            if resp.status_code != 200:
                return jsonify({"error": "Failed to fetch today's slip"}), 502

            data = resp.json()
            slip = data.get("slip", {})
            matches = slip.get("matches", [])
            if not matches:
                return jsonify({"status": "no_matches", "date": data.get("date", "")})

            date_str = data.get("date", _date_str())
            picks = []
            for m in matches:
                picks.append({
                    "home_team": m.get("home_team", ""),
                    "away_team": m.get("away_team", ""),
                    "market": m.get("market", ""),
                    "odds": m.get("odds", 0),
                    "confidence": m.get("ai_probability", 0) * 100,
                    "result": "pending",
                    "league": m.get("league", ""),
                    "home_logo": m.get("home_logo"),
                    "away_logo": m.get("away_logo"),
                    "league_logo": m.get("league_logo"),
                    "home_short_code": m.get("home_short_code"),
                    "away_short_code": m.get("away_short_code"),
                    "kickoff": m.get("kickoff"),
                })

            count = save_daily_picks(date_str, picks)
            return jsonify({"status": "ok", "date": date_str, "picks_saved": count})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/history/<date_str>", methods=["POST"])
    def api_save_picks(date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        payload = request.get_json(force=True)
        picks = payload.get("picks", [])
        count = save_daily_picks(date_str, picks)
        return jsonify({"status": "ok", "date": date_str, "picks_saved": count})

    @app.route("/api/history/<date_str>/<int:index>", methods=["PATCH"])
    def api_update_result(date_str, index):
        payload = request.get_json(force=True)
        result = payload.get("result", "")
        if result not in ("won", "lost", "pending", "void"):
            return jsonify({"error": "Result must be: won, lost, pending, or void"}), 400

        success = update_pick_result(date_str, index, result)
        if not success:
            return jsonify({"error": "Pick not found"}), 404
        return jsonify({"status": "ok"})
