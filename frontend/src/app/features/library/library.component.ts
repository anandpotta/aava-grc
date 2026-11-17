import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';
import { Control, Issue, Policy, Risk } from '../../core/models';

@Component({
  selector: 'aava-library',
  standalone: true,
  imports: [CommonModule],
  template: `
<div class="p-5">
 <div class="max-w-[1240px] mx-auto space-y-4">
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-5 py-3 flex gap-1">
    <button *ngFor="let t of tabs" (click)="tab.set(t)"
      class="px-4 py-1.5 rounded-lg text-[12.5px] font-medium"
      [class]="tab() === t ? 'bg-aava text-white' : 'text-ink-600 hover:bg-shell-100'">{{ t }}</button>
  </div>

  <!-- controls -->
  <div *ngIf="tab() === 'Controls'" class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
    <div class="px-5 py-3 border-b border-ink-200/50 text-[13px] font-semibold">
      Controls library <span class="text-[11.5px] text-ink-400 font-normal">{{ controls().length }} controls, tagged by jurisdiction and rule matter</span>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full text-[12px]" style="min-width:900px">
        <thead class="bg-shell-100 text-ink-400 text-[10.5px]">
          <tr><th class="px-3 py-2 text-left font-semibold w-[82px]">ID</th>
            <th class="px-3 py-2 text-left font-semibold">CONTROL</th>
            <th class="px-3 py-2 text-left font-semibold w-[160px]">OWNER</th>
            <th class="px-3 py-2 text-left font-semibold w-[100px]">TYPE</th>
            <th class="px-3 py-2 text-left font-semibold w-[120px]">AUTOMATION</th>
            <th class="px-3 py-2 text-left font-semibold w-[150px]">JURISDICTIONS</th>
            <th class="px-3 py-2 text-left font-semibold w-[130px]">LAST TEST</th></tr>
        </thead>
        <tbody>
          <ng-container *ngFor="let g of controlGroups()">
            <tr class="bg-aava-50/70"><td colspan="7" class="px-3 py-1.5 text-[11px] font-semibold text-aava-900">
              {{ g.key }} <span class="px-1.5 rounded-full bg-white text-aava-700 text-[10px]">{{ g.items.length }}</span></td></tr>
            <tr *ngFor="let c of g.items" class="border-b border-ink-200/40">
              <td class="px-3 py-2 mono text-[10.5px] text-aava-700">{{ c.id }}</td>
              <td class="px-3 py-2 font-medium">{{ c.name }}</td>
              <td class="px-3 py-2 text-ink-600 text-[11.5px]">{{ c.owner }}</td>
              <td class="px-3 py-2"><span class="px-1.5 py-[1px] rounded bg-shell text-[10.5px]">{{ c.controlType }}</span></td>
              <td class="px-3 py-2 text-[11.5px] text-ink-600">{{ c.automation }}</td>
              <td class="px-3 py-2">
                <span *ngFor="let j of c.jurisdictions"
                      class="inline-block px-1 py-[1px] mr-0.5 rounded bg-ink-200/40 text-[9.5px] font-bold">{{ state.jurisShort(j) }}</span>
              </td>
              <td class="px-3 py-2">
                <span class="px-1.5 py-[1px] rounded text-[10px] font-medium" [class]="testClass(c.testResult)">{{ c.testResult }}</span>
              </td>
            </tr>
          </ng-container>
        </tbody>
      </table>
    </div>
  </div>

  <!-- policies -->
  <div *ngIf="tab() === 'Policies'" class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
    <div class="px-5 py-3 border-b border-ink-200/50 text-[13px] font-semibold">
      Policies library <span class="text-[11.5px] text-ink-400 font-normal">{{ policies().length }} policies and standards</span>
    </div>
    <div class="p-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      <div *ngFor="let p of policies()" class="border border-ink-200/60 rounded-xl p-3.5 hover:shadow-card">
        <div class="flex items-start justify-between gap-2">
          <div class="font-medium text-[12.5px] leading-snug">{{ p.name }}</div>
          <span class="shrink-0 px-1.5 py-[1px] rounded bg-aava-100 text-aava-700 text-[10px] font-semibold">{{ p.version }}</span>
        </div>
        <div class="mono text-[10.5px] text-ink-400 mt-1">{{ p.id }}</div>
        <div class="text-[11.5px] text-ink-600 mt-1.5">{{ p.owner }}</div>
        <div class="text-[11px] text-ink-400">Next review {{ p.nextReview }} · {{ p.ruleMatter }}</div>
        <div class="mt-2">
          <span *ngFor="let j of p.jurisdictions"
                class="inline-block px-1 py-[1px] mr-0.5 rounded bg-ink-200/40 text-[9.5px] font-bold">{{ state.jurisShort(j) }}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- risks and issues -->
  <div *ngIf="tab() === 'Risks and issues'" class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
    <div class="px-5 py-3 border-b border-ink-200/50 text-[13px] font-semibold">Risk register</div>
    <div class="divide-y divide-ink-200/40">
      <div *ngFor="let r of risks()" class="px-5 py-3" [class.bg-magenta-50]="overAppetite(r)">
        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div class="font-medium text-[12.5px]">
              <span *ngIf="overAppetite(r)" class="text-magenta-700">&#9650; </span>{{ r.name }}
            </div>
            <div class="text-[10.5px] text-ink-400">{{ r.id }} · {{ r.ruleMatter }}</div>
          </div>
          <div class="text-[11.5px] text-ink-600">
            inherent {{ r.inherent }} · residual <b>{{ r.residual }}</b> · appetite {{ r.appetite }}
          </div>
        </div>
        <div *ngFor="let i of issuesFor(r.id)" class="mt-1.5 pl-3 border-l-2 border-magenta/40">
          <span class="mono text-[10px] text-ink-400">{{ i.id }}</span>
          <span class="text-[11.5px]"> {{ i.name }}</span>
          <span class="text-[10px] text-ink-400"> · {{ i.owner }} · due {{ i.due }} · {{ i.status }}</span>
        </div>
        <div *ngIf="!issuesFor(r.id).length" class="mt-1 text-[11px] text-magenta-700 font-medium">
          No issue raised yet.
        </div>
      </div>
    </div>
  </div>
 </div>
</div>
`,
})
export class LibraryComponent implements OnInit {
  private api = inject(ApiService);
  state = inject(StateService);

