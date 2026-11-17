"""Clause-level semantic mapping: regulation obligation -> policy clause.

Explainable by design. A mapping is scored on four axes a reviewer can argue
with, and every reason for a shortfall is returned in plain words:

    score = .40 concepts + .25 actions + .20 timing + .15 jurisdiction

Concepts are matched by meaning (a synonym map), so "legal entity customer" in a
rule meets "UBO register" in a policy. Actions are matched by verb family, so a
clause that *captures* an owner does not satisfy a rule that says *verify*.
Timing is compared as a duration where the rule gives one. A clause that
contradicts the rule (copies permitted where the rule says "only") is returned
as a Conflict and always wins selection, because it is the most decision-relevant
finding.

Swap `concept_hits` for embeddings and keep everything else: the output shape and
the reasons are what the human gate and the audit record depend on.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.services import obligation_service, store

EXTRA_CONCEPTS: Dict[str, List[str]] = {
    "beneficial owner": ["beneficial ownership"],
    "customer due diligence": ["verify the identity", "verify their identity", "verify the customer identity",
                               "identify the customer", "identify and verify"],
    "localisation": ["only in india", "stored in india", "outside the territory", "outside india",
                     "disaster recovery", "regional disaster recovery"],
    "monitoring": ["ongoing monitoring", "continuously monitor", "monitored on an ongoing basis",
                   "transaction monitoring", "scrutinise", "review existing records"],
    "politically exposed person": ["pep", "peps", "politically exposed persons", "domestic pep",
                                   "prominent public function"],
}
VERB_GROUPS: Dict[str, List[str]] = {
    "verify": ["verif", "validat", "authenticat", "confirm"],
    "identify": ["identif", "identity", "captur", "record", "obtain", "collect"],
    "report": ["report", "file", "submit", "notif"],
    "monitor": ["monitor", "scrutinis", "scrutiniz", "surveil", "review"],
    "retain": ["retain", "retention", "preserv", "archiv"],
    "store": ["stored", "storage", "store", "held", "hosted"],
    "test": ["test", "exercis"],
    "assess": ["assess", "evaluat"],
    "establish": ["establish", "maintain", "implement", "document", "set an"],
}
LEVEL = {"Zero": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def _sem() -> Dict[str, List[str]]:
    out = {k: list(v) for k, v in store.semantic().items()}
    for k, v in EXTRA_CONCEPTS.items():
        out.setdefault(k, [])
        out[k] = out[k] + v
    return out


def concept_hits(text: str) -> List[Dict[str, Any]]:
    hits = []
    for root, syns in _sem().items():
        for term in [root, *syns]:
            for m in re.finditer(r"\b" + re.escape(term) + r"(?:s|es)?\b", text, re.I):
                hits.append({"root": root, "surface": m.group(0).lower(), "start": m.start(), "end": m.end()})
    return hits


def _roots(hits) -> List[str]:
    return list(dict.fromkeys(h["root"] for h in hits))


def verbs_of(text: str) -> List[str]:
    t = text.lower()
    return [g for g, stems in VERB_GROUPS.items() if any(re.search(r"\b" + s, t) for s in stems)]


def _hours(t: Optional[str]) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:business\s+|calendar\s+)?(hour|day|month|year)s?", t or "", re.I)
    return int(m.group(1)) * {"hour": 1, "day": 24, "month": 720, "year": 8760}[m.group(2).lower()] if m else None


def timing_check(rule_timing: Optional[str], rule_text: str, clause: str) -> Dict[str, Any]:
    if re.search(r"\b(entire|only|solely)\b", rule_text, re.I) and re.search(r"\bcopies\b|replicat|may be (held|stored|kept)", clause, re.I):
        return {"kind": "conflict", "score": 0.0,
                "message": "Policy permits copies in other regions, but the rule requires the data to be held only in the territory"}
    if not rule_timing:
        return {"kind": "ok", "score": 1.0, "message": ""}
    rd, pd = _hours(rule_timing), _hours(clause)
    if rd:
        if pd:
            return {"kind": "ok", "score": 1.0, "message": ""} if pd <= rd else \
                   {"kind": "conflict", "score": 0.0, "message": f"Policy allows longer than the rule ({rule_timing})"}
        if re.search(r"promptly|without undue delay|as soon as|timely", clause, re.I):
            return {"kind": "vague", "score": 0.3,
                    "message": f"Rule sets a fixed deadline (“{rule_timing}”); policy only says “promptly”, which cannot be tested or evidenced"}
        return {"kind": "missing", "score": 0.35, "message": f"Rule sets a deadline (“{rule_timing}”); policy gives none"}
    families = [(r"before|at the time|prior to|opening", r"before|prior to|at onboarding|at the time|on opening"),
                (r"annual|periodic", r"annual|periodic|each year|risk tier"),
                (r"ongoing|continuous|at all times", r"ongoing|continuous")]
    for a, b in families:
        if re.search(a, rule_timing, re.I):
            if re.search(b, clause, re.I):
                return {"kind": "ok", "score": 1.0, "message": ""}
            return {"kind": "missing", "score": 0.4, "message": f"Rule timing “{rule_timing}” is not reflected in the policy"}
    return {"kind": "ok", "score": 1.0, "message": ""}


def score_clause(rule, ob, pol, clause, focus: Optional[List[str]] = None) -> Dict[str, Any]:
    juris_ok = 1.0 if rule["juris"] in pol["jurisdictions"] else 0.0
    if clause.get("synthetic"):
        return {"score": 0.5, "parts": {"concepts": .5, "actions": .5, "timing": .5, "jurisdiction": juris_ok},
                "timing": {"kind": "ok"}, "reasons": ["Policy text is not ingested, so it is matched on title and scope only."],
                "missing": [], "bridges": [], "conflict": False, "shared": []}
    ob_text = f'{ob["actor"]} {ob["trigger"]} {ob["action"]} {ob.get("timing") or ""}'
    a, b = concept_hits(ob_text), concept_hits(clause["text"])
    ra, rb = _roots(a), _roots(b)
    shared = [r for r in ra if r in rb]
    wt = lambda r: sum(1 for h in a if h["root"] == r)
    c = sum(wt(r) for r in shared) / sum(wt(r) for r in ra) if ra else .5
    va, vb = verbs_of(ob["action"]), verbs_of(clause["text"])
    v = len([x for x in va if x in vb]) / len(va) if va else .5
    t = timing_check(ob.get("timing"), rule["text"], clause["text"])
    score = .40 * c + .25 * v + .20 * t["score"] + .15 * juris_ok
    if t["kind"] == "conflict":
        score = min(score, .45)
    if focus and any(f in ra and f not in rb for f in focus):
        score = min(score, .62)
    missing = [r for r in ra if r not in rb and (not focus or r in focus)]
    reasons = [f'The rule requires you to {x}, but this clause only covers: {", ".join(vb) or "nothing relevant"}'
               for x in va if x not in vb]
    if missing:
        reasons.append("The clause does not mention: " + ", ".join(missing))
    if t["message"]:
        reasons.append(t["message"])
    if not juris_ok:
        reasons.append(f'Policy is not deployed in {rule["juris"].upper()}')
    bridges = []
    for r in shared:
        ha, hb = next(h for h in a if h["root"] == r), next(h for h in b if h["root"] == r)
        bridges.append({"concept": r, "rule": ha["surface"], "policy": hb["surface"], "identical": ha["surface"] == hb["surface"]})
    return {"score": round(score, 3), "parts": {"concepts": round(c, 3), "actions": round(v, 3),
            "timing": t["score"], "jurisdiction": juris_ok}, "timing": t, "reasons": reasons,
            "missing": missing, "bridges": bridges, "conflict": t["kind"] == "conflict", "shared": shared}


def spans(text: str, other_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Non-overlapping highlight spans: hl = same words, hl2 = same meaning, different words,
    dotted = a concept the other side does not mention, modal = the duty word, timing = the deadline."""
    roots = set(_roots(other_hits))
    surf = {h["surface"] for h in other_hits}
    out = []
    for h in concept_hits(text):
        cls = "dotted" if h["root"] not in roots else ("same" if h["surface"] in surf else "semantic")
        out.append({"start": h["start"], "end": h["end"], "cls": cls})
    for rx, _k, _w in obligation_service.MODALS:
        out += [{"start": m.start(), "end": m.end(), "cls": "modal"} for m in rx.finditer(text)]
    for rx in obligation_service.TIMING:
        out += [{"start": m.start(), "end": m.end(), "cls": "timing"} for m in rx.finditer(text)]
    out.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
    res, pos = [], 0
    for x in out:
        if x["start"] >= pos:
            res.append(x)
            pos = x["end"]
    return res


