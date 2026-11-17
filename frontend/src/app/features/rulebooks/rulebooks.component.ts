import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';
import { Rulebook } from '../../core/models';

@Component({
  selector: 'aava-rulebooks',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
<div class="p-5">
 <div class="max-w-[1180px] mx-auto space-y-4">

  <div *ngIf="state.pinnedCount() > 0" class="bg-white rounded-2xl shadow-card border border-gold/40">
    <div class="px-5 py-3 border-b border-ink-200/50 flex items-center gap-2 flex-wrap">
      <span class="text-[13px] font-semibold">{{ state.pinnedCount() }} pinned rules ready</span>
      <span class="text-[11.5px] text-ink-400">grouped by rule type · name the rulebook and create it</span>
    </div>
    <div class="p-5 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5">
      <div class="border border-ink-200/60 rounded-xl overflow-hidden">
        <table class="w-full text-[12px]">
          <thead class="bg-shell-100 text-ink-400 text-[10.5px]">
            <tr><th class="px-3 py-2 text-left font-semibold">RULE</th>
                <th class="px-3 py-2 text-left font-semibold w-[150px]">RULE MATTER</th>
                <th class="px-3 py-2 text-left font-semibold w-[70px]">JURIS</th>
                <th class="px-3 py-2 w-[40px]"></th></tr>
          </thead>
          <tbody>
            <ng-container *ngFor="let g of grouped()">
              <tr class="bg-aava-50/70"><td colspan="4" class="px-3 py-1.5 text-[11px] font-semibold text-aava-900">
                {{ g.key }} <span class="px-1.5 rounded-full bg-white text-aava-700 text-[10px]">{{ g.items.length }}</span>
              </td></tr>
              <tr *ngFor="let r of g.items" class="border-b border-ink-200/40">
                <td class="px-3 py-2">
                  <a [routerLink]="['/rules', r.id]" class="font-medium hover:text-aava-700">{{ r.title }}</a>
                  <div class="mono text-[10.5px] text-aava-700">{{ r.cite }}</div>
                </td>
                <td class="px-3 py-2 text-[11.5px] text-ink-600">{{ r.ruleMatter }}</td>
                <td class="px-3 py-2"><span class="px-1.5 py-[2px] rounded bg-ink-200/40 text-[10px] font-bold">{{ state.jurisShort(r.juris) }}</span></td>
                <td class="px-3 py-2"><button (click)="state.togglePin(r)" class="text-ink-200 hover:text-magenta">&times;</button></td>
              </tr>
            </ng-container>
          </tbody>
        </table>
      </div>
      <div>
        <label class="block text-[10.5px] font-semibold text-ink-400 tracking-[.06em] mb-1">RULEBOOK NAME</label>
        <input [(ngModel)]="name" placeholder="APAC payments licence 2027"
               class="w-full px-3 py-2 rounded-lg border border-ink-200 text-[12.5px] ring-focus" />
        <label class="block text-[10.5px] font-semibold text-ink-400 tracking-[.06em] mb-1 mt-3">SCOPE / ENTITY</label>
        <input [(ngModel)]="scope" placeholder="Retail bank, payments, HK + IN + SG"
               class="w-full px-3 py-2 rounded-lg border border-ink-200 text-[12.5px] ring-focus" />
        <button (click)="create()"
          class="mt-3 w-full py-2.5 rounded-lg bg-aava text-white text-[12.5px] font-semibold hover:bg-aava-600">
          Create rulebook and extract obligations
        </button>
        <div class="mt-2 text-[11px] text-ink-400 leading-snug">
          On create, AAVA extracts obligations from each pinned rule using trigger phrases and semantics,
          and queues them for human review.
        </div>
      </div>
    </div>
  </div>

  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50">
    <div class="px-5 py-3 border-b border-ink-200/50 flex items-center justify-between">
      <div><span class="text-[13px] font-semibold">Rulebooks</span>
        <span class="text-[11.5px] text-ink-400 ml-2">{{ books().length }} saved</span></div>
      <button (click)="seed()" class="px-3 py-1.5 rounded-lg border border-ink-200 text-[11.5px] hover:bg-shell-100">
        Load a sample rulebook
      </button>
    </div>
    <div *ngIf="books().length; else none" class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
      <div *ngFor="let b of books()" class="border border-ink-200/60 rounded-xl p-4 hover:shadow-card">
        <div class="font-semibold text-[13px]">{{ b.name }}</div>
        <div class="text-[11px] text-ink-400">{{ b.id }} · created {{ b.created }} · {{ b.scope }}</div>
        <div class="grid grid-cols-2 gap-2 mt-3">
          <div class="bg-shell-100 rounded-lg p-2"><div class="text-[9.5px] text-ink-400">RULES</div>
            <div class="text-[17px] font-semibold">{{ b.ruleIds.length }}</div></div>
          <div class="bg-shell-100 rounded-lg p-2"><div class="text-[9.5px] text-ink-400">OBLIGATIONS</div>
            <div class="text-[17px] font-semibold">{{ b.obligationCount }}</div></div>
        </div>
        <div class="mt-3 flex gap-2">
          <a routerLink="/obligations" [queryParams]="{ rulebookId: b.id }"
             class="flex-1 text-center py-1.5 rounded-lg bg-aava text-white text-[11.5px] font-medium">View obligations</a>
          <a routerLink="/maps" class="flex-1 text-center py-1.5 rounded-lg border border-ink-200 text-[11.5px] hover:bg-shell-100">Build map</a>
        </div>
      </div>
    </div>
    <ng-template #none>
      <div class="p-10 text-center">
        <div class="text-[13px] font-medium">No rulebooks yet</div>
        <div class="text-[12px] text-ink-400 mt-1 max-w-md mx-auto">
          Go to Regulatory Search, filter by rule matter and rule type, pin the rules you need, then create a rulebook here.
        </div>
        <div class="mt-3 flex items-center justify-center gap-2">
          <a routerLink="/search" class="px-4 py-2 rounded-lg bg-aava text-white text-[12px] font-semibold">Start a search</a>
          <button (click)="seed()" class="px-4 py-2 rounded-lg border border-ink-200 text-[12px] font-medium">Load a sample rulebook</button>
        </div>
      </div>
    </ng-template>
  </div>
 </div>
</div>
`,
})
export class RulebooksComponent implements OnInit {
  private api = inject(ApiService);
  state = inject(StateService);

  name = '';
  scope = '';
  books = signal<Rulebook[]>([]);

  grouped = computed(() => {
    const map = new Map<string, typeof this.state.pinned extends never ? never : ReturnType<typeof this.state.pinned>>();
    const out = new Map<string, ReturnType<typeof this.state.pinned>>();
    for (const r of this.state.pinned()) {
      const arr = out.get(r.ruleType) ?? [];
      arr.push(r);
      out.set(r.ruleType, arr);
    }
    void map;
    return [...out.entries()].map(([key, items]) => ({ key, items }));
  });

  ngOnInit(): void { this.refresh(); }
  private refresh(): void { this.api.rulebooks().subscribe((b) => this.books.set(b)); }

  create(): void {
    const ids = this.state.pinned().map((r) => r.id);
    if (!ids.length) { this.state.notify('Pin at least one rule first.'); return; }
    this.api
      .createRulebook(this.name.trim() || `Rulebook ${this.books().length + 1}`, this.scope.trim() || 'Not set', ids)
      .subscribe((b) => {
        this.state.clearPins();
        this.state.activeRulebookId.set(b.id);
        this.name = ''; this.scope = '';
        this.refresh();
        this.state.notify(`${b.name} created with ${b.ruleIds.length} rules.`);
      });
  }

  seed(): void {
    this.api.seedRulebook().subscribe((b) => {
      this.refresh();
      this.state.activeRulebookId.set(b.id);
      this.state.notify(`${b.name} loaded with ${b.ruleIds.length} rules.`);
    });
  }
}
