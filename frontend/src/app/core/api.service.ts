import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import * as M from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  private p(obj: Record<string, string | number | undefined | null>): HttpParams {
    let params = new HttpParams();
    Object.entries(obj).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
    });
    return params;
  }

  // ---- reference / search ------------------------------------------------
  reference(): Observable<M.Reference> {
    return this.http.get<M.Reference>(`${this.base}/reference`);
  }

  search(q: string, opts: {
    juris?: string | null; framework?: string | null;
    ruleMatter?: string | null; ruleType?: string | null;
    regulator?: string | null; instrument?: string | null; part?: string | null;
  } = {}): Observable<M.SearchResponse> {
    return this.http.get<M.SearchResponse>(`${this.base}/search`, {
      params: this.p({ q, ...opts }),
    });
  }

  rule(id: string): Observable<M.Rule> {
    return this.http.get<M.Rule>(`${this.base}/rules/${id}`);
  }
  ruleDetail(id: string): Observable<M.RuleDetail> {
    return this.http.get<M.RuleDetail>(`${this.base}/rules/${id}/detail`);
  }
  clauseFamily(ruleId: string, clauseId: string): Observable<M.ClauseFamily> {
    return this.http.get<M.ClauseFamily>(
      `${this.base}/rules/${ruleId}/detail/clause/${encodeURIComponent(clauseId)}/family`,
    );
  }

  // ---- rulebooks / obligations -------------------------------------------
  rulebooks(): Observable<M.Rulebook[]> {
    return this.http.get<M.Rulebook[]>(`${this.base}/rulebooks`);
  }
  createRulebook(name: string, scope: string, ruleIds: string[]): Observable<M.Rulebook> {
    return this.http.post<M.Rulebook>(`${this.base}/rulebooks`, { name, scope, ruleIds });
  }
  seedRulebook(): Observable<M.Rulebook> {
    return this.http.post<M.Rulebook>(`${this.base}/rulebooks/seed`, {});
  }
  obligations(opts: { rulebookId?: string; ruleId?: string } = {}): Observable<M.Obligation[]> {
    return this.http.get<M.Obligation[]>(`${this.base}/obligations`, { params: this.p(opts) });
  }
  validateObligation(id: string): Observable<M.ObligationValidation> {
    return this.http.get<M.ObligationValidation>(`${this.base}/obligations/${id}/validate`);
  }
  approveObligation(id: string): Observable<unknown> {
    return this.http.post(`${this.base}/obligations/${id}/approve`, {});
  }

  // ---- library -------------------------------------------------------------
  controls(): Observable<M.Control[]> { return this.http.get<M.Control[]>(`${this.base}/controls`); }
  policies(): Observable<M.Policy[]> { return this.http.get<M.Policy[]>(`${this.base}/policies`); }
  risks(): Observable<M.Risk[]> { return this.http.get<M.Risk[]>(`${this.base}/risks`); }
  issues(): Observable<M.Issue[]> { return this.http.get<M.Issue[]>(`${this.base}/issues`); }

  // ---- compliance maps -----------------------------------------------------
  maps(): Observable<M.MapSummaryDto[]> {
    return this.http.get<M.MapSummaryDto[]>(`${this.base}/maps`);
  }
  map(id: string, hideLayer?: number | null): Observable<M.SankeyGraph> {
    return this.http.get<M.SankeyGraph>(`${this.base}/maps/${id}`, {
      params: this.p({ layer: hideLayer ?? undefined }),
    });
  }
  buildMap(body: {
    name: string; rulebookId: string;
    policyIds: string[]; controlIds: string[]; includeObligations: boolean;
  }): Observable<M.SankeyGraph> {
    return this.http.post<M.SankeyGraph>(`${this.base}/maps/build`, body);
  }
  connected(mapId: string, uid: string): Observable<M.ConnectedResponse> {
    return this.http.get<M.ConnectedResponse>(
      `${this.base}/maps/${mapId}/connected/${encodeURIComponent(uid)}`,
    );
  }
  drill(mapId: string, uid: string): Observable<M.DrillResponse> {
    return this.http.get<M.DrillResponse>(
      `${this.base}/maps/${mapId}/drill/${encodeURIComponent(uid)}`,
    );
  }
  exportUrl(mapId: string, kind: 'csv' | 'xlsx' | 'pdf'): string {
    return `${this.base}/maps/${mapId}/export.${kind}`;
  }
  planUrl(mapId: string): string { return `${this.base}/maps/${mapId}/export-plan.html`; }

  // ---- reg change ----------------------------------------------------------
  changes(): Observable<M.RegChange[]> { return this.http.get<M.RegChange[]>(`${this.base}/changes`); }
  pipeline(): Observable<M.ChangePipeline> {
    return this.http.get<M.ChangePipeline>(`${this.base}/changes/pipeline`);
  }
  changeImpact(id: string): Observable<M.ChangeImpact> {
    return this.http.get<M.ChangeImpact>(`${this.base}/changes/${id}/impact`);
  }
  setChangeStatus(id: string, status: string, note?: string): Observable<unknown> {
    return this.http.post(`${this.base}/changes/${id}/status`, { status, note });
  }

  // ---- Ask AAVA ------------------------------------------------------------
  ask(question: string, mode: 'Ask' | 'Act' | 'Watch' = 'Ask'): Observable<any> {
    return this.http.post<any>(`${this.base}/ask`, { question, mode });
  }
  askScenarios(): Observable<{ id: string; title: string; q: string }[]> {
    return this.http.get<any>(`${this.base}/ask/scenarios`);
  }
  askApprove(runId: string, gate: string, subject: string): Observable<any> {
    return this.http.post<any>(`${this.base}/ask/approve`, { runId, gate, subject });
  }
  hierarchy(juris?: string): Observable<any[]> { return this.http.get<any[]>(`${this.base}/hierarchy`, { params: this.p({ juris }) }); }
  hierarchyValidate(): Observable<any> { return this.http.get<any>(`${this.base}/hierarchy/validate`); }
  scopeCatalog(): Observable<any> { return this.http.get<any>(`${this.base}/scope/catalog`); }
  addScopeItem(kind: 'policies' | 'controls', body: any): Observable<any> { return this.http.post<any>(`${this.base}/scope/${kind}`, body); }
  saveScope(scope: any): Observable<any> { return this.http.post<any>(`${this.base}/scope/save`, scope); }
  accessRoles(): Observable<any> { return this.http.get<any>(`${this.base}/access/roles`); }
  accessUsers(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/access/users`); }
  story(): Observable<any> { return this.http.get<any>(`${this.base}/story`); }
  accessMe(): Observable<any> { return this.http.get<any>(`${this.base}/access/me`); }
  accessUpdate(id: string, body: { role?: string; approves?: string[] }): Observable<any> { return this.http.put<any>(`${this.base}/access/users/${id}`, body); }
  frameworks(): Observable<any> { return this.http.get<any>(`${this.base}/frameworks`); }
  domains(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/domains`); }
  assessFramework(framework: string, subject: string, kind: string, domain: string, scope: any): Observable<any> { return this.http.post<any>(`${this.base}/assess/framework`, { framework, subject, kind, domain, scope }); }
  frameworkReport(framework: string, subject: string, kind: string, domain: string, scope: any): Observable<string> { return this.http.post(`${this.base}/assess/framework/report.html`, { framework, subject, kind, domain, scope }, { responseType: 'text' }); }
  assessSubjects(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/assess/subjects`); }
  assess(subject: string, scope: any): Observable<any> { return this.http.post<any>(`${this.base}/assess`, { subject, scope }); }
  assessReport(subject: string, scope: any): Observable<string> { return this.http.post(`${this.base}/assess/report.html`, { subject, scope }, { responseType: 'text' }); }
  posture(): Observable<any> { return this.http.get<any>(`${this.base}/posture`); }
  actions(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/actions`); }
  addAction(a: any): Observable<any> { return this.http.post<any>(`${this.base}/actions`, a); }
  fixPlan(subject: string, scope: any): Observable<any[]> { return this.http.post<any[]>(`${this.base}/actions/fix-plan`, { subject, scope }); }
  decideAction(id: string, decision: string): Observable<any> { return this.http.post<any>(`${this.base}/actions/${id}/decision`, { decision }); }
  shares(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/shares`); }
  share(body: any): Observable<any> { return this.http.post<any>(`${this.base}/shares`, body); }
  verifyShare(id: string): Observable<any> { return this.http.post<any>(`${this.base}/shares/${id}/verify`, {}); }
  stakeholders(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/stakeholders`); }
  notifyChange(id: string): Observable<any> { return this.http.post<any>(`${this.base}/changes/${id}/notify`, {}); }
  allNotifications(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/notifications`); }
  requestApproval(subject: string, gate: string, summary: string): Observable<any> { return this.http.post<any>(`${this.base}/threads/${subject}/approval`, { gate, summary }); }
  coordination(changeId: string): Observable<any> { return this.http.get<any>(`${this.base}/changes/${changeId}/coordination`); }
  notifications(changeId: string): Observable<any[]> { return this.http.get<any[]>(`${this.base}/notifications`, { params: { changeId } }); }
  ackNotification(id: string): Observable<any> { return this.http.post<any>(`${this.base}/notifications/${id}/ack`, {}); }
  escalate(changeId: string, hoursAhead: number): Observable<any> { return this.http.post<any>(`${this.base}/changes/${changeId}/escalate`, {}, { params: { hoursAhead } }); }
  comment(subject: string, authorId: string, text: string): Observable<any> { return this.http.post<any>(`${this.base}/threads/${subject}/comments`, { authorId, text }); }
  decide(subject: string, approverId: string, decision: string, note = ''): Observable<any> { return this.http.post<any>(`${this.base}/threads/${subject}/decision`, { approverId, decision, note }); }
  auditVerify(): Observable<any> { return this.http.get<any>(`${this.base}/audit/verify`); }
  audit(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/audit`);
  }
}
