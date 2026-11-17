"""In-memory store for the demo tenant.

Everything is loaded from app/data/seed on first access. Swap the loaders for
SQLAlchemy repositories when you move to a real database — the rest of the
services only talk to the accessors at the bottom of this module.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import SEED_DIR

_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}

# Mutable session state (rulebooks created at runtime, obligation approvals,
# change triage decisions). A real deployment persists these.
RULEBOOKS: List[Dict[str, Any]] = []
OBLIGATION_STATE: Dict[str, Dict[str, Any]] = {}
CHANGE_STATE: Dict[str, Dict[str, Any]] = {}
AUDIT: List[Dict[str, Any]] = []
CUSTOM: Dict[str, List[Dict[str, Any]]] = {"policies": [], "controls": []}   # items the user adds to their scope


def _load(name: str) -> Any:
    if name not in _CACHE:
        with _LOCK:
            if name not in _CACHE:
                path = SEED_DIR / f"{name}.json"
                _CACHE[name] = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE[name]


def jurisdictions() -> List[Dict[str, Any]]:
    return _load("jurisdictions")


def frameworks() -> List[Dict[str, Any]]:
    return _load("frameworks")


def rules() -> List[Dict[str, Any]]:
    return _load("rules")


def controls() -> List[Dict[str, Any]]:
    return _load("controls") + CUSTOM["controls"]


def policies() -> List[Dict[str, Any]]:
    return _load("policies") + CUSTOM["policies"]


def risks() -> List[Dict[str, Any]]:
    return _load("risks")


def issues() -> List[Dict[str, Any]]:
    return _load("issues")


def changes() -> List[Dict[str, Any]]:
    return _load("changes")


def semantic() -> Dict[str, List[str]]:
    return _load("semantic")


def taxonomy() -> Dict[str, List[str]]:
    return _load("taxonomy")


def policy_clauses() -> Dict[str, Any]:
    """Clause-level policy text, keyed by policy id. Client-owned content."""
    return _load("policy_clauses")


def sources() -> Dict[str, Any]:
    """The regulatory content source registry.

    Drives the ingest adapters: `access` picks the adapter, `licence` decides
    whether the text may be stored and shown or only linked to.
    """
    return _load("sources")


def rule_by_id(rule_id: str) -> Optional[Dict[str, Any]]:
    return next((r for r in rules() if r["id"] == rule_id), None)


def rule_by_cite(cite: str) -> Optional[Dict[str, Any]]:
    return next((r for r in rules() if r["cite"] == cite), None)


def control_by_id(cid: str) -> Optional[Dict[str, Any]]:
    return next((c for c in controls() if c["id"] == cid), None)


def policy_by_id(pid: str) -> Optional[Dict[str, Any]]:
    return next((p for p in policies() if p["id"] == pid), None)


def risk_by_id(rid: str) -> Optional[Dict[str, Any]]:
    return next((r for r in risks() if r["id"] == rid), None)


def issues_for_risk(rid: str) -> List[Dict[str, Any]]:
    return [i for i in issues() if i["riskId"] == rid]


def rulebook_by_id(bid: str) -> Optional[Dict[str, Any]]:
    return next((b for b in RULEBOOKS if b["id"] == bid), None)


def add_rulebook(name: str, scope: str, rule_ids: List[str]) -> Dict[str, Any]:
    book = {
        "id": f"RB-{len(RULEBOOKS) + 1:02d}",
        "name": name,
        "scope": scope,
        "ruleIds": [r for r in rule_ids if rule_by_id(r)],
        "created": datetime.now(timezone.utc).date().isoformat(),
        "obligationCount": 0,
    }
    RULEBOOKS.append(book)
    audit("rulebook.create", book["id"], {"rules": len(book["ruleIds"])})
    return book


def _digest(entry: Dict[str, Any], prev: str) -> str:
    import hashlib, json
    body = {k: entry[k] for k in ("at", "action", "subject", "detail", "actor")}
    return hashlib.sha256((prev + json.dumps(body, sort_keys=True, default=str)).encode()).hexdigest()


from contextvars import ContextVar

ACTOR: ContextVar = ContextVar("actor", default=("SH-01", "Priya Raman (Chief Compliance Officer)"))


def audit(action: str, subject: str, detail: Optional[Dict[str, Any]] = None) -> None:
    """Append-only and hash-chained: each entry commits to the one before, so an edit anywhere is detectable."""
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "action": action,
        "subject": subject,
        "detail": detail or {},
        "actor": ACTOR.get()[1],
        "actorId": ACTOR.get()[0],
    }
    prev = AUDIT[-1]["hash"] if AUDIT else "0" * 64
    entry["prev"], entry["hash"] = prev, _digest(entry, prev)
    AUDIT.append(entry)


def verify_audit() -> Dict[str, Any]:
    prev = "0" * 64
    for i, e in enumerate(AUDIT):
        if e.get("prev") != prev or e.get("hash") != _digest(e, prev):
            return {"ok": False, "entries": len(AUDIT), "brokenAt": i, "head": prev}
        prev = e["hash"]
    return {"ok": True, "entries": len(AUDIT), "brokenAt": None, "head": prev}


def reset() -> None:
    """Used by the tests."""
    RULEBOOKS.clear()
    OBLIGATION_STATE.clear()
    CHANGE_STATE.clear()
    AUDIT.clear()
    CUSTOM["policies"].clear(); CUSTOM["controls"].clear()
    from app.services import actions_service, collaboration_service
    collaboration_service.reset()
    from app.services import access_service
    access_service.reset()
    actions_service.reset()
