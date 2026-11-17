"""Validate a compliance-map dataset before it is trusted.

Run against the raw layers, not the built graph, so it reports what is wrong in the
data rather than what the engine happened to tolerate. Each finding has a severity:

    error    the map would be wrong or misleading if rendered as is
    warning  renders, but a reviewer should know
    info     worth knowing, not a defect

The engine repairs what it can (clamps values, folds duplicate links, keeps duplicate
nodes distinct); `repairs` says what it did so nothing is changed silently.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from app.core.config import settings
from app.services import sankey_service


def _real(k: Dict[str, Any]) -> bool:
    try:
        return float(k.get("value") or 0) > settings.PLACEHOLDER_VALUE
    except (TypeError, ValueError):
        return False


def _f(sev: str, code: str, msg: str, layer: int | None = None, nodes: List[str] | None = None, fix: str = "") -> Dict[str, Any]:
    return {"severity": sev, "code": code, "message": msg, "layer": layer, "nodes": (nodes or [])[:12], "fix": fix}


def validate_layers(layers: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    out: List[Dict[str, Any]] = []
    if len(layers) < 2:
        out.append(_f("error", "too_few_layers", "A compliance map needs at least two layers.", fix="Add the layer the first one maps to."))
    for li, layer in enumerate(layers):
        ids = [str(n.get("unique_id") or "") for n in layer]
        for n in layer:
            if not n.get("unique_id"):
                out.append(_f("error", "missing_unique_id", f"Layer {li}: a node has no unique_id.", li, [str(n.get("dsName"))], "Give every node a stable id."))
            if not (n.get("dsName") or n.get("prefix")):
                out.append(_f("error", "missing_name", f"Layer {li}: node {n.get('unique_id')} has no dsName or prefix.", li, [str(n.get("unique_id"))]))
        dup = [k for k, c in Counter(ids).items() if k and c > 1]
        if dup:
            out.append(_f("warning", "duplicate_unique_id", f"Layer {li}: {len(dup)} unique_id value(s) are shared by several nodes ({', '.join(dup[:4])}).",
                          li, dup, "Make ids unique. Until then each node keeps its own uid and links to a shared id reach all of them."))
        types = {n.get("type") for n in layer}
        if len(types) > 1:
            out.append(_f("warning", "mixed_layer_type", f"Layer {li} mixes types {sorted(map(str, types))}.", li))
        if any(n.get("dataSourceIndex") not in (None, li) for n in layer):
            out.append(_f("warning", "layer_index_mismatch", f"Layer {li}: dataSourceIndex does not match the layer position.", li))
        blank = [str(n.get("unique_id")) for n in layer if not (n.get("quote") or "").strip()]
        if blank:
            out.append(_f("warning", "empty_quote", f"Layer {li}: {len(blank)} node(s) have no quote, so a reviewer cannot see the source text.", li, blank))
        for n in layer:
            if n.get("impactedRule") not in (None, True, False, 0, 1):
                out.append(_f("warning", "impacted_not_boolean", f"Layer {li}: impactedRule on {n.get('unique_id')} is not a boolean.", li, [str(n.get("unique_id"))]))

    for li in range(len(layers) - 1):
        nxt = {str(n.get("unique_id")) for n in layers[li + 1]}
        real = 0
        for n in layers[li]:
            seen = set()
            for k in n.get("other_kps_ds2") or []:
                tid = str(k.get("id"))
                v = k.get("value")
                if tid not in nxt:
                    out.append(_f("error", "dangling_link", f"Layer {li}: {n.get('unique_id')} links to {tid}, which is not in layer {li + 1}.", li, [str(n.get("unique_id")), tid],
                                  "Remove the link or add the target node."))
                    continue
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    out.append(_f("error", "non_numeric_value", f"Layer {li}: link {n.get('unique_id')} → {tid} has value {v!r}.", li, [str(n.get("unique_id"))]))
                    continue
                if fv < 0 or fv > 1:
                    out.append(_f("error", "value_out_of_range", f"Layer {li}: link {n.get('unique_id')} → {tid} has value {fv}; expected 0 to 1.", li, [str(n.get("unique_id"))]))
                if tid in seen:
                    out.append(_f("warning", "duplicate_link", f"Layer {li}: {n.get('unique_id')} links to {tid} more than once.", li, [str(n.get("unique_id")), tid]))
                seen.add(tid)
                if fv > settings.PLACEHOLDER_VALUE:
                    real += 1
        if real == 0:
            out.append(_f("warning", "no_real_links", f"Layers {li} → {li + 1} have no real mappings; every link is a placeholder, so the map shows no coverage between them.", li,
                          fix="Run the mapper for this pair, or the report will say coverage is nil."))
        targeted = {str(k.get("id")) for n in layers[li] for k in (n.get("other_kps_ds2") or []) if _real(k)}
        orphans = [str(n.get("unique_id")) for n in layers[li + 1] if str(n.get("unique_id")) not in targeted]
        if orphans and real:
            out.append(_f("info", "unmapped_nodes", f"Layer {li + 1}: {len(orphans)} of {len(layers[li + 1])} nodes are not reached by anything above. These are real gaps, or content that is not needed.",
                          li + 1, orphans))
        if li > 0:
            dead = [str(n.get("unique_id")) for n in layers[li] if not any(_real(k) for k in (n.get("other_kps_ds2") or []))]
            if dead and real:
                out.append(_f("info", "dead_end", f"Layer {li}: {len(dead)} node(s) map to nothing below.", li, dead))

    counts = Counter(f["severity"] for f in out)
    score = max(0, 100 - 15 * counts["error"] - 4 * counts["warning"] - 1 * counts["info"])
    return {"errors": counts["error"], "warnings": counts["warning"], "info": counts["info"], "qualityScore": score,
            "ok": counts["error"] == 0, "findings": out}


def validate(map_id: str) -> Dict[str, Any]:
    layers = sankey_service.raw_layers(map_id)
    res = validate_layers(layers)
    g = sankey_service.get_graph(map_id)
    res["mapId"] = map_id
    res["repairs"] = {"clampedValues": g.sanitised["clamped"], "nonNumericValues": g.sanitised["nonNumeric"],
                      "duplicateIdsKeptDistinct": sorted(set(g.collisions))}
    return res
