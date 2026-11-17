"""Act mode: nothing that changes something is released until a named person approves it.

Items wait in a queue. Sharing a report fingerprints it; sending outside the organisation
creates a Gate 3 item for the CCO and the share is released only when that is approved.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.services import access_service, assess_service, store

QUEUE: List[Dict[str, Any]] = []
SHARES: List[Dict[str, Any]] = []
EXTERNAL = {"X-1": "External auditor", "X-2": "Regulator liaison"}


def reset() -> None:
    QUEUE.clear(); SHARES.clear()


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def add(key: str, title: str, detail: str, approver: str, gate: str, link: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ex = next((q for q in QUEUE if q["key"] == key), None)
    if ex:
        return ex
    q = {"id": f"ACT-{len(QUEUE) + 1}", "key": key, "title": title, "detail": detail, "approver": approver, "gate": gate, "status": "pending", "by": store.ACTOR.get()[0], "at": _iso(), "result": None, "link": link}
    QUEUE.append(q)
    store.audit("action.queued", q["id"], {"title": title, "gate": gate})
    return q


def decide(action_id: str, decision: str, actor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    q = next((x for x in QUEUE if x["id"] == action_id), None)
    if not q:
        raise KeyError(action_id)
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be approved or rejected")
    if q["status"] != "pending":
        raise ValueError("already decided")
    access_service.require_gate(actor or access_service.user(None), q["gate"], q.get("by"))
    q["status"] = decision
    q["result"] = "Released and audited." if decision == "approved" else "Rejected. Nothing was changed."
    store.audit("gate." + ("approve" if decision == "approved" else "reject"), q["id"], {"title": q["title"]})
    if decision == "approved" and q.get("link", {}) and q["link"].get("share"):
        sh = next(s for s in SHARES if s["id"] == q["link"]["share"])
        sh["status"] = "sent"
        q["result"] = "Released to external recipients."
        store.audit("report.release", sh["id"], {"to": sh["to"]})
    return q


def queue_fixes(subject: str, scope: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    out = []
    if subject.startswith("fw:"):
        fid, name, kind = assess_service.fw_parts(subject)
        rows = [dict(r, matter=f"{r['criterion']} {r['title']}") for r in assess_service.assess_framework(fid, scope, name, kind)["rows"]]
    else:
        rows = assess_service.assess(subject, scope)["rows"]
    for r in rows:
        if r["status"] != "Compliant":
            out.append(add(f"fx-{subject}-{r['matter']}", f"Fix plan: {r['matter']} ({r['status'].lower()})", " ".join(r["fix"]), r["owner"],
                           "Gate 3" if r["status"] == "Not compliant" else "Gate 2"))
    return out


def share(subject: str, scope: Optional[Dict[str, Any]], recipients: List[str], access: str, days: int, note: str) -> Dict[str, Any]:
    if not recipients:
        raise ValueError("choose at least one recipient")
    if access not in ("View only", "Can comment"):
        raise ValueError("access must be View only or Can comment")
    html = assess_service.report_html(subject, scope)
    names = [EXTERNAL.get(r, r) for r in recipients]
    ext = any(r in EXTERNAL for r in recipients)
    sh = {"id": f"SHR-{len(SHARES) + 1}", "subject": subject, "scope": scope, "to": names, "access": access, "expiresInDays": days, "note": note,
          "fingerprint": assess_service.fingerprint(html), "at": _iso(), "status": "awaiting CCO approval" if ext else "sent"}
    SHARES.append(sh)
    store.audit("report.share", sh["id"], {"to": names, "fingerprint": sh["fingerprint"][:12], "status": sh["status"]})
    if ext:
        add(f"shr-{sh['id']}", f"Approve external share {sh['id']} to {', '.join(n for r, n in zip(recipients, names) if r in EXTERNAL)}",
            f"Report leaves the organisation. {access}, expires in {days} days.", "Chief Compliance Officer", "Gate 3", {"share": sh["id"]})
    return sh


def verify(share_id: str) -> Dict[str, Any]:
    sh = next((s for s in SHARES if s["id"] == share_id), None)
    if not sh:
        raise KeyError(share_id)
    ok = assess_service.fingerprint(assess_service.report_html(sh["subject"], sh["scope"])) == sh["fingerprint"]
    store.audit("report.verify", share_id, {"matches": ok})
    return {"shareId": share_id, "matches": ok}