  tabs = ['Controls', 'Policies', 'Risks and issues'];
  tab = signal('Controls');

  controls = signal<Control[]>([]);
  policies = signal<Policy[]>([]);
  risks = signal<Risk[]>([]);
  issues = signal<Issue[]>([]);

  controlGroups = computed(() => {
    const m = new Map<string, Control[]>();
    this.controls().forEach((c) => {
      const arr = m.get(c.ruleMatter) ?? [];
      arr.push(c);
      m.set(c.ruleMatter, arr);
    });
    return [...m.entries()].map(([key, items]) => ({ key, items }));
  });

  ngOnInit(): void {
    this.api.controls().subscribe((c) => this.controls.set(c));
    this.api.policies().subscribe((p) => this.policies.set(p));
    this.api.risks().subscribe((r) => this.risks.set(r));
    this.api.issues().subscribe((i) => this.issues.set(i));
  }

  issuesFor(riskId: string): Issue[] { return this.issues().filter((i) => i.riskId === riskId); }

  overAppetite(r: Risk): boolean {
    const lvl: Record<string, number> = { Zero: 0, Low: 1, Medium: 2, High: 3, Critical: 4 };
    return (lvl[r.residual] ?? 0) > (lvl[r.appetite] ?? 0);
  }

  testClass(t: string): string {
    return {
      Effective: 'bg-jade-50 text-jade-700',
      'Needs improvement': 'bg-gold-50 text-gold-700',
      'Not tested': 'bg-magenta-50 text-magenta-700',
    }[t] ?? 'bg-shell text-ink-600';
  }
}
