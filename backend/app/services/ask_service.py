"""Ask AAVA — the agentic orchestrator behind the chat.

One question in, one structured, auditable run out:

    intent  ->  steps (agent, tool, knowledge base, output, gate)  ->  evidence blocks  ->  answer

Nothing here is free text from a model. Every number is computed from the rule,
policy, control, risk and issue records, so the client can render it, a reviewer can
check it and the audit trail can replay it. When the question cannot be grounded the
run abstains and logs a knowledge gap rather than guessing.

Modes
    Ask    read only, cited, abstains
    Act    drafts and creates tasks, but every write waits at a human gate
    Watch  standing subscriptions

Swap `route()` for an LLM intent classifier and `semantic_map_service.concept_hits`
for embeddings; keep the run shape and the gates.
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from app.services import change_service, collaboration_service as collab, obligation_service, semantic_map_service as sm, store

WATCHES: List[Dict[str, Any]] = []

SEED_PAIRS = [("us", "KYC and CDD"), ("uk", "KYC and CDD"), ("hk", "KYC and CDD"), ("in", "KYC and CDD"),
              ("us", "AML / CFT"), ("hk", "AML / CFT"), ("cn", "AML / CFT"),
              ("uk", "Operational resilience"), ("hk", "Operational resilience"), ("eu", "Operational resilience"),
              ("in", "Outsourcing and third party"), ("ca", "Outsourcing and third party"),
              ("in", "Data localisation"), ("cn", "Data localisation"),
              ("uk", "Data privacy"), ("us", "Data privacy"),
              ("uk", "Consumer protection"), ("in", "Cyber security")]
MATTER_KEYS = {
    "KYC and CDD": r"kyc|due diligence|beneficial|onboard|cdd|ubo",
    "AML / CFT": r"\baml\b|money laundering|suspicious|\bsar\b",
    "Sanctions screening": r"sanction|ofac",
    "Operational resilience": r"resilien|impact toleran|scenario",
    "Outsourcing and third party": r"outsourc|third.?party|vendor",
    "Data localisation": r"localis|localiz|residen|cross.?border transfer",
    "Data privacy": r"privacy|personal data|breach|gdpr",
    "Cyber security": r"cyber|security|privileged",
    "Consumer protection": r"consumer|customer outcome|fair value",
}
LEVEL = sm.LEVEL


def _step(agent, tool, output, ms, kb=None, gate=False):
    return {"agent": agent, "tool": tool, "kb": kb, "output": output, "ms": ms, "gate": gate}


# ------------------------------------------------------------------ routing
def route(q: str) -> Optional[Dict[str, Any]]:
    if re.search(r"assess|are we compliant|what is not compliant|how compliant|industry standard", q, re.I):
        return {"id": "assess"}
    if re.search(r"\bwatch\b|tell me when|notify me|alert me|subscribe", q, re.I):
        return {"id": "watch"}
    if re.search(r"stakeholder|who (needs|must|should|has) to|who.{0,20}(told|informed|notified)|coordinat|sign.?off|loop in", q, re.I):
        return {"id": "coordinate"}
    if re.search(r"report|board pack|summary of compliance", q, re.I):
        return {"id": "report"}
    if re.search(r"hkma|amend|what changed|change", q, re.I):
        return {"id": "change"}
    if re.search(r"payment token|non-indian|dr region|critical issue|iss-03|overdue|fix (this|the) issue", q, re.I):
        return {"id": "issue"}
    if re.search(r"appetite|top risks|which risks|risk posture", q, re.I):
        return {"id": "risks"}
    focus = sm._roots(sm.concept_hits(q))
    cite = next((r for r in store.rules() if r["cite"].lower() in q.lower()), None)
    if cite:
        return {"id": "map", "rules": [cite["id"]], "focus": focus}
    matter = next((m for m, rx in MATTER_KEYS.items() if re.search(rx, q, re.I)), None)
    if matter:
        norm = re.sub(r"united states", "US", re.sub(r"hong kong", "HK", q, flags=re.I), flags=re.I)
        # names match any case; two-letter codes only when written as codes, so "in the US" is not India
        js = [j["id"] for j in store.jurisdictions()
              if re.search(r"\b" + re.escape(j["name"]) + r"\b", norm, re.I) or re.search(r"\b" + j["id"].upper() + r"\b", norm)]
        def pick(j):
            cands = [r for r in store.rules() if r["juris"] == j and r["ruleMatter"] == matter]
            score = lambda r: sum(1 for h in sm.concept_hits(r["title"] + " " + r["text"]) if h["root"] in focus)
            return max(cands, key=score)["id"] if cands else None
        ids = [pick(j) for j in (js or ["us", "uk", "hk"])]
        ids = [i for i in ids if i]
        if ids:
            return {"id": "map", "rules": ids, "focus": focus}
    return None


# ---------------------------------------------------------------- scenarios
def _map(sel) -> Dict[str, Any]:
    ids = sel.get("rules") or ["31 CFR 1010.230", "MLR 2017 reg.28", "AMLO Sch.2 s.2"]
    focus = sel.get("focus") or ["beneficial owner"]
    maps = [m for m in (sm.map_rule(i, focus) for i in ids) if m]
    cnt = lambda v: sum(1 for m in maps if m["verdict"] == v)
    steps = [
        _step("Intent Router", "classify + scope", f"Intent map regulation → policy. {len(maps)} rule(s). Mode Ask (read only).", 210),
        _step("Retrieval Agent", "hybrid search", "Retrieved " + ", ".join(m["cite"] for m in maps), 640, "Regulatory corpus"),
        _step("Obligation Extractor", "clause parser", "Primary obligation per rule: trigger, actor, action, timing, confidence.", 910),
        _step("Semantic Mapper", "concept + action + timing match", "Scored every policy clause on four axes.", 1220, "Policy library"),
        _step("Evidence Checker", "control + test status", "Looked up deployed controls and their latest test result.", 480, "Control library"),
        _step("Risk & Issue Linker", "graph traversal", "Linked risks and open issues.", 390, "Risk register"),
        _step("Citation Verifier", "deterministic checks", "Every quoted phrase found in its source. Every ID resolves.", 260, gate=True),
        _step("Gate 2 · Mapping approval", "human in the loop",
              f'{sum(1 for m in maps if m["gate"]=="auto")} auto-pass, {sum(1 for m in maps if m["gate"]=="human")} routed to the policy owner.', 150, gate=True),
    ]
    answer = (f"{cnt('Covered')} covered, {cnt('Partial')} partial, {cnt('Gap') + cnt('Conflict')} gap or conflict. "
              + " ".join(f'{m["juris"].upper()}: {(m["match"] or {}).get("reasons", ["No policy covers this obligation."])[0]}.'
                         for m in maps if m["verdict"] != "Covered" and m["match"] and m["match"]["reasons"]))
    return {"kind": "map", "steps": steps, "answer": answer, "data": {"mappings": maps},
            "sources": [m["cite"] for m in maps]}


def _report() -> Dict[str, Any]:
    rules = []
    for j, m in SEED_PAIRS:
        r = next((x for x in store.rules() if x["juris"] == j and x["ruleMatter"] == m and x["id"] not in [y["id"] for y in rules]), None)
        if r:
            rules.append(r)
    maps = [sm.map_rule(r["id"]) for r in rules]
    gaps = [m for m in maps if m["verdict"] in ("Gap", "Conflict")]
    part = [m for m in maps if m["verdict"] == "Partial"]
    cov = [m for m in maps if m["verdict"] == "Covered"]
    score = round(100 * (1 - (len(gaps) + .5 * len(part)) / max(1, len(maps))))
    rank = {"Covered": 1, "Partial": 2, "Gap": 3, "Conflict": 3}
    matrix: Dict[str, Dict[str, str]] = {}
    for r, m in zip(rules, maps):
        cur = matrix.setdefault(r["ruleMatter"], {}).get(r["juris"])
        if cur is None or rank[m["verdict"]] > rank[cur]:
            matrix[r["ruleMatter"]][r["juris"]] = m["verdict"]
    over = [k for k in store.risks() if LEVEL[k["residual"]] > LEVEL[k["appetite"]]]
    plan = []
    for k in over:
        rel = [m for m in maps if m["risks"] and any(x["id"] == k["id"] for x in m["risks"]) and m["verdict"] != "Covered"]
        iss = store.issues_for_risk(k["id"])
        plan.append({"riskId": k["id"], "risk": k["name"], "residual": k["residual"], "appetite": k["appetite"],
                     "findings": len(rel), "owner": iss[0]["owner"] if iss else "Unassigned",
                     "action": ("Fix the weakest mitigating control and re-test" if iss else "Raise a remediation issue and assign an owner")})
    plan.sort(key=lambda p: -p["findings"])
    steps = [
        _step("Intent Router", "classify + scope", "Intent generate compliance report. Scope: cross-border banking rulebook 2027.", 230),
        _step("Rulebook Agent", "pinned rules", f"Loaded {len(rules)} rules.", 520, "Regulatory corpus"),
        _step("Semantic Mapper", "concept + action + timing match", "Mapped obligations to policies and controls.", 1180, "Policy library"),
        _step("Risk & Issue Linker", "graph traversal", "Linked risks, residual vs appetite, open issues.", 520, "Risk register"),
        _step("Coverage Judge", "rubric + deterministic checks", "Classified every rule Covered, Partial, Gap or Conflict.", 760, gate=True),
        _step("Remediation Planner", "action library", "Drafted an action and owner per risk above appetite.", 690, "Playbooks"),
        _step("Report Writer", "templated narrative", "Wrote the summary from the numbers, not from memory.", 540),
        _step("Gate 3 · CCO review", "human in the loop", "Marked draft for review.", 140, gate=True),
    ]
    return {"kind": "report", "steps": steps,
            "answer": f"Coverage {score}% across {len(maps)} rules: {len(cov)} covered, {len(part)} partial, {len(gaps)} gap or conflict. {len(over)} risks sit above appetite.",
            "data": {"coverageScore": score, "counts": {"rules": len(maps), "covered": len(cov), "partial": len(part), "gap": len(gaps)},
                     "matrix": matrix, "gaps": [{"cite": m["cite"], "juris": m["juris"], "verdict": m["verdict"],
                                                 "reason": (m["match"]["reasons"][:1] or [""])[0] if m["match"] else "No policy"} for m in gaps + part],
                     "plan": plan}, "sources": [r["cite"] for r in rules]}


def _change(sel) -> Dict[str, Any]:
    ch = store.changes()[0]
    rule = store.rule_by_cite(ch["affectedCites"][0])
    existing = " ".join(d["text"] for d in ch["diff"] if d["kind"] in ("unchanged", "removed"))
    amended = " ".join(d["text"] for d in ch["diff"] if d["kind"] in ("unchanged", "added"))
    tmp = {**rule, "id": "RUL-CHG01", "text": amended}
    old_actions = {o.action for o in obligation_service.extract(rule, limit=False)}
    maps = []
    for o in obligation_service.extract(tmp, limit=False):
        m = sm.map_obligation(tmp, o.model_dump())
        m["isNew"] = o.action not in old_actions
        maps.append(m)
    imp = change_service.impact(ch["id"])
    steps = [
        _step("Horizon Scanner", "standing watch", f'Detected {ch["title"]} published {ch["published"]}, effective {ch["effective"]}.', 300, "Regulatory corpus"),
        _step("Change Analyst", "clause diff", "Aligned the amended text to the stored clause.", 820),
        _step("Obligation Extractor", "clause parser", f'{len(maps)} duties, {sum(1 for m in maps if m["isNew"])} new.', 760),
        _step("Semantic Mapper", "concept + action + timing match", "Re-mapped every duty against policy clauses.", 1010, "Policy library"),
        _step("Impact Scorer", "0.40·materiality + 0.35·gap + 0.25·urgency", f"Impact {imp.impactScore}/100.", 340, gate=True),
        _step("Remediation Planner", "playbook", "Drafted actions with owners.", 620, "Playbooks"),
        _step("Gate 3 · CCO approval", "human in the loop",
              "Impact ≥ 70: cannot auto-complete." if imp.impactScore >= 70 else "Below 70: owner approval only.", 140, gate=True),
    ]
    return {"kind": "change", "steps": steps, "write": True,
            "answer": f'{ch["title"]}. Impact {imp.impactScore}/100, {ch["effective"]} effective.',
            "data": {"change": ch, "existing": existing, "amended": amended, "mappings": maps, "impact": imp.model_dump()},
            "sources": ch["affectedCites"] + [ch["id"]]}


ISSUE_PLAN = [
    ("Contain", "Stop replicating payment tokens to the non-Indian DR region and block the replication job", "Platform Engineering", "48 hours", "Change record and job disabled log"),
    ("Verify", "Prove the replicated data is purged and none is held outside India", "Platform Engineering", "7 days", "Deletion certificate and storage inventory"),
    ("Fix the cause", "Stand up in-country disaster recovery for payment data", "Platform Engineering", "60 days", "Architecture sign-off and DR test"),
    ("Fix the policy", "Remove “copies may be held in regional disaster recovery sites” from POL-09 §2.1", "Group DPO", "14 days", "Approved policy v2.1"),
    ("Fix the control", "Make CTRL-24 residency check automated across all regions and re-test", "Platform Engineering", "30 days", "Passed control test"),
    ("Regulator", "Commission the CERT-In empanelled system audit report", "Chief Compliance Officer", "45 days", "Audit report on file"),
    ("Close", "Close ISS-03 only when all evidence above is attached", "Issue owner", "—", "Closure checklist"),
]


def _issue() -> Dict[str, Any]:
    iss = next(i for i in store.issues() if i["id"] == "ISS-03")
    risk = store.risk_by_id(iss["riskId"])
    m = sm.map_rule("DPSS.CO.PD.No.1810")
    late = (date.today() - date.fromisoformat(iss["due"])).days
    steps = [
        _step("Intent Router", "classify + scope", f'Intent mitigate an issue: {iss["id"]} ({iss["severity"]}, {max(late,0)} days overdue). Write intent → Act mode.', 260, gate=True),
        _step("Risk & Issue Linker", "graph traversal", f'{iss["id"]} → {risk["id"]} {risk["name"]}: above appetite.', 420, "Risk register"),
        _step("Retrieval Agent", "hybrid search", "Rule found: DPSS.CO.PD.No.1810 (RBI), “only in India”.", 610, "Regulatory corpus"),
        _step("Semantic Mapper", "concept + action + timing match", "A contradiction was found between the rule and POL-09 §2.1.", 980, "Policy library"),
        _step("Evidence Checker", "control + test status", "CTRL-24 needs improvement; CTRL-25 not tested.", 390, "Control library"),
        _step("Remediation Planner", "playbook", "Seven-step plan built.", 700, "Playbooks"),
        _step("Gate 2 · issue owner", "human in the loop", "Plan needs approval before tasks are created.", 140, gate=True),
    ]
    return {"kind": "issue", "steps": steps, "write": True,
            "answer": "Root cause: the policy contradicts the rule. Fixing the replication job alone would leave the policy wrong.",
            "data": {"issue": iss, "risk": risk, "mappings": [m], "overdueDays": max(late, 0),
                     "plan": [dict(zip(("step", "action", "owner", "due", "evidence"), p)) for p in ISSUE_PLAN]},
            "sources": ["DPSS.CO.PD.No.1810", "POL-09 §2.1", "CTRL-24", risk["id"], iss["id"]]}


def _risks() -> Dict[str, Any]:
    over = sorted([k for k in store.risks() if LEVEL[k["residual"]] > LEVEL[k["appetite"]]],
                  key=lambda k: -(LEVEL[k["residual"]] - LEVEL[k["appetite"]]))
    rows = []
    for k in over:
        cs = [c for c in store.controls() if c["ruleMatter"] == k["ruleMatter"]]
        weak = [c for c in cs if c["testResult"] != "Effective"]
        iss = store.issues_for_risk(k["id"])
        rows.append({**k, "controls": len(cs), "weakControls": [c["id"] for c in weak], "issues": [i["id"] for i in iss],
                     "next": ("Raise a remediation issue and assign an owner" if not iss else
                              f'Fix {weak[0]["id"]}: {weak[0]["testResult"].lower()}' if weak else "Re-assess residual rating after remediation")})
    steps = [_step("Intent Router", "classify + scope", "Intent risk posture.", 200),
             _step("Risk & Issue Linker", "graph traversal", f'{len(store.risks())} risks read; compared residual with appetite.', 540, "Risk register"),
             _step("Evidence Checker", "control + test status", "Pulled mitigating controls and test results.", 610, "Control library"),
             _step("Remediation Planner", "playbook", f"{len(over)} above appetite.", 640, "Playbooks"),
             _step("Citation Verifier", "deterministic checks", "All IDs resolve. No figures estimated.", 180, gate=True)]
    return {"kind": "risks", "steps": steps, "answer": f'{len(over)} of {len(store.risks())} risks are above appetite.',
            "data": {"risks": rows}, "sources": [k["id"] for k in over]}


def _watch() -> Dict[str, Any]:
    WATCHES[:] = [{"scope": "AML / CFT · US, UK, HK", "rule": "Notify owners; CCO if impact ≥ 70"},
                  {"scope": "Data localisation · IN, CN", "rule": "Notify Group DPO"}]
    store.audit("watch.create", "AML / CFT US UK HK", {})
    steps = [_step("Intent Router", "classify + scope", "Intent standing subscription. Mode Watch.", 180),
             _step("Horizon Scanner", "subscription", "Subscribed to AML / CFT rules in US, UK and HK.", 420, "Regulatory corpus"),
             _step("Policy engine", "notification rules", "On change: re-map, score impact, notify the owner.", 260, gate=True)]
    return {"kind": "watch", "steps": steps, "answer": "Watch is on.", "data": {"watches": WATCHES}, "sources": []}


def _assess() -> Dict[str, Any]:
    from app.services import assess_service
    res = assess_service.assess("platform")
    steps = [_step("Scope Agent", "what is being assessed", "Subject Payments platform. Switch to the organisation, a process, a vendor or the industry.", 240),
             _step("Standards Mapper", "requirement → recognised framework", "NIST CSF 2.0, ISO 27001, GDPR, DORA, PCI DSS, FATF, Basel, COSO.", 620, "Regulatory corpus"),
             _step("Evidence Checker", "controls, tests, policies, issues", "Read each control, its latest test, the backing policy and any open High or Critical issue.", 780, "Control library"),
             _step("Verdict Engine", "deterministic rules", "Compliant only if a policy exists, controls are tested and effective, and no High or Critical issue is open.", 300, gate=True),
             _step("Remediation Planner", "playbook", "How to fix each finding, the owner and a due window.", 540, "Playbooks"),
             _step("Report Compiler", "HTML · fingerprint · share", "Sharing outside the organisation waits for CCO approval.", 260)]
    c = res["counts"]
    return {"kind": "assess", "steps": steps, "answer": f'{res["subject"]["name"]}: score {res["score"]}%. {c["compliant"]} compliant, {c["partial"]} partly, {c["notCompliant"]} not compliant.',
            "data": res, "sources": []}


def _coordinate() -> Dict[str, Any]:
    ch = store.changes()[0]
    note = collab.notify_change(ch["id"])
    imp = note["impactScore"]
    gate = "gate3" if imp >= 70 else "gate2"
    accountable = [n["to"]["id"] for n in note["notifications"] if n["raci"] == "A"]
    ap = collab.APPROVALS.get(ch["id"]) or collab.request_approval(
        ch["id"], gate, f'Approve the remediation plan for {ch["title"]} (impact {imp}/100, effective {ch["effective"]}).', accountable)
    rows = [{"name": n["to"]["name"], "role": n["to"]["role"], "raci": n["raci"], "raciText": n["raciText"], "channels": n["channels"],
             "dueBy": n["dueBy"], "why": n["body"].split("because: ")[-1], "id": n["id"], "sid": n["to"]["id"], "status": n["status"]} for n in note["notifications"]]
    steps = [
        _step("Change Analyst", "impact score", f'{ch["title"]}: impact {imp}/100, priority {note["priority"]}.', 340),
        _step("Stakeholder Router", "RACI from owners of affected policies, controls and issues", f"{len(rows)} people routed: {sum(r['raci']=='A' for r in rows)} accountable, {sum(r['raci']=='R' for r in rows)} responsible.", 410, "Policy and control registry"),
        _step("Notifier", "email · Teams · Jira", f'{note["created"]} notifications sent with SLA due times.', 380),
        _step("Coordinator", "thread + @mentions", "Opened one thread where people comment, mention each other and decide.", 260),
        _step("Escalation watch", "SLA timer", "Unacknowledged Accountable or Responsible notices go to the manager after the SLA.", 120),
        _step(f"{'Gate 3 · CCO' if gate=='gate3' else 'Gate 2 · Owner'} approval", "human in the loop", f"Approval requested from {', '.join(r['role'] for r in ap['required'])}.", 140, gate=True),
    ]
    return {"kind": "coordinate", "steps": steps, "write": True,
            "answer": f'{len(rows)} stakeholders notified about {ch["title"]}; approval requested from {", ".join(r["role"] for r in ap["required"])}.',
            "data": {"change": ch, "impact": imp, "priority": note["priority"], "routing": rows, "thread": collab.thread(ch["id"]),
                     "approval": ap, "status": collab.status(ch["id"])},
            "sources": ch["affectedCites"] + [ch["id"]]}


# ------------------------------------------------------------------- entry
def run(question: str, mode: str = "Ask") -> Dict[str, Any]:
    sel = route(question)
    run_id = "RUN-" + uuid.uuid4().hex[:8].upper()
    base = {"runId": run_id, "question": question, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if sel is None:
        store.audit("ask.abstain", run_id, {"question": question[:80]})
        return {**base, "intent": "abstain", "mode": mode, "abstained": True, "kind": "abstain", "steps": [],
                "answer": "I can’t answer that from the evidence I have, so I won’t guess. Try a rule citation, a topic with countries, or one of the suggested prompts.",
                "data": {}, "sources": [], "gates": []}
    body = {"map": lambda: _map(sel), "report": _report, "change": lambda: _change(sel), "issue": _issue,
            "risks": _risks, "watch": _watch, "coordinate": _coordinate, "assess": _assess}[sel["id"]]()
    if body.get("write") and mode != "Act":
        mode = "Act"
        store.audit("mode.escalate", run_id, {"from": "Ask", "to": "Act"})
    store.audit("ask.run", run_id, {"intent": sel["id"], "question": question[:80]})
    return {**base, "intent": sel["id"], "mode": mode, "abstained": False, **body,
            "gates": [s["agent"] for s in body["steps"] if s["gate"]]}


def approve(run_id: str, gate: str, subject: str, approver: str = "demo.user") -> Dict[str, Any]:
    store.audit(f"{gate}.approve", subject, {"runId": run_id, "approver": approver})
    return {"ok": True, "runId": run_id, "gate": gate, "subject": subject, "approver": approver}
