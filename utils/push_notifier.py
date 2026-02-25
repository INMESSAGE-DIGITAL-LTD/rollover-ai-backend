"""
Push Notification Service using Firebase Cloud Messaging (FCM).

Stores device tokens in Firestore → collection: fcm_tokens
Sends notifications after successful daily pick generation.

Token lifecycle:
  - Flutter app calls POST /api/register-token on startup with its FCM token.
  - Tokens are stored per-device (document ID = token itself for deduplication).
  - Stale tokens (rejected by FCM) are automatically cleaned up.
"""
from datetime import datetime, timezone


TOKENS_COLLECTION = 'fcm_tokens'


# ─── Token registration ───────────────────────────────────────────────────────

def register_token(token: str, platform: str = 'unknown') -> bool:
    """
    Save or update a device FCM token in Firestore.
    Called from POST /api/register-token.

    Args:
        token:    FCM registration token from the Flutter app.
        platform: 'android' or 'ios' (informational only).

    Returns:
        True on success, False on failure.
    """
    if not token or not token.strip():
        return False
    try:
        from firebase_config import get_firestore_client
        db = get_firestore_client()
        db.collection(TOKENS_COLLECTION).document(token).set({
            'token': token,
            'platform': platform,
            'registered_at': datetime.now(timezone.utc).isoformat(),
            'active': True,
        }, merge=True)
        return True
    except Exception as e:
        print(f"⚠️ PushNotifier: failed to register token: {e}")
        return False


def deregister_token(token: str) -> None:
    """Mark a token as inactive (called when FCM rejects it)."""
    try:
        from firebase_config import get_firestore_client
        db = get_firestore_client()
        db.collection(TOKENS_COLLECTION).document(token).update({'active': False})
    except Exception:
        pass


# ─── Send notifications ───────────────────────────────────────────────────────

def send_picks_ready(date_str: str, match_count: int, combined_odds: float) -> dict:
    """
    Send a push notification to all registered devices announcing that
    today's AI picks are ready.

    Args:
        date_str:      e.g. '2026-02-26'
        match_count:   number of picks generated
        combined_odds: combined odds of the slip

    Returns:
        dict with success/failure counts.
    """
    try:
        from firebase_admin import messaging
        from firebase_config import get_firestore_client
        db = get_firestore_client()
    except Exception as e:
        print(f"⚠️ PushNotifier: Firebase unavailable: {e}")
        return {'sent': 0, 'failed': 0, 'error': str(e)}

    # Fetch all active tokens
    try:
        token_docs = (
            db.collection(TOKENS_COLLECTION)
            .where('active', '==', True)
            .stream()
        )
        tokens = [doc.to_dict().get('token') for doc in token_docs]
        tokens = [t for t in tokens if t]
    except Exception as e:
        print(f"⚠️ PushNotifier: failed to fetch tokens: {e}")
        return {'sent': 0, 'failed': 0, 'error': str(e)}

    if not tokens:
        print("ℹ️ PushNotifier: no registered devices — skipping notification")
        return {'sent': 0, 'failed': 0}

    # Build the notification payload
    notification = messaging.Notification(
        title="Today's AI Picks Are Ready!",
        body=f"{match_count} picks | Combined odds {combined_odds:.2f}x — tap to view",
    )
    android_config = messaging.AndroidConfig(
        priority='high',
        notification=messaging.AndroidNotification(
            icon='ic_notification',
            color='#1DB954',
            channel_id='picks_channel',
        ),
    )
    apns_config = messaging.APNSConfig(
        payload=messaging.APNSPayload(
            aps=messaging.Aps(badge=1, sound='default'),
        ),
    )
    data_payload = {
        'type': 'picks_ready',
        'date': date_str,
        'match_count': str(match_count),
        'combined_odds': str(round(combined_odds, 2)),
    }

    # FCM allows max 500 tokens per multicast message
    sent = 0
    failed = 0
    stale_tokens = []

    batch_size = 500
    for i in range(0, len(tokens), batch_size):
        batch = tokens[i:i + batch_size]
        message = messaging.MulticastMessage(
            tokens=batch,
            notification=notification,
            android=android_config,
            apns=apns_config,
            data=data_payload,
        )
        try:
            response = messaging.send_each_for_multicast(message)
            sent += response.success_count
            failed += response.failure_count

            # Collect stale tokens (invalid/unregistered)
            for j, resp in enumerate(response.responses):
                if not resp.success:
                    err_code = getattr(resp.exception, 'code', '') or ''
                    if 'registration-token-not-registered' in str(err_code) or \
                       'invalid-registration-token' in str(err_code):
                        stale_tokens.append(batch[j])
        except Exception as e:
            print(f"⚠️ PushNotifier: multicast error: {e}")
            failed += len(batch)

    # Clean up stale tokens asynchronously
    for stale in stale_tokens:
        deregister_token(stale)

    print(f"📲 PushNotifier: sent={sent}, failed={failed}, "
          f"stale_cleaned={len(stale_tokens)}, total_devices={len(tokens)}")
    return {'sent': sent, 'failed': failed, 'stale_cleaned': len(stale_tokens)}


def send_custom(title: str, body: str, data: dict = None) -> dict:
    """
    Send a custom push notification to all active devices.
    Useful for announcements, maintenance warnings, etc.
    """
    try:
        from firebase_admin import messaging
        from firebase_config import get_firestore_client
        db = get_firestore_client()

        token_docs = db.collection(TOKENS_COLLECTION).where('active', '==', True).stream()
        tokens = [doc.to_dict().get('token') for doc in token_docs if doc.to_dict().get('token')]
    except Exception as e:
        return {'sent': 0, 'failed': 0, 'error': str(e)}

    if not tokens:
        return {'sent': 0, 'failed': 0}

    message = messaging.MulticastMessage(
        tokens=tokens[:500],
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
    )
    try:
        response = messaging.send_each_for_multicast(message)
        return {'sent': response.success_count, 'failed': response.failure_count}
    except Exception as e:
        return {'sent': 0, 'failed': 0, 'error': str(e)}
