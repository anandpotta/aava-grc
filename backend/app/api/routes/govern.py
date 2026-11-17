"""Scope, assessment, approvals (Act) and report sharing."""
from collections import defaultdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.api.deps import current, need
from app.services import access_service, actions_service as act, ask_service, assess_service, store

router = APIRouter()
PRESETS = {
    "Everything": None,
    "KYC and AML only": ["KYC and CDD", "AML / CFT", "Sanctions screening"],
    "Data and security": ["Data privacy", "Data localisation", "Cyber security", "Records and retention"],
    "Resilience and vendors": ["Operational resilience", "Outsourcing and third party"],
    "Conduct and customers": ["Consumer protection", "Complaints handling", "Conduct and culture"],
}


class Scope(BaseModel):
    rules: Optional[List[str]] = None          # None means everything
    policies: Optional[List[str]] = None
    controls: Optional[List[str]] = None


class AssessIn(BaseModel):
    subject: str = "org"
    scope: Optional[Scope] = None


class CustomItem(BaseModel):
    name: str = Field(min_length=2)
    owner: str = Field(min_length=2)
    ruleMatter: str
    jurisdictions: List[str] = Field(min_length=1)


class ShareIn(BaseModel):
    subject: str = "org"
    scope: Optional[Scope] = None
    recipients: List[str]
    access: str = "View only"
    expiresInDays: int = Field(7, ge=1, le=365)
    note: str = ""


class ActionIn(BaseModel):
    key: str
    title: str
    detail: str = ""
    approver: str = "Chief Compliance Officer"
    gate: str = "Gate 2"


class DecisionIn(BaseModel):
    decision: str


def _scope(s: Optional[Scope]):
    return s.model_dump() if s else None


# ------------------------------------------------------------------ scope
@router.get("/scope/catalog")
def catalog():
    """Rules, policies and controls grouped by rule matter, for the scope picker."""
    def group(items, fmt):
        g = defaultdict(list)
        for i in items:
            g[i["ruleMatter"]].append(fmt(i))
        return [{"matter": m, "items": v} for m, v in sorted(g.items())]
    return {
        "rules": group(store.rules(), lambda r: {"id": r["id"], "label": f'{r["cite"]} {r["title"]}', "sub": f'{r["jurisName"]} · {r["regulator"]}'}),
        "policies": group(store.policies(), lambda p: {"id": p["id"], "label": f'{p["id"]} {p["name"]}', "sub": p["owner"] + (" · added by you" if p.get("custom") else "")}),
        "controls": group(store.controls(), lambda c: {"id": c["id"], "label": f'{c["id"]} {c["name"]}', "sub": f'{c["owner"]} · {c["testResult"]}' + (" · added by you" if c.get("custom") else "")}),
        "presets": [{"name": n, "matters": m} for n, m in PRESETS.items()],
    }


def _add(kind: str, body: CustomItem):
    n = len(store.CUSTOM[kind]) + 1
    if kind == "policies":
        item = {"id": f"POL-C{n}", "name": body.name, "owner": body.owner, "version": "v1.0", "nextReview": "", "jurisdictions": body.jurisdictions, "ruleMatter": body.ruleMatter, "custom": True}
    else:
        item = {"id": f"CTRL-C{n}", "name": body.name, "owner": body.owner, "controlType": "Preventive", "automation": "Manual", "jurisdictions": body.jurisdictions,
                "ruleMatter": body.ruleMatter, "testResult": "Not tested", "custom": True}
    store.CUSTOM[kind].append(item)
    store.audit("scope.add", item["id"], {"kind": kind, "name": body.name, "owner": body.owner})
    return item


@router.post("/scope/policies", status_code=201)
def add_policy(body: CustomItem, _u=Depends(need("edit_scope"))):
    return _add("policies", body)


@router.post("/scope/controls", status_code=201)
def add_control(body: CustomItem, _u=Depends(need("edit_scope"))):
    return _add("controls", body)


@router.post("/scope/save")
def save_scope(scope: Scope, _u=Depends(need("edit_scope"))):
    n = lambda x: "everything" if x is None else len(x)
    store.audit("scope.save", "scope", {"rules": n(scope.rules), "policies": n(scope.policies), "controls": n(scope.controls)})
    return {"ok": True}


