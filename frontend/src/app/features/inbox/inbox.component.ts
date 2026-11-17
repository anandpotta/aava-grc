import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';

/** Notifications, comments and approvals for every regulatory change, in one place. */
@Component({
  selector: 'aava-inbox',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
<div class="max-w-[1100px] mx-auto p-6 space-y-3">
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-5 py-4"><div class="text-[16px] font-semibold">Inbox</div>
    <div class="text-[11.5px] text-ink-400">When a regulation changes, the owners of the affected policies, controls and issues are told here. Comment, mention people and approve in the thread for that change.</div></div>
  <div class="grid grid-cols-12 gap-3">
    <div class="col-span-4 bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Regulatory changes</div>
      <button *ngFor="let c of changes()" (click)="select(c)" class="w-full text-left px-4 py-2.5 border-b border-ink-200/40 hover:bg-shell-100" [class.bg-aava-50]="current()?.id===c.id">
        <div class="flex items-center gap-2"><span class="font-mono text-[10px] text-ink-400">{{ c.id }}</span><span class="px-1.5 rounded bg-shell-100 text-[9.5px]">{{ c.regulator }}</span><span *ngIf="count(c.id)" class="ml-auto px-1.5 rounded-full bg-magenta text-white text-[9.5px]">{{ count(c.id) }}</span></div>
        <div class="text-[12px] leading-snug">{{ c.title }}</div></button></div>
    <div class="col-span-8 space-y-3" *ngIf="current() as c">
      <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 p-4"><div class="flex items-center gap-2"><b class="text-[13px]">{{ c.id }} · {{ c.title }}</b>
        <button *ngIf="!coord()?.status?.total" (click)="notify(c)" class="ml-auto px-3 py-1.5 rounded-lg bg-aava text-white text-[11.5px]">Notify stakeholders</button></div></div>
      <ng-container *ngIf="coord()?.status?.total">
        <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden"><div class="px-4 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Notifications <span class="font-normal text-[10.5px] text-ink-400">{{ coord().status.acknowledged }} of {{ coord().status.total }} acknowledged · {{ coord().status.escalated }} escalated</span></div>
          <div *ngFor="let n of notes()" class="px-4 py-2 border-b border-ink-200/40 text-[11.5px] flex items-start gap-3">
            <span class="px-1.5 rounded font-bold" [ngClass]="n.raci==='A' ? 'bg-aava text-white' : n.raci==='R' ? 'bg-gold-50 text-gold-700' : 'bg-shell-100'" [title]="n.raciText">{{ n.raci }}</span>
            <div class="flex-1"><b>{{ n.to.name }}</b> <span class="text-ink-400">{{ n.to.role }} · {{ n.channels.join(' · ') }}</span><div class="text-ink-600">{{ n.body }}</div></div>
            <span class="px-1.5 py-[1px] rounded text-[10px] font-semibold" [ngClass]="n.status==='acknowledged' ? 'bg-jade-50 text-jade-700' : n.status==='escalated' ? 'bg-magenta-50 text-magenta-700' : 'bg-gold-50 text-gold-700'">{{ n.status }}</span>
            <button *ngIf="n.status==='sent'" (click)="ack(n)" class="text-aava-700 hover:underline">Acknowledge</button></div>
          <div class="px-4 py-2 bg-shell-100 text-[11px]"><button (click)="escalate(c)" class="px-2.5 py-1 rounded-lg border border-ink-200 bg-white">Fast-forward 100 hours</button> <span class="text-ink-400">Silent Accountable or Responsible people go to their manager.</span></div></div>
        <div class="bg-white rounded-2xl shadow-card border border-ink-200/50"><div class="px-4 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Comments</div>
          <div class="p-3 space-y-2 text-[11.5px] max-h-80 overflow-auto"><div *ngFor="let m of coord().messages" class="rounded-lg px-2.5 py-1.5" [ngClass]="m.authorKind==='agent' ? 'bg-shell-100' : m.type==='decision' ? 'bg-jade-50' : 'border border-ink-200/50'">
            <div class="flex justify-between text-[10px] text-ink-400"><b class="text-ink-800">{{ m.author }}</b><span>{{ m.at | date:'d MMM HH:mm' }}</span></div>{{ m.text }}</div></div>
          <div class="p-2.5 border-t border-ink-200/50 flex gap-1.5"><select [(ngModel)]="author" class="text-[11px] border border-ink-200 rounded-lg px-1.5"><option *ngFor="let s of people()" [value]="s.id">{{ s.name }}</option></select>
            <input [(ngModel)]="text" (keyup.enter)="say(c)" placeholder="Comment, or @Legal to pull someone in" class="flex-1 text-[11.5px] border border-ink-200 rounded-lg px-2 py-1"/><button (click)="say(c)" class="px-2.5 rounded-lg bg-aava text-white text-[11.5px]">Send</button></div></div>
        <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 p-4 text-[12px]"><div class="flex items-center gap-2 mb-1"><b>Approval</b>
          <span class="px-1.5 py-[1px] rounded text-[10px] font-semibold" [ngClass]="coord().approval?.status==='approved' ? 'bg-jade-50 text-jade-700' : 'bg-gold-50 text-gold-700'">{{ coord().approval?.status || 'not requested' }}</span>
          <button *ngIf="!coord().approval" (click)="requestApproval(c)" class="ml-auto px-3 py-1 rounded-lg border border-ink-200 hover:border-aava">Request CCO approval</button></div>
          <div *ngFor="let a of coord().approval?.required" class="flex items-center gap-2 py-1.5 border-t border-ink-200/40"><b class="w-40">{{ a.name }}</b><span class="w-52 text-ink-400">{{ a.role }}</span>
            <ng-container *ngIf="a.decision; else btns"><span class="px-1.5 rounded bg-shell-100 font-semibold">{{ a.decision }}</span><span class="text-ink-600">{{ a.note }}</span></ng-container>
            <ng-template #btns><button (click)="decide(c, a, 'approve')" class="px-2.5 py-1 rounded-lg bg-aava text-white">Approve</button><button (click)="decide(c, a, 'changes')" class="px-2.5 py-1 rounded-lg border border-ink-200">Request changes</button><button (click)="decide(c, a, 'reject')" class="px-2.5 py-1 rounded-lg border border-ink-200">Reject</button></ng-template></div>
          <div *ngIf="err" class="text-magenta-700 text-[11px] mt-1">{{ err }}</div></div>
      </ng-container>
    </div>
  </div>
</div>`,
})
export class InboxComponent implements OnInit {
  private api = inject(ApiService);
  private state = inject(StateService);
  changes = signal<any[]>([]);
  current = signal<any>(null);
  coord = signal<any>(null);
  notes = signal<any[]>([]);
  all = signal<any[]>([]);
  people = signal<any[]>([]);
  author = 'SH-02';
  text = '';
  err = '';

  ngOnInit() {
    this.api.stakeholders().subscribe((p) => this.people.set(p));
    this.api.changes().subscribe((c) => { this.changes.set(c); if (c.length) this.select(c[0]); });
    this.loadAll();
  }
  private loadAll() { this.api.allNotifications().subscribe((n) => this.all.set(n)); }
  count = (id: string) => this.all().filter((n) => n.changeId === id && n.status === 'sent').length;
  select(c: any) { this.current.set(c); this.refresh(c); }
  refresh(c: any) {
    this.api.coordination(c.id).subscribe((x) => this.coord.set(x));
    this.api.notifications(c.id).subscribe((n) => this.notes.set(n));
    this.loadAll();
  }
  notify(c: any) { this.api.notifyChange(c.id).subscribe(() => { this.state.notify('Stakeholders notified.'); this.refresh(c); }); }
  ack(n: any) { this.api.ackNotification(n.id).subscribe(() => this.refresh(this.current())); }
  escalate(c: any) { this.api.escalate(c.id, 100).subscribe(() => this.refresh(c)); }
  say(c: any) { this.err = ''; this.api.comment(c.id, this.author, this.text).subscribe({ next: () => { this.text = ''; this.refresh(c); }, error: (e) => (this.err = e.error?.detail ?? 'Could not post') }); }
  requestApproval(c: any) { this.api.requestApproval(c.id, 'gate3', `Approve the remediation plan for ${c.title}.`).subscribe(() => this.refresh(c)); }
  decide(c: any, a: any, d: string) { this.err = ''; this.api.decide(c.id, a.id, d, this.text).subscribe({ next: () => { this.text = ''; this.refresh(c); }, error: (e) => (this.err = e.error?.detail ?? 'Could not record') }); }
}
