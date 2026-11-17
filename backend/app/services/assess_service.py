"""Assess anything against recognised standards, from the evidence we hold.

A requirement (one rule matter) is
  compliant      a policy exists, every control is tested and effective, no High/Critical issue is open
  partial        controls are untested or need improvement, or a High/Critical issue is open
  not compliant  there is no policy or no control
The verdict is a rule over data, never a model's opinion, so a reviewer can argue with it and an auditor can replay it.
The standards each requirement maps to are illustrative and need specialist review before a customer relies on them.
"""
from __future__ import annotations

import hashlib
import html as _html
from datetime import date
from typing import Any, Dict, List, Optional

from app.services import store

SUBJECTS = [
    {"id": "org", "name": "Our whole organisation", "kind": "Organisation", "matters": None},
    {"id": "platform", "name": "Payments platform", "kind": "Product or platform", "matters": ["Cyber security", "Data privacy", "Data localisation", "Fraud and payments", "Operational resilience", "Outsourcing and third party", "Records and retention"]},
    {"id": "process", "name": "Customer onboarding", "kind": "Process", "matters": ["KYC and CDD", "AML / CFT", "Sanctions screening", "Data privacy", "Consumer protection"]},
    {"id": "vendor", "name": "Cloud provider", "kind": "Critical vendor", "matters": ["Outsourcing and third party", "Cyber security", "Operational resilience", "Data localisation"]},
    {"id": "industry", "name": "Banking industry baseline", "kind": "Industry", "matters": None},
]
STANDARDS = {
    "KYC and CDD": ["FATF R.10", "Basel CDD guidelines", "ISO 37301 8.2"], "AML / CFT": ["FATF R.20", "Wolfsberg AML principles"],
    "Sanctions screening": ["OFAC compliance framework", "UN Security Council lists"], "Cyber security": ["NIST CSF 2.0", "ISO/IEC 27001:2022", "SOC 2 CC6"],
    "Data privacy": ["GDPR Art.32", "ISO/IEC 27701", "NIST Privacy Framework"], "Data localisation": ["RBI payment data storage", "GDPR Chapter V"],
    "Operational resilience": ["DORA Art.5-16", "ISO 22301", "BCBS operational resilience"], "Outsourcing and third party": ["DORA Art.28", "EBA outsourcing guidelines", "ISO/IEC 27001 A.5.19"],
    "Fraud and payments": ["PCI DSS v4.0", "PSD2 strong authentication"], "Records and retention": ["ISO 15489"], "Regulatory reporting": ["BCBS 239"],
    "Capital and liquidity": ["Basel III"], "Complaints handling": ["ISO 10002"], "Consumer protection": ["FCA Consumer Duty", "ISO 37301"],
    "Conduct and culture": ["ISO 37301", "FSB conduct guidance"], "Governance and accountability": ["COSO internal control 2013", "IIA Three Lines Model", "ISO 37000"],
}
WHAT = {
    "KYC and CDD": "Know who the customer and the real owner is before and during the relationship", "AML / CFT": "Detect and report suspicious activity in time",
    "Sanctions screening": "Never deal with a listed person or country", "Cyber security": "Protect systems and data with controls that are tested",
    "Data privacy": "Use personal data lawfully and protect it", "Data localisation": "Keep regulated data where the law says",
    "Operational resilience": "Keep important services running through disruption", "Outsourcing and third party": "Stay accountable for what a supplier does for us",
    "Fraud and payments": "Prevent and detect payment fraud", "Records and retention": "Keep the right records for the right time", "Regulatory reporting": "Report accurately and on time",
    "Capital and liquidity": "Hold enough capital and cash", "Complaints handling": "Treat complaints fairly and learn from them", "Consumer protection": "Deliver good outcomes for customers",
    "Conduct and culture": "Behave the way the rules intend", "Governance and accountability": "Clear owners, clear oversight",
}
import json as _json, os as _os
PACKS = _json.load(open(_os.path.join(_os.path.dirname(__file__), "..", "data", "seed", "packs.json"), encoding="utf-8"))
STANDARDS.update(PACKS["standards"]); WHAT.update(PACKS["what"])
ORDER = {"Not compliant": 0, "Partial": 1, "Compliant": 2}


def subject(sid: str) -> Optional[Dict[str, Any]]:
    return next((s for s in SUBJECTS if s["id"] == sid), None)


