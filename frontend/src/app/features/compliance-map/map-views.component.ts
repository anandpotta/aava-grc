import { Component, Input, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SankeyGraph, SankeyLinkDto, SankeyNodeDto } from '../../core/models';

type Cov = 'Covered' | 'Partial' | 'Gap';
interface PathRow { nodes: SankeyNodeDto[]; cov: Cov; }
const RANK: Record<Cov, number> = { Covered: 0, Partial: 1, Gap: 2 };
const COL: Record<Cov, string> = { Covered: '#00A67E', Partial: '#E0A800', Gap: '#CC0066' };
const worse = (a: Cov | undefined, b: Cov): Cov => (!a || RANK[b] > RANK[a] ? b : a);
const trunc = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
const health = (ps: PathRow[]) => Math.round((100 * ps.reduce((a, p) => a + (p.cov === 'Covered' ? 1 : p.cov === 'Partial' ? 0.5 : 0), 0)) / Math.max(1, ps.length));
const linkCov = (ls: SankeyLinkDto[]): Cov => {
  let c: Cov = 'Covered';
  for (const l of ls) { if (l.placeholder || l.band === 'Unmapped' || l.band === 'Minimal') return 'Gap'; if (l.band === 'Partial') c = 'Partial'; }
  return c;
};

/** Layered trace, coverage matrix and roll-up views of one compliance map, plus a detail table you can group by dragging headings. */
@Component({
  selector: 'aava-map-views',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
<div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden" *ngIf="g() as graph">
  <div class="px-5 py-2 border-b border-ink-200/50 flex items-center gap-3 text-[11px] text-ink-600 flex-wrap">
    <span class="flex-1">{{ hint() }}</span>
    <span *ngIf="focus().length" class="px-2 py-0.5 rounded-full bg-aava-50 text-aava-900 text-[10.5px]">Showing {{ shown().length }} of {{ paths().length }} paths <button (click)="focus.set([])" class="text-aava-700 hover:underline ml-1">Clear</button></span>
  </div>
  <div class="p-3 bg-shell-100/30">
    <div *ngIf="!paths().length" class="py-12 text-center text-[12.5px] text-ink-400">No traced paths in this map.</div>

    <!-- layered trace -->
    <div *ngIf="mode()==='dag' && paths().length" style="max-height:660px" class="overflow-auto rounded-xl bg-white border border-ink-200/50">
      <svg [attr.width]="dag().W" [attr.height]="dag().H">
        <rect *ngFor="let h of dag().heads" [attr.x]="h.x-8" y="0" [attr.width]="170+16" [attr.height]="dag().H" rx="8" fill="#6666CC" opacity=".045"/>
        <ng-container *ngFor="let h of dag().heads"><text [attr.x]="h.x" y="18" font-size="11.5" font-weight="700" fill="#4a4aa8">{{ h.label.toUpperCase() }}</text><text [attr.x]="h.x" y="33" font-size="9.5" fill="#6b6b80">{{ h.count }} nodes</text></ng-container>
        <path *ngFor="let l of dag().links" [attr.d]="l.d" fill="none" [attr.stroke]="l.col" [attr.stroke-width]="l.on && focus().length ? 2.4 : 1.4" [attr.stroke-dasharray]="l.dashed ? '5 4' : null" [attr.opacity]="l.on ? (focus().length ? .95 : .55) : .07"/>
        <g *ngFor="let n of dag().nodes" style="cursor:pointer" [attr.opacity]="n.on ? 1 : .18" (click)="pick([n.uid])">
          <title>{{ n.layer }}: {{ n.name }} · {{ n.cov }}</title>
          <rect [attr.x]="n.x" [attr.y]="n.y" width="170" height="26" rx="6" [attr.fill]="n.sel ? '#EEF' : '#fff'" [attr.stroke]="n.col" [attr.stroke-width]="n.sel ? 3 : 2" [attr.stroke-dasharray]="n.hole ? '4 3' : null"/>
          <text [attr.x]="n.x+10" [attr.y]="n.y+11" font-size="10.5" font-weight="600" fill="#1d1d2b">{{ n.label }}</text>
          <text [attr.x]="n.x+10" [attr.y]="n.y+21" font-size="8.5" fill="#6b6b80">{{ n.sub }}</text></g>
      </svg></div>

    <!-- matrix -->
    <div *ngIf="mode()==='matrix' && paths().length">
      <div class="flex items-center gap-3 mb-2 flex-wrap text-[11px]">
        <select [ngModel]="mxA()" (ngModelChange)="mxA.set(+$event)" class="px-2 py-1.5 rounded-lg border border-ink-200 bg-white"><option *ngFor="let l of graph.layers" [ngValue]="l.index">{{ l.label }}</option></select>×
        <select [ngModel]="mxB()" (ngModelChange)="mxB.set(+$event)" class="px-2 py-1.5 rounded-lg border border-ink-200 bg-white"><option *ngFor="let l of graph.layers" [ngValue]="l.index">{{ l.label }}</option></select>
        <span><b [ngClass]="mx().orphR ? 'text-magenta-700' : 'text-jade-700'">{{ mx().orphR }}</b> of {{ mx().R.length }} rows have no real mapping</span>
        <span><b [ngClass]="mx().orphC ? 'text-magenta-700' : 'text-jade-700'">{{ mx().orphC }}</b> of {{ mx().C.length }} columns protect nothing or only gaps</span></div>
      <div style="max-height:660px" class="overflow-auto rounded-xl bg-white border border-ink-200/50 p-1">
        <svg [attr.width]="mx().W" [attr.height]="mx().H">
          <g *ngFor="let c of mx().cells" style="cursor:pointer" [attr.opacity]="c.on ? 1 : .15" (click)="pick([c.r, c.c])"><title>{{ c.t }}</title><rect [attr.x]="c.x" [attr.y]="c.y" width="17" height="17" rx="3" [attr.fill]="c.fill"/></g>
          <text *ngFor="let r of mx().rowL" [attr.x]="r.x" [attr.y]="r.y" text-anchor="end" font-size="10" [attr.fill]="r.orph ? '#CC0066' : '#1d1d2b'" [attr.font-weight]="r.orph ? 700 : 500" style="cursor:pointer" (click)="pick([r.uid])">{{ r.t }}</text>
          <text *ngFor="let c of mx().colL" [attr.transform]="c.tr" font-size="10" [attr.fill]="c.orph ? '#CC0066' : '#1d1d2b'" [attr.font-weight]="c.orph ? 700 : 500" style="cursor:pointer" (click)="pick([c.uid])">{{ c.t }}</text>
        </svg></div></div>

    <!-- roll-up -->
    <div *ngIf="mode()==='rollup' && paths().length">
      <div class="flex items-center gap-2 mb-2 text-[11px]"><button (click)="zoom.set('')" class="px-2 py-1 rounded border border-ink-200" [class.opacity-50]="!zoom()">All</button><span *ngIf="zoom()" class="text-ink-400">›</span><span class="font-medium">{{ zoomName() }}</span>
        <span class="ml-auto text-ink-400">Health = covered paths plus half of partial paths.</span></div>
      <div class="overflow-x-auto rounded-xl bg-white border border-ink-200/50 p-2"><svg [attr.width]="1240" [attr.height]="ru().H">
        <g *ngFor="let r of ru().rects" style="cursor:pointer" (click)="ruClick(r)"><title>{{ r.name }} · {{ r.h }}% healthy · {{ r.n }} paths</title>
          <rect [attr.x]="r.x+1" [attr.y]="r.y+1" [attr.width]="r.w-2" height="48" rx="5" [attr.fill]="r.bg" stroke="#fff"/>
          <ng-container *ngIf="r.w > 40"><text [attr.x]="r.x+7" [attr.y]="r.y+20" font-size="11" font-weight="600" [attr.fill]="r.fg">{{ r.label }}</text><text [attr.x]="r.x+7" [attr.y]="r.y+36" font-size="10" [attr.fill]="r.fg">{{ r.h }}% · {{ r.n }} paths</text></ng-container></g>
      </svg></div></div>
  </div>
</div>

<!-- detail table -->
<div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden" *ngIf="g() as graph">
  <div class="px-5 py-3 border-b border-ink-200/50 flex items-center justify-between flex-wrap gap-2"><div><span class="text-[13px] font-semibold">Detailed mapping table</span><span class="text-[11.5px] text-ink-400 ml-2">{{ rows().length }} mapped paths{{ group().length ? ' · grouped by ' + groupNames() : '' }}</span></div>
    <div class="flex items-center gap-2"><input [ngModel]="qs()" (ngModelChange)="qs.set($event)" placeholder="Filter any column" class="px-2.5 py-1.5 rounded-lg border border-ink-200 text-[11.5px] w-52"/><button (click)="csv()" class="px-3 py-1.5 rounded-lg border border-ink-200 text-[11.5px] hover:bg-shell-100">Download table (CSV)</button></div></div>
  <div class="px-5 py-2.5 border-b border-ink-200/50 flex items-center gap-2 text-[11px] text-ink-400"><span class="font-semibold text-ink-600">Group by</span>
    <div (dragover)="$event.preventDefault()" (drop)="drop($event)" class="flex-1 min-h-[34px] px-2 py-1 rounded-lg border border-dashed border-ink-200 flex items-center gap-1.5 flex-wrap">
      <span *ngIf="!group().length">Drag a column heading here to group</span>
      <span *ngFor="let k of group()" class="px-2 py-0.5 rounded-full bg-aava text-white text-[10.5px] flex items-center gap-1">{{ colName(k).toLowerCase() }}<button (click)="ungroup(k)" aria-label="Remove grouping">&times;</button></span></div></div>
  <div style="max-height:560px;overflow:auto"><table class="w-full" [style.min-width.px]="cols().length*170">
    <thead><tr class="bg-shell-100 text-ink-400 text-[10.5px]"><th *ngFor="let c of cols()" class="px-3 py-2 text-left font-semibold select-none cursor-grab whitespace-nowrap" draggable="true" (dragstart)="$event.dataTransfer?.setData('text/plain', c.k)" title="Drag into the group zone. Click to sort."><span (click)="sortBy(c.k)">{{ c.l }}{{ sort()===c.k ? (dir()>0 ? ' ▲' : ' ▼') : ' ⠿' }}</span></th></tr></thead>
    <tbody>
      <tr *ngIf="!rows().length"><td [attr.colspan]="cols().length" class="px-3 py-8 text-center text-ink-400 text-[12px]">No paths match.</td></tr>
      <ng-container *ngIf="!group().length"><tr *ngFor="let r of rows().slice(0,500)" class="border-b border-ink-200/40 align-top text-[11.5px] hover:bg-aava-50/40"><td *ngFor="let c of cols()" class="px-3 py-2"><ng-container *ngTemplateOutlet="cell; context:{c:c, r:r}"/></td></tr></ng-container>
      <ng-container *ngIf="group().length"><ng-container *ngFor="let gp of groups(); let i = index">
        <tr class="bg-aava-50/60 border-y border-ink-200/50 cursor-pointer" (click)="toggle(i)"><td [attr.colspan]="cols().length" class="px-3 py-1.5"><div class="flex items-center gap-2 text-[11.5px] font-semibold text-aava-900"><span>{{ closed()[i] ? '▸' : '▾' }}</span>{{ gp.key }}<span class="font-normal text-ink-400">{{ gp.items.length }} paths</span>
          <span class="flex h-1.5 w-24 rounded overflow-hidden bg-shell-100"><span class="bg-jade" [style.width.%]="100*gp.cov/gp.items.length"></span><span class="bg-gold" [style.width.%]="100*gp.par/gp.items.length"></span><span class="bg-magenta" [style.width.%]="100*gp.gap/gp.items.length"></span></span>
          <span [ngClass]="gp.h>=80 ? 'text-jade-700' : gp.h>=50 ? 'text-gold-700' : 'text-magenta-700'">{{ gp.h }}% healthy</span><span class="font-normal text-ink-400">{{ gp.gap }} gaps · {{ gp.par }} partial</span></div></td></tr>
        <ng-container *ngIf="!closed()[i]"><tr *ngFor="let r of gp.items.slice(0,200)" class="border-b border-ink-200/40 align-top text-[11.5px] hover:bg-aava-50/40"><td *ngFor="let c of cols()" class="px-3 py-2"><ng-container *ngTemplateOutlet="cell; context:{c:c, r:r}"/></td></tr></ng-container>
      </ng-container></ng-container>
    </tbody></table></div>
  <ng-template #cell let-c="c" let-r="r">
    <span *ngIf="c.k==='cov'" class="px-1.5 py-[1px] rounded text-[10px] font-semibold" [ngClass]="r.cov==='Gap' ? 'bg-magenta-50 text-magenta-700' : r.cov==='Partial' ? 'bg-gold-50 text-gold-700' : 'bg-jade-50 text-jade-700'">{{ r.cov }}</span>
    <span *ngIf="c.k!=='cov'" [ngClass]="isHole(val(r, c.k)) ? 'text-magenta-700 font-medium' : ''">{{ val(r, c.k) }}</span>
  </ng-template>
</div>`,
})
export class MapViewsComponent {
  g = signal<SankeyGraph | null>(null);
  mode = signal<string>('dag');
  @Input() set graph(v: SankeyGraph | null) { this.g.set(v); this.focus.set([]); this.zoom.set(''); const n = v?.layers.length ?? 0; this.mxA.set(0); this.mxB.set(Math.min(3, Math.max(0, n - 1))); }
  @Input() set view(v: string) { this.mode.set(v); this.focus.set([]); }
  focus = signal<string[]>([]);
  zoom = signal('');
  mxA = signal(0);
  mxB = signal(3);
  group = signal<string[]>([]);
  sort = signal<string | null>(null);
  dir = signal(1);
  closed = signal<Record<number, boolean>>({});
  qs = signal('');

  hint = computed(() => ({
    dag: 'Click any node to light up its full path and dim the rest. Red outline = gap, amber = partial, green = covered. Dashed line = a missing or broken link.',
    matrix: 'One square per mapping. An empty row or column is an orphan. Click a square to see the paths behind it.',
    rollup: 'Each block is sized by the paths it carries and coloured by health. Click a block to zoom in, the top block to zoom out.',
  } as Record<string, string>)[this.mode()] ?? '');

  /** Every end-to-end path through the map, parent layer to child layer. */
  paths = computed<PathRow[]>(() => {
    const g = this.g(); if (!g) return [];
    const by = new Map(g.nodes.map((n) => [n.uid, n])), out = new Map<string, SankeyLinkDto[]>(), hasIn = new Set<string>();
    g.links.forEach((l) => { (out.get(l.source) ?? out.set(l.source, []).get(l.source)!).push(l); hasIn.add(l.target); });
    const res: PathRow[] = [];
    const walk = (chain: SankeyNodeDto[], ls: SankeyLinkDto[]) => {
      if (res.length > 6000) return;
      const nx = out.get(chain[chain.length - 1].uid) ?? [];
      if (!nx.length) { if (chain.length > 1) res.push({ nodes: chain, cov: linkCov(ls) }); return; }
      nx.forEach((l) => { const t = by.get(l.target); if (t) walk([...chain, t], [...ls, l]); });
    };
    g.nodes.filter((n) => !hasIn.has(n.uid) && out.has(n.uid)).forEach((r) => walk([r], []));
    return res;
  });
  shown = computed(() => { const f = this.focus(); return f.length ? this.paths().filter((p) => f.every((u) => p.nodes.some((n) => n.uid === u))) : this.paths(); });
  status = computed(() => { const m = new Map<string, Cov>(); this.paths().forEach((p) => p.nodes.forEach((n) => m.set(n.uid, worse(m.get(n.uid), p.cov)))); return m; });
  isHole = (v: string) => /^(No |None|Unmapped)/i.test(v);
  pick(ids: string[]) { if (ids.some((i) => !i)) return; this.focus.set(JSON.stringify(this.focus()) === JSON.stringify(ids) ? [] : ids); }

  dag = computed(() => {
    const g = this.g()!, st = this.status(), f = this.focus(), fp = f.length ? this.shown() : null;
    const layers = [...g.layers].sort((a, b) => a.index - b.index), colW = 212, padT = 48, pad = 14, gap = 34;
    const lanes = layers.map((l) => g.nodes.filter((n) => n.layer === l.index));
    const lay = new Map<string, number>(), pos = new Map<string, number>(); lanes.forEach((a, k) => a.forEach((n, i) => { lay.set(n.uid, k); pos.set(n.uid, i); }));
    const nb = new Map<string, string[]>(); g.links.forEach((l) => { (nb.get(l.source) ?? nb.set(l.source, []).get(l.source)!).push(l.target); (nb.get(l.target) ?? nb.set(l.target, []).get(l.target)!).push(l.source); });
    const sweep = (k: number, d: number) => { const bc = (n: SankeyNodeDto) => { const ns = (nb.get(n.uid) ?? []).filter((x) => lay.get(x) === k + d); return ns.length ? ns.reduce((a, x) => a + pos.get(x)!, 0) / ns.length : pos.get(n.uid)!; }; lanes[k].sort((a, b) => bc(a) - bc(b)).forEach((n, i) => pos.set(n.uid, i)); };
    for (let it = 0; it < 3; it++) { for (let k = 1; k < lanes.length; k++) sweep(k, -1); for (let k = lanes.length - 2; k >= 0; k--) sweep(k, 1); }
    const H = padT + Math.max(1, ...lanes.map((a) => a.length)) * gap + 10, W = pad * 2 + lanes.length * colW;
    const xy = new Map<string, { x: number; y: number }>(); lanes.forEach((a, k) => a.forEach((n) => xy.set(n.uid, { x: pad + k * colW, y: padT + pos.get(n.uid)! * gap })));
    const fn = new Set<string>(), fl = new Set<string>();
    fp?.forEach((p) => { p.nodes.forEach((n) => fn.add(n.uid)); for (let i = 0; i < p.nodes.length - 1; i++) fl.add(p.nodes[i].uid + '>' + p.nodes[i + 1].uid); });
    const byU = new Map(g.nodes.map((n) => [n.uid, n]));
    const links = g.links.filter((l) => xy.has(l.source) && xy.has(l.target)).map((l) => {
      const a = xy.get(l.source)!, b = xy.get(l.target)!, x1 = a.x + 170, y1 = a.y + 13, x2 = b.x, y2 = b.y + 13, mx = (x1 + x2) / 2, c = linkCov([l]);
      return { d: `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`, col: COL[c], dashed: c === 'Gap', on: !fp || fl.has(l.source + '>' + l.target) };
    });
    const nodes = g.nodes.map((n) => { const p = xy.get(n.uid)!, c = st.get(n.uid) ?? 'Covered'; return { uid: n.uid, x: p.x, y: p.y, col: COL[c], cov: c, on: !fp || fn.has(n.uid), sel: f.includes(n.uid), hole: this.isHole(n.label || n.name), label: trunc(n.label || n.name, 24), sub: trunc(n.name, 32), name: n.name, layer: n.layerType }; });
    const heads = layers.map((l, k) => ({ x: pad + k * colW, label: l.label, count: lanes[k].length }));
    void byU;
    return { W, H, links, nodes, heads };
  });

  mx = computed(() => {
    const g = this.g()!, A = this.mxA(), B = this.mxB(), f = this.focus(), fp = f.length ? this.shown() : null;
    const at = (p: PathRow, layer: number) => p.nodes.find((n) => n.layer === layer);
    const rows = new Map<string, SankeyNodeDto>(), cols = new Map<string, SankeyNodeDto>(), cell = new Map<string, { cov: Cov; n: number }>(), rc = new Map<string, Set<string>>(), cr = new Map<string, Set<string>>();
    this.paths().forEach((p) => { const r = at(p, A), c = at(p, B); if (!r || !c) return; rows.set(r.uid, r); cols.set(c.uid, c); const k = r.uid + '§' + c.uid, o = cell.get(k) ?? { cov: p.cov, n: 0 }; o.cov = worse(o.cov, p.cov); o.n++; cell.set(k, o); (rc.get(r.uid) ?? rc.set(r.uid, new Set()).get(r.uid)!).add(c.uid); (cr.get(c.uid) ?? cr.set(c.uid, new Set()).get(c.uid)!).add(r.uid); });
    const nm = (n: SankeyNodeDto) => n.label || n.name;
    const R = [...rows.values()].sort((a, b) => nm(a).localeCompare(nm(b))), C = [...cols.values()].sort((a, b) => Number(this.isHole(nm(a))) - Number(this.isHole(nm(b))) || nm(a).localeCompare(nm(b)));
    const orphR = new Set(R.filter((n) => [...rc.get(n.uid)!].every((c) => this.isHole(nm(cols.get(c)!))) || this.isHole(nm(n))).map((n) => n.uid));
    const orphC = new Set(C.filter((n) => this.isHole(nm(n)) || [...cr.get(n.uid)!].every((r) => cell.get(r + '§' + n.uid)!.cov === 'Gap')).map((n) => n.uid));
    const lw = 240, ch = 118, cs = 19, fcell = new Set<string>(); fp?.forEach((p) => { const r = at(p, A), c = at(p, B); if (r && c) fcell.add(r.uid + '§' + c.uid); });
    const cells: any[] = []; R.forEach((r, i) => C.forEach((c, j) => { const o = cell.get(r.uid + '§' + c.uid), x = lw + j * cs, y = ch + i * cs; cells.push(o ? { x, y, r: r.uid, c: c.uid, fill: COL[o.cov], on: !fp || fcell.has(r.uid + '§' + c.uid), t: `${nm(r)} → ${nm(c)}\n${o.n} path(s) · ${o.cov}` } : { x, y, r: '', c: '', fill: '#f3f3f8', on: true, t: '' }); }));
    return { R, C, orphR: orphR.size, orphC: orphC.size, W: lw + C.length * cs + 120, H: ch + R.length * cs + 10, cells: cells.filter((c) => true),
      rowL: R.map((r, i) => ({ uid: r.uid, x: lw - 8, y: ch + i * cs + cs - 6, t: trunc(nm(r), 40), orph: orphR.has(r.uid) })),
      colL: C.map((c, j) => ({ uid: c.uid, tr: `translate(${lw + j * cs + cs / 2},${ch - 6}) rotate(-58)`, t: trunc(nm(c), 30), orph: orphC.has(c.uid) })), g };
  });

  private tree = computed(() => {
    const lv = [...(this.g()?.layers ?? [])].sort((a, b) => a.index - b.index).slice(0, 4).map((l) => l.index);
    const root: any = { name: 'All', paths: this.paths(), kids: [], depth: 0, key: '' };
    const rec = (node: any, d: number) => { if (d >= lv.length) return; const m = new Map<string, PathRow[]>(); node.paths.forEach((p: PathRow) => { const n = p.nodes.find((x) => x.layer === lv[d]); const k = n ? (n.label || n.name) : '—'; (m.get(k) ?? m.set(k, []).get(k)!).push(p); });
      node.kids = [...m].map(([k, ps]) => { const c: any = { name: k, paths: ps, kids: [], depth: d + 1, key: node.key + '|' + k }; rec(c, d + 1); return c; }).sort((a: any, b: any) => health(a.paths) - health(b.paths) || b.paths.length - a.paths.length); };
    rec(root, 0); return root;
  });
  private zoomNode = computed(() => { const k = this.zoom(); const f = (n: any): any => (n.key === k ? n : n.kids.map(f).find(Boolean)); return (k && f(this.tree())) || this.tree(); });
  zoomName = computed(() => this.zoomNode().name);
  ru = computed(() => {
    const zr = this.zoomNode(), W = 1240, RH = 52, rects: any[] = [];
    const lay = (n: any, x: number, w: number, d: number) => { const h = health(n.paths), ok = h >= 80 ? ['#D3F0E5', '#007A5C'] : h >= 50 ? ['#FFF0B8', '#8A6A00'] : ['#FAD0E2', '#A30052'];
      if (w >= 1) rects.push({ key: n.key, name: n.name, x, y: d * RH, w, h, n: n.paths.length, bg: ok[0], fg: ok[1], label: trunc(n.name, Math.floor(w / 6.3)), leaf: !n.kids.length, top: n === zr });
      let cx = x; n.kids.forEach((k: any) => { const kw = (w * k.paths.length) / n.paths.length; lay(k, cx, kw, d + 1); cx += kw; }); };
    lay(zr, 0, W, 0); const maxD = Math.max(0, ...rects.map((r) => r.y / RH));
    return { rects, H: (maxD + 1) * RH + 6 };
  });
  ruClick(r: any) { if (r.leaf) { return; } const k: string = r.key; this.zoom.set(r.top ? k.slice(0, Math.max(0, k.lastIndexOf('|'))) : k); }

  // ---- detail table
  cols = computed(() => [...(this.g()?.layers ?? [])].sort((a, b) => a.index - b.index).map((l) => ({ k: 'L' + l.index, l: l.label.toUpperCase() })).concat([{ k: 'cov', l: 'COVERAGE' }]));
  colName = (k: string) => this.cols().find((c) => c.k === k)?.l ?? k;
  groupNames = () => this.group().map((k) => this.colName(k).toLowerCase()).join(' › ');
  val = (r: PathRow, k: string): string => { if (k === 'cov') return r.cov; const n = r.nodes.find((x) => 'L' + x.layer === k); return n ? `${n.label || n.name}${n.label && n.name && n.label !== n.name ? ' · ' + trunc(n.name, 60) : ''}` : '—'; };
  rows = computed(() => {
    let ps = this.shown(); const q = this.qs().trim().toLowerCase(), cs = this.cols();
    if (q) ps = ps.filter((p) => cs.some((c) => this.val(p, c.k).toLowerCase().includes(q)));
    const s = this.sort(); if (s) ps = [...ps].sort((a, b) => this.val(a, s).localeCompare(this.val(b, s)) * this.dir());
    return ps;
  });
  groups = computed(() => {
    const m = new Map<string, PathRow[]>(); this.rows().forEach((p) => { const k = this.group().map((g) => this.val(p, g)).join(' › '); (m.get(k) ?? m.set(k, []).get(k)!).push(p); });
    return [...m].map(([key, items]) => ({ key, items, cov: items.filter((p) => p.cov === 'Covered').length, par: items.filter((p) => p.cov === 'Partial').length, gap: items.filter((p) => p.cov === 'Gap').length, h: health(items) })).sort((a, b) => a.h - b.h || b.items.length - a.items.length);
  });
  drop(e: DragEvent) { e.preventDefault(); const k = e.dataTransfer?.getData('text/plain') ?? ''; if (this.cols().some((c) => c.k === k) && !this.group().includes(k)) this.group.update((g) => [...g, k]); }
  ungroup(k: string) { this.group.update((g) => g.filter((x) => x !== k)); }
  sortBy(k: string) { if (this.sort() === k) this.dir.update((d) => -d); else { this.sort.set(k); this.dir.set(1); } }
  toggle(i: number) { this.closed.update((c) => ({ ...c, [i]: !c[i] })); }
  csv() {
    const q = (v: string) => '"' + v.replace(/"/g, '""') + '"', cs = this.cols();
    const text = [cs.map((c) => q(c.l)).join(','), ...this.rows().map((r) => cs.map((c) => q(this.val(r, c.k))).join(','))].join('\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv' })); a.download = 'aava-map-table.csv'; a.click();
  }
}
