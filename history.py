"""
Rollover AI Backend — Pick History Endpoints (Firestore)

Cloud-synced pick history using Firebase Firestore.
Replaces the old SQLite implementation for persistence on Render.
"""

import os
import json
from datetime import datetime, timedelta
from flask import request, jsonify
from firebase_config import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# ─── Firestore Operations ────────────────────────────────────

def get_history(days=7):
    """Fetch last N days of predictions from Firestore."""
    db = get_firestore_client()
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # Query collection: daily_predictions where date >= cutoff
    docs = (
        db.collection('daily_predictions')
        .where('date', '>=', cutoff)
        .order_by('date', direction='DESCENDING')
        .stream()
    )
    
    history = {}
    for doc in docs:
        data = doc.to_dict()
        date_str = data.get('date')
        matches = data.get('matches', [])
        
        if not matches:
            continue

        # Ensure format consistency
        clean_matches = []
        for m in matches:
            try:
                clean_matches.append({
                    "home_team": m.get("home_team", ""),
                    "away_team": m.get("away_team", ""),
                    "market": m.get("market", ""),
                    "odds": float(m.get("odds", 0)),
                    "confidence": float(m.get("ai_probability", 0) or 0),
                    "result": m.get("result", "pending"),
                    "league": m.get("league", ""),
                    "home_logo": m.get("home_logo"),
                    "away_logo": m.get("away_logo"),
                    "league_logo": m.get("league_logo"),
                    "home_short_code": m.get("home_short_code"),
                    "away_short_code": m.get("away_short_code"),
                    "kickoff": m.get("kickoff"),
                })
            except (ValueError, TypeError):
                continue
            
        if date_str:
            history[date_str] = clean_matches
            
    return history


def save_daily_picks(date_str, picks):
    """Save picks to Firestore daily_predictions/{date_str}."""
    db = get_firestore_client()
    
    doc_ref = db.collection('daily_predictions').document(date_str)
    
    doc_data = {
        'date': date_str,
        'matches': picks,
        'match_count': len(picks),
        'updated_at': SERVER_TIMESTAMP,
        'source': 'history_api' 
    }
    
    # Set merge=True so we don't overwrite other fields if they exist
    doc_ref.set(doc_data, merge=True)
    return len(picks)

def init_history_db():
    """No-op for Firestore (init happens in firebase_config)."""
    pass

# ─── Flask Route Registration ────────────────────────────────

def register_history_routes(app):
    """
    Register API routes for history.
    """

    @app.route("/api/history", methods=["GET"])
    def api_get_history():
        try:
            return jsonify(get_history())
        except Exception as e:
            print(f"❌ Error fetching history: {e}")
            return jsonify({"error": str(e)}), 500
