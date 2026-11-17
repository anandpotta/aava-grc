import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ApiService } from '../../core/api.service';
import { AssessPanelComponent } from '../../shared/assess-panel.component';
import { ActionCenterComponent } from '../../shared/action-center.component';
import { WatchPanelComponent } from '../../shared/watch-panel.component';

interface Span { start: number; end: number; cls: string; }
interface Turn { q: string; run?: any; shown: number; done: boolean; approved: Record<string, boolean>; }

const SPAN_CLASS: Record<string, string> = {
  same: 'bg-gold-50 shadow-[inset_0_-2px_0_#FFCC00] rounded-sm px-px',
  semantic: 'bg-aava-100 shadow-[inset_0_-2px_0_#6666CC] rounded-sm px-px',
  dotted: 'border-b border-dotted border-aava-400',
  modal: 'font-semibold',
  timing: 'border-b-2 border-gold',
};
const VERDICT: Record<string, string> = {
  Covered: 'bg-jade-50 text-jade-700 border-jade/30',
  Partial: 'bg-gold-50 text-gold-700 border-gold/50',
  Gap: 'bg-magenta-50 text-magenta-700 border-magenta/30',
  Conflict: 'bg-magenta-50 text-magenta-700 border-magenta/30',
};

/**
 * Ask AAVA. The server returns one structured, auditable run (steps, evidence, answer);
 * this component only renders it. Nothing here decides anything.
 */
