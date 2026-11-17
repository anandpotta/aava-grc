"""Regulatory search: keyword + citation + semantic expansion.

The scoring is deliberately simple and explainable — a compliance analyst has
to be able to say *why* a rule surfaced. Swap `_score` for a vector search
against the regulatory corpus when the embedding index is in place; keep the
`hits` list, because that is what drives the highlighting and the keyword map.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from app.models.schemas import (
    ConceptExpansion,
    KeywordNode,
    Rule,
    SearchHit,
    SearchResponse,
)
from app.services import store

STOP = set(
    "a an the of for and or to in on at by with must shall should is are be from any "
    "each all its their this that which not no as if we i it".split()
)


def tokenise(q: str) -> List[str]:
    q = (q or "").lower()
    q = re.sub(r"[^a-z0-9 \-/\.]", " ", q)
    return [t for t in q.split() if len(t) > 2 and t not in STOP]


def expand(q: str) -> List[ConceptExpansion]:
    ql = (q or "").lower()
    out: List[ConceptExpansion] = []
    for root, terms in store.semantic().items():
        if root in ql or any(t in ql for t in terms):
            out.append(ConceptExpansion(root=root, terms=terms))
    return out


def _score(rule: Dict[str, Any], words: List[str], phrases: List[str]):
    title = rule["title"].lower()
    text = rule["text"].lower()
    matter = rule["ruleMatter"].lower()
    ident = f'{rule["cite"]} {rule["regulator"]}'.lower()
    score = 0.0
    hits: set = set()
    for w in words:
        if w in title:
            score += 3.0
            hits.add(w)
        if w in text:
            score += 1.0
            hits.add(w)
        if w in matter:
            score += 2.0
            hits.add(w)
        if w in ident:
            score += 2.5
            hits.add(w)
    for p in phrases:
        if p in title or p in text:
            score += 1.6
            hits.add(p)
    return score, sorted(hits)


def search(
    q: str = "",
    juris: Optional[str] = None,
    framework: Optional[str] = None,
    rule_matter: Optional[str] = None,
    rule_type: Optional[str] = None,
    limit: int = 200,
    regulator: Optional[str] = None,
    instrument: Optional[str] = None,
    part: Optional[str] = None,
) -> SearchResponse:
    pool = store.rules()
    if juris:
        pool = [r for r in pool if r["juris"] == juris]
    if framework:
        pool = [r for r in pool if framework in r.get("frameworks", [])]
    if rule_matter:
        pool = [r for r in pool if r["ruleMatter"] == rule_matter]
    if rule_type:
        pool = [r for r in pool if r["ruleType"] == rule_type]

    if regulator or instrument or part:
        from app.services import hierarchy_service
        pool = [r for r in pool if hierarchy_service.matches(r, regulator, instrument, part)]

    concepts = expand(q)
    phrases = [c.root for c in concepts] + [t for c in concepts for t in c.terms]
    words = sorted(
        {*tokenise(q), *[w for p in phrases for w in p.split() if len(w) > 2]}
    )

    scored: List[SearchHit] = []
    if not words:
        for r in sorted(pool, key=lambda x: x["effectiveDate"], reverse=True):
            scored.append(SearchHit(rule=Rule(**_rule_payload(r)), score=1.0, hits=[]))
    else:
        for r in pool:
            s, hits = _score(r, words, phrases)
            if s > 0:
                scored.append(SearchHit(rule=Rule(**_rule_payload(r)), score=round(s, 2), hits=hits))
        scored.sort(key=lambda h: (-h.score, h.rule.juris))

    scored = scored[:limit]

    freq = Counter()
    for h in scored:
        for t in h.hits:
            freq[t] += 1
    top = freq.most_common(11)
    peak = top[0][1] if top else 0
    keyword_map = [
        KeywordNode(term=t, count=c, primary=bool(peak and c >= peak * 0.7))
        for t, c in top
    ]

    facets = {
        "juris": dict(Counter(h.rule.juris for h in scored)),
        "ruleMatter": dict(Counter(h.rule.ruleMatter for h in scored)),
        "ruleType": dict(Counter(h.rule.ruleType for h in scored)),
    }
    return SearchResponse(
        total=len(scored),
        results=scored,
        keywordMap=keyword_map,
        concepts=concepts,
        facets=facets,
    )


def _rule_payload(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": r["id"],
        "juris": r["juris"],
        "jurisName": r.get("jurisName", ""),
        "regulator": r["regulator"],
        "cite": r["cite"],
        "title": r["title"],
        "ruleType": r["ruleType"],
        "ruleMatter": r["ruleMatter"],
        "effectiveDate": r["effectiveDate"],
        "text": r["text"],
        "severity": r.get("severity", "Medium"),
        "obligationCount": r.get("obligationCount", 0),
        "frameworks": r.get("frameworks", []),
    }