def _scoped(items: List[Dict[str, Any]], ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    return items if ids is None else [i for i in items if i["id"] in set(ids)]


def evidence_row(m: str, pols: List[Dict[str, Any]], ctls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One requirement (rule matter) judged from the policies, controls and open issues we hold."""
    cs, ps = [c for c in ctls if c["ruleMatter"] == m], [p for p in pols if p["ruleMatter"] == m]
    risks = [k["id"] for k in store.risks() if k["ruleMatter"] == m]
    issues = [i for i in store.issues() if i["riskId"] in risks and i["status"] != "Closed"]
    eff = sum(c["testResult"] == "Effective" for c in cs)
    ni = sum(c["testResult"] == "Needs improvement" for c in cs)
    nt = sum(c["testResult"] == "Not tested" for c in cs)
    hi = [i for i in issues if i["severity"] in ("High", "Critical")]
    st, why, fix = "Compliant", [], []
    if not ps:
        st = "Not compliant"; why.append("No policy"); fix.append("Adopt a policy: owner, scope, review cycle. AAVA drafts it from the rule clauses for approval.")
    if not cs:
        st = "Not compliant"; why.append("No control"); fix.append("Design a control with an owner, frequency and evidence, then add it to the test plan.")
    if nt:
        st = st if st != "Compliant" else "Partial"; why.append(f"{nt} control(s) never tested"); fix.append("Run a design and operating-effectiveness test and attach the evidence.")
    if ni:
        st = st if st != "Compliant" else "Partial"; why.append(f"{ni} control(s) need improvement"); fix.append("Fix the weakness found, then re-test within 30 days.")
    if hi:
        st = st if st == "Not compliant" else "Partial"; why.append(f'Open {hi[0]["severity"]} issue {hi[0]["id"]}'); fix.append(f'Close {hi[0]["id"]} with evidence. Do not accept the risk.')
    worst = next((c for c in cs if c["testResult"] != "Effective"), cs[0] if cs else None)
    return ({"matter": m, "what": WHAT.get(m, ""), "standards": STANDARDS.get(m, ["ISO 37301"]), "status": st, "why": why, "fix": fix,
                 "evidence": f"{len(cs)} controls: {eff} effective, {ni} need improvement, {nt} not tested. {len(ps)} policies.",
                 "owner": (worst or {}).get("owner") or (ps[0]["owner"] if ps else "Unassigned"),
                 "due": "—" if st == "Compliant" else "30 to 60 days" if st == "Partial" else "90 days", "issues": [i["id"] for i in issues]})


def assess(sid: str, scope: Optional[Dict[str, Optional[List[str]]]] = None) -> Dict[str, Any]:
    sub = subject(sid)
    if not sub:
        raise KeyError(sid)
    scope = scope or {}
    pols, ctls = _scoped(store.policies(), scope.get("policies")), _scoped(store.controls(), scope.get("controls"))
    rules = _scoped(store.rules(), scope.get("rules"))
    scoped = any(scope.get(k) is not None for k in ("policies", "controls", "rules"))
    in_scope = {x["ruleMatter"] for x in pols + ctls + rules} if scoped else None
    base = sub["matters"] or sorted({c["ruleMatter"] for c in store.controls()})
    matters = [m for m in base if in_scope is None or m in in_scope]
    rows = [evidence_row(m, pols, ctls) for m in matters]
    rows.sort(key=lambda r: ORDER[r["status"]])
    n = lambda s: sum(r["status"] == s for r in rows)
    score = round(100 * (n("Compliant") + .5 * n("Partial")) / len(rows)) if rows else 0
    return {"subject": sub, "score": score, "counts": {"compliant": n("Compliant"), "partial": n("Partial"), "notCompliant": n("Not compliant"), "total": len(rows)},
            "rows": rows, "scope": {"scoped": scoped, "rules": len(rules), "policies": len(pols), "controls": len(ctls)}}


def fw_parts(sid: str):
    """`fw:soc2|Customer app|Application` names a framework assessment so share, fix plan and report reuse the same subject id."""
    p = sid.split("|")
    return p[0][3:], (p[1] if len(p) > 1 else ""), (p[2] if len(p) > 2 else "Application")


def report_html(sid: str, scope: Optional[Dict[str, Any]] = None) -> str:
    if sid.startswith("fw:"):
        fid, name, kind = fw_parts(sid)
        return framework_report_html(fid, scope, name, kind)
    a = assess(sid, scope); e = _html.escape
    colour = {"Compliant": "#E2F3EE;color:#006B53", "Partial": "#FFF6D6;color:#8A6D00", "Not compliant": "#FBE6F0;color:#A30052"}
    sc = a["scope"]
    scope_line = (f'Scope: {sc["rules"]} rules, {sc["policies"]} policies, {sc["controls"]} controls chosen by the user.' if sc["scoped"] else "Scope: everything in the library.")
    rows = "".join(f'<tr><td><b>{e(r["matter"])}</b><br><span class=m>{e(r["what"])}</span></td><td>{e(", ".join(r["standards"]))}</td>'
                   f'<td><span class=k style="background:{colour[r["status"]]}">{r["status"]}</span></td><td>{e("; ".join(r["why"]) or "Tested and effective")}<br><span class=m>{e(r["evidence"])}</span></td>'
                   f'<td>{"<br>".join(map(e, r["fix"])) or "Keep testing on schedule"}</td><td>{e(r["owner"])}<br><span class=m>{r["due"]}</span></td></tr>' for r in a["rows"])
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>AAVA assessment: {e(a["subject"]["name"])}</title><style>body{{font-family:Segoe UI,sans-serif;max-width:1000px;margin:34px auto;padding:0 24px;line-height:1.55;color:#212121}}'
            'h1{font-size:22px;margin:0}.m{color:#71758A;font-size:12px}table{width:100%;border-collapse:collapse;font-size:11.5px}th{background:#F2F2F4;text-align:left;padding:7px;font-size:10px}td{padding:7px;border-bottom:1px solid #e6e6ea;vertical-align:top}.k{padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600}.n{background:#EEEEFA;border-left:3px solid #6666CC;padding:10px 13px;margin:12px 0}</style></head><body>'
            f'<h1>Compliance assessment: {e(a["subject"]["name"])}</h1><div class=m>{e(a["subject"]["kind"])} · generated {date.today().isoformat()} · AAVA GRC Intelligence (illustrative data)</div>'
            f'<div class=n><b>Compliance score {a["score"]}%.</b> {a["counts"]["compliant"]} of {a["counts"]["total"]} requirements compliant, {a["counts"]["partial"]} partly, {a["counts"]["notCompliant"]} not compliant. {e(scope_line)}</div>'
            f'<table><tr><th>REQUIREMENT</th><th>STANDARDS</th><th>STATUS</th><th>WHY</th><th>HOW TO FIX</th><th>OWNER</th></tr>{rows}</table></body></html>')


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ frameworks and domains
def frameworks() -> List[Dict[str, Any]]:
    return [{k: f[k] for k in ("id", "name", "kind", "issuer", "summary", "note")} | {"criteria": len(f["criteria"]),
            "domains": [d["id"] for d in PACKS["domains"] if f["id"] in d["frameworks"]]} for f in PACKS["frameworks"]]


def domains() -> List[Dict[str, Any]]:
    return PACKS["domains"]


def framework(fid: str) -> Optional[Dict[str, Any]]:
    return next((f for f in PACKS["frameworks"] if f["id"] == fid), None)


def readiness(score: int, not_compliant: int) -> str:
    if score >= 90 and not_compliant == 0:
        return "Audit-ready"
    return "Close: fix the partial items first" if score >= 70 and not_compliant == 0 else "Not ready: gaps to close before an audit"


def assess_framework(fid: str, scope: Optional[Dict[str, Optional[List[str]]]] = None, name: str = "", kind: str = "Application", domain: str = "") -> Dict[str, Any]:
    """Readiness against one framework. Each criterion is judged from the evidence behind the rule matter it maps to."""
    fw = framework(fid)
    if not fw:
        raise KeyError(fid)
    scope = scope or {}
    pols, ctls = _scoped(store.policies(), scope.get("policies")), _scoped(store.controls(), scope.get("controls"))
    scoped = any(scope.get(k) is not None for k in ("policies", "controls", "rules"))
    in_scope = {x["ruleMatter"] for x in pols + ctls} if scoped else None
    rows, skipped = [], []
    for c in fw["criteria"]:
        if in_scope is not None and c["matter"] not in in_scope:
            skipped.append({"id": c["id"], "title": c["title"], "matter": c["matter"]}); continue
        r = evidence_row(c["matter"], pols, ctls)
        r.update({"criterion": c["id"], "title": c["title"], "request": c["evidence"], "standards": [f'{fw["name"].split(" (")[0]} {c["id"]}']})
        rows.append(r)
    rows.sort(key=lambda r: ORDER[r["status"]])
    n = lambda s: sum(r["status"] == s for r in rows)
    score = round(100 * (n("Compliant") + .5 * n("Partial")) / len(rows)) if rows else 0
    d = next((x for x in PACKS["domains"] if x["id"] == domain), None)
    return {"framework": {k: fw[k] for k in ("id", "name", "kind", "issuer", "summary", "note")}, "subject": {"name": name or "Our organisation", "kind": kind, "domain": (d or {}).get("name", "")},
            "score": score, "readiness": readiness(score, n("Not compliant")),
            "counts": {"compliant": n("Compliant"), "partial": n("Partial"), "notCompliant": n("Not compliant"), "total": len(rows)},
            "rows": rows, "notAssessed": skipped, "evidenceRequests": [{"criterion": r["criterion"], "request": r["request"], "status": r["status"]} for r in rows],
            "scope": {"scoped": scoped, "policies": len(pols), "controls": len(ctls), "rules": 0}}


def framework_report_html(fid: str, scope: Optional[Dict[str, Any]], name: str = "", kind: str = "Application", domain: str = "") -> str:
    a = assess_framework(fid, scope, name, kind, domain); e = _html.escape
    colour = {"Compliant": "#E2F3EE;color:#006B53", "Partial": "#FFF6D6;color:#8A6D00", "Not compliant": "#FBE6F0;color:#A30052"}
    rows = "".join(f'<tr><td><b>{e(r["criterion"])}</b><br>{e(r["title"])}</td><td><span class=k style="background:{colour[r["status"]]}">{r["status"]}</span></td>'
                   f'<td>{e("; ".join(r["why"]) or "Tested and effective")}<br><span class=m>{e(r["evidence"])}</span></td><td>{"<br>".join(map(e, r["fix"])) or "Keep testing on schedule"}</td>'
                   f'<td>{e(r["request"])}</td><td>{e(r["owner"])}<br><span class=m>{r["due"]}</span></td></tr>' for r in a["rows"])
    skipped = "".join(f"<li>{e(x['id'])} {e(x['title'])}</li>" for x in a["notAssessed"])
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{e(a["framework"]["name"])} readiness</title><style>body{{font-family:Segoe UI,sans-serif;max-width:1040px;margin:34px auto;padding:0 24px;line-height:1.55;color:#212121}}'
            'h1{font-size:22px;margin:0}.m{color:#71758A;font-size:12px}table{width:100%;border-collapse:collapse;font-size:11.5px}th{background:#F2F2F4;text-align:left;padding:7px;font-size:10px}td{padding:7px;border-bottom:1px solid #e6e6ea;vertical-align:top}.k{padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600}.n{background:#EEEEFA;border-left:3px solid #6666CC;padding:10px 13px;margin:12px 0}</style></head><body>'
            f'<h1>{e(a["framework"]["name"])} readiness: {e(a["subject"]["name"])}</h1><div class=m>{e(a["subject"]["kind"])} · {e(a["subject"]["domain"])} · generated {date.today().isoformat()} · AAVA GRC Intelligence (illustrative data)</div>'
            f'<div class=n><b>{e(a["readiness"])}. Score {a["score"]}%.</b> {a["counts"]["compliant"]} of {a["counts"]["total"]} criteria compliant, {a["counts"]["partial"]} partly, {a["counts"]["notCompliant"]} not compliant.<br>{e(a["framework"]["note"])}'
            f'{"<br><b>Not assessed (outside your scope):</b><ul>"+skipped+"</ul>" if skipped else ""}</div>'
            f'<table><tr><th>CRITERION</th><th>STATUS</th><th>WHY</th><th>HOW TO FIX</th><th>EVIDENCE AN AUDITOR WILL ASK FOR</th><th>OWNER</th></tr>{rows}</table>'
            '<p class=m>This is a readiness view from the controls and policies in AAVA. It is not an audit opinion or a certificate.</p></body></html>')
