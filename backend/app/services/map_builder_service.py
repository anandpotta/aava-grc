"""Build a compliance map from a rulebook.

The output is emitted in exactly the dataset contract your existing maps use
(a list of layers, each node carrying `other_kps_ds2`), so a generated map and
an imported one are rendered by the same engine and exported by the same code.

Layers: Rules -> Obligations -> Policies -> Controls -> Risks -> Issues

Scoring is explainable on purpose, because a reviewer has to accept or reject
each proposed mapping:

    0.50  the policy/control addresses the same rule matter
   +0.25  it is deployed in the rule's jurisdiction
   +0.10  the control was tested and found effective
   +0.05  the control is automated

A policy or control that addresses the matter but is **not deployed in that
jurisdiction** produces no link at all. That is deliberate: it is the single
most common real gap, and burying it as a weak match hides it.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services import obligation_service, store
from app.services.sankey_service import ComplianceGraph, register

LVL = {"Zero": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def _node(ds_index: int, idx: int, uid: str, name: str, prefix: str, ntype: str,
          quote: str, impacted: bool = False, match: str = "") -> Dict[str, Any]:
    return {
        "dsName": name,
        "unique_id": uid,
        "type": ntype,
        "quote": quote,
        "prefix": prefix,
        "dataSourceIndex": ds_index,
        "node": idx,
        "impactedRule": impacted,
        "match": match,
        "other_kps_ds2": [],
    }


def _band_name(v: float) -> str:
    if v >= 0.75:
        return "Strong"
    if v >= 0.60:
        return "Partial"
    if v >= 0.40:
        return "Minimal"
    return ""


def build(
    map_id: str,
    name: str,
    rule_ids: List[str],
    policy_ids: List[str],
    control_ids: List[str],
    include_obligations: bool = True,
) -> ComplianceGraph:
    rules = [store.rule_by_id(r) for r in rule_ids]
    rules = [r for r in rules if r]
    changed_cites = {c for ch in store.changes() for c in ch["affectedCites"]}

    pol_pool = [p for p in store.policies() if not policy_ids or p["id"] in policy_ids]
    ctl_pool = [c for c in store.controls() if not control_ids or c["id"] in control_ids]

    rule_layer: List[Dict[str, Any]] = []
    obl_layer: List[Dict[str, Any]] = []
    pol_layer: List[Dict[str, Any]] = []
    ctl_layer: List[Dict[str, Any]] = []
    risk_layer: List[Dict[str, Any]] = []
    iss_layer: List[Dict[str, Any]] = []

    used_pol: Dict[str, Dict[str, Any]] = {}
    used_ctl: Dict[str, Dict[str, Any]] = {}
    used_risk: Dict[str, Dict[str, Any]] = {}
    used_iss: Dict[str, Dict[str, Any]] = {}

    # ---- rules + obligations ---------------------------------------------
    for ri, rule in enumerate(rules):
        amended = any(c in rule["cite"] or rule["cite"] in c for c in changed_cites)
        rnode = _node(
            0, ri, rule["id"],
            f'{rule["cite"]} — {rule["title"]}',
            f'{rule["cite"]}|{rule["title"]}',
            "Rule", rule["text"], impacted=amended,
        )
        rnode["juris"] = rule["juris"]
        rnode["jurisName"] = rule.get("jurisName", "")
        rnode["ruleMatter"] = rule["ruleMatter"]
        rnode["ruleType"] = rule["ruleType"]
        rnode["regulator"] = rule["regulator"]
        rnode["effectiveDate"] = rule["effectiveDate"]
        rnode["detailKey"] = rule.get("detailKey")
        rule_layer.append(rnode)

        obls = obligation_service.extract(rule) if include_obligations else []
        for ob in obls:
            onode = _node(
                1, len(obl_layer), ob.id,
                f"{ob.actor} {ob.trigger} {ob.action}",
                f"{ob.id}|{ob.kind}", "Obligation",
                f"{ob.actor} {ob.trigger} {ob.action}",
            )
            onode["confidence"] = ob.confidence
            onode["kind"] = ob.kind
            onode["timing"] = ob.timing
            onode["ruleId"] = rule["id"]
            obl_layer.append(onode)
            rnode["other_kps_ds2"].append(
                {"id": ob.id, "name": ob.id, "prefix": ob.id,
                 "quote": onode["quote"], "value": round(ob.confidence / 100, 4)}
            )
        if not include_obligations:
            rnode["_matter"] = rule["ruleMatter"]
            rnode["_juris"] = rule["juris"]

    # ---- policies ---------------------------------------------------------
    def policy_links(matter: str, juris: str) -> List[Dict[str, Any]]:
        out = []
        for p in pol_pool:
            if p["ruleMatter"] != matter:
                continue
            if juris not in p["jurisdictions"]:
                continue        # deployed elsewhere: that is a real gap
            score = 0.5 + 0.25 + 0.05
            if p["id"] not in used_pol:
                pn = _node(2, len(pol_layer), p["id"], p["name"],
                           f'{p["id"]}|{p["name"]}', "Policy",
                           f'{p["name"]} ({p["version"]}), owned by {p["owner"]}, next review {p["nextReview"]}.')
                pn["owner"] = p["owner"]
                pn["version"] = p["version"]
                pn["nextReview"] = p["nextReview"]
                pn["ruleMatter"] = p["ruleMatter"]
                pol_layer.append(pn)
                used_pol[p["id"]] = pn
            out.append({"id": p["id"], "name": p["name"], "prefix": p["name"],
                        "quote": used_pol[p["id"]]["quote"], "value": round(score, 4)})
        return out

    source_layer = obl_layer if include_obligations else rule_layer
    for n in source_layer:
        if include_obligations:
            rule = store.rule_by_id(n["ruleId"])
            matter, juris = rule["ruleMatter"], rule["juris"]
        else:
            matter, juris = n["_matter"], n["_juris"]
        n["other_kps_ds2"] = n.get("other_kps_ds2", []) + policy_links(matter, juris)
        n["_matter"], n["_juris"] = matter, juris

    # ---- controls ---------------------------------------------------------
    for pn in pol_layer:
        matter = pn["ruleMatter"]
        jurs = {s["_juris"] for s in source_layer if s.get("_matter") == matter}
        for c in ctl_pool:
            if c["ruleMatter"] != matter:
                continue
            if not (set(c["jurisdictions"]) & jurs):
                continue
            score = 0.5 + 0.25
            if c["testResult"] == "Effective":
                score += 0.10
            if c["automation"] == "Automated":
                score += 0.05
            if c["id"] not in used_ctl:
                cn = _node(3, len(ctl_layer), c["id"], c["name"],
                           f'{c["id"]}|{c["name"]}', "Control",
                           f'{c["name"]}. {c["controlType"]}, {c["automation"]}, owned by {c["owner"]}. Last test: {c["testResult"]}.')
                cn["owner"] = c["owner"]
                cn["testResult"] = c["testResult"]
                cn["controlType"] = c["controlType"]
                cn["automation"] = c["automation"]
                cn["ruleMatter"] = c["ruleMatter"]
                cn["impactedRule"] = c["testResult"] != "Effective"
                ctl_layer.append(cn)
                used_ctl[c["id"]] = cn
            pn["other_kps_ds2"].append(
                {"id": c["id"], "name": c["name"], "prefix": c["name"],
                 "quote": used_ctl[c["id"]]["quote"], "value": round(score, 4)}
            )

    # ---- risks ------------------------------------------------------------
    for cn in ctl_layer:
        for rk in store.risks():
            if rk["ruleMatter"] != cn["ruleMatter"]:
                continue
            over = LVL.get(rk["residual"], 0) > LVL.get(rk["appetite"], 0)
            score = 0.8 if cn["testResult"] == "Effective" else 0.62
            if rk["id"] not in used_risk:
                rn = _node(4, len(risk_layer), rk["id"], rk["name"],
                           f'{rk["id"]}|{rk["name"]}', "Risk",
                           f'{rk["name"]}. Inherent {rk["inherent"]}, residual {rk["residual"]}, appetite {rk["appetite"]}.')
                rn["residual"] = rk["residual"]
                rn["appetite"] = rk["appetite"]
                rn["inherent"] = rk["inherent"]
                rn["overAppetite"] = over
                rn["impactedRule"] = over
                risk_layer.append(rn)
                used_risk[rk["id"]] = rn
            cn["other_kps_ds2"].append(
                {"id": rk["id"], "name": rk["name"], "prefix": rk["name"],
                 "quote": used_risk[rk["id"]]["quote"], "value": round(score, 4)}
            )

    # ---- issues -----------------------------------------------------------
    for rn in risk_layer:
        linked = store.issues_for_risk(rn["unique_id"])
        for iss in linked:
            if iss["id"] not in used_iss:
                inode = _node(5, len(iss_layer), iss["id"], iss["name"],
                              f'{iss["id"]}|{iss["name"]}', "Issue",
                              f'{iss["name"]}. Severity {iss["severity"]}, owner {iss["owner"]}, due {iss["due"]}, status {iss["status"]}.')
                inode["severity"] = iss["severity"]
                inode["owner"] = iss["owner"]
                inode["due"] = iss["due"]
                inode["statusLabel"] = iss["status"]
                inode["impactedRule"] = iss["status"] != "Closed"
                iss_layer.append(inode)
                used_iss[iss["id"]] = inode
            rn["other_kps_ds2"].append(
                {"id": iss["id"], "name": iss["name"], "prefix": iss["name"],
                 "quote": used_iss[iss["id"]]["quote"], "value": 0.8}
            )
        if not linked and rn.get("overAppetite"):
            # A risk above appetite with nothing remediating it is a governance
            # gap in its own right, so it gets a visible terminal node.
            pid = f'ISS-NONE-{rn["unique_id"]}'
            if pid not in used_iss:
                inode = _node(5, len(iss_layer), pid,
                              "No issue raised for a risk above appetite",
                              f"{pid}|No issue raised", "Issue",
                              f'No remediation issue exists for {rn["unique_id"]}, which sits above appetite.')
                inode["severity"] = "High"
                inode["owner"] = "Unassigned"
                inode["due"] = "Not set"
                inode["statusLabel"] = "Not raised"
                inode["impactedRule"] = True
                inode["synthetic"] = True
                iss_layer.append(inode)
                used_iss[pid] = inode
            rn["other_kps_ds2"].append(
                {"id": pid, "name": "No issue raised", "prefix": "No issue raised",
                 "quote": used_iss[pid]["quote"], "value": 0.45}
            )

    # mark rules whose chain never reaches a control
    reached = {s.get("_matter") for s in source_layer}
    covered_matters = {c["ruleMatter"] for c in ctl_layer}
    for rn in rule_layer:
        matter = rn.get("ruleMatter")
        if matter and matter not in covered_matters:
            rn["impactedRule"] = True

    for n in source_layer + rule_layer:
        n.pop("_matter", None)
        n.pop("_juris", None)

    # best-match band per node, for parity with the imported datasets
    for layer in (rule_layer, obl_layer, pol_layer, ctl_layer, risk_layer):
        for n in layer:
            best = max([k["value"] for k in n["other_kps_ds2"]], default=0.0)
            n["match"] = _band_name(best)

    layers = [l for l in (rule_layer, obl_layer, pol_layer, ctl_layer, risk_layer, iss_layer) if l]
    graph = ComplianceGraph(map_id, name, layers)
    register(graph)
    store.audit("map.build", map_id, {"nodes": len(graph.nodes), "layers": len(layers)})
    return graph
