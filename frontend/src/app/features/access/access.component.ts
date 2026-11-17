import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';

/** Who is who: roles say what a person can do, named gates say what they may release. */
@Component({
  selector: 'aava-access',
  standalone: true,
  imports: [CommonModule],
  template: `
<div class="max-w-[1180px] mx-auto p-6 space-y-3">
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 px-5 py-4"><div class="text-[16px] font-semibold">Roles and access</div>
    <div class="text-[11.5px] text-ink-400 mt-0.5">A <b>role</b> says what a person can do. A <b>named approver</b> says which gates they may release. Both are needed, and nobody approves what they raised themselves. Use <b>Acting as</b> in the top bar to see the platform as any of these people.</div>
    <div *ngIf="!state.can('manage_roles')" class="mt-2 text-[11px] px-2.5 py-1.5 rounded-lg bg-gold-50 text-gold-700">Only a platform administrator can change this page. Switch Acting as to Kavya Nair to try it.</div></div>
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden"><div class="px-5 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Who is who</div>
    <table class="w-full text-[11.5px]"><tr class="bg-shell-100 text-[9.5px] tracking-wide text-ink-400 text-left"><th class="px-4 py-1.5">PERSON</th><th>ROLE</th><th>NAMED APPROVER FOR</th></tr>
      <tr *ngFor="let u of users()" class="border-t border-ink-200/40 align-top" [class.bg-aava-50]="u.id===state.userId()">
        <td class="px-4 py-2"><b>{{ u.name }}</b> <span *ngIf="u.id===state.userId()" class="px-1 rounded bg-aava text-white text-[9px]">acting as</span><div class="text-[10px] text-ink-400">{{ u.title }}</div></td>
        <td class="pr-3"><select [disabled]="!state.can('manage_roles')" (change)="setRole(u, $any($event.target).value)" class="border border-ink-200 rounded-lg px-1.5 py-1 text-[11px] bg-white"><option *ngFor="let r of roles()" [value]="r.id" [selected]="r.id===u.role">{{ r.name }}</option></select></td>
        <td class="pr-3"><label *ngFor="let g of gates" class="inline-flex items-center gap-1 mr-2" [class.opacity-40]="!canApprove(u)"><input type="checkbox" [checked]="u.approves.includes(g)" [disabled]="!state.can('manage_roles') || !canApprove(u)" (change)="setGate(u, g, $any($event.target).checked)"> {{ g }}</label></td></tr></table></div>
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-x-auto"><div class="px-5 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">What each role can do</div>
    <table class="w-full text-[11px]"><tr class="bg-shell-100 text-[9.5px] tracking-wide text-ink-400 text-left"><th class="px-4 py-1.5">PERMISSION</th><th *ngFor="let r of roles()" class="px-2 text-center">{{ r.name.toUpperCase() }}</th></tr>
      <tr *ngFor="let p of permKeys()" class="border-t border-ink-200/40"><td class="px-4 py-1.5">{{ perms()[p] }}</td><td *ngFor="let r of roles()" class="text-center" [ngClass]="r.perms.includes(p) ? 'text-jade-700' : 'text-ink-200'">{{ r.perms.includes(p) ? '●' : '·' }}</td></tr></table></div>
  <div class="rounded-xl bg-aava-50 border-l-4 border-aava px-4 py-3 text-[11.5px] leading-relaxed"><b>Rules that never change.</b> Auditors and regulators cannot change or approve anything. Anything leaving the organisation needs a Gate 3 approver. Nobody approves what they raised. At least one administrator and one Gate 3 approver always exist. Every change here is written to the audit trail.</div>
</div>`,
})
export class AccessComponent implements OnInit {
  private api = inject(ApiService);
  state = inject(StateService);
  users = signal<any[]>([]);
  roles = signal<any[]>([]);
  perms = signal<Record<string, string>>({});
  gates = ['Gate 1', 'Gate 2', 'Gate 3'];
  permKeys = () => Object.keys(this.perms());
  ngOnInit() { this.api.accessRoles().subscribe((r) => { this.roles.set(r.roles); this.perms.set(r.permissions); }); this.load(); }
  load() { this.api.accessUsers().subscribe((u) => this.users.set(u)); this.api.accessMe().subscribe((m) => this.state.me.set(m)); }
  canApprove = (u: any) => this.roles().find((r) => r.id === u.role)?.perms.includes('approve');
  setRole(u: any, role: string) { this.api.accessUpdate(u.id, { role }).subscribe({ next: () => this.load(), error: (e) => { this.state.notify(e.error?.detail ?? 'Not allowed'); this.load(); } }); }
  setGate(u: any, g: string, on: boolean) {
    const approves = on ? [...new Set([...u.approves, g])] : u.approves.filter((x: string) => x !== g);
    this.api.accessUpdate(u.id, { approves }).subscribe({ next: () => this.load(), error: (e) => { this.state.notify(e.error?.detail ?? 'Not allowed'); this.load(); } });
  }
}