@Component({
  selector: 'aava-ask',
  standalone: true,
  imports: [CommonModule, FormsModule, AssessPanelComponent, ActionCenterComponent, WatchPanelComponent],
  template: `
<div class="h-[calc(100vh-0px)] flex bg-shell">
 <div class="flex-1 min-w-0 flex flex-col">
  <div class="px-6 pt-4 pb-2 flex items-center gap-3">
    <div class="w-9 h-9 rounded-xl bg-aava text-white flex items-center justify-center font-bold">✦</div>
    <div class="leading-tight"><div class="text-[16px] font-semibold">Ask AAVA</div>
      <div class="text-[11px] text-ink-400">Grounded in rules, policies, controls, risks and issues. Every answer cited, every write gated.</div></div>
    <div class="ml-auto p-0.5 rounded-lg bg-shell-100 border border-ink-200/60 flex">
      <button *ngFor="let m of modes" (click)="mode.set(m)"
        class="px-3 py-1 rounded-md text-[11.5px] font-medium"
        [ngClass]="mode()===m ? 'bg-white shadow-card text-aava-700' : 'text-ink-600'">{{ m }}</button>
    </div>
  </div>

  <div class="flex-1 overflow-y-auto px-6 pb-4 space-y-3" #thread>
    <aava-action-center *ngIf="mode()==='Act'" />
    <aava-watch-panel *ngIf="mode()==='Watch'" />
    <div *ngIf="!turns().length" class="max-w-[820px] mx-auto pt-6">
      <div class="text-center mb-5"><div class="text-[20px] font-semibold">What do you need to prove today?</div></div>
      <div class="grid grid-cols-3 gap-3">
        <button *ngFor="let s of scenarios(); let i = index" (click)="send(s.q)"
          class="text-left rounded-xl bg-white border border-ink-200/60 shadow-card p-3.5 hover:border-aava">
          <div class="flex items-center gap-2 mb-1.5"><span class="w-5 h-5 rounded-full bg-aava-100 text-aava-700 text-[10.5px] font-bold flex items-center justify-center">{{ i + 1 }}</span>
            <b class="text-[12.5px]">{{ s.title }}</b></div>
          <div class="text-[11.5px] text-ink-600">“{{ s.q }}”</div>
        </button>
      </div>
    </div>

    <ng-container *ngFor="let t of turns()">
      <div class="flex justify-end"><div class="max-w-[78%] px-3.5 py-2 rounded-2xl bg-aava text-white text-[12.5px]">{{ t.q }}</div></div>

      <div *ngIf="t.run" class="rounded-xl border border-aava-200 bg-white shadow-card overflow-hidden">
        <div class="px-3.5 py-2 bg-aava-50 border-b border-aava-200/60 flex items-center gap-2 text-[11px]">
          <span class="w-2 h-2 rounded-full" [ngClass]="t.done ? 'bg-jade' : 'bg-aava animate-pulse'"></span>
          <b class="text-aava-700">Agent run</b><span class="mono text-ink-400">{{ t.run.runId }}</span>
          <span class="ml-auto text-ink-400">{{ t.run.steps.length }} steps · {{ t.run.gates.length }} gate checks</span>
        </div>
        <div *ngFor="let s of t.run.steps.slice(0, t.shown)" class="px-3.5 py-2 flex gap-2.5 text-[11.5px] border-b border-ink-200/40 last:border-0">
          <span class="mt-[2px] w-4 h-4 rounded-full text-[9px] flex items-center justify-center shrink-0"
            [ngClass]="s.gate ? 'bg-gold-50 text-gold-700 border border-gold/50' : 'bg-jade-50 text-jade-700'">{{ s.gate ? 'G' : '✓' }}</span>
          <div class="flex-1"><b>{{ s.agent }}</b> <span class="text-ink-400">· {{ s.tool }}<ng-container *ngIf="s.kb"> · KB: {{ s.kb }}</ng-container></span>
            <div class="text-ink-600">{{ s.output }}</div></div>
          <span class="mono text-[10px] text-ink-400">{{ s.ms }} ms</span>
        </div>
      </div>

      <ng-container *ngIf="t.done && t.run">
        <div class="rounded-xl bg-white border border-ink-200/60 shadow-card px-4 py-3 text-[12.5px] leading-relaxed">{{ t.run.answer }}</div>

        <!-- clause-level mapping cards -->
        <div *ngFor="let m of t.run.data.mappings" class="rounded-xl border bg-white shadow-card overflow-hidden"
             [ngClass]="m.verdict==='Covered' ? 'border-jade/40' : m.verdict==='Partial' ? 'border-gold/60' : 'border-magenta/40'">
          <div class="px-4 py-2.5 bg-shell-100 flex items-center gap-2.5 border-b border-ink-200/40">
            <span class="w-[26px] h-[17px] rounded-[3px] bg-ink-200/50 text-[9px] font-bold text-ink-600 flex items-center justify-center uppercase">{{ m.juris }}</span>
            <div class="flex-1 min-w-0"><div class="text-[12.5px] font-semibold truncate">{{ m.cite }} <span class="font-normal text-ink-600">· {{ m.ruleTitle }}</span></div>
              <div class="text-[10.5px] text-ink-400">{{ m.regulator }} · {{ m.ruleMatter }} · {{ m.obligation.id }} · extraction {{ m.obligation.confidence }}%</div></div>
            <span *ngIf="m.isNew" class="px-2 py-0.5 rounded bg-aava text-white text-[10px] font-semibold">NEW</span>
            <span class="px-2 py-0.5 rounded-full border text-[10.5px] font-semibold" [ngClass]="verdictClass(m.verdict)">{{ m.verdict }}</span>
            <span *ngIf="m.match" class="text-[15px] font-bold">{{ (m.match.score*100) | number:'1.0-0' }}</span>
          </div>
          <div class="grid grid-cols-2 gap-px bg-ink-200/40">
            <div class="bg-white p-3.5"><div class="text-[10px] font-semibold tracking-wide text-ink-400 mb-1">REGULATORY OBLIGATION · {{ m.obligation.kind.toUpperCase() }}</div>
              <div class="text-[12.5px] leading-relaxed" [innerHTML]="mark(m.obligationText, m.obligationSpans)"></div></div>
            <div class="bg-white p-3.5"><div class="text-[10px] font-semibold tracking-wide text-ink-400 mb-1" *ngIf="m.match">POLICY CLAUSE · {{ m.match.policyId }} §{{ m.match.clauseSec }} · {{ m.match.policyName }} {{ m.match.version }}</div>
              <div class="text-[12.5px] leading-relaxed" [innerHTML]="mark(m.match?.clauseText, m.clauseSpans)"></div>
              <div class="mt-2 flex flex-wrap gap-1 text-[10px]">
                <span *ngFor="let c of m.match?.shared" class="px-1.5 rounded bg-jade-50 text-jade-700">✓ {{ c }}</span>
                <span *ngFor="let c of m.match?.missing" class="px-1.5 rounded bg-magenta-50 text-magenta-700">✗ {{ c }}</span></div></div>
          </div>
          <div *ngIf="semBridges(m).length" class="px-4 py-2 bg-aava-50 border-t border-ink-200/40 text-[11.5px]">
            <b class="text-aava-700">Semantic bridge</b> — different words, same meaning:
            <span *ngFor="let b of semBridges(m)" class="mr-3"><span class="bg-gold-50 px-1">{{ b.rule }}</span> ≈ <span class="bg-aava-100 px-1">{{ b.policy }}</span> → {{ b.concept }}</span>
          </div>
          <div *ngIf="m.match" class="px-4 py-3 border-t border-ink-200/40 grid grid-cols-[1fr_1.2fr] gap-5">
            <div class="space-y-1.5">
              <div *ngFor="let p of parts(m)" class="flex items-center gap-2 text-[10.5px]"><span class="w-[70px] text-ink-400">{{ p[0] }}</span>
                <div class="flex-1 h-1.5 rounded bg-shell"><div class="h-1.5 rounded" [style.width.%]="p[1]*100" [style.background]="p[1]>=.8?'#008567':p[1]>=.5?'#C9A100':'#CC0066'"></div></div>
                <span class="w-8 text-right mono">{{ p[1]*100 | number:'1.0-0' }}%</span></div>
              <div class="text-[10px] text-ink-400">score = .40 concepts + .25 actions + .20 timing + .15 jurisdiction</div></div>
            <div class="text-[11.5px] space-y-1">
              <div *ngFor="let r of m.match.reasons" class="flex gap-1.5"><span class="text-magenta-700">✗</span><span>{{ r }}</span></div>
              <div *ngIf="!m.match.reasons.length" class="flex gap-1.5"><span class="text-jade-700">✓</span><span>Concepts, actions and timing all reflected.</span></div></div>
          </div>
          <div class="px-4 py-2.5 border-t border-ink-200/40 bg-shell-100 grid grid-cols-3 gap-4 text-[11px]">
            <div><div class="text-[9.5px] font-semibold text-ink-400 mb-0.5">CONTROLS</div>
              <div *ngFor="let c of m.controls.slice(0,3)"><span class="mono text-[10px]">{{ c.id }}</span> {{ c.name }} <i class="text-ink-400">· {{ c.testResult }}</i></div>
              <div *ngIf="!m.controls.length" class="text-magenta-700">None deployed here</div></div>
            <div><div class="text-[9.5px] font-semibold text-ink-400 mb-0.5">RISK</div>
              <div *ngFor="let k of m.risks.slice(0,2)"><span class="mono text-[10px]">{{ k.id }}</span> {{ k.name }} <i class="text-ink-400">· {{ k.residual }} vs {{ k.appetite }}</i></div></div>
            <div><div class="text-[9.5px] font-semibold text-ink-400 mb-0.5">OPEN ISSUES</div>
              <div *ngFor="let i of m.issues.slice(0,2)"><span class="mono text-[10px]">{{ i.id }}</span> {{ i.name }} <i class="text-ink-400">· {{ i.severity }}</i></div>
              <div *ngIf="!m.issues.length" class="text-magenta-700">None raised</div></div>
          </div>
          <div *ngIf="m.draft" class="px-4 py-3 border-t border-ink-200/40 bg-aava-50">
            <div class="text-[10px] font-semibold tracking-wide text-aava-700 mb-1">PROPOSED REMEDIATION · Gate 2 · {{ m.match?.policyOwner || 'policy owner' }}</div>
            <div class="text-[12px]">{{ m.draft }}</div>
            <button *ngIf="!t.approved[m.cite]" (click)="approve(t, 'gate2', 'Draft for ' + m.cite)" class="mt-2 px-2.5 py-1 rounded-lg bg-aava text-white text-[11px] font-medium">Send draft to owner for approval</button>
            <span *ngIf="t.approved[m.cite]" class="mt-2 inline-block px-2.5 py-1 rounded-lg bg-jade-50 text-jade-700 text-[11px]">✓ Sent to owner · audited</span>
          </div>
        </div>

        <!-- change: redline -->
        <div *ngIf="t.run.kind==='change'" class="rounded-xl bg-white border border-ink-200/60 shadow-card p-4">
          <div class="text-[10px] font-semibold tracking-wide text-ink-400 mb-1.5">EXISTING → AMENDED · impact {{ t.run.data.impact.impactScore }}/100</div>
          <div class="text-[12.5px] leading-relaxed" [innerHTML]="redline(t.run.data.existing, t.run.data.amended)"></div>
          <div class="mt-3 grid grid-cols-3 gap-2 text-[11px]">
            <div class="bg-shell-100 rounded-lg p-2">MATERIALITY <b class="block text-[18px]">{{ t.run.data.impact.materiality }}</b></div>
            <div class="bg-shell-100 rounded-lg p-2">GAP SEVERITY <b class="block text-[18px]">{{ t.run.data.impact.gapSeverity }}</b></div>
            <div class="bg-shell-100 rounded-lg p-2">URGENCY <b class="block text-[18px]">{{ t.run.data.impact.urgency }}</b></div></div>
          <table class="w-full text-[11.5px] mt-3"><tr *ngFor="let a of t.run.data.impact.recommendedActions" class="border-t border-ink-200/40">
            <td class="py-1.5 pr-3">{{ a.action }}</td><td class="pr-3 text-ink-600">{{ a.owner }}</td><td class="text-ink-400">{{ a.why }}</td></tr></table>
          <button *ngIf="!t.approved['chg']" (click)="approve(t, 'gate3', t.run.data.change.id + ' action plan')" class="mt-3 px-3 py-1.5 rounded-lg bg-aava text-white text-[12px] font-medium">Approve as CCO and create tasks</button>
          <span *ngIf="t.approved['chg']" class="mt-3 inline-block px-3 py-1.5 rounded-lg bg-jade-50 text-jade-700 text-[12px]">✓ Approved · tasks created</span>
        </div>

        <!-- issue: plan -->
        <div *ngIf="t.run.kind==='issue'" class="rounded-xl bg-white border border-ink-200/60 shadow-card overflow-hidden">
          <div class="px-4 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Remediation plan for {{ t.run.data.issue.id }} · {{ t.run.data.overdueDays }} days overdue</div>
          <table class="w-full text-[11.5px]"><tr *ngFor="let p of t.run.data.plan; let i = index" class="border-t border-ink-200/40 align-top">
            <td class="px-4 py-2 font-semibold whitespace-nowrap">{{ i+1 }}. {{ p.step }}</td><td class="pr-2">{{ p.action }}</td><td>{{ p.owner }}</td><td class="whitespace-nowrap">{{ p.due }}</td><td class="pr-3 text-ink-600">{{ p.evidence }}</td></tr></table>
          <div class="px-4 py-2.5 bg-shell-100"><button *ngIf="!t.approved['iss']" (click)="approve(t, 'gate2', t.run.data.issue.id + ' remediation plan')" class="px-3 py-1.5 rounded-lg bg-aava text-white text-[12px] font-medium">Approve plan and create {{ t.run.data.plan.length }} tasks</button>
            <span *ngIf="t.approved['iss']" class="px-3 py-1.5 rounded-lg bg-jade-50 text-jade-700 text-[12px]">✓ Approved · tasks created · audited</span></div>
        </div>

        <!-- report -->
        <div *ngIf="t.run.kind==='report'" class="space-y-3">
          <div class="grid grid-cols-4 gap-2">
            <div class="rounded-xl bg-white border border-ink-200/60 p-3"><div class="text-[9.5px] text-ink-400">COVERAGE</div><div class="text-[22px] font-semibold text-aava-700">{{ t.run.data.coverageScore }}%</div></div>
            <div class="rounded-xl bg-white border border-ink-200/60 p-3"><div class="text-[9.5px] text-ink-400">COVERED</div><div class="text-[22px] font-semibold">{{ t.run.data.counts.covered }}</div></div>
            <div class="rounded-xl bg-white border border-ink-200/60 p-3"><div class="text-[9.5px] text-ink-400">PARTIAL</div><div class="text-[22px] font-semibold text-gold-700">{{ t.run.data.counts.partial }}</div></div>
            <div class="rounded-xl bg-white border border-ink-200/60 p-3"><div class="text-[9.5px] text-ink-400">GAP OR CONFLICT</div><div class="text-[22px] font-semibold text-magenta-700">{{ t.run.data.counts.gap }}</div></div></div>
          <div class="rounded-xl bg-white border border-ink-200/60 shadow-card p-4"><div class="text-[12.5px] font-semibold mb-2">Coverage matrix</div>
            <table class="w-full text-[10.5px]"><tr><th></th><th *ngFor="let j of matrixCols(t.run.data.matrix)" class="uppercase text-ink-600 pb-1">{{ j }}</th></tr>
              <tr *ngFor="let row of matrixRows(t.run.data.matrix)"><td class="pr-2 text-ink-600 whitespace-nowrap">{{ row }}</td>
                <td *ngFor="let j of matrixCols(t.run.data.matrix)" class="p-0.5"><div class="h-6 rounded text-[9.5px] font-semibold flex items-center justify-center"
                  [ngClass]="cellClass(t.run.data.matrix[row][j])">{{ cellText(t.run.data.matrix[row][j]) }}</div></td></tr></table></div>
          <div class="rounded-xl bg-white border border-ink-200/60 shadow-card overflow-hidden"><div class="px-4 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Mitigation plan</div>
            <table class="w-full text-[11.5px]"><tr *ngFor="let p of t.run.data.plan" class="border-t border-ink-200/40"><td class="px-4 py-2">{{ p.riskId }} {{ p.risk }}</td><td>{{ p.residual }} / {{ p.appetite }}</td><td>{{ p.action }}</td><td class="pr-4">{{ p.owner }}</td></tr></table></div>
        </div>

        <!-- risks -->
        <div *ngIf="t.run.kind==='risks'" class="rounded-xl bg-white border border-ink-200/60 shadow-card overflow-hidden">
          <table class="w-full text-[11.5px]"><tr class="bg-shell-100 text-[9.5px] text-ink-400 text-left"><th class="px-3 py-1.5">RISK</th><th>RESIDUAL / APPETITE</th><th>WEAK CONTROLS</th><th>ISSUES</th><th>NEXT ACTION</th></tr>
            <tr *ngFor="let r of t.run.data.risks" class="border-t border-ink-200/40 align-top"><td class="px-3 py-2">{{ r.id }} {{ r.name }}</td><td>{{ r.residual }} / {{ r.appetite }}</td>
              <td>{{ r.weakControls.join(', ') || '—' }}</td><td>{{ r.issues.join(', ') || 'none raised' }}</td><td class="pr-3">{{ r.next }}</td></tr></table></div>

        <div *ngIf="t.run.kind==='coordinate'" class="space-y-3">
          <div class="rounded-xl bg-white border border-ink-200/60 shadow-card overflow-hidden">
            <div class="px-4 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Who is told, and why <span class="font-normal text-[10.5px] text-ink-400">· {{ t.run.data.change.id }} · impact {{ t.run.data.impact }}/100 · {{ t.run.data.priority }}</span></div>
            <table class="w-full text-[11.5px]"><tr class="bg-shell-100 text-[9.5px] tracking-wide text-ink-400 text-left"><th class="px-3 py-1.5">PERSON</th><th>RACI</th><th>CHANNELS</th><th>REPLY BY</th><th>STATUS</th><th></th></tr>
              <tr *ngFor="let r of t.run.data.routing" class="border-t border-ink-200/40 align-top">
                <td class="px-3 py-2"><b>{{ r.name }}</b><div class="text-[10px] text-ink-400">{{ r.role }}</div><div class="text-[10.5px] text-ink-600">{{ r.why }}</div></td>
                <td><span class="px-1.5 py-[1px] rounded font-bold" [ngClass]="r.raci==='A' ? 'bg-aava text-white' : r.raci==='R' ? 'bg-gold-50 text-gold-700' : 'bg-shell-100 text-ink-600'" [title]="r.raciText">{{ r.raci }}</span></td>
                <td>{{ r.channels.join(' · ') }}</td><td class="whitespace-nowrap">{{ r.dueBy | date:'d MMM, HH:mm' }}</td>
                <td><span class="px-1.5 py-[1px] rounded text-[10px] font-semibold" [ngClass]="r.status==='acknowledged' ? 'bg-jade-50 text-jade-700' : r.status==='escalated' ? 'bg-magenta-50 text-magenta-700' : 'bg-gold-50 text-gold-700'">{{ r.status }}</span></td>
                <td class="pr-3"><button *ngIf="r.status==='sent'" (click)="ack(t, r)" class="text-aava-700 hover:underline">Acknowledge</button></td></tr></table>
            <div class="px-4 py-2 bg-shell-100 text-[11px] flex items-center gap-2"><button (click)="escalateNow(t)" class="px-2.5 py-1 rounded-lg border border-ink-200 bg-white hover:border-aava">Fast-forward 100 hours</button><span class="text-ink-400">Silent Accountable or Responsible people are escalated to their manager.</span></div></div>
          <div class="rounded-xl bg-white border border-ink-200/60 shadow-card">
            <div class="px-4 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Thread</div>
            <div class="p-3 space-y-2 text-[11.5px] max-h-80 overflow-auto"><div *ngFor="let m of t.run.data.thread.messages" class="rounded-lg px-2.5 py-1.5" [ngClass]="m.authorKind==='agent' ? 'bg-shell-100' : m.type==='decision' ? 'bg-jade-50' : 'border border-ink-200/50'">
              <div class="flex justify-between text-[10px] text-ink-400"><b class="text-ink-800">{{ m.author }}</b><span>{{ m.at | date:'HH:mm' }}</span></div>{{ m.text }}</div></div>
            <div class="p-2.5 border-t border-ink-200/50 flex gap-1.5"><select [(ngModel)]="authorId" class="text-[11px] border border-ink-200 rounded-lg px-1.5"><option *ngFor="let r of t.run.data.routing" [value]="r.sid">{{ r.name }}</option></select>
              <input [(ngModel)]="note" (keyup.enter)="say(t)" placeholder="Comment, or @Legal to pull someone in" class="flex-1 text-[11.5px] border border-ink-200 rounded-lg px-2 py-1"/><button (click)="say(t)" class="px-2.5 rounded-lg bg-aava text-white text-[11.5px]">Send</button></div></div>
          <div class="rounded-xl bg-white border border-ink-200/60 shadow-card p-4 text-[12px]">
            <div class="flex items-center gap-2 mb-1"><b>Approval</b><span class="px-1.5 py-[1px] rounded text-[10px] font-semibold" [ngClass]="t.run.data.approval.status==='approved' ? 'bg-jade-50 text-jade-700' : 'bg-gold-50 text-gold-700'">{{ t.run.data.approval.status }}</span><span class="text-[10.5px] text-ink-400">Only the named approver can decide. Reject or request changes needs a note.</span></div>
            <div *ngFor="let a of t.run.data.approval.required" class="flex items-center gap-2 py-1.5 border-t border-ink-200/40"><b class="w-40">{{ a.name }}</b><span class="w-52 text-ink-400">{{ a.role }}</span>
              <ng-container *ngIf="a.decision; else buttons"><span class="px-1.5 py-[1px] rounded bg-shell-100 font-semibold">{{ a.decision }}</span><span class="text-ink-600">{{ a.note }}</span></ng-container>
              <ng-template #buttons><button (click)="decideNow(t, a, 'approve')" class="px-2.5 py-1 rounded-lg bg-aava text-white">Approve</button><button (click)="decideNow(t, a, 'changes')" class="px-2.5 py-1 rounded-lg border border-ink-200">Request changes</button><button (click)="decideNow(t, a, 'reject')" class="px-2.5 py-1 rounded-lg border border-ink-200">Reject</button></ng-template></div>
            <div *ngIf="err" class="text-magenta-700 text-[11px] mt-1">{{ err }}</div></div></div>

        <aava-assess-panel *ngIf="t.run.kind==='assess' && t.done" [initial]="t.run.data" />

        <div *ngIf="t.run.kind==='watch'" class="rounded-xl bg-white border border-ink-200/60 shadow-card p-4 text-[12px]">
          <div *ngFor="let w of t.run.data.watches" class="py-1.5 border-b border-ink-200/40 last:border-0"><b>{{ w.scope }}</b> <span class="text-ink-400">· {{ w.rule }}</span></div></div>

        <div *ngIf="t.run.sources?.length" class="text-[10.5px] text-ink-400 px-1">Sources: {{ t.run.sources.join(' · ') }}</div>
      </ng-container>
    </ng-container>
  </div>

  <div class="px-6 pb-4 pt-2">
    <div class="flex gap-2">
      <input [(ngModel)]="draft" (keyup.enter)="send(draft)" placeholder="Ask about a rule, a policy, a gap, a change or a risk…"
        class="flex-1 px-4 py-2.5 rounded-xl border border-ink-200 bg-white text-[12.5px]">
      <button (click)="send(draft)" [disabled]="busy()" class="px-4 py-2.5 rounded-xl bg-aava text-white text-[12.5px] font-medium">Ask</button>
    </div>
  </div>
 </div>
</div>`,
})
export class AskComponent implements OnInit {
  private api = inject(ApiService);
  private dom = inject(DomSanitizer);
  modes: ('Ask' | 'Act' | 'Watch')[] = ['Ask', 'Act', 'Watch'];
  mode = signal<'Ask' | 'Act' | 'Watch'>('Ask');
  scenarios = signal<{ id: string; title: string; q: string }[]>([]);
  turns = signal<Turn[]>([]);
  busy = signal(false);
  draft = '';
  authorId = '';
  note = '';
  err = '';

