# firestore_store.py
from __future__ import annotations
import os, time, re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

# ---- Client ----
_PROJECT = os.getenv("FIRESTORE_PROJECT")
_db = firestore.Client(project=_PROJECT)

# ---- Helpers ----
def _user_refs(uid: str):
    user = _db.collection("users").document(uid)
    return {
        "user": user,
        "memories": user.collection("memories"),
        "messages": user.collection("messages"),
        "profile": user.collection("meta").document("profile"),
    }

_slug_rx = re.compile(r"[^a-z0-9]+")
def _slug(s: str) -> str:
    return _slug_rx.sub("-", s.lower()).strip("-")

def _now() -> float:
    return float(time.time())

VERSION_TAG = "firestore_store v0.2 NON-TRANSACTIONAL"  # <- visible in logs

# ---- Public API ----
def add_memory(uid: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Non-transactional upsert (MVP)."""
    refs = _user_refs(uid)
    mtype = item.get("type", "semantic")
    key = item.get("key", "")
    value = item.get("value", "")
    confidence = float(item.get("confidence", 0.9))
    salience = float(item.get("salience", 1.0))
    ts = float(item.get("ts", _now()))
    doc_id = f"{mtype}:{_slug(key) or 'key'}"
    doc_ref = refs["memories"].document(doc_id)

    snap = doc_ref.get()
    cur = snap.to_dict() if snap.exists else {}

    # If same {type,key,value} re-appears, nudge salience & keep higher confidence
    if cur and (cur.get("value") == value) and (cur.get("type") == mtype):
        salience = min(float(cur.get("salience", 1.0)) + 0.2, 10.0)
        confidence = max(float(cur.get("confidence", 0.9)), confidence)

    data = {
        **(cur or {}),
        "type": mtype,
        "key": key,
        "value": value,
        "confidence": confidence,
        "salience": salience,
        "ts": cur.get("ts", ts) if cur else ts,
        "updated_at": _now(),
    }
    data["score"] = round(float(data["salience"]) * float(data["confidence"]), 6)
    doc_ref.set(data)
    return data

def get_top_facts(uid: str, limit: int = 6) -> list[dict]:
    refs = _user_refs(uid)
    q = (
        refs["memories"]
        .where(filter=FieldFilter("type", "==", "semantic"))
        .order_by("score", direction=firestore.Query.DESCENDING)
        .limit(int(limit))
    )
    return [{**d.to_dict(), "id": d.id} for d in q.stream()]

def log_message(uid: str, role: str, content: str, ts: Optional[float] = None) -> str:
    refs = _user_refs(uid)
    doc = {"role": role, "content": content, "ts": float(ts or _now())}
    ref = refs["messages"].document()
    ref.set(doc)
    return ref.id

def get_last_messages(uid: str, limit: int = 6) -> List[Dict[str, Any]]:
    refs = _user_refs(uid)
    q = refs["messages"].order_by("ts", direction=firestore.Query.DESCENDING).limit(int(limit))
    docs = [d.to_dict() for d in q.stream()]
    return list(reversed(docs))
