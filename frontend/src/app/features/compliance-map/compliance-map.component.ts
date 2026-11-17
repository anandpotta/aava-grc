import { Component, Input, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';
import { SankeyComponent } from '../../shared/sankey/sankey.component';
import { MapViewsComponent } from './map-views.component';
import {
  Control, DrillResponse, MapSummaryDto, Policy, Rulebook,
  SankeyGraph, SankeyNodeDto,
} from '../../core/models';

@Component({
  selector: 'aava-compliance-map',
  standalone: true,
  imports: [CommonModule, FormsModule, SankeyComponent, MapViewsComponent],
  template: `
<div class="p-5">
 <div class="max-w-[1400px] mx-auto space-y-4">

  <!-- picker / builder -->
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-5 py-4">
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h2 class="text-[16px] font-semibold">Compliance maps</h2>
        <p class="text-[12px] text-ink-400 mt-0.5 max-w-3xl">
          Trace rule &rarr; obligation &rarr; policy &rarr; control &rarr; risk &rarr; issue. Click any node to isolate
          everything connected to it. A red triangle marks an impacted node.
        </p>
      </div>
      <div class="flex gap-2 flex-wrap">
        <select [(ngModel)]="mapId" (change)="load()"
          class="px-3 py-2 rounded-lg border border-ink-200 text-[12px] bg-white min-w-[230px]">
          <optgroup label="Imported datasets">
            <option *ngFor="let m of datasetMaps()" [value]="m.id">{{ m.name }} ({{ m.nodeCount }})</option>
          </optgroup>
          <optgroup label="Built in this session" *ngIf="generatedMaps().length">
            <option *ngFor="let m of generatedMaps()" [value]="m.id">{{ m.name }} ({{ m.nodeCount }})</option>
          </optgroup>
        </select>
        <button (click)="buildFromRulebook()" [disabled]="building()"
          class="px-3 py-2 rounded-lg bg-aava text-white text-[12px] font-semibold disabled:opacity-50">
          {{ building() ? 'Building…' : 'Build from a rulebook' }}
        </button>
      </div>
    </div>
  </div>

  <ng-container *ngIf="graph() as g">
    <!-- KPIs -->
    <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-5 py-4">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h3 class="text-[15px] font-semibold">{{ g.name }}</h3>
          <p class="text-[11.5px] text-ink-400 mt-0.5">
            {{ g.summary.totalNodes }} nodes · {{ g.summary.realLinks }} mapped links ·
            {{ g.summary.totalLinks - g.summary.realLinks }} layout placeholders ·
            {{ g.layers.length }} layers
          </p>
        </div>
        <div class="flex gap-2 flex-wrap">
          <a [href]="api.exportUrl(g.mapId, 'csv')" class="px-3 py-2 rounded-lg border border-ink-200 text-[11.5px] font-medium hover:bg-shell-100">Download mapping (CSV)</a>
          <a [href]="api.exportUrl(g.mapId, 'xlsx')" class="px-3 py-2 rounded-lg border border-ink-200 text-[11.5px] font-medium hover:bg-shell-100">Excel</a>
          <a [href]="api.planUrl(g.mapId)" class="px-3 py-2 rounded-lg bg-magenta text-white text-[11.5px] font-semibold">Download impact and mitigation plan</a>
          <a [href]="api.exportUrl(g.mapId, 'pdf')" class="px-3 py-2 rounded-lg border border-ink-200 text-[11.5px] font-medium hover:bg-shell-100">PDF</a>
          <button (click)="rebuild()" [disabled]="building()" class="px-3 py-2 rounded-lg border border-ink-200 text-[11.5px] font-medium hover:bg-shell-100 disabled:opacity-50">{{ building() ? 'Rebuilding…' : 'Rebuild' }}</button>
        </div>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-6 gap-2.5 mt-4">
        <div class="bg-shell-100 rounded-xl p-2.5">
          <div class="text-[9px] text-ink-400">COVERAGE SCORE</div>
          <div class="text-[20px] font-semibold"
               [class.text-jade-700]="g.summary.coverageScore >= 70"
               [class.text-gold-700]="g.summary.coverageScore >= 45 && g.summary.coverageScore < 70"
               [class.text-magenta-700]="g.summary.coverageScore < 45">{{ g.summary.coverageScore }}%</div>
        </div>
        <div class="bg-shell-100 rounded-xl p-2.5"><div class="text-[9px] text-ink-400">STRONG</div><div class="text-[20px] font-semibold text-jade-700">{{ g.summary.strong }}</div></div>
        <div class="bg-shell-100 rounded-xl p-2.5"><div class="text-[9px] text-ink-400">PARTIAL</div><div class="text-[20px] font-semibold text-gold-700">{{ g.summary.partial }}</div></div>
        <div class="bg-shell-100 rounded-xl p-2.5"><div class="text-[9px] text-ink-400">MINIMAL</div><div class="text-[20px] font-semibold text-magenta-700">{{ g.summary.minimal }}</div></div>
        <div class="bg-shell-100 rounded-xl p-2.5"><div class="text-[9px] text-ink-400">UNMAPPED</div><div class="text-[20px] font-semibold text-magenta-700">{{ g.summary.unmapped }}</div></div>
        <div class="bg-shell-100 rounded-xl p-2.5"><div class="text-[9px] text-ink-400">IMPACTED</div><div class="text-[20px] font-semibold text-magenta-700">{{ g.summary.impacted }}</div></div>
      </div>
    </div>

    <!-- view switcher -->
    <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-5 py-3 flex items-center gap-2 flex-wrap">
      <button *ngFor="let m of modes" (click)="view.set(m.id)" class="px-3 py-1.5 rounded-lg text-[11.5px] border text-left"
        [ngClass]="view()===m.id ? 'bg-aava text-white border-aava' : 'border-ink-200 hover:border-aava bg-white'"><div class="font-semibold leading-tight">{{ m.t }}</div><div class="text-[9.5px] opacity-75 leading-tight">{{ m.best }}</div></button>
    </div>
    <aava-map-views *ngIf="view()!=='flow'" [graph]="g" [view]="view()" />

    <!-- diagram -->
    <div *ngIf="view()==='flow'" class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
      <div class="px-5 py-3 border-b border-ink-200/50 flex items-center justify-between flex-wrap gap-2">
        <div>
          <span class="text-[13px] font-semibold">Traceability map</span>
          <span class="text-[11.5px] text-ink-400 ml-2">click any node to isolate everything connected to it</span>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <select [(ngModel)]="hideLayer" (change)="load()"
            class="px-2.5 py-1.5 rounded-lg border border-ink-200 text-[11px] bg-white">
            <option [ngValue]="null">All layers</option>
            <option *ngFor="let l of g.layers" [ngValue]="l.index">Hide {{ l.label.toLowerCase() }}</option>
          </select>
          <label class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-ink-200 text-[11px] cursor-pointer">
            <input type="checkbox" [(ngModel)]="showPlaceholders" /> show placeholder links
          </label>
        </div>
      </div>

      <div class="px-5 py-2 border-b border-ink-200/50 flex items-center gap-3.5 text-[10.5px] text-ink-600 flex-wrap bg-shell-100/50">
        <span *ngFor="let l of g.layers" class="flex items-center gap-1">
          <span class="w-2.5 h-2.5 rounded-sm" [style.background]="layerColour(l.type, l.index)"></span>{{ l.label }}
        </span>
        <span class="flex items-center gap-1 pl-2.5 border-l border-ink-200">
          <svg width="11" height="10" viewBox="0 0 11 10"><polygon points="5.5,0 11,10 0,10" fill="#CC0066"/></svg>impacted
        </span>
        <span class="flex items-center gap-1"><span class="w-5 h-[3px] rounded" style="background:#74C476"></span>strong</span>
        <span class="flex items-center gap-1"><span class="w-5 h-[3px] rounded" style="background:#F0B429"></span>partial</span>
        <span class="flex items-center gap-1"><span class="w-5 h-[3px] rounded" style="background:#E24B4A"></span>minimal</span>

        <span *ngIf="selectedNode() as n" class="ml-auto flex items-center gap-2">
          <span class="px-1.5 py-[1px] rounded text-[9.5px] font-semibold text-white"
                [style.background]="layerColour(n.layerType, n.layer)">{{ n.layerType.toUpperCase() }}</span>
          <span class="font-medium text-[10.5px]">{{ n.label || n.name }}</span>
          <span class="text-ink-400 text-[10px]">{{ connectedLabel() }}</span>
          <button (click)="clearSelection()" class="px-1.5 py-[1px] rounded border border-ink-200 text-[10px] bg-white">clear</button>
        </span>
      </div>

      <aava-sankey [graph]="g" [focus]="focus()" [selectedUid]="selectedUid()"
                   [showPlaceholders]="showPlaceholders"
                   (nodeClick)="onNodeClick($event)" (backgroundClick)="clearSelection()" />
    </div>

    <!-- drill-down -->
    <div *ngIf="drill() as dr"
         class="bg-white rounded-2xl shadow-card border overflow-hidden fadein"
         [class.border-magenta]="dr.node.impacted" [class.border-ink-200]="!dr.node.impacted">
      <div class="px-5 py-3 border-b border-ink-200/50 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <svg *ngIf="dr.node.impacted" width="12" height="11" viewBox="0 0 11 10"><polygon points="5.5,0 11,10 0,10" fill="#CC0066"/></svg>
            <span class="px-1.5 py-[2px] rounded text-[10px] font-semibold text-white"
                  [style.background]="layerColour(dr.node.layerType, dr.node.layer)">{{ dr.node.layerType.toUpperCase() }}</span>
            <span class="text-[13.5px] font-semibold">{{ dr.node.label || dr.node.name }}</span>
          </div>
          <div class="text-[11.5px] text-ink-600 mt-0.5 max-w-3xl">{{ dr.node.quote.slice(0, 260) }}</div>
          <div class="text-[11px] text-ink-400 mt-1">
            {{ dr.rows.length }} traced path(s){{ dr.truncated ? ' (truncated)' : '' }} · parent to child
          </div>
        </div>
        <button (click)="clearSelection()" class="text-ink-400 hover:text-ink text-lg leading-none">&times;</button>
      </div>

      <div *ngIf="dr.findings.length" class="px-5 py-2.5 bg-magenta-50/50 border-b border-magenta/20">
        <span class="text-[11px] font-semibold text-magenta-700">Why this is flagged:</span>
        <span class="text-[11.5px] text-ink-600"> {{ dr.findings.join(' · ') }}</span>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-[11.5px]">
          <thead class="bg-shell-100 text-ink-400 text-[10px]">
            <tr>
              <th *ngFor="let c of dr.columns" class="px-3 py-2 text-left font-semibold">{{ c.toUpperCase() }}</th>
              <th class="px-3 py-2 text-left font-semibold w-[84px]">BAND</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let row of dr.rows" class="border-b border-ink-200/40 align-top hover:bg-shell-100/60">
              <td *ngFor="let c of dr.columns" class="px-3 py-2">
                <ng-container *ngIf="row.cells[c] as cell; else blank">
                  <span class="block" [class.text-magenta-700]="cell.impacted" [class.font-medium]="cell.impacted">
                    <span *ngIf="cell.impacted">&#9650; </span>{{ cell.label || cell.name }}
                  </span>
                  <span class="block text-[10px] text-ink-400">{{ cell.band }}</span>
                </ng-container>
                <ng-template #blank><span class="text-ink-200">—</span></ng-template>
              </td>
              <td class="px-3 py-2">
                <span class="px-1.5 py-[1px] rounded text-[10px] font-medium" [class]="bandClass(row.band)">{{ row.band }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- per-layer coverage -->
    <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
      <div class="px-5 py-3 border-b border-ink-200/50 text-[13px] font-semibold">Coverage by layer</div>
      <table class="w-full text-[12px]">
        <thead class="bg-shell-100 text-ink-400 text-[10.5px]">
          <tr>
            <th class="px-3 py-2 text-left font-semibold">LAYER</th>
            <th class="px-3 py-2 text-left font-semibold w-[90px]">NODES</th>
            <th class="px-3 py-2 text-left font-semibold w-[90px]">STRONG</th>
            <th class="px-3 py-2 text-left font-semibold w-[90px]">PARTIAL</th>
            <th class="px-3 py-2 text-left font-semibold w-[90px]">MINIMAL</th>
            <th class="px-3 py-2 text-left font-semibold w-[100px]">UNMAPPED</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let r of g.summary.byLayer" class="border-b border-ink-200/40">
            <td class="px-3 py-2 font-medium">{{ r['label'] }}</td>
            <td class="px-3 py-2">{{ r['nodes'] }}</td>
            <td class="px-3 py-2 text-jade-700">{{ r['strong'] }}</td>
            <td class="px-3 py-2 text-gold-700">{{ r['partial'] }}</td>
            <td class="px-3 py-2 text-magenta-700">{{ r['minimal'] }}</td>
            <td class="px-3 py-2 text-magenta-700">{{ r['unmapped'] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </ng-container>

  <div *ngIf="loading()" class="bg-white rounded-2xl border border-ink-200/50 p-10 text-center text-[12.5px] text-ink-400">
    Loading the map…
  </div>
 </div>
</div>
`,
})
export class ComplianceMapComponent implements OnInit {
  api = inject(ApiService);
  state = inject(StateService);

  @Input() set mapIdParam(v: string) { if (v) this.mapId = v; }

  mapId = 'code-of-ethics';
  hideLayer: number | null = null;
  showPlaceholders = false;

  view = signal<'dag' | 'matrix' | 'rollup' | 'flow'>('dag');
  modes = [
    { id: 'dag' as const, t: 'Layered trace', best: 'Best for tracing' },
    { id: 'matrix' as const, t: 'Coverage matrix', best: 'Best for finding gaps' },
    { id: 'rollup' as const, t: 'Roll-up', best: 'Best for leadership' },
    { id: 'flow' as const, t: 'Flow', best: 'Best for the story' },
  ];
  maps = signal<MapSummaryDto[]>([]);
  graph = signal<SankeyGraph | null>(null);
  drill = signal<DrillResponse | null>(null);
  selectedNode = signal<SankeyNodeDto | null>(null);
  focus = signal<Set<string> | null>(null);
  loading = signal(false);
  building = signal(false);
  private counts = signal<Record<string, number>>({});

  selectedUid = computed(() => this.selectedNode()?.uid ?? null);
  datasetMaps = computed(() => this.maps().filter((m) => m.source === 'dataset'));
  generatedMaps = computed(() => this.maps().filter((m) => m.source !== 'dataset'));
  connectedLabel = computed(() =>
    Object.entries(this.counts())
      .map(([k, n]) => `${n} ${k.toLowerCase()}${n > 1 ? 's' : ''}`)
      .join(' · '),
  );

  ngOnInit(): void {
    this.api.maps().subscribe((m) => {
      this.maps.set(m);
      if (!m.some((x) => x.id === this.mapId) && m.length) this.mapId = m[0].id;
      this.load();
    });
  }

  load(): void {
    this.loading.set(true);
    this.clearSelection();
    this.api.map(this.mapId, this.hideLayer).subscribe({
      next: (g) => { this.graph.set(g); this.loading.set(false); },
      error: () => { this.loading.set(false); this.state.notify('Could not load that map.'); },
    });
  }

  /** After you correct policies, controls or the rulebook, rebuild the same map so the score and the plan reflect the fixes. */
  rebuild(): void {
    const id = this.graph()?.mapId ?? this.mapId;
    if (id.startsWith('generated-')) {
      this.building.set(true);
      this.api.buildMap({ name: this.graph()?.name ?? "Rebuilt map", rulebookId: id.slice('generated-'.length).toUpperCase(), policyIds: [], controlIds: [], includeObligations: true }).subscribe({
        next: (g) => { this.graph.set(g); this.building.set(false); this.state.notify(`Rebuilt: ${g.summary.totalNodes} nodes, ${g.summary.realLinks} mapped links. Download the plan again to see what changed.`); },
        error: () => { this.building.set(false); this.state.notify('Could not rebuild the map.'); },
      });
    } else { this.load(); this.state.notify('Reloaded from the dataset.'); }
  }

  buildFromRulebook(): void {
    this.building.set(true);
    const run = (book: Rulebook) =>
      this.api
        .buildMap({
          name: book.name, rulebookId: book.id,
          policyIds: [], controlIds: [], includeObligations: true,
        })
        .subscribe({
          next: (g) => {
            this.graph.set(g);
            this.mapId = g.mapId;
            this.building.set(false);
            this.api.maps().subscribe((m) => this.maps.set(m));
            this.state.notify(`Map built: ${g.summary.totalNodes} nodes, ${g.summary.realLinks} mapped links.`);
          },
          error: () => { this.building.set(false); this.state.notify('Could not build the map.'); },
        });

    this.api.rulebooks().subscribe((books) => {
      if (books.length) run(books[books.length - 1]);
      else this.api.seedRulebook().subscribe((b) => run(b));
    });
  }

  onNodeClick(node: SankeyNodeDto): void {
    this.selectedNode.set(node);
    const g = this.graph();
    if (!g) return;
    this.api.connected(g.mapId, node.uid).subscribe((c) => {
      this.focus.set(new Set(c.nodes));
      this.counts.set(c.counts);
    });
    this.api.drill(g.mapId, node.uid).subscribe((d) => this.drill.set(d));
  }

  clearSelection(): void {
    this.selectedNode.set(null);
    this.focus.set(null);
    this.drill.set(null);
    this.counts.set({});
  }

  layerColour(type: string, index: number): string {
    const byType: Record<string, string> = {
      'Rule': '#6666CC', 'Rule Book': '#6666CC', 'Obligation': '#8A8AD9',
      'Policy': '#008567', 'Control': '#BA7517', 'Risk': '#CC0066', 'Issue': '#A30052',
    };
    const fallback = ['#6666CC', '#8A8AD9', '#008567', '#BA7517', '#CC0066', '#A30052'];
    return byType[type] ?? fallback[index % fallback.length];
  }

  bandClass(band: string): string {
    return {
      Strong: 'bg-jade-50 text-jade-700',
      Partial: 'bg-gold-50 text-gold-700',
      Minimal: 'bg-magenta-50 text-magenta-700',
      Unmapped: 'bg-magenta-50 text-magenta-700',
    }[band] ?? 'bg-shell text-ink-600';
  }
}
