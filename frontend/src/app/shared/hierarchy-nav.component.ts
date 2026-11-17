import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';

interface HNode { id: string; label: string; level: string; count: number; ruleId?: string; title?: string; children?: HNode[]; q: Record<string, string>; }
const KEY: Record<string, string> = { jurisdiction: 'juris', regulator: 'regulator', instrument: 'instrument', part: 'part' };

/** Jurisdiction > regulator > instrument > part > rule. Opens to the first level; each click narrows the search. */
@Component({
  selector: 'aava-hierarchy-nav',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
<ng-template #node let-n let-depth="depth">
  <div class="flex items-center" [style.padding-left.px]="depth * 12">
    <button *ngIf="n.children?.length; else spacer" (click)="toggle(n.id)" class="w-4 h-5 text-ink-400 text-[11px]" [attr.aria-label]="isOpen(n.id) ? 'Collapse' : 'Expand'">
      <span class="inline-block transition-transform" [class.rotate-90]="isOpen(n.id)">&rsaquo;</span></button>
    <ng-template #spacer><span class="w-4"></span></ng-template>
    <a *ngIf="n.level !== 'rule'; else leaf" routerLink="/search" [queryParams]="n.q"
       class="flex-1 min-w-0 px-1.5 py-[5px] rounded-md flex items-center gap-1.5 hover:bg-shell-100 text-ink-600" [class.font-semibold]="depth === 0" [title]="n.label">
      <span *ngIf="depth === 0" class="w-[22px] h-[16px] rounded-[3px] bg-ink-200/50 text-[8.5px] font-bold text-ink-600 flex items-center justify-center shrink-0">{{ n.id.toUpperCase().slice(0,2) }}</span>
      <span class="truncate flex-1">{{ n.label }}</span><span class="text-[10px] text-ink-400">{{ n.count }}</span></a>
    <ng-template #leaf><a [routerLink]="['/rules', n.ruleId]" class="flex-1 min-w-0 px-1.5 py-[4px] rounded-md hover:bg-shell-100 text-ink-600 text-[11.5px]" [title]="n.title">
      <span class="mono text-[10.5px] text-aava-700">{{ n.label }}</span></a></ng-template>
  </div>
  <ng-container *ngIf="n.children?.length && isOpen(n.id)">
    <ng-container *ngFor="let c of n.children"><ng-container *ngTemplateOutlet="node; context: { $implicit: c, depth: depth + 1 }"></ng-container></ng-container>
  </ng-container>
</ng-template>
<div *ngFor="let n of tree()"><ng-container *ngTemplateOutlet="node; context: { $implicit: n, depth: 0 }"></ng-container></div>
`,
})
export class HierarchyNavComponent implements OnInit {
  private api = inject(ApiService);
  tree = signal<HNode[]>([]);
  private open = signal<Set<string>>(new Set());

  ngOnInit(): void {
    this.api.hierarchy().subscribe((t: any[]) => {
      const nodes = t.map((n) => this.decorate(n, {}));
      this.tree.set(nodes);
      this.open.set(new Set(nodes.map((n) => n.id)));          // first level open: every country shows its regulators
    });
  }
  private decorate(n: any, parent: Record<string, string>): HNode {
    const q = KEY[n.level] ? { ...parent, [KEY[n.level]]: KEY[n.level] === 'juris' ? n.id : n.label } : parent;
    return { ...n, q, children: n.children?.map((c: any) => this.decorate(c, q)) };
  }
  isOpen = (id: string) => this.open().has(id);
  toggle(id: string) { const s = new Set(this.open()); s.has(id) ? s.delete(id) : s.add(id); this.open.set(s); }
}
