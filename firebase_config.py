"""
Firebase Admin SDK initialization for server-side Firestore writes.
Uses FIREBASE_SERVICE_ACCOUNT env var (JSON string) for credentials.
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

_db = None


def get_firestore_client():
    """Return a Firestore client, initializing Firebase Admin SDK on first call."""
    global _db
    if _db is not None:
        return _db

    sa_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    if not sa_json:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT env var not set. "
            "Set it to the JSON string of your Firebase service account key."
        )

    cred_dict = json.loads(sa_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    _db = firestore.client()
    print("✅ Firebase Admin SDK initialized")
    return _db
