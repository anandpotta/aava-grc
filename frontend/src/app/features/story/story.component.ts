import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';

/** The worked leadership example: one regulatory change followed end to end. Content comes from /api/story. */
@Component({
  selector: 'aava-story',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
<div *ngIf="s() as st" class="max-w-[1180px] mx-auto p-6 space-y-4">
  <div class="rounded-2xl text-white px-6 py-5 shadow-card" style="background:#1e2147">
    <div class="text-[10px] tracking-widest" style="color:#b8bdf0">WORKED EXAMPLE · {{ st.institution }}</div>
    <div class="text-[24px] font-semibold mt-1">{{ st.title }}</div>
    <div class="text-[13px] mt-1" style="color:#d5d8ee">{{ st.tagline }}</div>
    <div class="mt-3 text-[12px] bg-white/10 rounded-lg px-3 py-2"><b>The trigger</b> ({{ st.trigger.ref }}): {{ st.trigger.text }}</div>
    <div class="mt-2 text-[10.5px]" style="color:#aab0d8">{{ st.disclaimer }}</div></div>
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 p-5"><div class="text-[13px] font-semibold mb-3">What happens, step by step</div>
    <div class="space-y-2"><div *ngFor="let x of st.steps" class="flex gap-3 items-start rounded-xl border border-ink-200/60 px-3 py-2.5">
      <div class="w-16 shrink-0 text-[11px] font-semibold text-ink-500">{{ x.time }}</div>
      <div class="flex-1"><div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded text-[9.5px] font-semibold bg-aava-50 text-aava-700">{{ x.mode.toUpperCase() }}</span><span class="text-[12.5px] font-semibold">{{ x.n }}. {{ x.title }}</span></div>
        <div class="text-[11.5px] text-ink-600 mt-0.5">{{ x.what }}</div>
        <div class="text-[11px] text-aava-700 mt-0.5"><b>{{ x.agent }}.</b> {{ x.human }}</div></div>
      <a routerLink="/ask" class="shrink-0 px-2.5 py-1 rounded-lg border border-aava text-aava-700 text-[10.5px]">Run in Ask AAVA</a></div></div></div>
  <div class="grid grid-cols-2 gap-4">
    <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 overflow-hidden"><div class="px-5 py-2.5 border-b border-ink-200/50 text-[12.5px] font-semibold">Before and after (targets, to confirm in a pilot)</div>
      <table class="w-full text-[11px]"><tr *ngFor="let c of st.compare" class="border-t border-ink-200/40 align-top"><td class="px-4 py-2 font-medium">{{ c.q }}</td><td class="pr-2 text-ink-500">{{ c.before }}</td><td class="pr-2 text-jade-700">{{ c.after }}</td></tr></table></div>
    <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 p-5"><div class="text-[12.5px] font-semibold mb-2">Why this is our USP</div>
      <ul class="space-y-1.5 text-[11.5px]"><li *ngFor="let u of st.usp">● {{ u }}</li></ul></div></div>
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 p-5"><div class="text-[13px] font-semibold mb-2">The narration, ready to say aloud</div>
    <div *ngFor="let n of st.narration" class="flex gap-3 mb-2"><div class="w-24 shrink-0 text-[10px] font-semibold text-aava-700 pt-0.5">{{ n.beat.toUpperCase() }}</div><div class="text-[12.5px] leading-relaxed">{{ n.say }}</div></div></div>
  <div class="bg-white rounded-2xl shadow-card border border-ink-200/50 p-5"><div class="text-[13px] font-semibold mb-3">Problems this solves</div>
    <div class="grid grid-cols-3 gap-3"><div *ngFor="let p of st.problems" class="rounded-xl border border-ink-200/60 p-3"><div class="text-[11.5px] font-semibold text-aava-700 mb-1.5">{{ p.group }}</div>
      <ul class="space-y-1 text-[11px] text-ink-600"><li *ngFor="let i of p.items">• {{ i }}</li></ul></div></div></div>
</div>`,
})
export class StoryComponent implements OnInit {
  private api = inject(ApiService);
  s = signal<any>(null);
  ngOnInit() { this.api.story().subscribe((d) => this.s.set(d)); }
}
