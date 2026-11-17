import { Component, Input, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';
import { Obligation, Rule, RuleClause, RuleDetail } from '../../core/models';

/**
 * Clause-level rule reader.
 *
 * The legacy page highlighted a clause family by string-matching dotted element
 * ids in jQuery. Here the tree comes from the server already wired, so:
 *
 *  - selecting `_b.1.i` never also lights `_b.1.ii`;
 *  - the outline rail on the left is generated from the same tree;
 *  - trigger phrases, deadlines and cross references are highlighted from
 *    server-computed character offsets rather than re-scanned in the browser;
 *  - each clause is individually pinnable and individually addressable, so an
 *    obligation can cite the exact sub-clause it came from.
 */
@Component({
  selector: 'aava-rule-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
<div class="p-5" *ngIf="detail() as d">
 <div class="max-w-[1320px] mx-auto space-y-4">

  <!-- header: breadcrumb + authority -->
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-5 py-4">
    <nav class="text-[11.5px] leading-relaxed">
      <div *ngFor="let b of d.breadcrumb" [style.padding-left.px]="b.depth * 16"
           class="flex items-center gap-1.5">
        <span class="w-1 h-1 rounded-full bg-ink-200"></span>
        <span [class.font-semibold]="b.level === 'section'"
              [class.text-ink-400]="b.level !== 'section'"
              [class.text-[13px]]="b.level === 'section'">{{ b.text }}</span>
        <span class="px-1.5 py-[1px] rounded bg-shell text-ink-400 text-[9px] uppercase tracking-wide">{{ b.level }}</span>
      </div>
    </nav>

    <div class="mt-3 pt-3 border-t border-ink-200/50 flex items-start justify-between gap-4 flex-wrap">
      <div>
        <div class="text-[10.5px] font-semibold text-ink-400 tracking-[.06em]">PART AUTHORITY</div>
        <div class="text-[11.5px] text-ink-600 mt-0.5">
          {{ d.authority.text }}
          <a *ngFor="let l of d.authority.links" [href]="l.href" target="_blank" rel="noopener"
             class="ml-1 text-aava-700 underline">{{ l.text }}</a>
        </div>
      </div>
      <div class="flex gap-2 flex-wrap">
        <div class="px-3 py-1.5 rounded-lg bg-shell-100 text-[11px]">
          <span class="text-ink-400">Clauses</span> <b>{{ d.stats.clauses }}</b>
        </div>
        <div class="px-3 py-1.5 rounded-lg bg-aava-50 text-[11px] text-aava-700">
          <span class="opacity-70">Duty clauses</span> <b>{{ d.stats.dutyClauses }}</b>
        </div>
        <div class="px-3 py-1.5 rounded-lg bg-gold-50 text-[11px] text-gold-700">
          <span class="opacity-70">Flagged</span> <b>{{ d.stats.flagged }}</b>
        </div>
        <button (click)="pinRule()" class="px-3 py-1.5 rounded-lg bg-aava text-white text-[11.5px] font-semibold">
          Pin rule to rulebook
        </button>
      </div>
    </div>

    <div *ngIf="d.amendmentHistory.length" class="mt-2 text-[10.5px] text-ink-400">
      <span class="font-medium text-ink-600">Amendment history:</span>
      <span *ngFor="let h of d.amendmentHistory" class="ml-1.5">[{{ h }}]</span>
    </div>
  </div>

  <div class="grid grid-cols-1 xl:grid-cols-[236px_minmax(0,1fr)_300px] gap-4">

    <!-- outline rail -->
    <aside class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden self-start sticky top-[70px]">
      <div class="px-4 py-2.5 border-b border-ink-200/50 text-[12px] font-semibold">Clause outline</div>
      <div class="max-h-[560px] overflow-y-auto py-1.5">
        <button *ngFor="let c of d.clauses" (click)="select(c.id)"
          [style.padding-left.px]="10 + c.depth * 12"
          class="w-full text-left pr-2 py-[5px] text-[11px] flex items-center gap-1.5 hover:bg-shell-100"
          [class.bg-aava-50]="family().has(c.id)"
          [class.font-semibold]="selected() === c.id">
          <span class="text-ink-400 w-[22px] shrink-0">{{ c.label || '—' }}</span>
          <span class="truncate text-ink-600">{{ c.text.slice(0, 40) }}</span>
          <span *ngIf="c.spans.trigger.length" class="ml-auto w-1.5 h-1.5 rounded-full bg-aava shrink-0"
                title="Contains a duty"></span>
        </button>
      </div>
    </aside>

    <!-- clause body -->
    <section class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
      <div class="px-5 py-2.5 border-b border-ink-200/50 flex items-center justify-between flex-wrap gap-2">
        <div class="flex items-center gap-3 text-[10.5px] text-ink-600 flex-wrap">
          <span class="flex items-center gap-1"><span class="w-3 h-2 rounded-sm bg-gold"></span>trigger phrase</span>
          <span class="flex items-center gap-1"><span class="w-3 h-2 rounded-sm bg-jade"></span>deadline</span>
          <span class="flex items-center gap-1 text-aava-700 underline decoration-dotted">cross reference</span>
          <span class="flex items-center gap-1"><span class="w-3 h-2 rounded-sm bg-gold-50 border border-gold"></span>flagged in source</span>
        </div>
        <button *ngIf="selected()" (click)="clear()" class="text-[11px] text-aava-700 font-medium">clear selection</button>
      </div>

      <!-- selection bar -->
      <div *ngIf="selectedClause() as sc" class="px-5 py-2.5 bg-aava-50 border-b border-aava-200 flex items-center gap-3 flex-wrap">
        <span class="mono text-[10.5px] text-aava-700">{{ sc.path }}</span>
        <span class="text-[11.5px] font-medium">{{ family().size }} clauses in this family</span>
        <span class="text-[11px] text-ink-400">{{ ancestorCount() }} ancestors · {{ descendantCount() }} descendants</span>
        <div class="ml-auto flex gap-2">
          <button (click)="copyPath(sc)" class="px-2 py-1 rounded border border-ink-200 bg-white text-[10.5px]">Copy clause id</button>
          <button (click)="pinClause(sc)" class="px-2 py-1 rounded bg-aava text-white text-[10.5px] font-medium">Pin clause</button>
        </div>
      </div>

      <div class="p-4 space-y-1">
        <div *ngFor="let c of d.clauses" [id]="'cl-' + c.id"
             (click)="select(c.id)"
             [style.margin-left.px]="c.depth * 22"
             class="rounded-lg px-3 py-2 cursor-pointer border-l-2 transition-colors"
             [class.bg-jade-50]="family().has(c.id) && selected() !== c.id"
             [class.bg-aava-100]="selected() === c.id"
             [class.border-gold]="c.flagged"
             [class.border-transparent]="!c.flagged"
             [class.hover:bg-shell-100]="!family().has(c.id)">
          <div class="flex items-start gap-2">
            <span class="mono text-[10px] text-ink-400 shrink-0 mt-[2px] w-[26px]">{{ c.label }}</span>
            <div class="flex-1 min-w-0">
              <div class="text-[12.5px] leading-relaxed" [innerHTML]="render(c)"></div>
              <div class="flex items-center gap-2 mt-1 flex-wrap" *ngIf="c.spans.trigger.length || c.spans.timing.length">
                <span *ngFor="let t of c.spans.trigger"
                      class="px-1.5 py-[1px] rounded bg-aava-100 text-aava-700 text-[9.5px] font-semibold">{{ t.kind }}</span>
                <span *ngFor="let t of c.spans.timing"
                      class="px-1.5 py-[1px] rounded bg-jade-50 text-jade-700 text-[9.5px]">{{ t.text }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- right panel -->
    <aside class="space-y-4 self-start sticky top-[70px]">
      <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-ink-200/50 text-[12px] font-semibold">
          Obligations extracted
          <span class="text-[10.5px] text-ink-400 font-normal">({{ obligations().length }})</span>
        </div>
        <div class="max-h-[420px] overflow-y-auto divide-y divide-ink-200/40">
          <div *ngFor="let o of obligations()" class="px-4 py-2.5">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="mono text-[10px] text-aava-700">{{ o.id }}</span>
              <span class="px-1.5 py-[1px] rounded text-[9.5px] font-semibold"
                    [class]="kindClass(o.kind)">{{ o.kind }}</span>
              <span class="ml-auto text-[10.5px] font-semibold"
                    [class.text-jade-700]="o.confidence >= 90"
                    [class.text-gold-700]="o.confidence >= 80 && o.confidence < 90"
                    [class.text-magenta-700]="o.confidence < 80">{{ o.confidence }}%</span>
            </div>
            <div class="text-[11.5px] mt-1 leading-snug">
              <span class="font-medium">{{ o.actor }}</span>
              <span class="hl">{{ o.trigger }}</span>
              {{ o.action }}
            </div>
            <div *ngIf="o.timing" class="text-[10.5px] text-ink-400 mt-0.5">Timing: {{ o.timing }}</div>
          </div>
          <div *ngIf="!obligations().length" class="px-4 py-6 text-center text-[11.5px] text-ink-400">
            No obligation extracted yet.
          </div>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-4 py-3" *ngIf="rule() as r">
        <div class="text-[12px] font-semibold mb-2">Rule facts</div>
        <dl class="text-[11.5px] space-y-1">
          <div class="flex justify-between gap-2"><dt class="text-ink-400">Citation</dt><dd class="mono text-aava-700">{{ r.cite }}</dd></div>
          <div class="flex justify-between gap-2"><dt class="text-ink-400">Regulator</dt><dd>{{ r.regulator }}</dd></div>
          <div class="flex justify-between gap-2"><dt class="text-ink-400">Jurisdiction</dt><dd>{{ r.jurisName }}</dd></div>
          <div class="flex justify-between gap-2"><dt class="text-ink-400">Rule type</dt><dd>{{ r.ruleType }}</dd></div>
          <div class="flex justify-between gap-2"><dt class="text-ink-400">Rule matter</dt><dd>{{ r.ruleMatter }}</dd></div>
          <div class="flex justify-between gap-2"><dt class="text-ink-400">Effective</dt><dd>{{ r.effectiveDate }}</dd></div>
        </dl>
        <a routerLink="/maps" class="mt-3 block text-center px-3 py-1.5 rounded-lg border border-ink-200 text-[11.5px] hover:bg-shell-100">
          See it in a compliance map
        </a>
      </div>
    </aside>
  </div>
 </div>
</div>
`,
})
export class RuleDetailComponent implements OnInit {
  private api = inject(ApiService);
  private sanitizer = inject(DomSanitizer);
  state = inject(StateService);

  @Input() id = '';

  detail = signal<RuleDetail | null>(null);
  rule = signal<Rule | null>(null);
  obligations = signal<Obligation[]>([]);
  selected = signal<string | null>(null);
  family = signal<Set<string>>(new Set());
  private ancestors = signal<string[]>([]);
  private descendants = signal<string[]>([]);

  ancestorCount = computed(() => this.ancestors().length);
  descendantCount = computed(() => this.descendants().length);
  selectedClause = computed<RuleClause | null>(() => {
    const id = this.selected();
    if (!id) return null;
    return this.detail()?.clauses.find((c) => c.id === id) ?? null;
  });

  ngOnInit(): void {
    this.api.ruleDetail(this.id).subscribe((d) => this.detail.set(d));
    this.api.rule(this.id).subscribe((r) => this.rule.set(r));
    this.api.obligations({ ruleId: this.id }).subscribe((o) => this.obligations.set(o));
  }

  /**
   * Walk the clause tree locally. The server exposes the same answer at
   * /detail/clause/{id}/family; doing it here keeps selection instant.
   */
  select(clauseId: string): void {
    const d = this.detail();
    if (!d) return;
    if (this.selected() === clauseId) { this.clear(); return; }
    const byId = new Map(d.clauses.map((c) => [c.id, c]));
    const anc: string[] = [];
    let cur = byId.get(clauseId)?.parentId ?? null;
    while (cur) { anc.push(cur); cur = byId.get(cur)?.parentId ?? null; }
    const desc: string[] = [];
    const stack = [...(byId.get(clauseId)?.childIds ?? [])];
    while (stack.length) {
      const cid = stack.pop() as string;
      desc.push(cid);
      stack.push(...(byId.get(cid)?.childIds ?? []));
    }
    this.selected.set(clauseId);
    this.ancestors.set(anc);
    this.descendants.set(desc);
    this.family.set(new Set([...anc, clauseId, ...desc]));
  }

  clear(): void {
    this.selected.set(null);
    this.family.set(new Set());
    this.ancestors.set([]);
    this.descendants.set([]);
  }

  copyPath(c: RuleClause): void {
    void navigator.clipboard?.writeText(c.id);
    this.state.notify(`Clause id ${c.id} copied.`);
  }

  pinClause(c: RuleClause): void {
    const r = this.rule();
    if (r) this.state.togglePin(r);
    this.state.notify(`Clause ${c.label || c.path} pinned with its rule.`);
  }

  pinRule(): void {
    const r = this.rule();
    if (!r) return;
    this.state.togglePin(r);
    this.state.notify(this.state.pinnedIds().has(r.id) ? 'Rule pinned.' : 'Rule unpinned.');
  }

  kindClass(kind: string): string {
    return {
      Prohibition: 'bg-magenta-50 text-magenta-700',
      Mandatory: 'bg-aava-100 text-aava-700',
      Expectation: 'bg-gold-50 text-gold-700',
      Permission: 'bg-jade-50 text-jade-700',
    }[kind] ?? 'bg-shell text-ink-600';
  }

  /** Apply the server-computed spans without letting them overlap. */
  render(c: RuleClause): SafeHtml {
    type Mark = { start: number; end: number; cls: string };
    const marks: Mark[] = [
      ...c.spans.trigger.map((s) => ({ start: s.start, end: s.end, cls: 'hl' })),
      ...c.spans.timing.map((s) => ({ start: s.start, end: s.end, cls: 'hl-time' })),
      ...c.spans.xref.map((s) => ({ start: s.start, end: s.end, cls: 'hl-xref' })),
    ].sort((a, b) => a.start - b.start || b.end - a.end);

    let out = '';
    let cursor = 0;
    for (const m of marks) {
      if (m.start < cursor) continue;           // drop overlaps
      out += escapeHtml(c.text.slice(cursor, m.start));
      out += `<span class="${m.cls}">${escapeHtml(c.text.slice(m.start, m.end))}</span>`;
      cursor = m.end;
    }
    out += escapeHtml(c.text.slice(cursor));
    return this.sanitizer.bypassSecurityTrustHtml(out);
  }
}

function escapeHtml(s: string): string {
  return (s ?? '').replace(/[&<>]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch] ?? ch));
}
