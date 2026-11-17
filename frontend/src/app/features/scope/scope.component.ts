import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { StateService } from '../../core/state.service';

type Kind = 'rules' | 'policies' | 'controls';
interface Group { matter: string; items: { id: string; label: string; sub: string }[]; }

/** Choose only what applies to you. Everything else (assessment, map, report, watch) uses this scope. */
@Component({
  selector: 'aava-scope',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
<div class="max-w-[960px] mx-auto p-6">
  <div class="mb-3"><h1 class="text-[18px] font-semibold">Choose what applies to you</h1>
    <p class="text-[12px] text-ink-400">Assessments, the compliance map, reports and Watch use only what you choose here. Add a policy or control that is specific to you.</p></div>
  <div class="flex flex-wrap items-center gap-1.5 text-[11px] mb-3"><span class="text-ink-400">Start from</span>
    <button *ngFor="let p of presets()" (click)="preset(p)" class="px-2.5 py-1 rounded-full border border-ink-200 hover:border-aava bg-white">{{ p.name }}</button></div>
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden">
    <div class="px-4 pt-2 flex items-center gap-1 border-b border-ink-200/40">
      <button *ngFor="let t of tabs" (click)="tab.set(t.k)" class="px-3 py-1.5 text-[12px] border-b-2" [ngClass]="tab()===t.k ? 'border-aava text-aava-700 font-medium' : 'border-transparent text-ink-600'">{{ t.l }} <span *ngIf="t.k!=='add'" class="text-[10px] text-ink-400">{{ count(t.k) }}</span></button>
      <input *ngIf="tab()!=='add'" [(ngModel)]="q" placeholder="Search" class="ml-auto mb-1 border border-ink-200 rounded-lg px-2 py-1 text-[11.5px] w-56"/></div>
    <div *ngIf="tab()!=='add'" class="px-4 py-2 max-h-[56vh] overflow-y-auto">
      <div *ngFor="let g of groups()" class="border-b border-ink-200/40">
        <div class="flex items-center gap-2 py-1.5"><button (click)="fold(g.matter)" class="w-4 text-ink-400"><span class="inline-block" [class.rotate-90]="isOpen(g.matter)">&rsaquo;</span></button>
          <input type="checkbox" [checked]="onCount(g)===g.items.length" (change)="cat(g, $any($event.target).checked)"><b class="text-[12px]">{{ g.matter }}</b>
          <span class="text-[10.5px] text-ink-400">{{ onCount(g) }} of {{ g.items.length }} selected</span></div>
        <ng-container *ngIf="isOpen(g.matter)"><label *ngFor="let x of g.items" class="flex items-start gap-2 pl-8 py-1 text-[11.5px] hover:bg-shell-100/60 rounded">
          <input type="checkbox" class="mt-0.5" [checked]="isOn(x.id)" (change)="tog(x.id)"><span>{{ x.label }}<span class="block text-[10px] text-ink-400">{{ x.sub }}</span></span></label></ng-container></div></div>
    <div *ngIf="tab()==='add'" class="p-4 grid grid-cols-2 gap-5 text-[12px]">
      <div *ngFor="let k of kinds" class="rounded-xl border border-ink-200/60 p-4"><div class="font-semibold mb-2">Add a {{ k.one }}</div>
        <input [(ngModel)]="form[k.key].name" [placeholder]="k.one + ' name'" class="w-full border border-ink-200 rounded-lg px-2 py-1.5 mb-1.5"/>
        <input [(ngModel)]="form[k.key].owner" placeholder="Owner (role or team)" class="w-full border border-ink-200 rounded-lg px-2 py-1.5 mb-1.5"/>
        <select [(ngModel)]="form[k.key].ruleMatter" class="w-full border border-ink-200 rounded-lg px-2 py-1.5 mb-1.5"><option *ngFor="let m of matters()">{{ m }}</option></select>
        <div class="flex flex-wrap gap-x-3 gap-y-0.5 mb-2 text-[11px]"><label *ngFor="let j of juris()"><input type="checkbox" [checked]="form[k.key].jurisdictions.includes(j.id)" (change)="togJ(k.key, j.id)"> {{ j.short }}</label></div>
        <button (click)="add(k.key)" class="px-3 py-1.5 rounded-lg bg-aava text-white">Add {{ k.one }}</button>
        <div class="text-[10.5px] text-ink-400 mt-1.5">{{ k.key==='controls' ? 'A new control starts as Not tested, so it counts as partial until you test it.' : 'It is added to your scope straight away.' }}</div></div></div>
    <div class="px-4 py-3 border-t border-ink-200/60 bg-shell-100 flex items-center gap-2 text-[11.5px]"><span class="text-ink-600">{{ sel.rules.size }} rules · {{ sel.policies.size }} policies · {{ sel.controls.size }} controls</span>
      <button (click)="everything()" class="ml-auto px-3 py-1.5 rounded-lg border border-ink-200 bg-white">Use everything</button><button (click)="save()" class="px-3 py-1.5 rounded-lg bg-aava text-white font-medium">Save scope</button></div></div>
</div>`,
})
export class ScopeComponent implements OnInit {
  private api = inject(ApiService);
  private state = inject(StateService);
  cat_ = signal<any>(null);
  tab = signal<Kind | 'add'>('rules');
  q = '';
  open = signal<Set<string>>(new Set());
  sel: Record<Kind, Set<string>> = { rules: new Set(), policies: new Set(), controls: new Set() };
  tabs: { k: Kind | 'add'; l: string }[] = [{ k: 'rules', l: 'Rules' }, { k: 'policies', l: 'Policies' }, { k: 'controls', l: 'Controls' }, { k: 'add', l: 'Add your own' }];
  kinds: { key: 'policies' | 'controls'; one: string }[] = [{ key: 'policies', one: 'policy' }, { key: 'controls', one: 'control' }];
  form: Record<string, { name: string; owner: string; ruleMatter: string; jurisdictions: string[] }> = {
    policies: { name: '', owner: '', ruleMatter: 'KYC and CDD', jurisdictions: ['us'] }, controls: { name: '', owner: '', ruleMatter: 'KYC and CDD', jurisdictions: ['us'] } };
  presets = () => this.cat_()?.presets ?? [];
  juris = () => this.state.reference()?.jurisdictions ?? [];
  matters = () => (this.cat_()?.policies ?? []).map((g: Group) => g.matter);

  ngOnInit() { this.load(true); }
  private load(initial = false) {
    this.api.scopeCatalog().subscribe((c) => {
      this.cat_.set(c);
      if (initial) { const s = this.state.scope(); (['rules', 'policies', 'controls'] as Kind[]).forEach((k) => (this.sel[k] = new Set(s[k] ?? this.all(k)))); }
    });
  }
  private all(k: Kind): string[] { return (this.cat_()?.[k] ?? []).flatMap((g: Group) => g.items.map((i) => i.id)); }
  groups(): Group[] {
    const t = this.tab(); if (t === 'add') return [];
    const q = this.q.toLowerCase();
    return (this.cat_()?.[t] ?? []).map((g: Group) => ({ matter: g.matter, items: g.items.filter((i) => !q || (i.label + i.sub).toLowerCase().includes(q)) })).filter((g: Group) => g.items.length);
  }
  isOpen = (m: string) => !!this.q || this.open().has(m);
  fold(m: string) { const s = new Set(this.open()); s.has(m) ? s.delete(m) : s.add(m); this.open.set(s); }
  count = (k: Kind | 'add') => (k === 'add' ? 0 : this.sel[k].size);
  onCount = (g: Group) => g.items.filter((i) => this.sel[this.tab() as Kind].has(i.id)).length;
  isOn = (id: string) => this.sel[this.tab() as Kind].has(id);
  tog(id: string) { const s = this.sel[this.tab() as Kind]; s.has(id) ? s.delete(id) : s.add(id); }
  cat(g: Group, on: boolean) { const s = this.sel[this.tab() as Kind]; g.items.forEach((i) => (on ? s.add(i.id) : s.delete(i.id))); }
  preset(p: { name: string; matters: string[] | null }) {
    (['rules', 'policies', 'controls'] as Kind[]).forEach((k) => (this.sel[k] = new Set((this.cat_()[k] as Group[]).filter((g) => !p.matters || p.matters.includes(g.matter)).flatMap((g) => g.items.map((i) => i.id)))));
  }
  togJ(k: string, j: string) { const a = this.form[k].jurisdictions; this.form[k].jurisdictions = a.includes(j) ? a.filter((x) => x !== j) : [...a, j]; }
  add(key: 'policies' | 'controls') {
    this.api.addScopeItem(key, this.form[key]).subscribe({
      next: (it) => { this.sel[key].add(it.id); this.state.notify(`Added ${it.id} and put it in scope.`); this.form[key].name = ''; this.api.scopeCatalog().subscribe((c) => { this.cat_.set(c); this.tab.set(key); }); },
      error: () => this.state.notify('Give it a name, an owner and at least one country.'),
    });
  }
  everything() { this.state.scope.set({ rules: null, policies: null, controls: null }); (['rules', 'policies', 'controls'] as Kind[]).forEach((k) => (this.sel[k] = new Set(this.all(k)))); this.api.saveScope({ rules: null, policies: null, controls: null }).subscribe(); this.state.notify('Scope is now everything.'); }
  save() {
    const s = { rules: [...this.sel.rules], policies: [...this.sel.policies], controls: [...this.sel.controls] };
    if (!s.rules.length && !s.policies.length && !s.controls.length) { this.state.notify('Choose at least one item.'); return; }
    this.state.scope.set(s); this.api.saveScope(s).subscribe(() => this.state.notify('Scope saved. Assessments and reports now use only this.'));
  }
}
