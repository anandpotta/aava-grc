import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';
import { StateService } from '../core/state.service';

/** Share a report with named people. Anyone outside the organisation needs CCO approval, and every copy is fingerprinted. */
@Component({
  selector: 'aava-share-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
<div class="mt-3">
  <button (click)="open.set(!open())" class="px-3 py-1.5 rounded-lg border border-ink-200 bg-white text-[11.5px] hover:border-aava">Share…</button>
  <div *ngIf="open()" class="mt-2 rounded-lg bg-shell-100 p-3 text-[11.5px]">
    <div class="grid grid-cols-3 gap-x-3 gap-y-1">
      <label *ngFor="let p of people()" class="flex items-center gap-1.5"><input type="checkbox" [checked]="sel.has(p.id)" (change)="toggle(p.id)"> {{ p.name }} <span class="text-ink-400">{{ p.short }}</span></label>
      <label *ngFor="let x of external" class="flex items-center gap-1.5"><input type="checkbox" [checked]="sel.has(x.id)" (change)="toggle(x.id)"> {{ x.name }} <span class="px-1 rounded bg-gold-50 text-gold-700 text-[9px]">needs CCO approval</span></label>
    </div>
    <div class="flex items-center gap-2 mt-2">
      <select [(ngModel)]="access" class="border border-ink-200 rounded-lg px-1.5 py-1"><option>View only</option><option>Can comment</option></select>
      <select [(ngModel)]="days" class="border border-ink-200 rounded-lg px-1.5 py-1"><option [ngValue]="7">Expires in 7 days</option><option [ngValue]="30">30 days</option><option [ngValue]="90">90 days</option></select>
      <input [(ngModel)]="note" placeholder="Message (optional)" class="flex-1 border border-ink-200 rounded-lg px-2 py-1"/>
      <button (click)="send()" class="px-3 py-1 rounded-lg bg-aava text-white">Share</button></div>
    <div class="text-[10.5px] text-ink-400 mt-1.5">The report is fingerprinted when shared. Anyone can later check that their copy is the copy that was sent.</div></div>
  <div *ngIf="shares().length" class="mt-2"><div class="text-[10px] font-semibold tracking-wide text-ink-400 mb-1">SHARED REPORTS</div>
    <div *ngFor="let s of shares()" class="flex items-center gap-2 py-1.5 border-t border-ink-200/40 text-[11.5px]"><span class="font-mono text-[10px]">{{ s.id }}</span>
      <span class="flex-1">{{ s.to.join(', ') }}<span class="text-ink-400"> · {{ s.access }} · expires {{ s.expiresInDays }} d · #{{ s.fingerprint.slice(0,10) }}</span></span>
      <span class="px-1.5 py-[1px] rounded text-[10px] font-semibold" [ngClass]="s.status==='sent' ? 'bg-jade-50 text-jade-700' : 'bg-gold-50 text-gold-700'">{{ s.status }}</span>
      <button (click)="verify(s.id)" class="text-aava-700 hover:underline">Verify copy</button></div></div>
</div>`,
})
export class SharePanelComponent implements OnInit {
  private api = inject(ApiService);
  private state = inject(StateService);
  @Input() subject = 'org';
  people = signal<any[]>([]);
  shares = signal<any[]>([]);
  open = signal(false);
  sel = new Set<string>();
  access = 'View only';
  days = 7;
  note = '';
  external = [{ id: 'X-1', name: 'External auditor' }, { id: 'X-2', name: 'Regulator liaison' }];

  ngOnInit() { this.api.stakeholders().subscribe((p) => this.people.set(p)); this.reload(); }
  reload() { this.api.shares().subscribe((s) => this.shares.set(s)); }
  toggle(id: string) { this.sel.has(id) ? this.sel.delete(id) : this.sel.add(id); }
  send() {
    this.api.share({ subject: this.subject, scope: this.state.scope(), recipients: [...this.sel], access: this.access, expiresInDays: this.days, note: this.note }).subscribe({
      next: (s) => { this.state.notify(s.status === 'sent' ? 'Shared and audited.' : 'Waiting for CCO approval before it leaves the organisation.'); this.sel.clear(); this.open.set(false); this.reload(); },
      error: (e) => this.state.notify(e.error?.detail ?? 'Could not share'),
    });
  }
  verify(id: string) { this.api.verifyShare(id).subscribe((r) => this.state.notify(r.matches ? 'Verified: this copy matches what was shared.' : 'Different: the report changed since it was shared.')); }
}
