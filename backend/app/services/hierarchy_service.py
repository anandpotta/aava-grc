"""Where a rule sits: jurisdiction > regulator > instrument (title / act / handbook) > part > rule.

Navigation, search filters, breadcrumbs and validation all read this one structure.

The path is derived from the citation, and `verified` is true only where the rule also has
its source markup (the CFR rule with a clause tree), whose real Title / Volume / Chapter /
Part / Section breadcrumb is cross-checked against the derived path. The validator reports
every rule whose path cannot be trusted, so the tree is never silently wrong.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.services import rule_detail_service, store

CFR_TITLES = {"12": "Banks and Banking", "16": "Commercial Practices", "17": "Commodity and Securities Exchanges",
              "31": "Money and Finance: Treasury", "45": "Public Welfare"}

# (pattern, instrument) — first match wins. Acts and articles have no part level.
INSTRUMENTS: List[Tuple[str, str]] = [
    (r"^SYSC|^PRIN", "FCA Handbook"), (r"^PRA Rulebook", "PRA Rulebook"), (r"^MLR 2017", "Money Laundering Regulations 2017"),
    (r"^UK GDPR", "UK GDPR"), (r"^GDPR", "GDPR"), (r"^DORA", "DORA"), (r"^CRR", "CRR"), (r"^PSD2", "PSD2"),
    (r"^PCMLTFA", "PCMLTFA"), (r"^PCMLTFR", "PCMLTF Regulations"), (r"^Bank Act", "Bank Act"), (r"^Guideline [BE]", "OSFI Guidelines"),
    (r"^Master Direction", "RBI Master Directions"), (r"^(DPSS|CO\.|DOS\.|CEPD|DoR)", "RBI Circulars"), (r"^SEBI", "SEBI Circulars"),
    (r"^DPDP", "DPDP Act 2023"), (r"^PBoC|^Circular 2023", "PBoC Orders and Circulars"), (r"^PIPL", "PIPL"), (r"^DSL", "Data Security Law"),
    (r"^Commercial Bank Capital", "NFRA Rules"), (r"^AML/CFT Guidelines \(rev", "JFSA AML/CFT Guidelines"), (r"^FIEA", "FIEA"),
    (r"^APPI", "APPI"), (r"^Supervisory Guidelines", "JFSA Supervisory Guidelines"), (r"^AMLO", "AMLO"),
    (r"^AML/CFT Guideline", "HKMA AML/CFT Guideline"), (r"^SPM", "HKMA Supervisory Policy Manual"), (r"^PDPO", "PDPO"),
    (r"^Code of Conduct", "SFC Code of Conduct"), (r"^EFTA", "Electronic Financial Transactions Act"), (r"^PIPA", "PIPA"),
    (r"^AML Supervisory", "FSS Supervisory Regulations"), (r"^MAS Notice", "MAS Notices"), (r"^Outsourcing Guidelines", "MAS Guidelines"),
    (r"^SAMA", "SAMA Frameworks and Rules"), (r"^Business Continuity", "SAMA Frameworks and Rules"), (r"^Directive", "SARB Directives"),
    (r"^FIC Act", "FIC Act"), (r"^CBN", "CBN Regulations"), (r"^POPIA", "POPIA"), (r"^OCC Bulletin", "OCC Bulletins"),
]


def locate(rule: Dict[str, Any]) -> Dict[str, Any]:
    cite = rule["cite"]
    m = re.match(r"^(\d+) CFR (\d+)", cite)
    if m:
        title, part = m.group(1), m.group(2)
        return {"instrument": f"Title {title} CFR · {CFR_TITLES.get(title, '')}".strip(" ·"), "title": title, "part": f"Part {part}", "partNo": part}
    if re.match(r"^(SYSC|PRIN)", cite):
        return {"instrument": "FCA Handbook", "title": None, "part": cite.split()[0], "partNo": cite.split()[0]}
    for rx, name in INSTRUMENTS:
        if re.match(rx, cite):
            return {"instrument": name, "title": None, "part": None, "partNo": None}
    return {"instrument": f"{rule['regulator']} publications", "title": None, "part": None, "partNo": None}


def path_for(rule: Dict[str, Any]) -> List[Dict[str, str]]:
    loc = locate(rule)
    p = [{"level": "jurisdiction", "label": rule["jurisName"], "id": rule["juris"]},
         {"level": "regulator", "label": rule["regulator"], "id": f'{rule["juris"]}/{rule["regulator"]}'},
         {"level": "instrument", "label": loc["instrument"], "id": f'{rule["juris"]}/{rule["regulator"]}/{loc["instrument"]}'}]
    if loc["part"]:
        p.append({"level": "part", "label": loc["part"], "id": p[-1]["id"] + "/" + loc["part"]})
    p.append({"level": "rule", "label": cite_label(rule), "id": rule["id"]})
    return p


def cite_label(rule: Dict[str, Any]) -> str:
    return rule["cite"]


def tree(juris: Optional[str] = None) -> List[Dict[str, Any]]:
    root: Dict[str, Any] = {}
    for r in store.rules():
        if juris and r["juris"] != juris:
            continue
        cur = root
        for step in path_for(r):
            node = cur.setdefault(step["id"], {"id": step["id"], "label": step["label"], "level": step["level"], "count": 0, "_kids": {}})
            node["count"] += 1
            if step["level"] == "rule":
                node["ruleId"] = r["id"]
                node["title"] = r["title"]
            cur = node["_kids"]

    def flat(d: Dict[str, Any]) -> List[Dict[str, Any]]:
        out = []
        for n in d.values():
            kids = flat(n.pop("_kids"))
            if kids:
                n["children"] = sorted(kids, key=lambda k: (k["level"] == "rule", k["label"]))
            out.append(n)
        return out
    return sorted(flat(root), key=lambda n: n["label"])


def validate() -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    rules = store.rules()
    seen: Dict[str, str] = {}
    jur_ids = {j["id"] for j in store.jurisdictions()}
    reg_juris: Dict[str, set] = defaultdict(set)
    for r in rules:
        reg_juris[r["regulator"]].add(r["juris"])
        if r["cite"] in seen:
            findings.append({"severity": "error", "code": "duplicate_cite", "rule": r["id"], "message": f'{r["cite"]} appears twice ({seen[r["cite"]]}, {r["id"]})'})
        seen[r["cite"]] = r["id"]
        if r["juris"] not in jur_ids:
            findings.append({"severity": "error", "code": "unknown_jurisdiction", "rule": r["id"], "message": f'{r["cite"]}: jurisdiction {r["juris"]} is not defined'})
        loc = locate(r)
        if loc["instrument"].endswith("publications"):
            findings.append({"severity": "warning", "code": "instrument_not_recognised", "rule": r["id"],
                             "message": f'{r["cite"]}: no instrument pattern matched, filed under “{loc["instrument"]}”'})
        # a CFR citation must agree with its own title number
        m = re.match(r"^(\d+) CFR", r["cite"])
        if m and m.group(1) not in CFR_TITLES:
            findings.append({"severity": "warning", "code": "cfr_title_unnamed", "rule": r["id"], "message": f'{r["cite"]}: Title {m.group(1)} has no name on file'})
        # the real breadcrumb, where we have source markup
        if r.get("detailKey"):
            d = rule_detail_service.load(r["detailKey"])
            if d:
                bc = {b["level"]: b["text"] for b in d["breadcrumb"]}
                ok_title = loc["title"] and re.search(rf"\bTitle\s+{loc['title']}\b", bc.get("title", ""))
                ok_part = loc["partNo"] and re.search(rf"\b{loc['partNo']}\b", bc.get("part", ""))
                ok_sect = r["cite"].split()[-1] in d.get("section", "") or r["cite"].split()[-1] in bc.get("section", "")
                for name, ok in (("title", ok_title), ("part", ok_part), ("section", ok_sect)):
                    if not ok:
                        findings.append({"severity": "error", "code": f"breadcrumb_{name}_mismatch", "rule": r["id"],
                                         "message": f'{r["cite"]}: source breadcrumb {name} “{bc.get(name, "")}” does not match the citation'})
    for reg, js in reg_juris.items():
        if len(js) > 1:
            findings.append({"severity": "info", "code": "regulator_in_several_jurisdictions", "rule": None, "message": f"{reg} appears in {sorted(js)}"})
    verified = [r["id"] for r in rules if r.get("detailKey")]
    errs = sum(1 for f in findings if f["severity"] == "error")
    return {"ok": errs == 0, "rules": len(rules), "verifiedAgainstSource": len(verified), "derivedFromCitation": len(rules) - len(verified),
            "errors": errs, "warnings": sum(1 for f in findings if f["severity"] == "warning"), "findings": findings}


def matches(rule: Dict[str, Any], regulator: Optional[str], instrument: Optional[str], part: Optional[str]) -> bool:
    if regulator and rule["regulator"] != regulator:
        return False
    loc = locate(rule)
    if instrument and loc["instrument"] != instrument:
        return False
    if part and loc["part"] != part:
        return False
    return True
