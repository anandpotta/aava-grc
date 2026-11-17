import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';
import { KeywordNode, Rule, SearchHit, SearchResponse } from '../../core/models';

type GroupKey = 'ruleType' | 'ruleMatter' | 'juris';

@Component({
  selector: 'aava-reg-search',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
<div class="p-5">
 <div class="max-w-[1180px] mx-auto">

  <!-- hero -->
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-6 pt-5 pb-5">
    <div class="flex items-center justify-center gap-1 mb-4">
      <button *ngFor="let d of domains()" [disabled]="!d.enabled" (click)="domain.set(d.id)"
        class="relative px-5 py-2 text-[13px] font-medium rounded-t-lg border-b-2 transition"
        [class.border-aava]="domain() === d.id" [class.text-aava-700]="domain() === d.id"
        [class.border-transparent]="domain() !== d.id"
        [class.text-ink-600]="domain() !== d.id && d.enabled"
        [class.text-ink-200]="!d.enabled" [class.cursor-not-allowed]="!d.enabled">
        {{ d.label }}
        <span *ngIf="!d.enabled" class="ml-1.5 px-1.5 py-0.5 rounded bg-shell text-ink-400 text-[9px] font-semibold align-middle">SOON</span>
      </button>
    </div>

    <div class="text-center mb-3">
      <h1 class="text-[20px] font-semibold tracking-tight">Search the regulatory universe</h1>
      <p class="text-[12.5px] text-ink-400 mt-0.5">
        {{ counts()['rules'] || 0 }} rules · {{ jurisdictionCount() }} jurisdictions · keyword, semantic and citation search
      </p>
    </div>

    <div class="relative">
      <input [(ngModel)]="query" (keydown.enter)="run()"
        placeholder="e.g. verify beneficial owner before onboarding, or 31 CFR 1010.230"
        class="w-full pl-4 pr-[112px] py-3.5 rounded-xl border border-ink-200 text-[14px] ring-focus bg-shell-100" />
      <button (click)="run()"
        class="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 rounded-lg bg-aava text-white text-[12.5px] font-semibold hover:bg-aava-600">
        Search
      </button>
    </div>

    <div *ngIf="hierChips().length" class="mb-3 flex items-center gap-1.5 flex-wrap text-[11.5px]"><span class="text-ink-400">Browsing</span>
      <span *ngFor="let c of hierChips()" class="px-2 py-0.5 rounded-full bg-aava-100 text-aava-900 flex items-center gap-1">{{ c[1] }}<button (click)="dropHier(c[0])" aria-label="Remove filter">&times;</button></span></div>
    <!-- filters -->
    <div class="flex flex-wrap items-end gap-3 mt-3.5">
      <div class="min-w-[230px] flex-1">
        <label class="block text-[10.5px] font-semibold text-ink-400 tracking-[.06em] mb-1">RULE MATTER</label>
        <select [(ngModel)]="ruleMatter" (change)="run()"
          class="w-full px-3 py-2 rounded-lg border border-ink-200 text-[12.5px] bg-white ring-focus">
          <option value="">All rule matters</option>
          <option *ngFor="let m of ruleMatters()" [value]="m">{{ m }}</option>
        </select>
      </div>
      <div class="min-w-[200px] flex-1">
        <label class="block text-[10.5px] font-semibold text-ink-400 tracking-[.06em] mb-1">RULE TYPE</label>
        <select [(ngModel)]="ruleType" (change)="run()"
          class="w-full px-3 py-2 rounded-lg border border-ink-200 text-[12.5px] bg-white ring-focus">
          <option value="">All rule types</option>
          <option *ngFor="let t of ruleTypes()" [value]="t">{{ t }}</option>
        </select>
      </div>
      <div class="min-w-[150px]">
        <label class="block text-[10.5px] font-semibold text-ink-400 tracking-[.06em] mb-1">GROUP BY</label>
        <div (dragover)="$event.preventDefault()" (drop)="dropGroup($event)"
             class="min-h-[36px] px-2 py-1.5 rounded-lg border border-dashed text-[11.5px] flex items-center gap-1.5 flex-wrap"
             [class]="groupBy.length ? 'border-aava bg-aava-50/50' : 'border-ink-200 text-ink-400'">
          <span *ngIf="!groupBy.length">Drag a column heading here</span>
          <span *ngFor="let g of groupBy" class="px-2 py-0.5 rounded-full bg-aava text-white text-[10.5px] flex items-center gap-1">{{ colLabel(g) }}
            <button (click)="ungroup(g)" class="opacity-80 hover:opacity-100" aria-label="Remove grouping">&times;</button></span>
        </div>
      </div>
      <button (click)="clear()" class="px-3 py-2 rounded-lg border border-ink-200 text-[12px] text-ink-600 hover:bg-shell-100">Clear</button>
    </div>

    <div class="flex flex-wrap gap-1.5 mt-3">
      <span class="text-[11px] text-ink-400 mr-1 self-center">Try:</span>
      <button *ngFor="let s of samples" (click)="query = s; run()"
        class="px-2.5 py-1 rounded-full bg-shell text-[11px] text-ink-600 hover:bg-aava-100 hover:text-aava-700">{{ s }}</button>
    </div>
  </div>

  <!-- keyword map -->
  <div *ngIf="res() as r" class="mt-4">
    <div *ngIf="r.keywordMap.length" class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden fadein">
      <div class="px-5 py-2.5 border-b border-ink-200/50 flex items-center justify-between flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <span class="text-[12.5px] font-semibold">Keyword map</span>
          <span class="text-[11px] text-ink-400">semantic expansion of your query, with hit counts across {{ r.total }} rules</span>
        </div>
        <div class="flex items-center gap-3 text-[10.5px] text-ink-400">
          <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-gold"></span>primary term</span>
          <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-aava"></span>semantic match</span>
        </div>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-[300px_1fr]">
        <div class="p-2 border-r border-ink-200/50 bg-shell-100">
          <svg viewBox="0 0 300 216" class="w-full h-[216px]">
            <line *ngFor="let n of kwNodes()" [attr.x1]="150" [attr.y1]="108" [attr.x2]="n.x" [attr.y2]="n.y"
                  stroke="#D6D6F3" stroke-width="1.2" />
            <circle cx="150" cy="108" r="30" fill="#6666CC" />
            <text x="150" y="106" text-anchor="middle" fill="#fff" font-size="9.5" font-weight="600">QUERY</text>
            <text x="150" y="117" text-anchor="middle" fill="#D6D6F3" font-size="8">{{ r.total }} hits</text>
            <g *ngFor="let n of kwNodes()">
              <circle [attr.cx]="n.x" [attr.cy]="n.y" [attr.r]="n.r"
                      [attr.fill]="n.primary ? '#FFF6D6' : '#EEEEFA'"
                      [attr.stroke]="n.primary ? '#FFCC00' : '#6666CC'" stroke-width="1.3" />
              <text [attr.x]="n.x" [attr.y]="n.y + 3" text-anchor="middle" font-size="8.5" font-weight="600"
                    [attr.fill]="n.primary ? '#8A6D00' : '#43439B'">{{ n.count }}</text>
              <text [attr.x]="n.x" [attr.y]="n.labelY" text-anchor="middle" font-size="7.8" fill="#4A4A52">{{ n.short }}</text>
            </g>
          </svg>
        </div>
        <div class="p-4">
          <div class="flex flex-wrap gap-1.5 mb-3">
            <button *ngFor="let k of r.keywordMap" (click)="addTerm(k.term)"
              class="px-2.5 py-1 rounded-full text-[11.5px] font-medium border hover:bg-white"
              [class]="k.primary ? 'bg-gold-50 border-gold/50 text-gold-700' : 'bg-aava-50 border-aava-200 text-aava-700'">
              {{ k.term }} <span class="opacity-60">{{ k.count }}</span>
            </button>
          </div>
          <div *ngIf="r.concepts.length; else noConcept" class="text-[11.5px] text-ink-600 leading-relaxed">
            <span class="font-medium">Concepts recognised:</span>
            <span *ngFor="let c of r.concepts" class="inline-block mr-2">
              <span class="font-medium text-aava-700">{{ c.root }}</span> &rarr; {{ c.terms.slice(0, 4).join(', ') }}
            </span>
            <div class="mt-2 text-ink-400">
              AAVA searched for these related phrases as well as your exact words, which is why rules that never use your wording still appear.
            </div>
          </div>
          <ng-template #noConcept>
            <div class="text-[11.5px] text-ink-400">No semantic concept matched. Results are keyword and citation matches only.</div>
          </ng-template>
        </div>
      </div>
    </div>
  </div>

  <!-- results -->
  <div *ngIf="res() as r" class="mt-4">
    <div *ngIf="r.results.length; else empty"
         class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden fadein">
      <div class="px-5 py-3 border-b border-ink-200/50 flex items-center justify-between flex-wrap gap-2">
        <div>
          <span class="text-[13px] font-semibold">{{ r.total }} rules</span>
          <span class="text-[11.5px] text-ink-400 ml-2">{{ groupBy.length ? 'grouped by ' + groupLabel() + ' · ' + groups().length + ' groups' : 'not grouped · drag a column heading into Group by' }}</span>
        </div>
        <div class="flex items-center gap-2">
          <button (click)="pinAll()" class="px-3 py-1.5 rounded-lg border border-ink-200 text-[11.5px] hover:bg-shell-100">Pin all results</button>
          <a routerLink="/rulebooks" class="px-3 py-1.5 rounded-lg bg-aava text-white text-[11.5px] font-semibold hover:bg-aava-600">
            Create rulebook ({{ state.pinnedCount() }})
          </a>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-[12px]" style="min-width:1000px">
          <thead class="bg-shell-100 text-ink-400 text-[10.5px]">
            <tr>
              <th class="w-[46px] px-3 py-2 text-left font-semibold">PIN</th>
              <th class="w-[150px] px-3 py-2 text-left font-semibold cursor-grab select-none" draggable="true" (dragstart)="$event.dataTransfer?.setData('text/plain', 'ruleType')" title="Drag into Group by">RULE TYPE ⠿</th>
              <th class="w-[160px] px-3 py-2 text-left font-semibold cursor-grab select-none" draggable="true" (dragstart)="$event.dataTransfer?.setData('text/plain', 'ruleMatter')" title="Drag into Group by">RULE MATTER ⠿</th>
              <th class="px-3 py-2 text-left font-semibold">RULE AND DESCRIPTION</th>
              <th class="w-[100px] px-3 py-2 text-left font-semibold cursor-grab select-none" draggable="true" (dragstart)="$event.dataTransfer?.setData('text/plain', 'juris')" title="Drag into Group by">JURISDICTION ⠿</th>
              <th class="w-[78px] px-3 py-2 text-left font-semibold">OBLIG.</th>
              <th class="w-[72px] px-3 py-2 text-left font-semibold">SCORE</th>
            </tr>
          </thead>
          <tbody>
            <ng-container *ngFor="let g of groups()">
              <tr *ngIf="groupBy.length" class="bg-aava-50/70 border-y border-aava-200/60">
                <td colspan="7" class="px-3 py-1.5">
                  <button (click)="toggle(g.key)" class="flex items-center gap-2 text-[11.5px] font-semibold text-aava-900">
                    <span class="inline-block transition-transform" [class.rotate-90]="!collapsed().has(g.key)">&rsaquo;</span>
                    {{ g.key }}
                    <span class="px-1.5 py-0.5 rounded-full bg-white text-aava-700 text-[10px] font-semibold">{{ g.items.length }}</span>
                  </button>
                </td>
              </tr>
              <ng-container *ngIf="!groupBy.length || !collapsed().has(g.key)">
                <tr *ngFor="let h of g.items" class="border-b border-ink-200/40 align-top hover:bg-shell-100/60">
                  <td class="px-3 py-2.5">
                    <button (click)="state.togglePin(h.rule)" [title]="isPinned(h.rule.id) ? 'Unpin' : 'Pin to rulebook'" [attr.aria-label]="isPinned(h.rule.id) ? 'Unpin' : 'Pin to rulebook'"
                      class="w-7 h-7 rounded-lg flex items-center justify-center border"
                      [class]="isPinned(h.rule.id) ? 'bg-gold-50 text-gold-700 border-gold/50' : 'text-ink-200 hover:text-aava hover:bg-aava-50 border-transparent'">
                      <svg class="w-[15px] h-[15px]" viewBox="0 0 24 24" [attr.fill]="isPinned(h.rule.id) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" aria-hidden="true"><path d="M14 2l8 8-3.2 1.1L15.6 18 12 13.3 7 18.3l-1.3-1.3 5-5L6 8.4z"/></svg>
                    </button>
                  </td>
                  <td class="px-3 py-2.5"><span class="px-1.5 py-[2px] rounded bg-shell text-ink-600 text-[10.5px] font-medium">{{ h.rule.ruleType }}</span></td>
                  <td class="px-3 py-2.5 text-[11.5px] text-ink-600">{{ h.rule.ruleMatter }}</td>
                  <td class="px-3 py-2.5">
                    <a [routerLink]="['/rules', h.rule.id]" class="font-medium text-[12.5px] leading-snug hover:text-aava-700"
                       [innerHTML]="mark(h.rule.title, h.hits)"></a>
                    <div class="flex items-center gap-2 mt-0.5 mb-1 flex-wrap">
                      <span class="mono text-[10.5px] text-aava-700">{{ h.rule.cite }}</span>
                      <span class="text-ink-200">·</span><span class="text-[10.5px] text-ink-400">{{ h.rule.regulator }}</span>
                      <span class="text-ink-200">·</span><span class="text-[10.5px] text-ink-400">effective {{ h.rule.effectiveDate }}</span>
                      <span class="px-1.5 py-[1px] rounded border text-[10px] font-medium" [class]="sevClass(h.rule.severity)">{{ h.rule.severity }}</span>
                    </div>
                    <div class="text-[11.5px] text-ink-600 leading-relaxed" [innerHTML]="mark(h.rule.text, h.hits)"></div>
                  </td>
                  <td class="px-3 py-2.5">
                    <span class="px-1.5 py-[2px] rounded bg-ink-200/40 text-ink-600 text-[10px] font-bold">{{ state.jurisShort(h.rule.juris) }}</span>
                    <div class="text-[10.5px] text-ink-400 mt-0.5">{{ h.rule.jurisName }}</div>
                  </td>
                  <td class="px-3 py-2.5"><span class="text-[12px] font-semibold">{{ h.rule.obligationCount }}</span></td>
                  <td class="px-3 py-2.5">
                    <div class="h-1.5 rounded-full bg-shell overflow-hidden">
                      <div class="h-full bg-aava" [style.width.%]="barWidth(h.score)"></div>
                    </div>
                    <div class="text-[10px] text-ink-400 mt-1">{{ h.score.toFixed(1) }}</div>
                  </td>
                </tr>
              </ng-container>
            </ng-container>
          </tbody>
        </table>
      </div>
    </div>
    <ng-template #empty>
      <div class="bg-white rounded-2xl border border-ink-200/50 p-10 text-center">
        <div class="text-[13px] font-medium">No rules matched</div>
        <div class="text-[12px] text-ink-400 mt-1">Widen the rule matter or rule type filter, or clear the jurisdiction.</div>
      </div>
    </ng-template>
  </div>
 </div>
</div>
`,
})
export class RegSearchComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  state = inject(StateService);

  query = '';
  ruleMatter = '';
  ruleType = '';
  groupBy: GroupKey[] = [];              // ungrouped until the user drags a column in
  hier = signal<Record<string, string>>({});
  domain = signal('banking');

  res = signal<SearchResponse | null>(null);
  collapsed = signal<Set<string>>(new Set());
  private juris = signal<string | null>(null);
  hierKeys = ['regulator', 'instrument', 'part'];
  private framework = signal<string | null>(null);

  samples = [
    'verify beneficial owner before onboarding',
    'suspicious transaction report deadline',
    'outsourcing exit plan critical vendor',
    'payment data stored in India',
    'impact tolerance scenario testing',
    'record retention 25 months',
  ];

  domains = computed(() => this.state.reference()?.domains ?? []);
  ruleMatters = computed(() => this.state.reference()?.ruleMatters ?? []);
  ruleTypes = computed(() => this.state.reference()?.ruleTypes ?? []);
  counts = computed(() => this.state.reference()?.counts ?? {});
  jurisdictionCount = computed(() => this.state.reference()?.jurisdictions.length ?? 0);

  ngOnInit(): void {
    this.route.queryParamMap.subscribe((p) => {
      this.juris.set(p.get('juris'));
      this.framework.set(p.get('framework'));
      this.hier.set(Object.fromEntries(this.hierKeys.filter((k) => p.get(k)).map((k) => [k, p.get(k) as string])));
      const q = p.get('q');
      if (q !== null) this.query = q;
      this.run();
    });
  }

  run(): void {
    this.api
      .search(this.query, {
        juris: this.juris(), framework: this.framework(),
        ruleMatter: this.ruleMatter, ruleType: this.ruleType,
        regulator: this.hier()['regulator'], instrument: this.hier()['instrument'], part: this.hier()['part'],
      })
      .subscribe((r) => this.res.set(r));
  }

  clear(): void {
    this.query = ''; this.ruleMatter = ''; this.ruleType = '';
    this.router.navigate(['/search'], { queryParams: {} });
  }

  addTerm(t: string): void { this.query = `${this.query} ${t}`.trim(); this.run(); }

  colLabel = (g: GroupKey) => ({ ruleType: 'Rule type', ruleMatter: 'Rule matter', juris: 'Jurisdiction' }[g]);
  groupLabel(): string { return this.groupBy.map((g) => this.colLabel(g).toLowerCase()).join(' › '); }
  dropGroup(e: DragEvent): void {
    e.preventDefault();
    const k = e.dataTransfer?.getData('text/plain') as GroupKey;
    if (['ruleType', 'ruleMatter', 'juris'].includes(k) && !this.groupBy.includes(k)) this.groupBy = [...this.groupBy, k];
  }
  ungroup(g: GroupKey): void { this.groupBy = this.groupBy.filter((x) => x !== g); }
  hierChips(): Array<[string, string]> { return Object.entries(this.hier()); }
  dropHier(k: string): void {
    const q: Record<string, string> = { ...this.hier() };
    delete q[k];
    if (k === 'regulator') { delete q['instrument']; delete q['part']; }
    if (k === 'instrument') delete q['part'];
    if (this.juris()) q['juris'] = this.juris() as string;
    this.router.navigate(['/search'], { queryParams: q });
  }

  groups(): Array<{ key: string; items: SearchHit[] }> {
    const r = this.res();
    if (!r) return [];
    if (!this.groupBy.length) return [{ key: 'All rules', items: r.results }];
    const map = new Map<string, SearchHit[]>();
    for (const h of r.results) {
      const key = this.groupBy.map((g) => (g === 'juris' ? h.rule.jurisName : (h.rule[g] as string))).join(' › ');
      const arr = map.get(key) ?? [];
      arr.push(h);
      map.set(key, arr);
    }
    return [...map.entries()]
      .map(([key, items]) => ({ key, items }))
      .sort((a, b) => b.items.length - a.items.length);
  }

  toggle(key: string): void {
    const s = new Set(this.collapsed());
    s.has(key) ? s.delete(key) : s.add(key);
    this.collapsed.set(s);
  }

  kwNodes(): Array<KeywordNode & { x: number; y: number; r: number; labelY: number; short: string }> {
    const list = this.res()?.keywordMap ?? [];
    const peak = list[0]?.count ?? 1;
    return list.map((k, i) => {
      const a = (i / list.length) * Math.PI * 2 - Math.PI / 2;
      const rr = 86 * (0.62 + 0.38 * (1 - k.count / peak));
      const x = 150 + Math.cos(a) * rr;
      const y = 108 + Math.sin(a) * rr;
      return {
        ...k, x, y,
        r: 8 + Math.min(9, k.count * 0.55),
        labelY: y + (y < 108 ? -16 : 24),
        short: k.term.length > 22 ? k.term.slice(0, 22) : k.term,
      };
    });
  }

  isPinned(id: string): boolean { return this.state.pinnedIds().has(id); }
  pinAll(): void {
    const rules: Rule[] = (this.res()?.results ?? []).map((h) => h.rule);
    this.state.pinMany(rules);
    this.state.notify(`${this.state.pinnedCount()} rules pinned.`);
  }
  barWidth(score: number): number { return Math.min(100, score * 9); }

  sevClass(sev: string): string {
    return {
      Critical: 'bg-magenta-50 text-magenta-700 border-magenta/30',
      High: 'bg-gold-50 text-gold-700 border-gold/40',
      Medium: 'bg-aava-100 text-aava-700 border-aava-200',
      Low: 'bg-jade-50 text-jade-700 border-jade/30',
    }[sev] ?? 'bg-shell text-ink-600 border-ink-200';
  }

  /** Highlight the matched terms the API reported, so the user sees why a rule surfaced. */
  mark(text: string, hits: string[]): string {
    let out = text.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c] ?? c));
    const uniq = [...new Set(hits)].filter((h) => h.length > 2).sort((a, b) => b.length - a.length);
    uniq.slice(0, 14).forEach((h) => {
      const rx = new RegExp(`(?![^<]*>)(${h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      out = out.replace(rx, '<mark class="hl">$1</mark>');
    });
    return out;
  }
}
