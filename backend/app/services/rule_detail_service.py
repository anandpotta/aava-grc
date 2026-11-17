"""Clause-level rule detail.

Your current rule-detail page ships a blob of HTML and re-implements the
hierarchy in jQuery by string-matching dotted element ids. That works, but the
structure only exists in the DOM, so nothing else in the platform can use it.

This module parses the same markup once, on the server, into a **clause tree**:

    12:8.0.2.1.3.0.1.12_b            (b) Preservation of records
      12:8.0.2.1.3.0.1.12_b.1        (1) Applications. For 25 months ...
        12:8.0.2.1.3.0.1.12_b.1.i    (i) Any application that it receives ...

Once the tree exists on the server the same clause id becomes the anchor for
everything else:

* an obligation points at the exact clause it was extracted from;
* a compliance-map node can be a clause rather than a whole section;
* a regulatory change diffs clause-by-clause instead of document-by-document;
* a rulebook can pin one sub-clause instead of the whole rule.

It also enriches each clause with things the HTML only implies:

* ``depth`` and ``childIds`` so the client never has to string-match ids;
* detected **trigger phrases** (shall / must / within 25 months ...) with their
  character offsets, which is what the obligation extractor keys on;
* detected **cross references** (§ 1002.5(a)(4)) turned into jump targets;
* the part authority and the amendment history parsed out of the footer.
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import DATA_DIR

RULE_HTML_DIR = DATA_DIR / "rule_html"

_DIV_RE = re.compile(
    r'<div\s+id="(?P<id>[^"]+)"\s+class="(?P<cls>ruleDetailList[^"]*)"\s*'
    r'style="padding-left:(?P<pad>\d+)px"\s*>(?P<body>.*?)</div>',
    re.S,
)
_HDR_RE = re.compile(
    r'<div\s+style="padding-left:(?P<pad>\d+)px"\s*>(?P<body>.*?)</div>', re.S
)
_A_RE = re.compile(r'<a\s+href="(?P<href>[^"]*)"[^>]*>(?P<text>.*?)</a>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_CITA_RE = re.compile(r"\[(?P<body>[^\]]*FR[^\]]*)\]")

# Phrases that create a duty. Order matters: the longest/strongest first.
TRIGGERS: List[tuple] = [
    (re.compile(r"\b(shall not|must not|may not|is prohibited from)\b", re.I), "Prohibition"),
    (re.compile(r"\b(shall|must)\b", re.I), "Mandatory"),
    (re.compile(r"\b(is required to|are required to)\b", re.I), "Mandatory"),
    (re.compile(r"\b(should)\b", re.I), "Expectation"),
    (re.compile(r"\b(may)\b", re.I), "Permission"),
]
TIMING = re.compile(
    r"(for\s+\d+\s+months?|within\s+\d+\s+(?:business\s+|calendar\s+)?(?:days?|hours?|months?|years?)"
    r"|no later than[^,.;]{3,60}|not later than[^,.;]{3,60}|prior to[^,.;]{3,50}"
    r"|annually|quarterly|periodically|promptly|without undue delay|at all times)",
    re.I,
)
XREF = re.compile(r"§+\s*[\d]+\.[\d]+(?:\([a-z0-9]+\))*", re.I)
USC = re.compile(r"\b\d+\s+U\.S\.C\.\s+[\d]+[a-z]?\b")


def _text_of(fragment: str) -> str:
    return html.unescape(_TAG_RE.sub("", fragment)).strip()


def _links_of(fragment: str) -> List[Dict[str, str]]:
    return [
        {"href": m.group("href"), "text": _text_of(m.group("text"))}
        for m in _A_RE.finditer(fragment)
    ]


def _spans(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """Character offsets the client highlights without re-scanning the text."""
    out: Dict[str, List[Dict[str, Any]]] = {"trigger": [], "timing": [], "xref": []}
    for rx, kind in TRIGGERS:
        m = rx.search(text)
        if m:
            out["trigger"].append(
                {"start": m.start(), "end": m.end(), "text": m.group(0), "kind": kind}
            )
            break
    for m in TIMING.finditer(text):
        out["timing"].append({"start": m.start(), "end": m.end(), "text": m.group(0)})
    for m in list(XREF.finditer(text)) + list(USC.finditer(text)):
        out["xref"].append({"start": m.start(), "end": m.end(), "text": m.group(0)})
    return out


def _label_of(text: str) -> str:
    """'(b)  Preservation of records -' -> '(b)'."""
    m = re.match(r"\s*(\([a-z0-9ivx]+\))", text, re.I)
    return m.group(1) if m else ""


def parse_rule_html(raw: str, rule_id: str = "", cite: str = "") -> Dict[str, Any]:
    """Turn one rule-detail HTML document into a structured record."""
    # ---- breadcrumb -------------------------------------------------------
    breadcrumb: List[Dict[str, Any]] = []
    # Everything between the header marker and whatever comes next (the part
    # authority block, or the first <br>). Matching on the closing </div> pair
    # loses the last level, because its </div> doubles as the block terminator.
    head_block = ""
    hm = re.search(r'class="ruleDetailsHeaderPart"\s*>(.*)', raw, re.S)
    if hm:
        tail = hm.group(1)
        stop = len(tail)
        for marker in ("partAuthorityHeaderPart", "<br>", "<br/>", "<br />"):
            pos = tail.find(marker)
            if pos != -1:
                stop = min(stop, pos)
        head_block = tail[:stop]
    levels = ["title", "volume", "chapter", "part", "section"]
    for i, hm in enumerate(_HDR_RE.finditer(head_block)):
        txt = _text_of(hm.group("body"))
        if not txt:
            continue
        links = _links_of(hm.group("body"))
        depth = int(hm.group("pad")) // 20
        breadcrumb.append(
            {
                "level": levels[min(depth, len(levels) - 1)],
                "depth": depth,
                "text": txt,
                "href": links[0]["href"] if links else None,
            }
        )
        if len(breadcrumb) >= 5:
            break

    # ---- part authority ---------------------------------------------------
    authority: Dict[str, Any] = {"text": "", "links": []}
    am = re.search(r'class="partAuthorityHeaderPart".*?>(.*?)</div>\s*</div>', raw, re.S)
    if am:
        authority = {
            "text": _text_of(am.group(1)).replace("Part Authority:", "").strip(),
            "links": _links_of(am.group(1)),
        }

    # ---- clauses ----------------------------------------------------------
    clauses: List[Dict[str, Any]] = []
    for cm in _DIV_RE.finditer(raw):
        cid = cm.group("id")
        body = cm.group("body")
        text = _text_of(body)
        if not text:
            continue
        pad = int(cm.group("pad"))
        suffix = cid.split("_", 1)[1] if "_" in cid else cid
        clauses.append(
            {
                "id": cid,
                "path": suffix,
                "depth": pad // 20,
                "label": _label_of(text),
                "text": text,
                "flagged": "bg-warning" in cm.group("cls"),
                "links": _links_of(body),
                "spans": _spans(text),
                "childIds": [],
                "parentId": None,
            }
        )

    # parent / child wiring from the dotted path — done once, on the server
    by_path = {c["path"]: c for c in clauses}
    for c in clauses:
        parent_path = c["path"].rsplit(".", 1)[0] if "." in c["path"] else None
        if parent_path and parent_path in by_path:
            c["parentId"] = by_path[parent_path]["id"]
            by_path[parent_path]["childIds"].append(c["id"])

    # ---- amendment history ------------------------------------------------
    history: List[str] = []
    for hm in _CITA_RE.finditer(raw):
        body = _text_of(hm.group("body"))
        if body and body not in history:
            history.append(body)

    section = breadcrumb[-1]["text"] if breadcrumb else cite
    duties = sum(1 for c in clauses if c["spans"]["trigger"])
    return {
        "id": rule_id or (clauses[0]["id"].split("_")[0] if clauses else "rule"),
        "cite": cite or section,
        "section": section,
        "breadcrumb": breadcrumb,
        "authority": authority,
        "clauses": clauses,
        "amendmentHistory": history,
        "stats": {
            "clauses": len(clauses),
            "dutyClauses": duties,
            "flagged": sum(1 for c in clauses if c["flagged"]),
            "maxDepth": max([c["depth"] for c in clauses], default=0),
        },
    }


def clause_family(detail: Dict[str, Any], clause_id: str) -> Dict[str, List[str]]:
    """Ancestors and descendants of a clause.

    This replaces the jQuery ``startsWith`` loop. Because the tree is already
    wired, the answer is exact: ``_b.1.i`` is a child of ``_b.1`` but ``_b.1.ii``
    never matches ``_b.1.i``.
    """
    by_id = {c["id"]: c for c in detail["clauses"]}
    if clause_id not in by_id:
        return {"ancestors": [], "descendants": [], "family": []}
    ancestors: List[str] = []
    cur = by_id[clause_id].get("parentId")
    while cur:
        ancestors.append(cur)
        cur = by_id[cur].get("parentId") if cur in by_id else None
    descendants: List[str] = []
    stack = list(by_id[clause_id]["childIds"])
    while stack:
        cid = stack.pop()
        descendants.append(cid)
        stack.extend(by_id[cid]["childIds"])
    return {
        "ancestors": ancestors,
        "descendants": descendants,
        "family": ancestors + [clause_id] + descendants,
    }


_CACHE: Dict[str, Dict[str, Any]] = {}


def available() -> List[Dict[str, str]]:
    return [
        {"key": p.stem, "file": p.name}
        for p in sorted(RULE_HTML_DIR.glob("*.html"))
    ]


def load(key: str) -> Optional[Dict[str, Any]]:
    if key in _CACHE:
        return _CACHE[key]
    path = RULE_HTML_DIR / f"{key}.html"
    if not path.exists():
        return None
    detail = parse_rule_html(path.read_text(encoding="utf-8"), rule_id=key)
    _CACHE[key] = detail
    return detail
