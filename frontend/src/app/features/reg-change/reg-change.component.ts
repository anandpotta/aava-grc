import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';
import { ChangeImpact, ChangePipeline, RegChange } from '../../core/models';

/**
 * Regulatory change management.
 *
 * The board on top is the pipeline; selecting a change loads the clause diff
 * and the impact analysis. Impact is shown as its three components rather than
 * one opaque number, because the reviewer has to be able to argue with it.
 */
@Component({
  selector: 'aava-reg-change',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
<div class="p-5">
 <div class="max-w-[1320px] mx-auto space-y-4">

  <!-- pipeline -->
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-5 py-4">
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h2 class="text-[16px] font-semibold">Regulatory change management</h2>
        <p class="text-[12px] text-ink-400 mt-0.5 max-w-3xl">
          Horizon scan &rarr; clause diff &rarr; applicability &rarr; impact score &rarr; redline &rarr; plan and prove.
          Every change re-runs against the compliance maps that reference the affected citation.
        </p>
      </div>
    </div>
    <div *ngIf="pipeline() as p" class="grid grid-cols-2 md:grid-cols-6 gap-2.5 mt-4">
      <div *ngFor="let s of p.stages" class="rounded-xl p-2.5"
           [class]="(p.counts[s] || 0) > 0 ? 'bg-aava-50' : 'bg-shell-100'">
        <div class="text-[9px] text-ink-400">{{ s.toUpperCase() }}</div>
        <div class="text-[20px] font-semibold" [class.text-aava-700]="(p.counts[s] || 0) > 0">{{ p.counts[s] || 0 }}</div>
      </div>
    </div>
  </div>

  <div class="grid grid-cols-1 xl:grid-cols-[380px_minmax(0,1fr)] gap-4">
    <!-- feed -->
    <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden self-start">
      <div class="px-5 py-3 border-b border-ink-200/50 text-[13px] font-semibold">
        Horizon scan feed <span class="text-[11.5px] text-ink-400 font-normal">{{ changes().length }} open</span>
      </div>
      <div class="divide-y divide-ink-200/40 max-h-[680px] overflow-y-auto">
        <button *ngFor="let c of changes()" (click)="select(c)"
          class="w-full text-left px-5 py-3.5 hover:bg-shell-100/60"
          [class.bg-aava-50]="selected()?.id === c.id">
          <div class="flex items-start gap-2">
            <span class="shrink-0 px-1.5 py-[2px] rounded bg-ink-200/40 text-[10px] font-bold mt-0.5">{{ state.jurisShort(c.juris) }}</span>
            <div class="flex-1 min-w-0">
              <div class="font-medium text-[12.5px] leading-snug">{{ c.title }}</div>
              <div class="text-[11px] text-ink-400 mt-0.5">{{ c.regulator }} · published {{ c.published }}</div>
              <div class="flex items-center gap-2 mt-1 flex-wrap">
                <span class="px-1.5 py-[1px] rounded border text-[10px] font-medium" [class]="impactClass(c.impact)">{{ c.impact }}</span>
                <span class="text-[10.5px] text-ink-400">{{ c.status }}</span>
                <span class="text-[10.5px] font-medium"
                      [class.text-magenta-700]="c.daysToComply <= 90"
                      [class.text-ink-400]="c.daysToComply > 90">{{ c.daysToComply }} days to comply</span>
              </div>
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- detail -->
    <div *ngIf="selected() as c; else pick" class="space-y-4">
      <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-5 py-4">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div class="max-w-2xl">
            <h3 class="text-[15px] font-semibold">{{ c.title }}</h3>
            <div class="text-[11.5px] text-ink-400 mt-0.5">
              {{ c.regulator }} · {{ state.jurisName(c.juris) }} · published {{ c.published }} · effective {{ c.effective }}
            </div>
            <p class="text-[12px] text-ink-600 mt-2 leading-relaxed">{{ c.summary }}</p>
          </div>
          <div class="flex gap-2 items-start">
            <select [(ngModel)]="status" (change)="setStatus(c)"
              class="px-3 py-2 rounded-lg border border-ink-200 text-[11.5px] bg-white">
              <option *ngFor="let s of stages()" [value]="s">{{ s }}</option>
            </select>
          </div>
        </div>
      </div>

      <!-- clause diff -->
      <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
        <div class="px-5 py-3 border-b border-ink-200/50 flex items-center justify-between flex-wrap gap-2">
          <span class="text-[13px] font-semibold">Clause diff</span>
          <div class="flex items-center gap-3 text-[10.5px] text-ink-600">
            <span class="flex items-center gap-1"><span class="w-3 h-2 rounded-sm bg-jade-50 border border-jade"></span>added</span>
            <span class="flex items-center gap-1"><span class="w-3 h-2 rounded-sm bg-magenta-50 border border-magenta"></span>removed</span>
          </div>
        </div>
        <div class="p-4 space-y-1.5 text-[12.5px] leading-relaxed">
          <div *ngFor="let d of c.diff" class="px-3 py-1.5 rounded-lg"
               [class]="d.kind === 'added' ? 'bg-jade-50 border-l-2 border-jade'
                      : d.kind === 'removed' ? 'bg-magenta-50 border-l-2 border-magenta line-through text-ink-400'
                      : 'bg-shell-100/60'">
            <span class="mono text-[10px] mr-1.5"
                  [class.text-jade-700]="d.kind === 'added'"
                  [class.text-magenta-700]="d.kind === 'removed'"
                  [class.text-ink-200]="d.kind === 'unchanged'">{{ d.kind === 'added' ? '+' : d.kind === 'removed' ? '−' : ' ' }}</span>
            {{ d.text }}
          </div>
        </div>
      </div>

      <!-- impact -->
      <div *ngIf="impact() as im" class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
        <div class="px-5 py-3 border-b border-ink-200/50 text-[13px] font-semibold">Impact analysis</div>
        <div class="px-5 py-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="rounded-xl p-3" [class]="im.impactScore >= 70 ? 'bg-magenta-50' : im.impactScore >= 45 ? 'bg-gold-50' : 'bg-jade-50'">
            <div class="text-[9px] text-ink-400">IMPACT SCORE</div>
            <div class="text-[24px] font-semibold"
                 [class.text-magenta-700]="im.impactScore >= 70"
                 [class.text-gold-700]="im.impactScore >= 45 && im.impactScore < 70"
                 [class.text-jade-700]="im.impactScore < 45">{{ im.impactScore }}</div>
          </div>
          <div *ngFor="let f of factors(im)" class="bg-shell-100 rounded-xl p-3">
            <div class="text-[9px] text-ink-400">{{ f.label }}</div>
            <div class="text-[20px] font-semibold">{{ f.value }}</div>
            <div class="h-1.5 rounded-full bg-white overflow-hidden mt-1">
              <div class="h-full bg-aava" [style.width.%]="f.value"></div>
            </div>
          </div>
        </div>

        <div class="px-5 pb-4 grid grid-cols-2 md:grid-cols-5 gap-2.5">
          <div *ngFor="let b of buckets(im)" class="bg-shell-100 rounded-lg p-2.5">
            <div class="text-[9px] text-ink-400">{{ b.label }}</div>
            <div class="text-[17px] font-semibold">{{ b.ids.length }}</div>
            <div class="text-[9.5px] text-ink-400 truncate">{{ b.ids.slice(0, 3).join(', ') }}</div>
          </div>
        </div>

        <div class="border-t border-ink-200/50">
          <div class="px-5 py-2.5 text-[12.5px] font-semibold">Recommended actions</div>
          <table class="w-full text-[11.5px]">
            <thead class="bg-shell-100 text-ink-400 text-[10px]">
              <tr><th class="px-5 py-2 text-left font-semibold">ACTION</th>
                <th class="px-3 py-2 text-left font-semibold w-[180px]">OWNER</th>
                <th class="px-3 py-2 text-left font-semibold">WHY</th></tr>
            </thead>
            <tbody>
              <tr *ngFor="let a of im.recommendedActions" class="border-b border-ink-200/40 align-top">
                <td class="px-5 py-2 font-medium">{{ a.action }}</td>
                <td class="px-3 py-2 text-ink-600">{{ a.owner }}</td>
                <td class="px-3 py-2 text-ink-400">{{ a.why }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="px-5 py-3 bg-shell-100 text-[11.5px] text-ink-600 flex items-center justify-between flex-wrap gap-2">
          <span>Affected rules:
            <a *ngFor="let r of im.affectedRules" [routerLink]="['/rules', r]"
               class="mono text-[10.5px] text-aava-700 underline mr-1.5">{{ r }}</a>
          </span>
          <a routerLink="/maps" class="px-3 py-1.5 rounded-lg bg-aava text-white text-[11.5px] font-semibold">
            Re-run the compliance map
          </a>
        </div>
      </div>
    </div>

    <ng-template #pick>
      <div class="bg-white rounded-2xl border border-ink-200/50 p-12 text-center">
        <div class="text-[13px] font-medium">Select a change</div>
        <div class="text-[12px] text-ink-400 mt-1">Pick an item from the horizon scan feed to see its clause diff and impact analysis.</div>
      </div>
    </ng-template>
  </div>
 </div>
</div>
`,
})
export class RegChangeComponent implements OnInit {
  private api = inject(ApiService);
  state = inject(StateService);

  changes = signal<RegChange[]>([]);
  pipeline = signal<ChangePipeline | null>(null);
  selected = signal<RegChange | null>(null);
  impact = signal<ChangeImpact | null>(null);
  status = '';

  stages = computed(() => this.pipeline()?.stages ?? []);

  ngOnInit(): void { this.refresh(); }

  private refresh(): void {
    this.api.changes().subscribe((c) => {
      this.changes.set(c);
      if (!this.selected() && c.length) this.select(c[0]);
    });
    this.api.pipeline().subscribe((p) => this.pipeline.set(p));
  }

  select(c: RegChange): void {
    this.selected.set(c);
    this.status = c.status;
    this.impact.set(null);
    this.api.changeImpact(c.id).subscribe((i) => this.impact.set(i));
  }

  setStatus(c: RegChange): void {
    this.api.setChangeStatus(c.id, this.status).subscribe(() => {
      this.state.notify(`${c.id} moved to ${this.status}.`);
      this.refresh();
    });
  }

  factors(im: ChangeImpact): Array<{ label: string; value: number }> {
    return [
      { label: 'MATERIALITY', value: im.materiality },
      { label: 'GAP SEVERITY', value: im.gapSeverity },
      { label: 'URGENCY', value: im.urgency },
    ];
  }

  buckets(im: ChangeImpact): Array<{ label: string; ids: string[] }> {
    return [
      { label: 'OBLIGATIONS', ids: im.affectedObligations },
      { label: 'POLICIES', ids: im.affectedPolicies },
      { label: 'CONTROLS', ids: im.affectedControls },
      { label: 'RISKS', ids: im.affectedRisks },
      { label: 'OPEN ISSUES', ids: im.openIssues },
    ];
  }

  impactClass(i: string): string {
    return {
      Critical: 'bg-magenta-50 text-magenta-700 border-magenta/30',
      High: 'bg-gold-50 text-gold-700 border-gold/40',
      Medium: 'bg-aava-100 text-aava-700 border-aava-200',
      Low: 'bg-jade-50 text-jade-700 border-jade/30',
    }[i] ?? 'bg-shell text-ink-600 border-ink-200';
  }
}
