"""Stakeholders, notifications and conversations.

A change in a rule is only handled when the right people know, say so, and sign off.
This service turns an impact into a routed set of notifications (RACI), keeps a thread
per subject where people comment, @mention each other and approve, and escalates when
someone does not respond inside the SLA. Every message and decision is audited.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services import change_service, store

_SEED = Path(__file__).resolve().parents[1] / "data" / "seed" / "stakeholders.json"
NOTIFS: List[Dict[str, Any]] = []
THREADS: Dict[str, List[Dict[str, Any]]] = {}
APPROVALS: Dict[str, Dict[str, Any]] = {}

SLA_HOURS = {"critical": 4, "high": 24, "normal": 72}
RACI_TEXT = {"A": "Accountable — must approve", "R": "Responsible — does the work", "C": "Consulted — asked for input", "I": "Informed — told, no action"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.isoformat(timespec="seconds").replace("+00:00", "Z")


def stakeholders() -> List[Dict[str, Any]]:
    return json.loads(_SEED.read_text("utf-8"))


def by_id(sid: str) -> Optional[Dict[str, Any]]:
    return next((s for s in stakeholders() if s["id"] == sid), None)


def by_short(short: str) -> Optional[Dict[str, Any]]:
    return next((s for s in stakeholders() if s["short"] == short), None)


def owner_to_stakeholder(owner: str) -> Dict[str, Any]:
    for s in stakeholders():
        if owner in s["owns"]:
            return s
    return by_short("CCO")          # unowned items go to the CCO rather than nowhere


def routing(impact: Any) -> List[Dict[str, Any]]:
    """Who must hear about this, in which RACI role, and why. One row per person, strongest role wins."""
    rank = {"A": 0, "R": 1, "C": 2, "I": 3}
    rows: Dict[str, Dict[str, Any]] = {}

    def add(sh: Dict[str, Any], role: str, why: str, item: str):
        cur = rows.get(sh["id"])
        if not cur:
            rows[sh["id"]] = {"stakeholder": sh, "raci": role, "reasons": [why], "items": [item]}
            return
        if rank[role] < rank[cur["raci"]]:
            cur["raci"] = role
        cur["reasons"].append(why)
        cur["items"].append(item)

    issues = {i["id"]: i for i in store.issues()}
    for pid in impact.affectedPolicies:
        p = store.policy_by_id(pid)
        if p:
            add(owner_to_stakeholder(p["owner"]), "A", f"Owns policy {pid}", pid)
    for cid in impact.affectedControls:
        c = store.control_by_id(cid)
        if c:
            add(owner_to_stakeholder(c["owner"]), "R", f"Owns control {cid}", cid)
    for iid in impact.openIssues:
        i = issues.get(iid)
        if i:
            add(owner_to_stakeholder(i["owner"]), "R", f"Owns open issue {iid}", iid)
    cco = by_short("CCO")
    add(cco, "A" if impact.impactScore >= 70 else "I", "Impact ≥ 70 needs CCO approval" if impact.impactScore >= 70 else "Informed of every change", "impact")
    add(by_short("Legal"), "C", "Interprets the amended wording", "wording")
    add(by_short("CRO"), "I" if impact.impactScore < 70 else "C", "Risk posture moves", "risk")
    add(by_short("Internal Audit"), "I", "Third line is kept informed", "audit")
    out = list(rows.values())
    out.sort(key=lambda r: (rank[r["raci"]], r["stakeholder"]["name"]))
    return out


def notify_change(change_id: str) -> Dict[str, Any]:
    """Create one notification per routed stakeholder. Re-running does not duplicate."""
    imp = change_service.impact(change_id)
    if not imp:
        raise KeyError(change_id)
    ch = change_service.get_change(change_id)
    prio = "critical" if imp.impactScore >= 70 else "high" if imp.impactScore >= 40 else "normal"
    made = []
    for row in routing(imp):
        sh = row["stakeholder"]
        if any(n["changeId"] == change_id and n["to"]["id"] == sh["id"] for n in NOTIFS):
            continue
        due = _now() + timedelta(hours=SLA_HOURS[prio] if row["raci"] in ("A", "R") else SLA_HOURS["normal"] * 2)
        n = {"id": "NTF-" + uuid.uuid4().hex[:6].upper(), "changeId": change_id, "at": _iso(_now()), "to": {k: sh[k] for k in ("id", "name", "role", "short")},
             "raci": row["raci"], "raciText": RACI_TEXT[row["raci"]], "priority": prio, "channels": sh["channels"],
             "subject": f'{ch["regulator"]} changed {ch["affectedCites"][0]}: {ch["title"]}',
             "body": f'Impact {imp.impactScore}/100, effective {ch["effective"]}. You are {RACI_TEXT[row["raci"]].split(" —")[0].lower()} because: {"; ".join(dict.fromkeys(row["reasons"]))}.',
             "dueBy": _iso(due), "status": "sent", "ackAt": None, "escalatedTo": None}
        NOTIFS.append(n)
        made.append(n)
        store.audit("notify.send", change_id, {"to": sh["id"], "raci": row["raci"], "channels": sh["channels"]})
    ensure_thread(change_id, ch, imp)
    return {"changeId": change_id, "impactScore": imp.impactScore, "priority": prio,
            "notifications": [n for n in NOTIFS if n["changeId"] == change_id], "created": len(made)}


def ensure_thread(change_id: str, ch: Dict[str, Any], imp: Any) -> None:
    if change_id in THREADS:
        return
    sys = by_short("CCO")
    THREADS[change_id] = [_msg(change_id, "AAVA", "agent", f'Opened coordination for {ch["title"]}. Impact {imp.impactScore}/100. '
                               f'{len(imp.affectedPolicies)} policies, {len(imp.affectedControls)} controls and {len(imp.openIssues)} open issues are affected. '
                               f'Please acknowledge and comment here; approval is requested from the roles marked Accountable.', "system")]


def _msg(subject: str, author: str, kind: str, text: str, type_: str = "comment", mentions: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"id": "MSG-" + uuid.uuid4().hex[:6].upper(), "subject": subject, "at": _iso(_now()), "author": author, "authorKind": kind,
            "type": type_, "text": text, "mentions": mentions or []}


def mentions_in(text: str) -> List[Dict[str, Any]]:
    found = []
    for tok in re.findall(r"@([A-Za-z][\w ]{1,20}?)(?=[\s,.:;!?]|$)", text):
        t = tok.strip().lower()
        for s in stakeholders():
            if t in (s["short"].lower(), s["name"].split()[0].lower(), s["name"].lower()):
                found.append(s)
                break
    return list({s["id"]: s for s in found}.values())


def thread(subject: str) -> Dict[str, Any]:
    return {"subject": subject, "messages": THREADS.get(subject, []), "approval": APPROVALS.get(subject)}


def comment(subject: str, author_id: str, text: str) -> Dict[str, Any]:
    sh = by_id(author_id)
    if not sh:
        raise KeyError(author_id)
    if not text.strip():
        raise ValueError("empty comment")
    ment = mentions_in(text)
    m = _msg(subject, sh["name"], "human", text.strip(), "comment", [s["id"] for s in ment])
    m["authorRole"] = sh["role"]
    THREADS.setdefault(subject, []).append(m)
    store.audit("thread.comment", subject, {"by": sh["id"], "mentions": m["mentions"]})
    sent = []
    for s in ment:
        if s["id"] == sh["id"]:
            continue
        n = {"id": "NTF-" + uuid.uuid4().hex[:6].upper(), "changeId": subject, "at": _iso(_now()), "to": {k: s[k] for k in ("id", "name", "role", "short")},
             "raci": "C", "raciText": "Mentioned in a comment", "priority": "normal", "channels": s["channels"],
             "subject": f'{sh["name"]} mentioned you on {subject}', "body": text.strip()[:160], "dueBy": _iso(_now() + timedelta(hours=24)),
             "status": "sent", "ackAt": None, "escalatedTo": None}
        NOTIFS.append(n)
        sent.append(n["id"])
    return {"message": m, "mentionNotifications": sent}


def request_approval(subject: str, gate: str, summary: str, only: Optional[List[str]] = None) -> Dict[str, Any]:
    needed = [s for s in stakeholders() if gate in s["approves"] and (not only or s["id"] in only)] or [by_short("CCO")]
    if gate == "gate3":
        needed = [s for s in needed if s["short"] in ("CCO",)]          # the CCO signs gate 3; the CRO is consulted
    if not needed:
        raise ValueError("no approver for " + gate)
    APPROVALS[subject] = {"subject": subject, "gate": gate, "summary": summary, "status": "pending", "requestedAt": _iso(_now()),
                          "required": [{"id": s["id"], "name": s["name"], "role": s["role"], "decision": None, "at": None, "note": None} for s in needed]}
    THREADS.setdefault(subject, []).append(_msg(subject, "AAVA", "agent", f'Approval requested ({gate}) from {", ".join(s["role"] for s in needed)}. {summary}', "approval_request", [s["id"] for s in needed]))
    store.audit("approval.request", subject, {"gate": gate, "required": [s["id"] for s in needed]})
    return APPROVALS[subject]


def decide(subject: str, approver_id: str, decision: str, note: str = "") -> Dict[str, Any]:
    ap = APPROVALS.get(subject)
    if not ap:
        raise KeyError("no approval requested for " + subject)
    if decision not in ("approve", "reject", "changes"):
        raise ValueError("decision must be approve, reject or changes")
    row = next((r for r in ap["required"] if r["id"] == approver_id), None)
    if not row:
        raise PermissionError("this person is not an approver for this request")
    if decision != "approve" and not note.strip():
        raise ValueError("a note is required when you reject or ask for changes")
    row.update(decision=decision, at=_iso(_now()), note=note.strip() or None)
    states = [r["decision"] for r in ap["required"]]
    ap["status"] = "rejected" if "reject" in states else "changes_requested" if "changes" in states else "approved" if all(s == "approve" for s in states) else "pending"
    THREADS.setdefault(subject, []).append(_msg(subject, row["name"], "human", f'{decision.upper()}{": " + note.strip() if note.strip() else ""}', "decision"))
    store.audit(f"approval.{decision}", subject, {"by": approver_id, "status": ap["status"]})
    if ap["status"] == "approved":
        for n in NOTIFS:
            if n["changeId"] == subject and n["status"] != "acknowledged":
                pass
    return ap


def acknowledge(notification_id: str) -> Dict[str, Any]:
    n = next((x for x in NOTIFS if x["id"] == notification_id), None)
    if not n:
        raise KeyError(notification_id)
    n["status"], n["ackAt"] = "acknowledged", _iso(_now())
    store.audit("notify.ack", n["changeId"], {"by": n["to"]["id"]})
    return n


def escalate(change_id: str, hours_ahead: float = 0) -> Dict[str, Any]:
    """Anything unacknowledged past its due time goes to the person's manager. `hours_ahead` lets a demo fast-forward."""
    now = _now() + timedelta(hours=hours_ahead)
    moved = []
    for n in NOTIFS:
        if n["changeId"] != change_id or n["status"] != "sent" or n["raci"] not in ("A", "R") or n["escalatedTo"]:
            continue
        if datetime.fromisoformat(n["dueBy"].replace("Z", "+00:00")) <= now:
            mgr = by_id((by_id(n["to"]["id"]) or {}).get("manager") or "") or by_short("CCO")
            n["escalatedTo"] = {k: mgr[k] for k in ("id", "name", "role", "short")}
            n["status"] = "escalated"
            moved.append(n)
            THREADS.setdefault(change_id, []).append(_msg(change_id, "AAVA", "agent", f'{n["to"]["name"]} did not respond by {n["dueBy"]}. Escalated to {mgr["name"]} ({mgr["role"]}).', "escalation", [mgr["id"]]))
            store.audit("notify.escalate", change_id, {"from": n["to"]["id"], "to": mgr["id"]})
    return {"changeId": change_id, "escalated": moved}


def status(change_id: str) -> Dict[str, Any]:
    ns = [n for n in NOTIFS if n["changeId"] == change_id]
    return {"changeId": change_id, "total": len(ns), "acknowledged": sum(n["status"] == "acknowledged" for n in ns),
            "escalated": sum(n["status"] == "escalated" for n in ns), "pending": sum(n["status"] == "sent" for n in ns),
            "approval": (APPROVALS.get(change_id) or {}).get("status", "not requested")}


def reset() -> None:
    NOTIFS.clear(); THREADS.clear(); APPROVALS.clear()