  ngOnInit() { this.api.askScenarios().subscribe((s) => this.scenarios.set(s)); }

  send(q: string) {
    q = (q || '').trim();
    if (!q || this.busy()) return;
    this.draft = '';
    this.busy.set(true);
    const turn: Turn = { q, shown: 0, done: false, approved: {} };
    this.turns.update((t) => [...t, turn]);
    this.api.ask(q, this.mode()).subscribe({
      next: (run) => {
        turn.run = run;
        if (run.mode) this.mode.set(run.mode);
        this.reveal(turn);
      },
      error: () => this.busy.set(false),
    });
  }

  /** Stream the steps in one at a time so the audience can follow the agents. */
  private reveal(turn: Turn) {
    const step = () => {
      if (turn.shown >= turn.run.steps.length) {
        turn.done = true;
        this.busy.set(false);
        this.turns.update((t) => [...t]);
        return;
      }
      turn.shown++;
      this.turns.update((t) => [...t]);
      setTimeout(step, Math.min(500, 160 + turn.run.steps[turn.shown - 1].ms / 2));
    };
    step();
  }

  approve(t: Turn, gate: string, subject: string) {
    this.api.askApprove(t.run.runId, gate, subject).subscribe(() => {
      const key = t.run.kind === 'change' ? 'chg' : t.run.kind === 'issue' ? 'iss' : subject.replace('Draft for ', '');
      t.approved[key] = true;
      this.turns.update((x) => [...x]);
    });
  }

