"""Compliance-map graph engine.

This is a faithful port of the behaviour of the legacy `script.js` / `d3Sankey.js`
pair, with the gaps closed. What is preserved from the original:

* the dataset contract — a list of layers, each layer a list of nodes carrying
  `other_kps_ds2` (the outgoing matches to the next layer);
* the **placeholder link** trick: every node of layer N+1 that nothing maps to
  is attached to the first node of layer N with weight 0.001 so that it is still
  laid out in its own column. Those links are flagged `placeholder=True` and the
  client draws them transparent. They never count as coverage;
* the similarity bands (Strong / Partial / Minimal) and their thresholds;
* `impactedRule` on a first-layer node, which the client renders as a red
  triangle;
* click-a-node-and-walk-both-directions selection.

What is new:

* duplicate `unique_id` values inside one layer no longer silently overwrite
  each other (the bundled best-execution dataset has three nodes sharing
  `pn0`); every node keeps its own uid and the collision is reported;
* a coverage summary per layer;
* drill-down path enumeration so the client can render the grouped
  parent-to-child table under the diagram;
* a findings list per node, which is what drives the impact analysis.
"""
from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from app.core.config import (
    BAND_MINIMAL,
    BAND_PARTIAL,
    BAND_STRONG,
    BAND_UNMAPPED,
    DATASET_DIR,
    band_for,
    settings,
)
from app.models.schemas import (
    ConnectedResponse,
    CoverageSummary,
    DrillResponse,
    DrillRow,
    LayerInfo,
    MapSummary,
    SankeyGraph,
    SankeyLink,
    SankeyNode,
)

# Human labels for the layer types we understand. Anything else falls back to
# the raw `type` value coming out of the dataset.
LAYER_LABELS = {
    "Rule": "Rules",
    "Rule Book": "Rules",
    "Obligation": "Obligations",
    "Policy": "Policies",
    "Control": "Controls",
    "Risk": "Risks",
    "Issue": "Issues",
}

DATASET_META = {
    "code-of-ethics": (
        "Code of ethics",
        "US code rules mapped to the code-of-ethics policy set, its controls and the open audit issues.",
    ),
    "anti-corruption": (
        "Anti-corruption",
        "eCFR rule book mapped to the anti-corruption policy and the AML control library.",
    ),
    "best-execution": (
        "Best execution",
        "Reg Best Execution rule book mapped to the investment-adviser code of ethics.",
    ),
    "large-volume": (
        "Large volume (stress)",
        "109 rules against 1,000 policies with a single real match — the layout stress case.",
    ),
}


def _short(prefix: str) -> str:
    """The legacy label rule: text before the first pipe."""
    if not prefix:
        return ""
    return prefix.split("|")[0].strip()


