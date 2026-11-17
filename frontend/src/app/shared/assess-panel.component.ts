import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';
import { StateService } from '../core/state.service';
import { SharePanelComponent } from './share-panel.component';

/** Assess anything: pick a subject, see what is compliant and what is not, how to fix it, then download, share or queue the fix plan. */
@Component({
  selector: 'aava-assess-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, SharePanelComponent],
  template: `
<ng-container *ngIf="res() as r">
  <div class="rounded-xl bg-white border border-ink-200/60 shadow-card p-4">
    <div class="rounded-lg bg-shell-100 p-3 mb-3"><div class="text-[10px] font-semibold tracking-wide text-ink-400 mb-1.5">MEASURE AGAINST A STANDARD OR CERTIFICATION</div>
      <div class="flex flex-wrap items-center gap-2 mb-2">
        <select [(ngModel)]="kind" class="px-2 py-1.5 rounded-lg border border-ink-200 text-[11.5px] bg-white"><option *ngFor="let k of kinds()" [value]="k">{{ k }}</option></select>
        <input [(ngModel)]="name" placeholder="Name it, e.g. Customer mobile app" class="px-2.5 py-1.5 rounded-lg border border-ink-200 text-[11.5px] w-56 bg-white"/>
        <select [(ngModel)]="domain" class="px-2 py-1.5 rounded-lg border border-ink-200 text-[11.5px] bg-white"><option value="">Any industry</option><option *ngFor="let d of domains()" [value]="d.id">{{ d.name }}</option></select></div>
      <div *ngIf="dom() as d" class="text-[10.5px] text-ink-600 mb-1.5">{{ d.why }} Regulators and bodies: {{ d.regulators.join(', ') }}.</div>
      <div class="flex flex-wrap gap-1.5"><button (click)="leaveFw()" class="px-2.5 py-1 rounded-lg text-[11px] border" [ngClass]="!fw ? 'bg-aava text-white border-aava' : 'border-ink-200 bg-white hover:border-aava'">Requirements view</button>
        <button *ngFor="let f of fwList()" (click)="setFw(f.id)" [title]="f.summary" class="px-2.5 py-1 rounded-lg text-[11px] border" [ngClass]="fw===f.id ? 'bg-aava text-white border-aava' : 'border-ink-200 bg-white hover:border-aava'">{{ f.name.split(' (')[0] }}<span class="opacity-60"> · {{ f.kind.split(' ')[0] }}</span></button></div></div>
    <div *ngIf="r.framework" class="rounded-lg border-l-4 border-aava bg-aava-50/50 px-3 py-2 mb-3 text-[11.5px] leading-relaxed"><b>{{ r.framework.name }}</b> · {{ r.framework.issuer }}<br>{{ r.framework.summary }}<br><span class="text-ink-600">{{ r.framework.note }}</span>
      <div *ngIf="r.notAssessed?.length" class="text-gold-700 mt-1">{{ r.notAssessed.length }} criteria are outside your scope and are not assessed.</div></div>
    <div *ngIf="!r.framework" class="flex flex-wrap gap-1.5 mb-3"><button *ngFor="let s of subjects()" (click)="pick(s.id)" class="px-3 py-1.5 rounded-lg text-[11.5px] border"
      [ngClass]="s.id===r.subject.id ? 'bg-aava text-white border-aava' : 'border-ink-200 hover:border-aava'">{{ s.name }}<span class="opacity-70"> · {{ s.kind }}</span></button></div>
    <div class="flex items-center gap-4"><div><div class="text-[10px] text-ink-400 tracking-wide">{{ r.framework ? 'READINESS SCORE' : 'COMPLIANCE SCORE' }}</div>
      <div class="text-[34px] font-semibold leading-none" [ngClass]="r.score>=80 ? 'text-jade-700' : r.score>=50 ? 'text-gold-700' : 'text-magenta-700'">{{ r.score }}%</div></div>
      <div class="flex-1"><div class="h-3 rounded-full overflow-hidden flex bg-shell-100"><div class="bg-jade h-full" [style.width.%]="pct(r.counts.compliant, r)"></div><div class="bg-gold h-full" [style.width.%]="pct(r.counts.partial, r)"></div><div class="bg-magenta h-full" [style.width.%]="pct(r.counts.notCompliant, r)"></div></div>
        <div class="flex gap-4 mt-1.5 text-[11px]"><span><b class="text-jade-700">{{ r.counts.compliant }}</b> compliant</span><span><b class="text-gold-700">{{ r.counts.partial }}</b> partly</span><span><b class="text-magenta-700">{{ r.counts.notCompliant }}</b> not compliant</span>
          <span class="text-ink-400">of {{ r.counts.total }} {{ r.framework ? 'criteria' : 'requirements' }} · scope: {{ r.scope.scoped ? 'your choice' : 'everything' }}</span></div>
        <div *ngIf="r.readiness" class="mt-1 text-[12px] font-semibold" [ngClass]="r.readiness==='Audit-ready' ? 'text-jade-700' : 'text-gold-700'">{{ r.readiness }}</div></div></div></div>
  <div class="rounded-xl bg-white border border-ink-200/60 shadow-card overflow-hidden mt-3">
    <table class="w-full text-[11.5px]"><tr class="bg-shell-100 text-[9.5px] tracking-wide text-ink-400 text-left"><th class="px-3 py-1.5">{{ r.framework ? 'CRITERION' : 'REQUIREMENT' }}</th><th>STANDARDS</th><th>STATUS</th><th>WHY</th><th>HOW TO MAKE IT COMPLIANT</th><th *ngIf="r.framework">AUDITOR WILL ASK FOR</th><th>OWNER · DUE</th></tr>
      <tr *ngFor="let x of r.rows" class="border-t border-ink-200/40 align-top"><td class="px-3 py-2"><b>{{ x.criterion ? x.criterion + ' · ' + x.title : x.matter }}</b><div class="text-[10.5px] text-ink-400">{{ x.criterion ? x.matter + ': ' : '' }}{{ x.what }}</div></td>
        <td class="pr-2"><span *ngFor="let s of x.standards" class="inline-block mr-1 mb-0.5 px-1.5 py-[1px] rounded bg-aava-50 text-aava-700 text-[10px]">{{ s }}</span></td>
        <td class="pr-2"><span class="px-1.5 py-[1px] rounded text-[10px] font-semibold" [ngClass]="x.status==='Compliant' ? 'bg-jade-50 text-jade-700' : x.status==='Partial' ? 'bg-gold-50 text-gold-700' : 'bg-magenta-50 text-magenta-700'">{{ x.status }}</span></td>
        <td class="pr-2 text-ink-600">{{ x.why.join('; ') || 'Controls tested and effective' }}<div class="text-[10px] text-ink-400">{{ x.evidence }}</div></td>
        <td class="pr-2"><div *ngFor="let f of x.fix">• {{ f }}</div><span *ngIf="!x.fix.length">Keep testing on schedule.</span></td>
        <td *ngIf="r.framework" class="pr-2 text-ink-600">{{ x.request }}</td><td class="pr-3 whitespace-nowrap">{{ x.owner }}<div class="text-[10px] text-ink-400">{{ x.due }}</div></td></tr></table>
    <div class="px-4 py-2.5 bg-shell-100"><div class="flex flex-wrap items-center gap-1.5">
      <button (click)="fix()" class="px-3 py-1.5 rounded-lg bg-aava text-white text-[11.5px]">Create the fix plan (goes to approval)</button>
      <button (click)="download()" class="px-3 py-1.5 rounded-lg border border-ink-200 bg-white text-[11.5px] hover:border-aava">Download report</button>
      <span class="text-[10.5px] text-ink-400">Standard mapping is illustrative and needs specialist review.</span></div>
      <aava-share-panel [subject]="subjectId()" /></div></div>
</ng-container>`,
})
export class AssessPanelComponent implements OnInit {
  private api = inject(ApiService);
  private state = inject(StateService);
  @Input() initial: any;
  res = signal<any>(null);
  subjects = signal<any[]>([]);
  kinds = signal<string[]>([]);
  domains = signal<any[]>([]);
  fws = signal<any[]>([]);
  fw: string | null = null;
  kind = 'Application';
  name = '';
  domain = '';

