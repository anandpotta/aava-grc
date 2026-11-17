export interface Jurisdiction { id: string; name: string; short: string; regulators: string; }
export interface Framework { id: string; name: string; sub: string; }
export interface DomainTab { id: string; label: string; enabled: boolean; }

export interface Reference {
  jurisdictions: Jurisdiction[];
  frameworks: Framework[];
  ruleMatters: string[];
  ruleTypes: string[];
  domains: DomainTab[];
  counts: Record<string, number>;
}

export interface Rule {
  id: string; juris: string; jurisName: string; regulator: string; cite: string;
  title: string; ruleType: string; ruleMatter: string; effectiveDate: string;
  text: string; severity: string; obligationCount: number; frameworks: string[];
}

export interface SearchHit { rule: Rule; score: number; hits: string[]; }
export interface KeywordNode { term: string; count: number; primary: boolean; }
export interface ConceptExpansion { root: string; terms: string[]; }
export interface SearchResponse {
  total: number; results: SearchHit[]; keywordMap: KeywordNode[];
  concepts: ConceptExpansion[]; facets: Record<string, Record<string, number>>;
}

export interface Obligation {
  id: string; ruleId: string; cite: string; juris: string; ruleMatter: string;
  kind: string; actor: string; action: string; timing?: string | null;
  condition?: string | null; trigger: string; keyPhrases: string[];
  confidence: number; status: string; approvedBy?: string | null; approvedAt?: string | null;
}
export interface ObligationValidation {
  checks: Record<string, boolean>; passed: boolean; gate: 'auto' | 'human';
}

export interface Rulebook {
  id: string; name: string; scope: string; ruleIds: string[];
  created: string; obligationCount: number;
}

export interface Control {
  id: string; name: string; owner: string; controlType: string; automation: string;
  jurisdictions: string[]; ruleMatter: string; testResult: string;
}
export interface Policy {
  id: string; name: string; owner: string; version: string; nextReview: string;
  jurisdictions: string[]; ruleMatter: string;
}
export interface Risk {
  id: string; name: string; ruleMatter: string; inherent: string; residual: string; appetite: string;
}
export interface Issue {
  id: string; riskId: string; name: string; severity: string; owner: string; due: string; status: string;
}

// ---------------------------------------------------------------- map
export type Band = 'Strong' | 'Partial' | 'Minimal' | 'Unmapped';

export interface SankeyNodeDto {
  uid: string; sourceId: string; name: string; prefix: string; label: string;
  layer: number; layerType: string; quote: string; impacted: boolean;
  match: string; band: Band; bestScore: number; inDegree: number; outDegree: number;
  meta: Record<string, unknown>;
}
export interface SankeyLinkDto {
  source: string; target: string; value: number; band: Band;
  placeholder: boolean; sourceLayer: number; targetLayer: number;
}
export interface LayerInfo { index: number; type: string; label: string; nodeCount: number; }
export interface CoverageSummary {
  strong: number; partial: number; minimal: number; unmapped: number; impacted: number;
  totalNodes: number; totalLinks: number; realLinks: number; coverageScore: number;
  byLayer: Array<Record<string, string | number>>;
}
export interface SankeyGraph {
  mapId: string; name: string; layers: LayerInfo[];
  nodes: SankeyNodeDto[]; links: SankeyLinkDto[]; summary: CoverageSummary;
}
export interface MapSummaryDto {
  id: string; name: string; description: string; layerTypes: string[];
  nodeCount: number; source: string;
}
export interface ConnectedResponse {
  uid: string; upstream: string[]; downstream: string[];
  nodes: string[]; links: number[]; counts: Record<string, number>;
}
export interface DrillCell {
  uid: string; label: string; name: string; band: Band; impacted: boolean; quote: string;
}
export interface DrillRow {
  cells: Record<string, DrillCell | null>; band: Band; impacted: boolean; findings: string[];
}
export interface DrillResponse {
  uid: string; node: SankeyNodeDto; columns: string[];
  rows: DrillRow[]; truncated: boolean; findings: string[];
}

// -------------------------------------------------------- rule detail
export interface ClauseSpan { start: number; end: number; text: string; kind?: string; }
export interface RuleClause {
  id: string; path: string; depth: number; label: string; text: string;
  flagged: boolean; links: Array<{ href: string; text: string }>;
  spans: { trigger: ClauseSpan[]; timing: ClauseSpan[]; xref: ClauseSpan[] };
  childIds: string[]; parentId: string | null;
}
export interface RuleDetail {
  id: string; ruleId: string; ruleTitle: string; cite: string; section: string;
  breadcrumb: Array<{ level: string; depth: number; text: string; href: string | null }>;
  authority: { text: string; links: Array<{ href: string; text: string }> };
  clauses: RuleClause[];
  amendmentHistory: string[];
  stats: { clauses: number; dutyClauses: number; flagged: number; maxDepth: number };
  synthetic?: boolean;
}
export interface ClauseFamily { ancestors: string[]; descendants: string[]; family: string[]; }

// --------------------------------------------------------- reg change
export interface ClauseDiff { kind: 'added' | 'removed' | 'unchanged'; text: string; }
export interface RegChange {
  id: string; juris: string; regulator: string; title: string; published: string;
  effective: string; status: string; impact: string; affectedCites: string[];
  summary: string; daysToComply: number; diff: ClauseDiff[];
}
export interface ChangeImpact {
  changeId: string; impactScore: number; materiality: number; gapSeverity: number; urgency: number;
  affectedRules: string[]; affectedObligations: string[]; affectedPolicies: string[];
  affectedControls: string[]; affectedRisks: string[]; openIssues: string[];
  recommendedActions: Array<{ action: string; owner: string; why: string }>;
}
export interface ChangePipeline {
  stages: string[]; counts: Record<string, number>; items: Record<string, string[]>;
}