class ComplianceGraph:
    """An in-memory compliance map, built once and queried many times."""

    def __init__(self, map_id: str, name: str, layers: List[List[Dict[str, Any]]]):
        self.map_id = map_id
        self.name = name
        self.raw_layers = [lyr for lyr in layers if lyr]
        self.collisions: List[str] = []
        self.nodes: List[SankeyNode] = []
        self.links: List[SankeyLink] = []
        self.by_uid: Dict[str, SankeyNode] = {}
        self.out_links: Dict[str, List[int]] = defaultdict(list)
        self.in_links: Dict[str, List[int]] = defaultdict(list)
        self._build()

    # ------------------------------------------------------------------ build
    def _num(self, raw: Any, count: bool = True) -> float:
        """A similarity value: numeric, clamped to 0..1. Bad data must not take the map down."""
        try:
            v = float(raw or 0)
        except (TypeError, ValueError):
            if count:
                self.sanitised["nonNumeric"] += 1
            return 0.0
        if v < 0 or v > 1:
            if count:
                self.sanitised["clamped"] += 1
            return min(1.0, max(0.0, v))
        return v

    def _build(self) -> None:
        # Pass 1 – materialise nodes, keeping duplicates distinct.
        uids: List[List[str]] = []                   # per layer, per node index -> uid
        by_raw: List[Dict[str, List[str]]] = []      # per layer: unique_id -> every uid sharing it
        self.sanitised = {"clamped": 0, "nonNumeric": 0}
        for li, layer in enumerate(self.raw_layers):
            seen: Dict[str, int] = {}
            lay_uids: List[str] = []
            canon: Dict[str, List[str]] = {}
            ltype = layer[0].get("type") or f"Layer {li}"
            for node in layer:
                raw_id = str(node.get("unique_id") or node.get("dsName") or len(self.nodes))
                ordinal = seen.get(raw_id, 0)
                seen[raw_id] = ordinal + 1
                uid = f"L{li}:{raw_id}" if ordinal == 0 else f"L{li}:{raw_id}~{ordinal}"
                if ordinal == 1:
                    self.collisions.append(raw_id)
                # The legacy code keyed everything on unique_id, last write wins, so the links of
                # every duplicate source node ended up on the last duplicate. Each node now keeps
                # its own uid; a link TO a shared id reaches every node that carries it.
                lay_uids.append(uid)
                canon.setdefault(raw_id, []).append(uid)

                best = 0.0
                for kp in node.get("other_kps_ds2") or []:
                    v = self._num(kp.get("value"), count=False)
                    if v > best and v > settings.PLACEHOLDER_VALUE:
                        best = v

                prefix = node.get("prefix") or node.get("dsName") or raw_id
                self.nodes.append(
                    SankeyNode(
                        uid=uid,
                        sourceId=raw_id,
                        name=node.get("dsName") or prefix,
                        prefix=prefix,
                        label=_short(prefix),
                        layer=li,
                        layerType=ltype,
                        quote=node.get("quote") or "",
                        impacted=bool(node.get("impactedRule")),
                        match=node.get("match") or "",
                        bestScore=round(best, 6),
                        band=band_for(best) if best else BAND_UNMAPPED,
                        meta={
                            k: v
                            for k, v in node.items()
                            if k
                            not in {
                                "other_kps_ds2",
                                "quote",
                                "prefix",
                                "dsName",
                                "unique_id",
                                "type",
                            }
                        },
                    )
                )
            uids.append(lay_uids)
            by_raw.append(canon)

        self.by_uid = {n.uid: n for n in self.nodes}

        # Pass 2 – real links from other_kps_ds2.
        linked_targets: List[Set[str]] = [set() for _ in self.raw_layers]
        for li, layer in enumerate(self.raw_layers[:-1]):
            target_canon = by_raw[li + 1]
            for ni, node in enumerate(layer):
                src_uid = uids[li][ni]
                done: Dict[str, float] = {}
                for kp in node.get("other_kps_ds2") or []:
                    value = self._num(kp.get("value"))
                    if value <= settings.PLACEHOLDER_VALUE:
                        # The dataset already carries a placeholder; fold it in
                        # with the generated ones below instead of duplicating.
                        continue
                    for tgt_uid in target_canon.get(str(kp.get("id")), []):
                        if done.get(tgt_uid, 0.0) >= value:      # same target twice: keep the strongest
                            continue
                        done[tgt_uid] = value
                for tgt_uid, value in done.items():
                    linked_targets[li + 1].add(tgt_uid)
                    self._add_link(src_uid, tgt_uid, value, li, li + 1, False)

        # Pass 3 – placeholder links so every node keeps its column.
        # Legacy behaviour: hang them off the FIRST node of the previous layer.
        for li in range(len(self.raw_layers) - 1):
            if not uids[li]:
                continue
            anchor = uids[li][0]
            for ni in range(len(self.raw_layers[li + 1])):
                uid = uids[li + 1][ni]
                if uid in linked_targets[li + 1]:
                    continue
                linked_targets[li + 1].add(uid)
                self._add_link(anchor, uid, settings.PLACEHOLDER_VALUE, li, li + 1, True)

        # Degrees
        for idx, link in enumerate(self.links):
            if link.placeholder:
                continue
            self.by_uid[link.source].outDegree += 1
            self.by_uid[link.target].inDegree += 1

        # A node in layer > 0 with no real inbound link is unmapped; a node in
        # a non-final layer with no real outbound link is a dead end.
        last_layer = len(self.raw_layers) - 1
        for node in self.nodes:
            if node.layer > 0 and node.inDegree == 0:
                node.band = BAND_UNMAPPED
            elif node.layer == 0 and node.outDegree == 0:
                node.band = BAND_UNMAPPED
            if node.layer < last_layer and node.outDegree == 0 and node.layer > 0:
                node.meta["deadEnd"] = True

    def _add_link(
        self,
        source: str,
        target: str,
        value: float,
        slayer: int,
        tlayer: int,
        placeholder: bool,
    ) -> None:
        idx = len(self.links)
        self.links.append(
            SankeyLink(
                source=source,
                target=target,
                value=max(value, settings.PLACEHOLDER_VALUE),
                band=BAND_UNMAPPED if placeholder else band_for(value),
                placeholder=placeholder,
                sourceLayer=slayer,
                targetLayer=tlayer,
            )
        )
        if not placeholder:
            self.out_links[source].append(idx)
            self.in_links[target].append(idx)

    # ---------------------------------------------------------------- queries
    def layer_infos(self) -> List[LayerInfo]:
        out = []
        for li, layer in enumerate(self.raw_layers):
            ltype = layer[0].get("type") or f"Layer {li}"
            out.append(
                LayerInfo(
                    index=li,
                    type=ltype,
                    label=LAYER_LABELS.get(ltype, ltype),
                    nodeCount=sum(1 for n in self.nodes if n.layer == li),
                )
            )
        return out

    def summary(self) -> CoverageSummary:
        counts = {BAND_STRONG: 0, BAND_PARTIAL: 0, BAND_MINIMAL: 0, BAND_UNMAPPED: 0}
        by_layer: List[Dict[str, Any]] = []
        for li, info in enumerate(self.layer_infos()):
            lc = {BAND_STRONG: 0, BAND_PARTIAL: 0, BAND_MINIMAL: 0, BAND_UNMAPPED: 0}
            for n in self.nodes:
                if n.layer != li:
                    continue
                lc[n.band if n.band in lc else BAND_UNMAPPED] += 1
                counts[n.band if n.band in counts else BAND_UNMAPPED] += 1
            by_layer.append(
                {
                    "layer": li,
                    "type": info.type,
                    "label": info.label,
                    "nodes": info.nodeCount,
                    "strong": lc[BAND_STRONG],
                    "partial": lc[BAND_PARTIAL],
                    "minimal": lc[BAND_MINIMAL],
                    "unmapped": lc[BAND_UNMAPPED],
                }
            )
        real = sum(1 for l in self.links if not l.placeholder)
        total = max(1, len(self.nodes))
        score = round(
            100
            * (
                counts[BAND_STRONG]
                + 0.6 * counts[BAND_PARTIAL]
                + 0.3 * counts[BAND_MINIMAL]
            )
            / total
        )
        return CoverageSummary(
            strong=counts[BAND_STRONG],
            partial=counts[BAND_PARTIAL],
            minimal=counts[BAND_MINIMAL],
            unmapped=counts[BAND_UNMAPPED],
            impacted=sum(1 for n in self.nodes if n.impacted),
            totalNodes=len(self.nodes),
            totalLinks=len(self.links),
            realLinks=real,
            coverageScore=score,
            byLayer=by_layer,
        )

    def graph(self) -> SankeyGraph:
        return SankeyGraph(
            mapId=self.map_id,
            name=self.name,
            layers=self.layer_infos(),
            nodes=self.nodes,
            links=self.links,
            summary=self.summary(),
        )

    # -- connected sub-graph ------------------------------------------------
    def connected(self, uid: str) -> ConnectedResponse:
        if uid not in self.by_uid:
            raise KeyError(uid)
        down: Set[str] = set()
        up: Set[str] = set()
        link_ids: Set[int] = set()

        stack = [uid]
        while stack:
            cur = stack.pop()
            for li in self.out_links.get(cur, []):
                link_ids.add(li)
                nxt = self.links[li].target
                if nxt not in down:
                    down.add(nxt)
                    stack.append(nxt)

        stack = [uid]
        while stack:
            cur = stack.pop()
            for li in self.in_links.get(cur, []):
                link_ids.add(li)
                prv = self.links[li].source
                if prv not in up:
                    up.add(prv)
                    stack.append(prv)

        all_nodes = up | down | {uid}
        # only keep links whose both ends survived the walk
        link_ids = {
            i
            for i in link_ids
            if self.links[i].source in all_nodes and self.links[i].target in all_nodes
        }
        counts: Dict[str, int] = defaultdict(int)
        for n in all_nodes:
            counts[self.by_uid[n].layerType] += 1
        return ConnectedResponse(
            uid=uid,
            upstream=sorted(up),
            downstream=sorted(down),
            nodes=sorted(all_nodes),
            links=sorted(link_ids),
            counts=dict(counts),
        )

    # -- drill-down ---------------------------------------------------------
    def _paths_down(self, uid: str, limit: int) -> List[List[str]]:
        out: List[List[str]] = []

        def walk(cur: str, acc: List[str]) -> None:
            if len(out) >= limit:
                return
            nxt = self.out_links.get(cur, [])
            if not nxt:
                out.append(list(acc))
                return
            for li in nxt:
                t = self.links[li].target
                acc.append(t)
                walk(t, acc)
                acc.pop()
                if len(out) >= limit:
                    return

        walk(uid, [])
        return out or [[]]

    def _paths_up(self, uid: str, limit: int) -> List[List[str]]:
        out: List[List[str]] = []

        def walk(cur: str, acc: List[str]) -> None:
            if len(out) >= limit:
                return
            prv = self.in_links.get(cur, [])
            if not prv:
                out.append(list(reversed(acc)))
                return
            for li in prv:
                s = self.links[li].source
                acc.append(s)
                walk(s, acc)
                acc.pop()
                if len(out) >= limit:
                    return

        walk(uid, [])
        return out or [[]]

    def findings_for(self, uid: str) -> List[str]:
        node = self.by_uid[uid]
        out: List[str] = []
        if node.impacted:
            out.append("Flagged as an impacted rule in the source data")
        if node.layer > 0 and node.inDegree == 0:
            out.append(f"No {self.layer_infos()[node.layer - 1].label.lower()[:-1]} maps to this {node.layerType.lower()}")
        last = len(self.raw_layers) - 1
        if node.layer < last and node.outDegree == 0:
            out.append(f"Nothing downstream — the chain stops at this {node.layerType.lower()}")
        if node.band == BAND_MINIMAL:
            out.append("Best match is only a minimal similarity")
        if node.meta.get("deadEnd"):
            out.append("Dead end in the traceability chain")
        return out

    def drill(self, uid: str, limit: Optional[int] = None) -> DrillResponse:
        if uid not in self.by_uid:
            raise KeyError(uid)
        cap = limit or settings.MAX_DRILL_ROWS
        node = self.by_uid[uid]
        ups = self._paths_up(uid, cap)
        downs = self._paths_down(uid, cap)
        columns = [li.label for li in self.layer_infos()]

        rows: List[DrillRow] = []
        truncated = False
        for u in ups:
            for d in downs:
                if len(rows) >= cap:
                    truncated = True
                    break
                chain = u + [uid] + d
                cells: Dict[str, Any] = {}
                worst = BAND_STRONG
                impacted = False
                for cuid in chain:
                    n = self.by_uid[cuid]
                    cells[columns[n.layer]] = {
                        "uid": n.uid,
                        "label": n.label or n.name,
                        "name": n.name,
                        "band": n.band,
                        "impacted": n.impacted,
                        "quote": n.quote[:400],
                    }
                    impacted = impacted or n.impacted
                    if _band_rank(n.band) > _band_rank(worst):
                        worst = n.band
                for col in columns:
                    cells.setdefault(col, None)
                rows.append(
                    DrillRow(
                        cells=cells,
                        band=worst,
                        impacted=impacted,
                        findings=[],
                    )
                )
            if truncated:
                break

        return DrillResponse(
            uid=uid,
            node=node,
            columns=columns,
            rows=rows,
            truncated=truncated,
            findings=self.findings_for(uid),
        )