def map_obligation(rule: Dict[str, Any], ob: Dict[str, Any], focus: Optional[List[str]] = None) -> Dict[str, Any]:
    # a time limit only counts if it belongs to this duty's own wording
    timing = ob.get("timing")
    if timing and timing.lower() not in ob["action"].lower():
        ob = {**ob, "timing": None}
    clauses = store.policy_clauses()
    best = conflict = None
    for pol in [p for p in store.policies() if p["ruleMatter"] == rule["ruleMatter"]]:
        for cl in clauses.get(pol["id"], [{"sec": "—", "text": "", "synthetic": True}]):
            sc = score_clause(rule, ob, pol, cl, focus)
            cand = {"policyId": pol["id"], "policyName": pol["name"], "policyOwner": pol["owner"], "version": pol["version"],
                    "clauseSec": cl["sec"], "clauseText": cl["text"], **sc}
            if best is None or cand["score"] > best["score"]:
                best = cand
            if cand["conflict"] and (conflict is None or cand["score"] < conflict["score"]):
                conflict = cand
    best = conflict or best     # a contradiction is the most decision-relevant finding
    controls = [c for c in store.controls() if c["ruleMatter"] == rule["ruleMatter"] and rule["juris"] in c["jurisdictions"]]
    risks = [k for k in store.risks() if k["ruleMatter"] == rule["ruleMatter"]]
    issues = [i for k in risks for i in store.issues_for_risk(k["id"])]
    if best is None:
        verdict = "Gap"
    elif best["conflict"]:
        verdict = "Conflict"
    elif best["score"] >= .8:
        verdict = "Covered"
    elif best["score"] >= .5:
        verdict = "Partial"
    else:
        verdict = "Gap"
    if verdict == "Covered" and (not controls or best["reasons"]):
        verdict = "Partial"
    auto = bool(best and best["score"] >= .85 and verdict == "Covered" and any(c["testResult"] == "Effective" for c in controls))
    ob_text = f'{ob["actor"]} {ob["trigger"]} {ob["action"]}' + (f' {ob["timing"]}' if ob.get("timing") and ob["timing"].lower() not in ob["action"].lower() else "")
    pol_hits = concept_hits(best["clauseText"]) if best and best["clauseText"] else []
    return {"ruleId": rule["id"], "cite": rule["cite"], "juris": rule["juris"], "ruleTitle": rule["title"],
            "regulator": rule["regulator"], "ruleMatter": rule["ruleMatter"],
            "obligationText": ob_text, "obligationSpans": spans(ob_text, pol_hits),
            "clauseSpans": spans(best["clauseText"], concept_hits(ob_text)) if best and best["clauseText"] else [],
            "obligation": ob, "match": best, "controls": controls, "risks": risks, "issues": issues,
            "verdict": verdict, "gate": "auto" if auto else "human",
            "draft": draft_clause(rule, ob, best) if verdict != "Covered" else None}


