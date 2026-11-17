"""Compliance maps: graph, selection, drill-down and export."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.deps import need

from app.models.schemas import (
    ConnectedResponse,
    DrillResponse,
    MapBuildRequest,
    MapSummary,
    SankeyGraph,
)
from app.services import export_service, map_builder_service, map_validator_service, sankey_service, store

router = APIRouter()


@router.get("/maps", response_model=List[MapSummary])
def list_maps():
    return sankey_service.list_maps()


@router.post("/maps/build", response_model=SankeyGraph, status_code=201)
def build_map(payload: MapBuildRequest, _u=Depends(need("rebuild_map"))):
    book = store.rulebook_by_id(payload.rulebookId)
    if not book:
        raise HTTPException(404, "rulebook not found")
    map_id = f"generated-{payload.rulebookId.lower()}"
    graph = map_builder_service.build(
        map_id=map_id,
        name=payload.name or book["name"],
        rule_ids=book["ruleIds"],
        policy_ids=payload.policyIds,
        control_ids=payload.controlIds,
        include_obligations=payload.includeObligations,
    )
    return graph.graph()


def _graph(map_id: str):
    try:
        return sankey_service.get_graph(map_id)
    except (FileNotFoundError, KeyError):
        raise HTTPException(404, f"map '{map_id}' not found")


@router.get("/maps/{map_id}", response_model=SankeyGraph)
def get_map(
    map_id: str,
    layer: Optional[int] = Query(None, description="Drop a layer, e.g. hide obligations"),
):
    graph = _graph(map_id)
    g = graph.graph()
    if layer is not None:
        g.nodes = [n for n in g.nodes if n.layer != layer]
        keep = {n.uid for n in g.nodes}
        g.links = [l for l in g.links if l.source in keep and l.target in keep]
    return g


@router.get("/maps/{map_id}/summary")
def map_summary(map_id: str):
    graph = _graph(map_id)
    s = graph.summary()
    return {
        "mapId": map_id,
        "name": graph.name,
        "summary": s,
        "layers": graph.layer_infos(),
        "duplicateSourceIds": sorted(set(graph.collisions)),
    }


@router.get("/maps/{map_id}/connected/{uid:path}", response_model=ConnectedResponse)
def connected(map_id: str, uid: str):
    graph = _graph(map_id)
    try:
        return graph.connected(uid)
    except KeyError:
        raise HTTPException(404, "node not found")


@router.get("/maps/{map_id}/drill/{uid:path}", response_model=DrillResponse)
def drill(map_id: str, uid: str, limit: int = Query(500, le=5000)):
    graph = _graph(map_id)
    try:
        return graph.drill(uid, limit)
    except KeyError:
        raise HTTPException(404, "node not found")


@router.get("/maps/{map_id}/export.csv")
def export_csv(map_id: str):
    graph = _graph(map_id)
    return Response(
        export_service.to_csv(graph),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="aava-map-{map_id}.csv"'},
    )


@router.get("/maps/{map_id}/export-plan.html")
def export_plan(map_id: str):
    """Impact and mitigation plan. Fix what it lists, rebuild the map, download again to see the score move."""
    graph = _graph(map_id)
    return Response(
        export_service.to_plan_html(graph),
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="aava-impact-mitigation-{map_id}.html"'},
    )


@router.get("/maps/{map_id}/export.xlsx")
def export_xlsx(map_id: str):
    graph = _graph(map_id)
    data = export_service.to_xlsx(graph)
    if data is None:
        raise HTTPException(503, "openpyxl is not installed on the server")
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="aava-map-{map_id}.xlsx"'},
    )


@router.get("/maps/{map_id}/export.pdf")
def export_pdf(map_id: str):
    graph = _graph(map_id)
    data = export_service.to_pdf(graph)
    if data is None:
        raise HTTPException(503, "reportlab is not installed on the server")
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="aava-map-{map_id}.pdf"'},
    )


@router.get("/maps/{map_id}/validate")
def validate_map(map_id: str):
    """Data-quality report for a dataset: dangling links, bad values, duplicate ids, orphans."""
    try:
        return map_validator_service.validate(map_id)
    except FileNotFoundError:
        raise HTTPException(404, "map not found")