  private refresh(t: Turn) {
    const id = t.run.data.change.id;
    this.api.coordination(id).subscribe((c) => {
      t.run.data.thread = { messages: c.messages }; t.run.data.approval = c.approval; t.run.data.status = c.status;
      this.api.notifications(id).subscribe((ns) => {
        for (const r of t.run.data.routing) { const n = ns.find((x: any) => x.id === r.id); if (n) r.status = n.status; }
        this.turns.update((x) => [...x]);
      });
    });
  }
  ack(t: Turn, r: any) { this.api.ackNotification(r.id).subscribe(() => this.refresh(t)); }
  escalateNow(t: Turn) { this.api.escalate(t.run.data.change.id, 100).subscribe(() => this.refresh(t)); }
  say(t: Turn) {
    this.err = '';
    if (!this.authorId) this.authorId = t.run.data.routing[0].sid;
    this.api.comment(t.run.data.change.id, this.authorId, this.note).subscribe({ next: () => { this.note = ''; this.refresh(t); }, error: (e) => (this.err = e.error?.detail ?? 'Could not post') });
  }
  decideNow(t: Turn, a: any, d: string) {
    this.err = '';
    this.api.decide(t.run.data.change.id, a.id, d, this.note).subscribe({ next: () => { this.note = ''; this.refresh(t); }, error: (e) => (this.err = e.error?.detail ?? 'Could not record') });
  }

