import { Injectable, computed, signal } from '@angular/core';
import { Reference, Rule } from './models';

/** Small amount of cross-feature state: the pin tray and the reference data. */
@Injectable({ providedIn: 'root' })
export class StateService {
  readonly reference = signal<Reference | null>(null);
  readonly pinned = signal<Rule[]>([]);
  readonly activeRulebookId = signal<string | null>(null);
  readonly toast = signal<string | null>(null);
  /** Who is acting. Sent as X-AAVA-User; in production this comes from single sign-on. */
  readonly userId = signal<string>(localStorage.getItem('aava.user') ?? 'SH-01');
  readonly me = signal<any>(null);
  can = (perm: string) => !!this.me()?.perms?.includes(perm);
  setUser(id: string): void { this.userId.set(id); try { localStorage.setItem('aava.user', id); } catch { /* private mode */ } }
  /** What applies to this organisation. null for a kind means everything. */
  readonly scope = signal<{ rules: string[] | null; policies: string[] | null; controls: string[] | null }>({ rules: null, policies: null, controls: null });

  readonly pinnedCount = computed(() => this.pinned().length);
  readonly pinnedIds = computed(() => new Set(this.pinned().map((r) => r.id)));

  togglePin(rule: Rule): void {
    const cur = this.pinned();
    this.pinned.set(
      cur.some((r) => r.id === rule.id) ? cur.filter((r) => r.id !== rule.id) : [...cur, rule],
    );
  }
  pinMany(rules: Rule[]): void {
    const seen = new Set(this.pinned().map((r) => r.id));
    this.pinned.set([...this.pinned(), ...rules.filter((r) => !seen.has(r.id))]);
  }
  clearPins(): void { this.pinned.set([]); }

  private timer: ReturnType<typeof setTimeout> | null = null;
  notify(message: string): void {
    this.toast.set(message);
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => this.toast.set(null), 2800);
  }

  jurisName(id: string): string {
    return this.reference()?.jurisdictions.find((j) => j.id === id)?.name ?? id;
  }
  jurisShort(id: string): string {
    return this.reference()?.jurisdictions.find((j) => j.id === id)?.short ?? id.toUpperCase();
  }
}
