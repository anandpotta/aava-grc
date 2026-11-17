"""Regulatory change management.

A change arrives from horizon scanning, gets diffed clause-by-clause, scored
for impact, and then re-run against whichever compliance maps reference the
affected citation. The impact score is the product of three things a compliance
officer already reasons about:

    materiality   how severe the affected rules are
    gapSeverity   how weak the current coverage of those rules is
    urgency       how little time is left before the effective date

Keeping them separate (rather than collapsing to one opaque number) means the
reviewer can argue with the score, which they will.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.schemas import ChangeImpact, RegChange
from app.services import obligation_service, store

SEV_WEIGHT = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
LVL = {"Zero": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def _days_to(effective: str) -> int:
    try:
        d = datetime.strptime(effective, "%Y-%m-%d").date()
    except ValueError:
        return 0
    return max(0, (d - date.today()).days)


def list_changes(juris: Optional[str] = None, status: Optional[str] = None) -> List[RegChange]:
    out: List[RegChange] = []
    for c in store.changes():
        if juris and c["juris"] != juris:
            continue
        state = store.CHANGE_STATE.get(c["id"], {})
        status_val = state.get("status", c["status"])
        if status and status_val != status:
            continue
        out.append(
            RegChange(
                id=c["id"], juris=c["juris"], regulator=c["regulator"], title=c["title"],
                published=c["published"], effective=c["effective"], status=status_val,
                impact=c["impact"], affectedCites=c["affectedCites"],
                summary=c.get("summary", ""), daysToComply=_days_to(c["effective"]),
                diff=c.get("diff", []),
            )
        )
    out.sort(key=lambda c: c.published, reverse=True)
    return out


def get_change(change_id: str) -> Optional[Dict[str, Any]]:
    return next((c for c in store.changes() if c["id"] == change_id), None)


def affected_rules(change: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for cite in change["affectedCites"]:
        for r in store.rules():
            if cite == r["cite"] or cite in r["cite"] or r["cite"] in cite:
                if r not in out:
                    out.append(r)
    return out


def impact(change_id: str) -> Optional[ChangeImpact]:
    change = get_change(change_id)
    if not change:
        return None
    rules = affected_rules(change)
    if not rules:
        return ChangeImpact(
            changeId=change_id, impactScore=0, materiality=0, gapSeverity=0, urgency=0,
            affectedRules=[], affectedObligations=[], affectedPolicies=[],
            affectedControls=[], affectedRisks=[], openIssues=[],
            recommendedActions=[{"action": "Confirm the citation mapping", "owner": "Regulatory Change", "why": "The change references a citation that is not in the corpus yet."}],
        )

    matters = {r["ruleMatter"] for r in rules}
    jurs = {r["juris"] for r in rules}

    obligations = obligation_service.for_rules([r["id"] for r in rules])
    policies = [p for p in store.policies() if p["ruleMatter"] in matters and set(p["jurisdictions"]) & jurs]
    controls = [c for c in store.controls() if c["ruleMatter"] in matters and set(c["jurisdictions"]) & jurs]
    risks = [k for k in store.risks() if k["ruleMatter"] in matters]
    open_issues = [
        i for k in risks for i in store.issues_for_risk(k["id"]) if i["status"] != "Closed"
    ]

    # --- the three factors -------------------------------------------------
    materiality = round(
        100 * sum(SEV_WEIGHT.get(r["severity"], 2) for r in rules) / (4 * max(1, len(rules)))
    )

    gap = 0
    if not policies:
        gap += 45
    if not controls:
        gap += 45
    else:
        weak = sum(1 for c in controls if c["testResult"] != "Effective")
        gap += round(55 * weak / len(controls))
    over = [k for k in risks if LVL.get(k["residual"], 0) > LVL.get(k["appetite"], 0)]
    if over:
        gap = min(100, gap + 20)
    gap_severity = min(100, gap)

    days = _days_to(change["effective"])
    urgency = 100 if days <= 30 else 80 if days <= 90 else 55 if days <= 180 else 30

    score = round(0.4 * materiality + 0.35 * gap_severity + 0.25 * urgency)

    # --- recommended actions ----------------------------------------------
    actions: List[Dict[str, str]] = []
    if not policies:
        actions.append({"action": f'Draft a policy clause covering {", ".join(sorted(matters))} in {", ".join(sorted(jurs))}',
                        "owner": "Policy owner", "why": "No policy currently covers the affected obligations in that jurisdiction."})
    else:
        actions.append({"action": f'Redline {policies[0]["name"]} ({policies[0]["version"]})',
                        "owner": policies[0]["owner"], "why": "The amended wording changes what the policy has to require."})
    weak_controls = [c for c in controls if c["testResult"] != "Effective"]
    if weak_controls:
        actions.append({"action": f'Re-test {weak_controls[0]["id"]} {weak_controls[0]["name"]}',
                        "owner": weak_controls[0]["owner"], "why": f'Control is currently {weak_controls[0]["testResult"].lower()} and the change raises the bar.'})
    if not controls:
        actions.append({"action": "Design and deploy a control in the affected jurisdiction",
                        "owner": "Control owner", "why": "Nothing operational evidences these obligations today."})
    for k in over:
        actions.append({"action": f'Review risk {k["id"]} against appetite',
                        "owner": "Chief Risk Officer", "why": f'Residual {k["residual"]} exceeds appetite {k["appetite"]}.'})
    if days <= 90:
        actions.append({"action": "Escalate to the CCO for Gate 3 approval",
                        "owner": "Chief Compliance Officer", "why": f"Only {days} days until the effective date."})

    return ChangeImpact(
        changeId=change_id,
        impactScore=score,
        materiality=materiality,
        gapSeverity=gap_severity,
        urgency=urgency,
        affectedRules=[r["id"] for r in rules],
        affectedObligations=[o.id for o in obligations],
        affectedPolicies=[p["id"] for p in policies],
        affectedControls=[c["id"] for c in controls],
        affectedRisks=[k["id"] for k in risks],
        openIssues=[i["id"] for i in open_issues],
        recommendedActions=actions,
    )


def set_status(change_id: str, status: str, note: Optional[str] = None) -> Dict[str, Any]:
    state = {"status": status, "note": note,
             "at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
    store.CHANGE_STATE[change_id] = state
    store.audit("change.status", change_id, state)
    return state


def pipeline() -> Dict[str, Any]:
    """Counts for the RCM board columns."""
    stages = ["New", "Triaged", "Assigned", "Impact analysis", "Remediation", "Closed"]
    buckets: Dict[str, List[str]] = {s: [] for s in stages}
    for c in list_changes():
        buckets.setdefault(c.status, []).append(c.id)
    return {
        "stages": stages,
        "counts": {k: len(v) for k, v in buckets.items()},
        "items": buckets,
    }
