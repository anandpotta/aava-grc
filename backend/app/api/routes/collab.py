"""Stakeholders, notifications, threads and approvals."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import current, need
from app.services import change_service, collaboration_service as cs

router = APIRouter()


class CommentIn(BaseModel):
    authorId: str
    text: str


class ApprovalIn(BaseModel):
    gate: str = "gate3"
    summary: str = ""


class DecisionIn(BaseModel):
    approverId: str
    decision: str          # approve | reject | changes
    note: str = ""


@router.get("/stakeholders")
def stakeholders():
    return cs.stakeholders()


@router.get("/changes/{change_id}/routing")
def routing(change_id: str):
    imp = change_service.impact(change_id)
    if not imp:
        raise HTTPException(404, "change not found")
    return [{"stakeholder": r["stakeholder"], "raci": r["raci"], "raciText": cs.RACI_TEXT[r["raci"]], "reasons": list(dict.fromkeys(r["reasons"])), "items": list(dict.fromkeys(r["items"]))}
            for r in cs.routing(imp)]


@router.post("/changes/{change_id}/notify", status_code=201)
def notify(change_id: str, _u=Depends(need("notify"))):
    try:
        return cs.notify_change(change_id)
    except KeyError:
        raise HTTPException(404, "change not found")


@router.get("/notifications")
def notifications(changeId: Optional[str] = None, to: Optional[str] = None):
    return [n for n in cs.NOTIFS if (not changeId or n["changeId"] == changeId) and (not to or n["to"]["id"] == to)]


@router.post("/notifications/{nid}/ack")
def ack(nid: str, _u=Depends(need("ack"))):
    try:
        return cs.acknowledge(nid)
    except KeyError:
        raise HTTPException(404, "notification not found")


@router.post("/changes/{change_id}/escalate")
def escalate(change_id: str, hoursAhead: float = 0, _u=Depends(need("notify"))):
    return cs.escalate(change_id, hoursAhead)


@router.get("/changes/{change_id}/coordination")
def coordination(change_id: str):
    return {**cs.thread(change_id), "status": cs.status(change_id)}


@router.post("/threads/{subject}/comments", status_code=201)
def comment(subject: str, body: CommentIn, u=Depends(need("comment"))):
    if body.authorId != u["id"]:
        raise HTTPException(403, f'You are acting as {u["name"]}. You can only comment as yourself.')
    try:
        return cs.comment(subject, body.authorId, body.text)
    except KeyError:
        raise HTTPException(404, "unknown author")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/threads/{subject}/approval", status_code=201)
def request_approval(subject: str, body: ApprovalIn, _u=Depends(need("queue_fix"))):
    try:
        return cs.request_approval(subject, body.gate, body.summary)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/threads/{subject}/decision")
def decide(subject: str, body: DecisionIn, u=Depends(need("approve"))):
    if body.approverId != u["id"]:
        raise HTTPException(403, f'You are acting as {u["name"]}. Only {body.approverId} can record their own decision.')
    try:
        return cs.decide(subject, body.approverId, body.decision, body.note)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