def _band_rank(band: str) -> int:
    return {BAND_STRONG: 0, BAND_PARTIAL: 1, BAND_MINIMAL: 2, BAND_UNMAPPED: 3}.get(band, 3)


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
_CUSTOM: Dict[str, ComplianceGraph] = {}


def _read_dataset(path: Path) -> List[List[Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, list):
        raise ValueError(f"{path.name}: expected a list of layers")
    return [lyr for lyr in raw if isinstance(lyr, list) and lyr]


@lru_cache(maxsize=16)
def _dataset_graph(map_id: str) -> ComplianceGraph:
    path = DATASET_DIR / f"{map_id}.json"
    if not path.exists():
        raise FileNotFoundError(map_id)
    name = DATASET_META.get(map_id, (map_id, ""))[0]
    return ComplianceGraph(map_id, name, _read_dataset(path))


def raw_layers(map_id: str) -> List[List[Dict[str, Any]]]:
    """The layers as supplied, before the engine touches them (for validation)."""
    g = get_graph(map_id)
    return g.raw_layers


def register(graph: ComplianceGraph) -> None:
    _CUSTOM[graph.map_id] = graph


def get_graph(map_id: str) -> ComplianceGraph:
    if map_id in _CUSTOM:
        return _CUSTOM[map_id]
    return _dataset_graph(map_id)


def list_maps() -> List[MapSummary]:
    out: List[MapSummary] = []
    for path in sorted(DATASET_DIR.glob("*.json")):
        mid = path.stem
        label, desc = DATASET_META.get(mid, (mid, ""))
        try:
            g = _dataset_graph(mid)
        except Exception:  # pragma: no cover - a malformed dataset is skipped
            continue
        out.append(
            MapSummary(
                id=mid,
                name=label,
                description=desc,
                layerTypes=[li.type for li in g.layer_infos()],
                nodeCount=len(g.nodes),
                source="dataset",
            )
        )
    for mid, g in _CUSTOM.items():
        out.append(
            MapSummary(
                id=mid,
                name=g.name,
                description="Built in this session from a rulebook.",
                layerTypes=[li.type for li in g.layer_infos()],
                nodeCount=len(g.nodes),
                source="generated",
            )
        )
    return out


def layers_to_dataset(layers: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
    """Normalise a freshly generated map into the dataset contract."""
    out = []
    for li, layer in enumerate(layers):
        norm = []
        for idx, node in enumerate(layer):
            n = dict(node)
            n.setdefault("dataSourceIndex", li)
            n.setdefault("node", idx)
            n.setdefault("impactedRule", False)
            n.setdefault("match", "")
            n.setdefault("other_kps_ds2", [])
            norm.append(n)
        out.append(norm)
    return out
