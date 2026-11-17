import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../core/api.service';
import { StateService } from '../core/state.service';
import { ComplianceMapComponent } from '../features/compliance-map/compliance-map.component';
import { SharePanelComponent } from './share-panel.component';

/** Watch mode: always-on posture, the live compliance map, the report and who it was shared with. */
@Component({
  selector: 'aava-watch-panel',
  standalone: true,
  imports: [CommonModule, ComplianceMapComponent, SharePanelComponent],
  template: `
<div class="space-y-3" *ngIf="p() as p">
  <div class="rounded-xl bg-white border border-ink-200/60 shadow-card p-4"><div class="flex items-center gap-2 mb-1.5"><span class="w-2 h-2 rounded-full bg-jade"></span><b class="text-[13px]">Watch is on</b>
    <span class="text-[11px] text-ink-400">I do the reading. You get told when something changes and matters.</span></div>
    <div *ngFor="let w of p.watches" class="text-[12px] py-1 border-t border-ink-200/40"><b>{{ w.scope }}</b> <span class="text-ink-400">· {{ w.rule }}</span></div></div>
  <div class="grid grid-cols-4 gap-2">
    <div class="rounded-lg bg-shell-100 px-3 py-2"><div class="text-[9.5px] text-ink-400 tracking-wide">COVERAGE SCORE</div><div class="text-[20px] font-semibold">{{ p.coverageScore }}%</div></div>
    <div class="rounded-lg bg-shell-100 px-3 py-2"><div class="text-[9.5px] text-ink-400 tracking-wide">GAPS</div><div class="text-[20px] font-semibold text-magenta-700">{{ p.counts.gap }}</div></div>
    <div class="rounded-lg bg-shell-100 px-3 py-2"><div class="text-[9.5px] text-ink-400 tracking-wide">PARTIAL</div><div class="text-[20px] font-semibold">{{ p.counts.partial }}</div></div>
    <div class="rounded-lg bg-shell-100 px-3 py-2"><div class="text-[9.5px] text-ink-400 tracking-wide">RISKS ABOVE APPETITE</div><div class="text-[20px] font-semibold text-magenta-700">{{ p.risksAboveAppetite }}</div></div></div>
  <div class="rounded-xl bg-white border border-ink-200/60 shadow-card overflow-hidden"><div class="px-4 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Live compliance map <span class="font-normal text-[10.5px] text-ink-400">Rule → obligation → policy → control → risk → issue. Click a node to trace it.</span></div>
    <div style="max-height:520px;overflow:auto"><aava-compliance-map /></div></div>
  <div class="rounded-xl bg-white border border-ink-200/60 shadow-card p-4"><div class="flex items-center gap-2 flex-wrap"><b class="text-[12.5px]">Report</b><span class="text-[11px] text-ink-400">What is compliant, what is not, the plan to fix it.</span>
    <button (click)="download()" class="ml-auto px-3 py-1.5 rounded-lg bg-aava text-white text-[11.5px]">Download report (HTML)</button></div>
    <aava-share-panel subject="org" /></div>
</div>`,
})
export class WatchPanelComponent implements OnInit {
  private api = inject(ApiService);
  private state = inject(StateService);
  p = signal<any>(null);
  ngOnInit() { this.api.posture().subscribe((p) => this.p.set(p)); }
  download() { this.api.assessReport('org', this.state.scope()).subscribe((html) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([html], { type: 'text/html' })); a.download = 'aava-assessment-org.html'; a.click(); }); }
}
