"""Ask AAVA — chat orchestration and the clause-level mapping it is built on."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import ask_service, semantic_map_service, store

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    mode: str = "Ask"          # Ask | Act | Watch


class ApproveRequest(BaseModel):
    runId: str
    gate: str                  # gate1 | gate2 | gate3
    subject: str


class MapRequest(BaseModel):
    ruleId: str
    focus: Optional[List[str]] = None


@router.post("/ask")
def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(400, "empty question")
    return ask_service.run(req.question, req.mode)


@router.post("/ask/approve")
def approve(req: ApproveRequest):
    return ask_service.approve(req.runId, req.gate, req.subject)


@router.get("/ask/scenarios")
def scenarios():
    return [
        {"id": "map", "title": "Does our policy cover this rule?", "q": "Do our policies cover beneficial ownership verification in the US, UK and Hong Kong?"},
        {"id": "report", "title": "Generate the compliance report", "q": "Generate the compliance report for our cross-border banking rulebook."},
        {"id": "change", "title": "A regulator changed the rule", "q": "What changed at the HKMA and what do we need to do?"},
        {"id": "issue", "title": "Fix a Critical issue at the root", "q": "We have a Critical issue: payment tokens replicated to a non-Indian DR region. How do we fix it?"},
        {"id": "risks", "title": "Which risks are above appetite?", "q": "Which risks are above appetite and what should we do first?"},
        {"id": "coordinate", "title": "Tell the right people and get sign-off", "q": "Who needs to be told about the HKMA change and who must sign it off?"},
        {"id": "assess", "title": "Assess anything against industry standards", "q": "Assess our payments platform against industry standards and tell me what is not compliant."},
        {"id": "watch", "title": "Watch for changes", "q": "Tell me when any AML rule changes in the US, UK or Hong Kong."},
    ]


@router.post("/map/obligation")
def map_obligation(req: MapRequest):
    m = semantic_map_service.map_rule(req.ruleId, req.focus)
    if not m:
        raise HTTPException(404, "rule not found")
    return m


@router.get("/policies/{policy_id}/clauses")
def policy_clauses(policy_id: str):
    return store.policy_clauses().get(policy_id, [])
