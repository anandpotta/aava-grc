"""Reference data, search, rulebooks, obligations and the library."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import need

from app.models.schemas import (
    Control,
    Obligation,
    Policy,
    Risk,
    Issue,
    Rule,
    Rulebook,
    RulebookCreate,
    SearchResponse,
)
from app.services import hierarchy_service, obligation_service, rule_detail_service, search_service, store

router = APIRouter()


# ----------------------------------------------------------------- reference
@router.get("/reference")
def reference():
    tax = store.taxonomy()
    return {
        "jurisdictions": store.jurisdictions(),
        "frameworks": store.frameworks(),
        "ruleMatters": tax["ruleMatters"],
        "ruleTypes": tax["ruleTypes"],
        "domains": [
            {"id": "banking", "label": "Banking", "enabled": True},
            {"id": "privacy", "label": "Privacy", "enabled": False},
        ],
        "counts": {
            "rules": len(store.rules()),
            "controls": len(store.controls()),
            "policies": len(store.policies()),
            "risks": len(store.risks()),
            "issues": len(store.issues()),
        },
    }


# -------------------------------------------------------------------- search
@router.get("/search", response_model=SearchResponse)
def search(
    q: str = "",
    juris: Optional[str] = None,
    framework: Optional[str] = None,
    ruleMatter: Optional[str] = None,
    ruleType: Optional[str] = None,
    limit: int = Query(200, le=500),
    regulator: Optional[str] = None,
    instrument: Optional[str] = None,
    part: Optional[str] = None,
):
    return search_service.search(q, juris, framework, ruleMatter, ruleType, limit, regulator, instrument, part)


# ----------------------------------------------------------------- hierarchy
@router.get("/hierarchy")
def hierarchy(juris: Optional[str] = None):
    """jurisdiction > regulator > instrument > part > rule, with counts. Drives the side nav."""
    return hierarchy_service.tree(juris)


@router.get("/hierarchy/validate")
def hierarchy_validate():
    return hierarchy_service.validate()


@router.get("/rules/{rule_id}/path")
def rule_path(rule_id: str):
    r = store.rule_by_id(rule_id)
    if not r:
        raise HTTPException(404, "rule not found")
    return hierarchy_service.path_for(r)


# --------------------------------------------------------------------- rules
@router.get("/rules/{rule_id}", response_model=Rule)
def get_rule(rule_id: str):
    r = store.rule_by_id(rule_id)
    if not r:
        raise HTTPException(404, "rule not found")
    return Rule(**search_service._rule_payload(r))


@router.get("/rules/{rule_id}/detail")
def rule_detail(rule_id: str):
    """Clause-level detail: breadcrumb, part authority, clause tree, history.

    Falls back to a single synthetic clause for rules that have no source HTML
    yet, so the client only has to implement one view.
    """
    rule = store.rule_by_id(rule_id)
    if not rule:
        raise HTTPException(404, "rule not found")
    key = rule.get("detailKey")
    detail = rule_detail_service.load(key) if key else None
    if detail:
        detail = {**detail, "ruleId": rule_id, "ruleTitle": rule["title"]}
        return detail
    return {
        "id": rule_id,
        "ruleId": rule_id,
        "ruleTitle": rule["title"],
        "cite": rule["cite"],
        "section": rule["cite"],
        "breadcrumb": [
            {"level": "title", "depth": 0, "text": rule["jurisName"], "href": None},
            {"level": "chapter", "depth": 1, "text": rule["regulator"], "href": None},
            {"level": "part", "depth": 2, "text": rule["ruleMatter"], "href": None},
            {"level": "section", "depth": 3, "text": rule["cite"], "href": None},
        ],
        "authority": {"text": rule["regulator"], "links": []},
        "clauses": [
            {
                "id": f'{rule_id}_a',
                "path": "a",
                "depth": 0,
                "label": "",
                "text": rule["text"],
                "flagged": False,
                "links": [],
                "spans": rule_detail_service._spans(rule["text"]),
                "childIds": [],
                "parentId": None,
            }
        ],
        "amendmentHistory": [f'Effective {rule["effectiveDate"]}'],
        "stats": {"clauses": 1, "dutyClauses": 1, "flagged": 0, "maxDepth": 0},
        "synthetic": True,
    }


@router.get("/rules/{rule_id}/detail/clause/{clause_id:path}/family")
def clause_family(rule_id: str, clause_id: str):
    rule = store.rule_by_id(rule_id)
    if not rule:
        raise HTTPException(404, "rule not found")
    detail = rule_detail_service.load(rule.get("detailKey") or "")
    if not detail:
        raise HTTPException(404, "no clause tree for this rule")
    return rule_detail_service.clause_family(detail, clause_id)


# ----------------------------------------------------------------- rulebooks
@router.get("/rulebooks", response_model=List[Rulebook])
def list_rulebooks():
    out = []
    for b in store.RULEBOOKS:
        b["obligationCount"] = len(obligation_service.for_rules(b["ruleIds"]))
        out.append(Rulebook(**b))
    return out


@router.post("/rulebooks", response_model=Rulebook, status_code=201)
def create_rulebook(payload: RulebookCreate):
    if not payload.ruleIds:
        raise HTTPException(400, "pin at least one rule")
    book = store.add_rulebook(payload.name, payload.scope, payload.ruleIds)
    book["obligationCount"] = len(obligation_service.for_rules(book["ruleIds"]))
    return Rulebook(**book)


@router.get("/rulebooks/{book_id}", response_model=Rulebook)
def get_rulebook(book_id: str):
    b = store.rulebook_by_id(book_id)
    if not b:
        raise HTTPException(404, "rulebook not found")
    b["obligationCount"] = len(obligation_service.for_rules(b["ruleIds"]))
    return Rulebook(**b)


@router.post("/rulebooks/seed", response_model=Rulebook, status_code=201)
def seed_rulebook():
    """One-click cross-border rulebook, so the map can be demonstrated
    without searching and pinning first."""
    want = [
        ("us", "KYC and CDD"), ("uk", "KYC and CDD"), ("hk", "KYC and CDD"), ("in", "KYC and CDD"),
        ("us", "AML / CFT"), ("hk", "AML / CFT"), ("cn", "AML / CFT"),
        ("uk", "Operational resilience"), ("hk", "Operational resilience"), ("eu", "Operational resilience"),
        ("in", "Outsourcing and third party"), ("ca", "Outsourcing and third party"),
        ("in", "Data localisation"), ("cn", "Data localisation"),
        ("uk", "Data privacy"), ("us", "Data privacy"),
        ("uk", "Consumer protection"), ("in", "Cyber security"),
        ("us", "Records and retention"),
    ]
    ids: List[str] = []
    for j, m in want:
        r = next((x for x in store.rules() if x["juris"] == j and x["ruleMatter"] == m and x["id"] not in ids), None)
        if r:
            ids.append(r["id"])
    book = store.add_rulebook("Cross-border banking rulebook 2027",
                              "Retail bank and payments · US, UK, EU, CA, IN, CN, HK", ids)
    book["obligationCount"] = len(obligation_service.for_rules(ids))
    return Rulebook(**book)


# --------------------------------------------------------------- obligations
@router.get("/obligations", response_model=List[Obligation])
def obligations(rulebookId: Optional[str] = None, ruleId: Optional[str] = None):
    if ruleId:
        rule = store.rule_by_id(ruleId)
        if not rule:
            raise HTTPException(404, "rule not found")
        return obligation_service.extract(rule)
    if rulebookId:
        book = store.rulebook_by_id(rulebookId)
        if not book:
            raise HTTPException(404, "rulebook not found")
        return obligation_service.for_rules(book["ruleIds"])
    ids = [rid for b in store.RULEBOOKS for rid in b["ruleIds"]]
    return obligation_service.for_rules(sorted(set(ids)))


@router.get("/obligations/{ob_id}/validate")
def validate_obligation(ob_id: str):
    rule_id = ob_id.replace("OBL", "RUL").rsplit("-", 1)[0]
    rule = store.rule_by_id(rule_id)
    if not rule:
        raise HTTPException(404, "obligation not found")
    ob = next((o for o in obligation_service.extract(rule) if o.id == ob_id), None)
    if not ob:
        raise HTTPException(404, "obligation not found")
    return obligation_service.validate(ob)


@router.post("/obligations/{ob_id}/approve")
def approve_obligation(ob_id: str):
    return obligation_service.approve(ob_id)


# ------------------------------------------------------------------- library
@router.get("/controls", response_model=List[Control])
def controls(ruleMatter: Optional[str] = None, juris: Optional[str] = None):
    out = store.controls()
    if ruleMatter:
        out = [c for c in out if c["ruleMatter"] == ruleMatter]
    if juris:
        out = [c for c in out if juris in c["jurisdictions"]]
    return out


@router.get("/policies", response_model=List[Policy])
def policies(ruleMatter: Optional[str] = None, juris: Optional[str] = None):
    out = store.policies()
    if ruleMatter:
        out = [p for p in out if p["ruleMatter"] == ruleMatter]
    if juris:
        out = [p for p in out if juris in p["jurisdictions"]]
    return out


@router.get("/risks", response_model=List[Risk])
def risks():
    return store.risks()


@router.get("/issues", response_model=List[Issue])
def issues(riskId: Optional[str] = None):
    return store.issues_for_risk(riskId) if riskId else store.issues()


@router.get("/sources")
def content_sources(juris: Optional[str] = None, licence: Optional[str] = None):
    """Where the regulatory corpus and the control library come from.

    This is the content engine's plan of record. Filter by `juris` to see what
    a jurisdiction pack costs to build, or by `licence` to find everything that
    needs a permission request or a purchase before it can be ingested.
    """
    data = store.sources()
    reg = data["regulatory"]
    if juris:
        reg = [s for s in reg if s["juris"] == juris]
    if licence:
        reg = [s for s in reg if s["licence"] == licence]
    frameworks = data["controlFrameworks"]
    if licence:
        frameworks = [f for f in frameworks if f["licence"] == licence]
    return {
        "regulatory": reg,
        "controlFrameworks": frameworks,
        "clientSide": data["clientSide"],
        "commercialProviders": data["commercialProviders"],
        "licenceMeanings": data["_licence_values"],
        "summary": {
            "regulatorySources": len(reg),
            "verified": sum(1 for s in reg if s.get("verified")),
            "machineReadable": sum(1 for s in reg if s["access"] in ("rest-api", "sparql")),
            "crawlRequired": sum(1 for s in reg if s["access"] == "crawl"),
            "permissionRequired": sum(1 for s in reg if s["licence"] == "permission-required"),
            "licensedFrameworks": sum(1 for f in frameworks if f["licence"] == "licensed"),
        },
    }


@router.get("/audit/verify")
def audit_verify(_u=Depends(need("verify_audit"))):
    return store.verify_audit()


@router.get("/audit")
def audit_trail(limit: int = 200):
    return store.AUDIT[-limit:][::-1]
