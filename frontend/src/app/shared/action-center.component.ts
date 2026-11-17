import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../core/api.service';
import { StateService } from '../core/state.service';

/** Act mode: everything that wants to change something waits here for a named approver. */
@Component({
  selector: 'aava-action-center',
  standalone: true,
  imports: [CommonModule],
  template: `
<div class="rounded-xl bg-white border border-aava-200 shadow-card overflow-hidden">
  <div class="px-4 py-2.5 border-b border-ink-200/50 flex items-center gap-2"><span class="text-[13px] font-semibold">Action center</span>
    <span class="px-1.5 py-[1px] rounded text-[10px] font-semibold" [ngClass]="pending() ? 'bg-gold-50 text-gold-700' : 'bg-jade-50 text-jade-700'">{{ pending() }} waiting</span>
    <span class="text-[10.5px] text-ink-400">Act can draft, create tasks and send, but nothing is released until a named person approves.</span></div>
  <div *ngFor="let x of items()" class="px-4 py-2.5 border-b border-ink-200/40 flex items-start gap-3 text-[12px]">
    <span class="font-mono text-[10px] text-ink-400 w-12 pt-0.5">{{ x.id }}</span>
    <div class="flex-1"><b>{{ x.title }}</b><div class="text-[11px] text-ink-600">{{ x.detail }}</div><div class="text-[10.5px] text-ink-400">{{ x.gate }} · approver: {{ x.approver }}</div>
      <div *ngIf="x.status==='approved'" class="text-[11px] text-jade-700 mt-0.5">✓ Approved. {{ x.result }}</div><div *ngIf="x.status==='rejected'" class="text-[11px] text-magenta-700 mt-0.5">Rejected. Nothing was changed.</div></div>
    <ng-container *ngIf="x.status==='pending'; else done"><button (click)="decide(x,'approved')" class="px-2.5 py-1 rounded-lg bg-aava text-white text-[11.5px]">Approve</button><button (click)="decide(x,'rejected')" class="px-2.5 py-1 rounded-lg border border-ink-200 text-[11.5px]">Reject</button></ng-container>
    <ng-template #done><span class="px-1.5 py-[1px] rounded bg-shell-100 text-[10px] font-semibold">{{ x.status }}</span></ng-template></div>
  <div *ngIf="!items().length" class="px-4 py-4 text-[12px] text-ink-400">Nothing waiting. Run a scenario, or create a fix plan from an assessment.</div>
</div>`,
})
export class ActionCenterComponent implements OnInit {
  private api = inject(ApiService);
  private state = inject(StateService);
  items = signal<any[]>([]);
  pending = () => this.items().filter((x) => x.status === 'pending').length;
  ngOnInit() { this.load(); }
  load() { this.api.actions().subscribe((a) => this.items.set(a)); }
  decide(x: any, d: string) { this.api.decideAction(x.id, d).subscribe({ next: () => { this.state.notify(d === 'approved' ? 'Approved and audited.' : 'Rejected. Nothing was changed.'); this.load(); }, error: (e) => this.state.notify(e.error?.detail ?? 'Failed') }); }
}