def draft_clause(rule, ob, best) -> str:
    body = re.sub(r"^to\s+", "", ob["action"].rstrip("."))
    tm = f', {ob["timing"]}' if ob.get("timing") and ob["timing"].lower() not in body.lower() else ""
    cm = re.match(r"^((?:where|if|unless|when)\b[^,]*),\s*(.+)$", body, re.I)
    sent = f'{cm.group(1)[:1].upper()+cm.group(1)[1:]}, the Bank shall {cm.group(2)}{tm}' if cm else f"The Bank shall {body}{tm}"
    head = f'Amend §{best["clauseSec"]} of {best["policyId"]}' if best and best["clauseSec"] != "—" else "New clause"
    return f'{head}: “{sent}.” [Ref: {rule["cite"]}]'


def primary_obligation(rule, focus: Optional[List[str]] = None) -> Dict[str, Any]:
    obs = [o.model_dump() for o in obligation_service.extract(rule, limit=False)]
    def fh(o):
        return sum(1 for h in concept_hits(o["actor"] + " " + o["action"]) if h["root"] in (focus or []))
    def own_timing(o):
        return 1 if o.get("timing") and o["timing"].lower() in o["action"].lower() else 0
    return sorted(obs, key=lambda o: (-fh(o), -own_timing(o), -o["confidence"]))[0]


def map_rule(rule_id_or_cite: str, focus: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    rule = store.rule_by_id(rule_id_or_cite) or store.rule_by_cite(rule_id_or_cite)
    if not rule:
        return None
    return map_obligation(rule, primary_obligation(rule, focus), focus)
