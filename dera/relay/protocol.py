from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone


def signed_envelope(device_id: str, message_type: str, payload: dict, secret: str) -> dict:
    """Create a tamper-evident outbound message for a relay to forward."""
    envelope = {
        "version": 1,
        "device_id": device_id,
        "message_type": message_type,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "nonce": secrets.token_urlsafe(16),
        "payload": payload,
    }
    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    envelope["signature"] = hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
    return envelope


def verify_envelope(envelope: dict, secret: str) -> bool:
    signature = envelope.get("signature")
    unsigned = {key: value for key, value in envelope.items() if key != "signature"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
    return isinstance(signature, str) and hmac.compare_digest(signature, expected)
