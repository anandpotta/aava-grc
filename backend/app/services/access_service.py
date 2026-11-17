"""Who can do what. Roles say what a person may do; the gates they are named to approve say what they may release.

Role is the capability (comment, share, edit scope, approve at all). `approves` is the named authority: Gate 1, 2 or 3.
A person can approve a request only if their role allows approving AND they are named for that gate AND they did not raise it.
Identity comes from the X-AAVA-User header in this build. In production it comes from your single sign-on token.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services import collaboration_service, store

PERMS = {
    "view": "See maps, assessments and the audit trail",
    "comment": "Comment and @mention in a change thread",
    "ack": "Acknowledge a notification",
    "notify": "Notify stakeholders and escalate",
    "run_assess": "Run an assessment or readiness check",
    "queue_fix": "Turn findings into a fix plan",
    "edit_scope": "Choose or add rules, policies and controls",
    "rebuild_map": "Rebuild a compliance map",
    "share": "Share a report (outside the organisation needs Gate 3)",
    "export": "Download reports and the map",
    "approve": "Approve or reject, for the gates they are named on",
    "verify_audit": "Verify the audit chain",
    "manage_roles": "Change roles and named approvers",
}
_C = ["view", "comment", "ack", "notify", "run_assess", "queue_fix", "edit_scope", "rebuild_map", "share", "export", "approve", "verify_audit"]
ROLES: Dict[str, Dict[str, Any]] = {
    "admin": {"name": "Platform administrator", "desc": "Manages roles and named approvers. Cannot approve compliance decisions.", "perms": ["view", "manage_roles", "verify_audit"]},
    "cco": {"name": "Chief Compliance Officer", "desc": "Owns the programme. Final approver for anything that leaves the organisation.", "perms": _C},
    "compliance_officer": {"name": "Compliance officer", "desc": "Runs assessments, raises fixes, approves at the gates they are named on.", "perms": _C},
    "risk_manager": {"name": "Risk manager", "desc": "Reads the register, raises fixes, approves at named gates.", "perms": ["view", "comment", "ack", "notify", "run_assess", "queue_fix", "export", "approve"]},
    "control_owner": {"name": "Control or policy owner", "desc": "Responds to changes in what they own. Cannot release anything.", "perms": ["view", "comment", "ack", "run_assess", "export"]},
    "internal_audit": {"name": "Internal auditor", "desc": "Independent. Reads everything, tests, verifies the audit chain. Cannot change or approve.", "perms": ["view", "comment", "run_assess", "export", "verify_audit"]},
    "external_auditor": {"name": "External auditor", "desc": "Audit room. Sees only reports released to them. Read-only.", "perms": ["view"], "room": True},
    "regulator": {"name": "Regulator", "desc": "Audit room. Sees only reports released to them. Read-only.", "perms": ["view"], "room": True},
    "executive": {"name": "Executive or board member", "desc": "Reads posture and reports. Cannot change anything.", "perms": ["view", "export"]},
}
DEFAULT_ROLE = {"SH-01": "cco", "SH-02": "compliance_officer", "SH-03": "compliance_officer", "SH-04": "control_owner", "SH-05": "control_owner", "SH-06": "risk_manager",
                "SH-07": "control_owner", "SH-08": "control_owner", "SH-09": "compliance_officer", "SH-10": "internal_audit"}
EXTRA = [
    {"id": "A-1", "name": "Kavya Nair", "title": "Platform administrator", "role": "admin", "approves": []},
    {"id": "E-1", "name": "Rahul Bhatt", "title": "Board risk committee member", "role": "executive", "approves": []},
    {"id": "X-1", "name": "External auditor", "title": "External audit firm", "role": "external_auditor", "approves": []},
    {"id": "X-2", "name": "Regulator liaison", "title": "Supervisory authority", "role": "regulator", "approves": []},
]
DEMO_DEFAULT = "SH-01"
USERS: Dict[str, Dict[str, Any]] = {}


def reset() -> None:
    USERS.clear()
    for s in collaboration_service.stakeholders():
        USERS[s["id"]] = {"id": s["id"], "name": s["name"], "title": s["role"], "role": DEFAULT_ROLE.get(s["id"], "control_owner"),
                          "approves": [g.replace("gate", "Gate ") for g in sorted(s["approves"])]}
    for u in EXTRA:
        USERS[u["id"]] = dict(u, approves=list(u["approves"]))


def user(uid: Optional[str]) -> Dict[str, Any]:
    if not USERS:
        reset()
    return USERS.get(uid or DEMO_DEFAULT) or USERS[DEMO_DEFAULT]


def can(u: Dict[str, Any], perm: str) -> bool:
    return perm in ROLES[u["role"]]["perms"]


def describe(u: Dict[str, Any]) -> Dict[str, Any]:
    r = ROLES[u["role"]]
    return dict(u, roleName=r["name"], perms=r["perms"], room=bool(r.get("room")), readOnly=not any(p in r["perms"] for p in ("queue_fix", "share", "approve", "edit_scope", "manage_roles", "rebuild_map", "notify")))


def require(u: Dict[str, Any], perm: str) -> None:
    if not can(u, perm):
        raise PermissionError(f'{u["name"]} ({ROLES[u["role"]]["name"]}) cannot {PERMS[perm].lower()}. Switch to a role that can.')


def require_gate(u: Dict[str, Any], gate: str, raised_by: Optional[str]) -> None:
    require(u, "approve")
    if gate not in u["approves"]:
        names = ", ".join(x["name"] for x in USERS.values() if gate in x["approves"] and can(x, "approve")) or "nobody"
        raise PermissionError(f'{u["name"]} is not named to approve {gate}. Named: {names}.')
    if raised_by and raised_by == u["id"]:
        raise PermissionError("Separation of duties: you raised this, so someone else must approve it.")


def update(uid: str, role: Optional[str], approves: Optional[List[str]]) -> Dict[str, Any]:
    u = USERS.get(uid)
    if not u:
        raise KeyError(uid)
    new_role = role or u["role"]
    if new_role not in ROLES:
        raise ValueError("unknown role")
    new_ap = u["approves"] if approves is None else sorted(set(approves))
    if any(g not in ("Gate 1", "Gate 2", "Gate 3") for g in new_ap):
        raise ValueError("gates are Gate 1, Gate 2 and Gate 3")
    if new_ap and "approve" not in ROLES[new_role]["perms"]:
        raise ValueError(f'{ROLES[new_role]["name"]} cannot approve, so cannot be named on a gate')
    after = {**USERS, uid: dict(u, role=new_role, approves=new_ap)}
    if not any(x["role"] == "admin" for x in after.values()):
        raise ValueError("keep at least one platform administrator")
    if not any("Gate 3" in x["approves"] and "approve" in ROLES[x["role"]]["perms"] for x in after.values()):
        raise ValueError("keep at least one person named on Gate 3")
    u.update(role=new_role, approves=new_ap)
    return describe(u)