# ----------------------------------------------------------------- assess
@router.get("/assess/subjects")
def subjects():
    return assess_service.SUBJECTS


@router.post("/assess")
def assess(body: AssessIn, _u=Depends(need("run_assess"))):
    try:
        res = assess_service.assess(body.subject, _scope(body.scope))
    except KeyError:
        raise HTTPException(404, "unknown subject")
    store.audit("assess.run", body.subject, {"score": res["score"], "scoped": res["scope"]["scoped"]})
    return res


@router.post("/assess/report.html")
def report(body: AssessIn, _u=Depends(need("export"))):
    try:
        html = assess_service.report_html(body.subject, _scope(body.scope))
    except KeyError:
        raise HTTPException(404, "unknown subject")
    store.audit("report.download", body.subject, {"fingerprint": assess_service.fingerprint(html)[:12]})
    return Response(html, media_type="text/html", headers={"Content-Disposition": f'attachment; filename="aava-assessment-{body.subject}.html"'})


class FrameworkIn(BaseModel):
    framework: str
    subject: str = ""
    kind: str = "Application"
    domain: str = ""
    scope: Optional[Scope] = None


@router.get("/frameworks")
def frameworks():
    return {"frameworks": assess_service.frameworks(), "kinds": assess_service.PACKS["kinds"]}


@router.get("/domains")
def domains():
    return assess_service.domains()


@router.post("/assess/framework")
def assess_framework(body: FrameworkIn, _u=Depends(need("run_assess"))):
    try:
        res = assess_service.assess_framework(body.framework, _scope(body.scope), body.subject, body.kind, body.domain)
    except KeyError:
        raise HTTPException(404, "unknown framework")
    store.audit("assess.framework", body.framework, {"score": res["score"], "subject": body.subject, "kind": body.kind})
    return res


@router.post("/assess/framework/report.html")
def framework_report(body: FrameworkIn, _u=Depends(need("export"))):
    try:
        html = assess_service.framework_report_html(body.framework, _scope(body.scope), body.subject, body.kind, body.domain)
    except KeyError:
        raise HTTPException(404, "unknown framework")
    store.audit("report.download", body.framework, {"fingerprint": assess_service.fingerprint(html)[:12]})
    return Response(html, media_type="text/html", headers={"Content-Disposition": f'attachment; filename="aava-{body.framework}-readiness.html"'})


@router.get("/posture")
def posture():
    rep = ask_service._report()
    over = [k for k in store.risks() if ask_service.LEVEL[k["residual"]] > ask_service.LEVEL[k["appetite"]]]
    return {"coverageScore": rep["data"]["coverageScore"], "counts": rep["data"]["counts"], "risksAboveAppetite": len(over), "watches": ask_service.WATCHES}


# ------------------------------------------------------------ act + share
@router.get("/actions")
def actions():
    return act.QUEUE


@router.post("/actions", status_code=201)
def add_action(body: ActionIn, _u=Depends(need("queue_fix"))):
    return act.add(body.key, body.title, body.detail, body.approver, body.gate)


@router.post("/actions/fix-plan", status_code=201)
def fix_plan(body: AssessIn, _u=Depends(need("queue_fix"))):
    try:
        return act.queue_fixes(body.subject, _scope(body.scope))
    except KeyError:
        raise HTTPException(404, "unknown subject")


@router.post("/actions/{action_id}/decision")
def decision(action_id: str, body: DecisionIn, u=Depends(current)):
    try:
        return act.decide(action_id, body.decision, u)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except KeyError:
        raise HTTPException(404, "action not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/shares")
def shares(u=Depends(current)):
    if access_service.ROLES[u["role"]].get("room"):   # the audit room shows only what was released to this person
        return [s for s in act.SHARES if s["status"] == "sent" and u["name"] in s["to"]]
    return act.SHARES


@router.post("/shares", status_code=201)
def share(body: ShareIn, _u=Depends(need("share"))):
    try:
        return act.share(body.subject, _scope(body.scope), body.recipients, body.access, body.expiresInDays, body.note)
    except KeyError:
        raise HTTPException(404, "unknown subject")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/shares/{share_id}/verify")
def verify(share_id: str):
    try:
        return act.verify(share_id)
    except KeyError:
        raise HTTPException(404, "share not found")