  ngOnInit() {
    this.api.assessSubjects().subscribe((s) => this.subjects.set(s));
    this.api.frameworks().subscribe((f) => { this.fws.set(f.frameworks); this.kinds.set(f.kinds); });
    this.api.domains().subscribe((d) => this.domains.set(d));
    this.res.set(this.initial);
  }
  dom = () => this.domains().find((d) => d.id === this.domain);
  fwList = () => { const d = this.dom(); return this.fws().filter((f) => !d || d.frameworks.includes(f.id)); };
  /** Subject id the share, fix-plan and report calls use: a preset id, or fw:<framework>|<name>|<kind>. */
  subjectId = () => (this.fw ? `fw:${this.fw}|${this.name}|${this.kind}` : this.res().subject.id);
  pct = (n: number, r: any) => (r.counts.total ? (100 * n) / r.counts.total : 0);
  pick(id: string) { this.fw = null; this.api.assess(id, this.state.scope()).subscribe((r) => this.res.set(r)); }
  setFw(id: string) { this.fw = id; this.api.assessFramework(id, this.name, this.kind, this.domain, this.state.scope()).subscribe((r) => this.res.set(r)); }
  leaveFw() { this.pick('platform'); }
  fix() { this.api.fixPlan(this.subjectId(), this.state.scope()).subscribe((q) => this.state.notify(q.length ? `${q.length} fixes queued. Open Act to approve them.` : 'Nothing to fix.')); }
  download() {
    const done = (html: string, id: string) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([html], { type: 'text/html' })); a.download = `aava-assessment-${id}.html`; a.click(); };
    if (this.fw) this.api.frameworkReport(this.fw, this.name, this.kind, this.domain, this.state.scope()).subscribe((h) => done(h, this.fw!));
    else this.api.assessReport(this.res().subject.id, this.state.scope()).subscribe((h) => done(h, this.res().subject.id));
  }
}
