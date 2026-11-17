"""Pydantic contracts shared with the Angular client."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Regulatory search / rulebooks / obligations
# --------------------------------------------------------------------------
class Rule(BaseModel):
    id: str
    juris: str
    jurisName: str = ""
    regulator: str
    cite: str
    title: str
    ruleType: str
    ruleMatter: str
    effectiveDate: str
    text: str
    severity: str = "Medium"
    obligationCount: int = 0
    frameworks: List[str] = Field(default_factory=list)


class SearchHit(BaseModel):
    rule: Rule
    score: float
    hits: List[str] = Field(default_factory=list)


class KeywordNode(BaseModel):
    term: str
    count: int
    primary: bool = False


class ConceptExpansion(BaseModel):
    root: str
    terms: List[str]


class SearchResponse(BaseModel):
    total: int
    results: List[SearchHit]
    keywordMap: List[KeywordNode]
    concepts: List[ConceptExpansion]
    facets: Dict[str, Dict[str, int]]


class Obligation(BaseModel):
    id: str
    ruleId: str
    cite: str
    juris: str
    ruleMatter: str
    kind: str                       # Mandatory / Prohibition / Expectation / Permission
    actor: str
    action: str
    timing: Optional[str] = None
    condition: Optional[str] = None
    trigger: str
    keyPhrases: List[str] = Field(default_factory=list)
    confidence: int = 0
    status: str = "Pending review"
    approvedBy: Optional[str] = None
    approvedAt: Optional[str] = None


class RulebookCreate(BaseModel):
    name: str
    scope: str = ""
    ruleIds: List[str]


class Rulebook(BaseModel):
    id: str
    name: str
    scope: str
    ruleIds: List[str]
    created: str
    obligationCount: int = 0


class Control(BaseModel):
    id: str
    name: str
    owner: str
    controlType: str
    automation: str
    jurisdictions: List[str]
    ruleMatter: str
    testResult: str


class Policy(BaseModel):
    id: str
    name: str
    owner: str
    version: str
    nextReview: str
    jurisdictions: List[str]
    ruleMatter: str


class Risk(BaseModel):
    id: str
    name: str
    ruleMatter: str
    inherent: str
    residual: str
    appetite: str


class Issue(BaseModel):
    id: str
    riskId: str
    name: str
    severity: str
    owner: str
    due: str
    status: str


# --------------------------------------------------------------------------
# Compliance map / Sankey
# --------------------------------------------------------------------------
class SankeyNode(BaseModel):
    """One node of one layer of a compliance map.

    `uid` is the stable identifier used by links and by the drill-down calls.
    It is the `unique_id` of the source dataset, namespaced by layer so that
    the same id appearing in two layers does not collide.
    """
    uid: str
    sourceId: str
    name: str
    prefix: str
    label: str
    layer: int
    layerType: str
    quote: str = ""
    impacted: bool = False
    match: str = ""
    band: str = "Unmapped"
    bestScore: float = 0.0
    inDegree: int = 0
    outDegree: int = 0
    meta: Dict[str, Any] = Field(default_factory=dict)


class SankeyLink(BaseModel):
    source: str
    target: str
    value: float
    band: str
    placeholder: bool = False
    sourceLayer: int
    targetLayer: int


class LayerInfo(BaseModel):
    index: int
    type: str
    label: str
    nodeCount: int


class CoverageSummary(BaseModel):
    strong: int = 0
    partial: int = 0
    minimal: int = 0
    unmapped: int = 0
    impacted: int = 0
    totalNodes: int = 0
    totalLinks: int = 0
    realLinks: int = 0
    coverageScore: int = 0
    byLayer: List[Dict[str, Any]] = Field(default_factory=list)


class SankeyGraph(BaseModel):
    mapId: str
    name: str
    layers: List[LayerInfo]
    nodes: List[SankeyNode]
    links: List[SankeyLink]
    summary: CoverageSummary


class ConnectedResponse(BaseModel):
    """The connected sub-graph of one node, walked in both directions."""
    uid: str
    upstream: List[str]
    downstream: List[str]
    nodes: List[str]
    links: List[int]
    counts: Dict[str, int]


class DrillRow(BaseModel):
    """One fully traced path through the clicked node."""
    cells: Dict[str, Any]
    band: str
    impacted: bool
    findings: List[str] = Field(default_factory=list)


class DrillResponse(BaseModel):
    uid: str
    node: SankeyNode
    columns: List[str]
    rows: List[DrillRow]
    truncated: bool = False
    findings: List[str] = Field(default_factory=list)


class MapSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    layerTypes: List[str]
    nodeCount: int
    source: str = "dataset"


class MapBuildRequest(BaseModel):
    name: str
    rulebookId: str
    policyIds: List[str] = Field(default_factory=list)
    controlIds: List[str] = Field(default_factory=list)
    includeObligations: bool = True


# --------------------------------------------------------------------------
# Regulatory change management
# --------------------------------------------------------------------------
class ClauseDiff(BaseModel):
    kind: str          # added | removed | unchanged
    text: str


class RegChange(BaseModel):
    id: str
    juris: str
    regulator: str
    title: str
    published: str
    effective: str
    status: str
    impact: str
    affectedCites: List[str]
    summary: str = ""
    daysToComply: int = 0
    diff: List[ClauseDiff] = Field(default_factory=list)


class ChangeImpact(BaseModel):
    changeId: str
    impactScore: int
    materiality: int
    gapSeverity: int
    urgency: int
    affectedRules: List[str]
    affectedObligations: List[str]
    affectedPolicies: List[str]
    affectedControls: List[str]
    affectedRisks: List[str]
    openIssues: List[str]
    recommendedActions: List[Dict[str, str]]


class ChangeStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None