  verdictClass = (v: string) => VERDICT[v] ?? '';
  parts(m: any): [string, number][] {
    const p = m.match.parts;
    return [['Concepts', p.concepts], ['Actions', p.actions], ['Timing', p.timing], ['Jurisdiction', p.jurisdiction]];
  }
  semBridges = (m: any) => (m.match?.bridges ?? []).filter((b: any) => !b.identical);

  mark(text: string | undefined, spans: Span[] | undefined): SafeHtml {
    if (!text) return '';
    const esc = (s: string) => s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c] as string));
    let out = '', pos = 0;
    for (const sp of spans ?? []) {
      out += esc(text.slice(pos, sp.start)) + `<span class="${SPAN_CLASS[sp.cls] ?? ''}">${esc(text.slice(sp.start, sp.end))}</span>`;
      pos = sp.end;
    }
    return this.dom.bypassSecurityTrustHtml(out + esc(text.slice(pos)));
  }

  /** Word-level redline (LCS). */
  redline(a: string, b: string): SafeHtml {
    const x = a.split(/\s+/), y = b.split(/\s+/);
    const L = Array.from({ length: x.length + 1 }, () => new Array(y.length + 1).fill(0));
    for (let i = x.length - 1; i >= 0; i--)
      for (let j = y.length - 1; j >= 0; j--)
        L[i][j] = x[i] === y[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
    let i = 0, j = 0, o = '';
    const del = (w: string) => `<del class="bg-magenta-50 text-magenta-700">${w}</del> `;
    const ins = (w: string) => `<ins class="bg-jade-50 text-jade-700 no-underline font-medium">${w}</ins> `;
    while (i < x.length && j < y.length) {
      if (x[i] === y[j]) { o += x[i] + ' '; i++; j++; }
      else if (L[i + 1][j] >= L[i][j + 1]) o += del(x[i++]);
      else o += ins(y[j++]);
    }
    while (i < x.length) o += del(x[i++]);
    while (j < y.length) o += ins(y[j++]);
    return this.dom.bypassSecurityTrustHtml(o);
  }

  matrixRows = (m: Record<string, any>) => Object.keys(m);
  matrixCols = (m: Record<string, any>) => [...new Set(Object.values(m).flatMap((r: any) => Object.keys(r)))];
  cellText = (v?: string) => (!v ? '' : v === 'Covered' ? 'OK' : v === 'Partial' ? 'PART' : 'GAP');
  cellClass = (v?: string) =>
    !v ? 'bg-shell' : v === 'Covered' ? 'bg-jade text-white' : v === 'Partial' ? 'bg-gold text-ink' : 'bg-magenta text-white';
}
