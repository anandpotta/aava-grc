import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ApiService } from './core/api.service';
import { StateService } from './core/state.service';
import { HierarchyNavComponent } from './shared/hierarchy-nav.component';

interface NavItem { path: string; label: string; wip?: boolean; }

@Component({
  selector: 'aava-root',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterOutlet, RouterLink, RouterLinkActive, HierarchyNavComponent],
  template: `
<div class="flex min-h-screen">
  <!-- side nav -->
  <aside class="w-[252px] shrink-0 bg-white border-r border-ink-200/60 flex flex-col sticky top-0 h-screen">
    <div class="px-4 py-4 border-b border-ink-200/50">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-lg bg-aava flex items-center justify-center text-white font-bold text-[13px]">AV</div>
        <div class="leading-tight">
          <div class="font-semibold text-[14px]">AAVA <span class="text-aava">GRC</span></div>
          <div class="text-[10.5px] text-ink-400">Regulatory Intelligence</div>
        </div>
      </div>
    </div>

    <nav class="flex-1 overflow-y-auto px-2.5 py-3 text-[12.5px]">
      <div class="px-2 pb-1.5 text-[10px] font-semibold tracking-[.09em] text-ink-400">WORKSPACE</div>
      <a *ngFor="let n of nav" [routerLink]="n.path" routerLinkActive="bg-aava-100 text-aava-700 font-medium"
         class="w-full text-left px-2.5 py-[7px] rounded-lg flex items-center gap-2 text-ink-600 hover:bg-shell-100">
        <span class="flex-1">{{ n.label }}</span>
        <span *ngIf="n.wip" class="px-1.5 py-0.5 rounded bg-gold-50 text-gold-700 text-[9px] font-semibold">WIP</span>
        <span *ngIf="n.path === '/rulebooks' && books() > 0"
              class="px-1.5 py-0.5 rounded-full bg-aava-200 text-aava-900 text-[9.5px] font-semibold">{{ books() }}</span>
      </a>

      <div class="px-2 pt-4 pb-1.5 text-[10px] font-semibold tracking-[.09em] text-ink-400">REGULATORY HIERARCHY</div>
      <div class="text-[12px]"><aava-hierarchy-nav /></div>

      <div class="px-2 pt-4 pb-1.5 text-[10px] font-semibold tracking-[.09em] text-ink-400">FRAMEWORKS</div>
      <a *ngFor="let f of frameworks()" [routerLink]="'/search'" [queryParams]="{ framework: f.id }"
         class="w-full text-left px-2.5 py-[7px] rounded-lg block text-ink-600 hover:bg-shell-100">
        <span class="block">{{ f.name }}</span>
        <span class="block text-[9.5px] text-ink-400">{{ f.sub }}</span>
      </a>
    </nav>

    <div class="px-3 py-2.5 border-t border-ink-200/50 bg-shell-100">
      <div class="text-[9.5px] text-ink-400 leading-snug">Demo tenant · illustrative seed data, not legal content</div>
    </div>
  </aside>

  <!-- main -->
  <main class="flex-1 min-w-0 flex flex-col">
    <header class="h-[54px] shrink-0 bg-white border-b border-ink-200/60 flex items-center justify-between px-5 sticky top-0 z-40">
      <div class="text-[12.5px] text-ink-400">Workspace</div>
      <div class="flex items-center gap-2">
        <a routerLink="/inbox" class="relative w-8 h-8 rounded-lg border border-ink-200 bg-white flex items-center justify-center hover:border-aava" title="Notifications and comments" aria-label="Notifications and comments">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0112 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 004 0"/></svg>
          <span *ngIf="unread() > 0" class="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-magenta text-white text-[9px] font-semibold flex items-center justify-center">{{ unread() }}</span></a>
        <a *ngIf="state.pinnedCount() > 0" routerLink="/rulebooks"
           class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-gold-50 border border-gold/40 text-[11.5px] font-medium">
          {{ state.pinnedCount() }} pinned — create rulebook
        </a>
        <div class="flex items-center gap-2 pl-2 border-l border-ink-200/60">
          <div class="w-7 h-7 rounded-full bg-magenta/10 text-magenta-700 flex items-center justify-center text-[11px] font-semibold">{{ initials() }}</div>
          <div class="text-[11px] leading-tight">
            <div class="text-[9px] text-ink-400 tracking-wide">ACTING AS</div>
            <select [ngModel]="state.userId()" (ngModelChange)="switchUser($event)" aria-label="Acting as" class="text-[11.5px] font-medium bg-transparent border-0 p-0 pr-4 cursor-pointer">
              <option *ngFor="let u of people()" [value]="u.id">{{ u.name }} · {{ u.roleName }}</option></select>
            <div class="text-[10px]" [ngClass]="state.me()?.readOnly ? 'text-gold-700' : 'text-ink-400'">{{ state.me()?.roleName }}<span *ngIf="state.me()?.approves?.length"> · approves {{ state.me().approves.join(', ') }}</span><span *ngIf="state.me()?.readOnly"> · read only</span></div>
          </div>
        </div>
      </div>
    </header>

    <div class="flex-1 min-w-0"><router-outlet /></div>
  </main>
</div>

<div *ngIf="state.toast() as msg"
     class="fixed bottom-5 left-1/2 -translate-x-1/2 z-[95] px-4 py-2.5 rounded-xl bg-ink text-white text-[12.5px] shadow-pop">
  {{ msg }}
</div>
`,
})
export class AppComponent implements OnInit {
  private api = inject(ApiService);
  state = inject(StateService);

  nav: NavItem[] = [
    { path: '/ask', label: 'Ask AAVA' },
    { path: '/scope', label: 'Scope' },
    { path: '/search', label: 'Regulatory Search' },
    { path: '/rulebooks', label: 'Rulebooks' },
    { path: '/obligations', label: 'Obligations' },
    { path: '/library', label: 'Controls and policies' },
    { path: '/maps', label: 'Compliance Maps' },
    { path: '/reg-change', label: 'Reg Change Management' },
    { path: '/inbox', label: 'Inbox' },
    { path: '/story', label: 'Worked example' },
    { path: '/access', label: 'Roles and access' },
  ];

  unread = signal(0);
  people = signal<any[]>([]);
  initials = () => (this.state.me()?.name ?? '').split(' ').map((x: string) => x[0]).join('').slice(0, 2);
  switchUser(id: string) { this.state.setUser(id); this.loadMe(); }
  loadMe() { this.api.accessMe().subscribe((m) => this.state.me.set(m)); this.api.accessUsers().subscribe((u) => this.people.set(u)); }
  private bookCount = signal(0);
  books = computed(() => this.bookCount());
  jurisdictions = computed(() => this.state.reference()?.jurisdictions ?? []);
  frameworks = computed(() => this.state.reference()?.frameworks ?? []);

  ngOnInit(): void {
    this.api.reference().subscribe({
      next: (r) => this.state.reference.set(r),
      error: () => this.state.notify('Cannot reach the API. Is the backend running on port 8000?'),
    });
    this.api.rulebooks().subscribe((b) => this.bookCount.set(b.length));
    const poll = () => this.api.allNotifications().subscribe({ next: (n) => this.unread.set(n.filter((x: any) => x.status === 'sent').length), error: () => {} });
    poll(); setInterval(poll, 15000);
    this.loadMe();
  }
}
