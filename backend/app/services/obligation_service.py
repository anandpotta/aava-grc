"""Obligation extraction.

Deterministic trigger-phrase extraction with a confidence score. The point is
not that it is clever — it is that every field can be traced back to a span in
the source clause, which is what lets a reviewer sign it off and a regulator
accept it.

Replace `extract` with an LLM call when you wire the model in, but keep the
output shape: actor / action / timing / condition / trigger / confidence, plus
the deterministic checks in `validate`. Those checks are what decide whether
the agentic line continues on its own or stops at the human gate.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.models.schemas import Obligation
from app.services import store

MODALS = [
    (re.compile(r"\b(shall not|must not|may not)\b", re.I), "Prohibition", 0.97),
    (re.compile(r"\b(shall|must)\b", re.I), "Mandatory", 0.95),
    (re.compile(r"\b(is required to|are required to)\b", re.I), "Mandatory", 0.92),
    (re.compile(r"\b(should)\b", re.I), "Expectation", 0.82),
    (re.compile(r"\b(may)\b", re.I), "Permission", 0.70),
]
TIMING = [
    re.compile(r"within\s+\d+\s+(?:business\s+|calendar\s+)?(?:days?|hours?|months?|years?)", re.I),
    re.compile(r"for\s+\d+\s+months?", re.I),
    re.compile(r"no later than\s+[^,.;]{3,60}", re.I),
    re.compile(r"not later than\s+[^,.;]{3,60}", re.I),
    re.compile(r"before\s+(?:establishing|opening|entering|execution|consummation|processing)[^,.;]{0,40}", re.I),
    re.compile(r"\b(annually|quarterly|periodically|at least annually|biennial|promptly|without undue delay|as soon as practicable|without delay|at all times|ongoing)\b", re.I),
    re.compile(r"by\s+(?:May|June|January|\d{4})[^,.;]{0,20}", re.I),
]
ACTOR = re.compile(
    r"\b((?:a|an|the|every|all)?\s*(?:bank|banking organisation|covered bank|financial institution|"
    r"authorised institution|licensed person|regulated entit\w*|reporting entity|accountable institution|"
    r"institution|firm|creditor|registrant|controller|processor|data fiduciary|personal information handler|"
    r"personal information controller|member organisation|payment service provider|system provider|"
    r"covered entity|relevant person|commercial banks?|financial compan\w*|"
    r"financial instruments business operator|management|responsible party|data user|person|entities|entity|"
    r"insurer|company)\w*)",
    re.I,
)
ACTION_VERBS = re.compile(
    r"\b(verify|identify|report|notify|maintain|implement|establish|conduct|retain|screen|assess|disclose|"
    r"appoint|submit|approve|monitor|test|preserve|document|designate|review|file|apply|secure|encrypt|"
    r"store|classify|investigate)\b",
    re.I,
)


def _segments(text: str) -> List[str]:
    out: List[str] = []
    for sentence in re.split(r"(?<=[.;])\s+", text):
        if len(sentence.strip()) <= 25:
            continue
        for part in re.split(r",\s+and\s+|;\s+and\s+|,\s+shall\s+", sentence):
            if len(part.strip()) > 22:
                out.append(part.strip())
    return out


def extract(rule: Dict[str, Any], limit: bool = True) -> List[Obligation]:
    text = rule["text"]
    segs = _segments(text)
    out: List[Obligation] = []
    for i, seg in enumerate(segs):
        modal = next((m for m in MODALS if m[0].search(seg)), None)
        if modal is None and i > 0:
            # a continuation of the sentence's main duty ("... and where there is X, take ...")
            first = re.split(r"(?<=[.;])\s+", text)[0]
            modal = next((m for m in MODALS if m[0].search(first)), MODALS[1])
        if modal is None:
            continue
        rx, kind, weight = modal
        tm_ = rx.search(seg) or rx.search(text)
        trigger = tm_.group(0) if tm_ else ""

        am = ACTOR.search(seg) or ACTOR.search(text)
        actor = am.group(1).strip() if am else "Regulated entity"
        actor = re.sub(r"^(a|an|the|every|all)\s+", "", actor, flags=re.I)
        actor = actor[:1].upper() + actor[1:]

        action = re.sub(
            r"^.*?\b(shall not|must not|may not|shall|must|should|may|is required to|are required to)\b\s*",
            "",
            seg,
            flags=re.I,
        ).strip()
        if len(action) > 180:
            action = re.sub(r"\s\S*$", "", action[:177]) + "…"

        timing: Optional[str] = None
        for t in TIMING:
            m = t.search(seg) or t.search(text)
            if m:
                timing = m.group(0)
                break
        cm = re.search(r"\b(where|if|unless|in the event of|prior to|when)\b[^,.;]{5,70}", seg, re.I)

        conf = int(round((weight - (0.0 if timing else 0.04) - i * 0.015) * 100))
        out.append(
            Obligation(
                id=f'{rule["id"].replace("RUL", "OBL")}-{len(out) + 1}',
                ruleId=rule["id"],
                cite=rule["cite"],
                juris=rule["juris"],
                ruleMatter=rule["ruleMatter"],
                kind=kind,
                actor=actor,
                action=action,
                timing=timing,
                condition=cm.group(0) if cm else None,
                trigger=trigger,
                keyPhrases=sorted({m.group(0).lower() for m in ACTION_VERBS.finditer(action)})[:4],
                confidence=max(40, min(99, conf)),
            )
        )
    capped = out[: max(2, min(len(out), rule.get("obligationCount", len(out)) or len(out)))] if limit else out
    for ob in capped:
        state = store.OBLIGATION_STATE.get(ob.id)
        if state:
            ob.status = state.get("status", ob.status)
            ob.approvedBy = state.get("approvedBy")
            ob.approvedAt = state.get("approvedAt")
    return capped


def validate(ob: Obligation) -> Dict[str, Any]:
    """Deterministic checks. All green + high confidence => no human gate."""
    checks = {
        "citationPresent": bool(ob.cite),
        "actorPresent": ob.actor.lower() not in ("", "regulated entity"),
        "modalPresent": bool(ob.trigger),
        "actionLongEnough": len(ob.action) > 20,
        "timingPresentIfDeadlineLanguage": True,
    }
    if re.search(r"\b(within|no later than|not later than)\b", ob.action, re.I) and not ob.timing:
        checks["timingPresentIfDeadlineLanguage"] = False
    passed = all(checks.values())
    return {
        "checks": checks,
        "passed": passed,
        "gate": "auto" if passed and ob.confidence >= 90 else "human",
    }


def for_rules(rule_ids: List[str]) -> List[Obligation]:
    out: List[Obligation] = []
    for rid in rule_ids:
        rule = store.rule_by_id(rid)
        if rule:
            out.extend(extract(rule))
    return out


def approve(ob_id: str, actor: str = "demo.user") -> Dict[str, Any]:
    from datetime import datetime, timezone

    state = {
        "status": "Approved",
        "approvedBy": actor,
        "approvedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    store.OBLIGATION_STATE[ob_id] = state
    store.audit("obligation.approve", ob_id, state)
    return state
