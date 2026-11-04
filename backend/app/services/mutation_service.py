"""Receipts are committed in the same transaction as the educational mutation."""
import hashlib
import json
from fastapi import HTTPException
from app.models.learning import MutationReceipt

def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

def replay(db, key, payload):
    old = db.get(MutationReceipt, key)
    if old and old.fingerprint != fingerprint(payload):
        raise HTTPException(409, 'IDEMPOTENCY_CONFLICT')
    return old.response if old else None

def receipt(db, key, payload, response):
    db.add(MutationReceipt(id=key, fingerprint=fingerprint(payload), response=response))
