import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';
import { Obligation, ObligationValidation, Rulebook } from '../../core/models';

@Component({
  selector: 'aava-obligations',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
<div class="p-5">
 <div class="max-w-[1180px] mx-auto">
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50">
    <div class="px-5 py-3 border-b border-ink-200/50 flex items-center justify-between flex-wrap gap-2">
      <div><span class="text-[13px] font-semibold">Obligations</span>
        <span class="text-[11.5px] text-ink-400 ml-2">extracted from trigger phrases and semantics, with the source clause attached</span></div>
      <select [(ngModel)]="rulebookId" (change)="load()"
        class="px-3 py-1.5 rounded-lg border border-ink-200 text-[11.5px] bg-white">
        <option value="">All rulebooks</option>
        <option *ngFor="let b of books()" [value]="b.id">{{ b.name }}</option>
      </select>
    </div>

    <div *ngIf="obligations().length; else none">
      <div class="px-5 py-3 grid grid-cols-2 md:grid-cols-5 gap-3 border-b border-ink-200/50">
        <div class="bg-shell-100 rounded-lg p-2.5"><div class="text-[9.5px] text-ink-400">TOTAL</div>
          <div class="text-[19px] font-semibold">{{ obligations().length }}</div></div>
        <div *ngFor="let k of kinds()" class="bg-shell-100 rounded-lg p-2.5">
          <div class="text-[9.5px] text-ink-400">{{ k.key.toUpperCase() }}</div>
          <div class="text-[19px] font-semibold">{{ k.count }}</div></div>
        <div class="bg-shell-100 rounded-lg p-2.5"><div class="text-[9.5px] text-ink-400">AVG CONFIDENCE</div>
          <div class="text-[19px] font-semibold">{{ avgConfidence() }}%</div></div>
      </div>

      <div class="divide-y divide-ink-200/40">
        <div *ngFor="let o of obligations()" class="px-5 py-3.5 hover:bg-shell-100/60">
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div class="flex-1 min-w-[320px]">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="mono text-[10.5px] text-aava-700">{{ o.id }}</span>
                <span class="px-1.5 py-[1px] rounded text-[10px] font-semibold" [class]="kindClass(o.kind)">{{ o.kind }}</span>
                <span class="px-1.5 py-[1px] rounded bg-ink-200/40 text-[10px] font-bold">{{ state.jurisShort(o.juris) }}</span>
                <span class="text-[10.5px] text-ink-400">{{ o.ruleMatter }}</span>
                <a [routerLink]="['/rules', o.ruleId]" class="mono text-[10.5px] text-aava-700 underline">{{ o.cite }}</a>
              </div>
              <div class="mt-1.5 text-[12.5px] leading-relaxed">
                <span class="font-medium">{{ o.actor }}</span>
                <span class="hl">{{ o.trigger }}</span>
                {{ o.action }}
              </div>
              <div class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-ink-400">
                <span *ngIf="o.timing"><span class="font-medium text-ink-600">Timing:</span> {{ o.timing }}</span>
                <span *ngIf="o.condition"><span class="font-medium text-ink-600">Condition:</span> {{ o.condition }}</span>
                <span *ngIf="o.keyPhrases.length"><span class="font-medium text-ink-600">Key phrases:</span> {{ o.keyPhrases.join(', ') }}</span>
              </div>
              <div *ngIf="checks()[o.id] as v" class="mt-2 flex flex-wrap gap-1.5">
                <span *ngFor="let c of entries(v.checks)"
                      class="px-1.5 py-[1px] rounded text-[9.5px] font-medium"
                      [class]="c.value ? 'bg-jade-50 text-jade-700' : 'bg-magenta-50 text-magenta-700'">
                  {{ c.value ? '✓' : '✗' }} {{ c.key }}
                </span>
                <span class="px-1.5 py-[1px] rounded text-[9.5px] font-semibold"
                      [class]="v.gate === 'auto' ? 'bg-jade-50 text-jade-700' : 'bg-gold-50 text-gold-700'">
                  gate: {{ v.gate }}
                </span>
              </div>
            </div>
            <div class="shrink-0 text-right w-[140px]">
              <div class="text-[10px] text-ink-400">CONFIDENCE</div>
              <div class="text-[15px] font-semibold"
                   [class.text-jade-700]="o.confidence >= 90"
                   [class.text-gold-700]="o.confidence >= 80 && o.confidence < 90"
                   [class.text-magenta-700]="o.confidence < 80">{{ o.confidence }}%</div>
              <div class="h-1.5 rounded-full bg-shell overflow-hidden mt-1">
                <div class="h-full" [style.width.%]="o.confidence"
                     [class.bg-jade]="o.confidence >= 90"
                     [class.bg-gold]="o.confidence >= 80 && o.confidence < 90"
                     [class.bg-magenta]="o.confidence < 80"></div>
              </div>
              <div class="mt-1.5 flex gap-1 justify-end">
                <button (click)="approve(o)" class="px-2 py-1 rounded border border-jade/40 text-jade-700 text-[10.5px] font-medium hover:bg-jade-50">Approve</button>
                <button (click)="validate(o)" class="px-2 py-1 rounded border border-ink-200 text-[10.5px] hover:bg-shell-100">Check</button>
              </div>
              <div class="mt-1 text-[10px]" [class.text-jade-700]="o.status.startsWith('Approved')"
                   [class.text-ink-400]="!o.status.startsWith('Approved')">{{ o.status }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <ng-template #none>
      <div class="p-10 text-center">
        <div class="text-[13px] font-medium">No obligations yet</div>
        <div class="text-[12px] text-ink-400 mt-1">Create a rulebook and AAVA extracts obligations automatically.</div>
        <a routerLink="/rulebooks" class="mt-3 inline-block px-4 py-2 rounded-lg bg-aava text-white text-[12px] font-semibold">Go to rulebooks</a>
      </div>
    </ng-template>
  </div>
 </div>
</div>
`,
})
export class ObligationsComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  state = inject(StateService);

  rulebookId = '';
  books = signal<Rulebook[]>([]);
  obligations = signal<Obligation[]>([]);
  checks = signal<Record<string, ObligationValidation>>({});

  kinds = computed(() => {
    const m = new Map<string, number>();
    this.obligations().forEach((o) => m.set(o.kind, (m.get(o.kind) ?? 0) + 1));
    return [...m.entries()].slice(0, 3).map(([key, count]) => ({ key, count }));
  });
  avgConfidence = computed(() => {
    const list = this.obligations();
    return list.length ? Math.round(list.reduce((a, o) => a + o.confidence, 0) / list.length) : 0;
  });

  ngOnInit(): void {
    this.api.rulebooks().subscribe((b) => this.books.set(b));
    this.route.queryParamMap.subscribe((p) => {
      this.rulebookId = p.get('rulebookId') ?? '';
      this.load();
    });
  }

  load(): void {
    this.api.obligations(this.rulebookId ? { rulebookId: this.rulebookId } : {})
      .subscribe((o) => this.obligations.set(o));
  }

  approve(o: Obligation): void {
    this.api.approveObligation(o.id).subscribe(() => {
      this.obligations.set(this.obligations().map((x) =>
        x.id === o.id ? { ...x, status: 'Approved · you' } : x));
      this.state.notify(`${o.id} approved and written to the audit trail.`);
    });
  }

  validate(o: Obligation): void {
    this.api.validateObligation(o.id).subscribe((v) =>
      this.checks.set({ ...this.checks(), [o.id]: v }));
  }

  entries(obj: Record<string, boolean>): Array<{ key: string; value: boolean }> {
    return Object.entries(obj).map(([key, value]) => ({ key, value }));
  }

  kindClass(kind: string): string {
    return {
      Prohibition: 'bg-magenta-50 text-magenta-700',
      Mandatory: 'bg-aava-100 text-aava-700',
      Expectation: 'bg-gold-50 text-gold-700',
      Permission: 'bg-jade-50 text-jade-700',
    }[kind] ?? 'bg-shell text-ink-600';
  }
}
