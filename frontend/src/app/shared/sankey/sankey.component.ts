import {
  AfterViewInit, Component, ElementRef, EventEmitter, Input, OnChanges,
  OnDestroy, Output, SimpleChanges, ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import * as d3 from 'd3';
import { sankey, sankeyLeft, sankeyLinkHorizontal } from 'd3-sankey';
import { Band, LayerInfo, SankeyGraph, SankeyLinkDto, SankeyNodeDto } from '../../core/models';

/** d3-sankey mutates the objects it is handed, so we feed it copies. */
interface SNode extends SankeyNodeDto {
  x0?: number; y0?: number; x1?: number; y1?: number; index?: number;
}
interface SLink extends Omit<SankeyLinkDto, 'source' | 'target'> {
  source: SNode | string; target: SNode | string;
  width?: number; y0?: number; y1?: number; index?: number;
}

/** Colour per layer type, falling back to position for unknown types. */
const LAYER_COLOUR: Record<string, string> = {
  'Rule': '#6666CC', 'Rule Book': '#6666CC', 'Obligation': '#8A8AD9',
  'Policy': '#008567', 'Control': '#BA7517', 'Risk': '#CC0066', 'Issue': '#A30052',
};
const FALLBACK = ['#6666CC', '#8A8AD9', '#008567', '#BA7517', '#CC0066', '#A30052'];

/** Link colour by similarity band — the legacy red / amber / green scale. */
const BAND_COLOUR: Record<Band, string> = {
  Strong: '#74C476', Partial: '#F0B429', Minimal: '#E24B4A', Unmapped: '#C9CBD6',
};

@Component({
  selector: 'aava-sankey',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative">
      <div #host class="overflow-x-auto bg-shell-100/30 p-3"></div>
      <div #tip class="tipbox hidden"></div>
    </div>
  `,
})
export class SankeyComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('host', { static: true }) hostRef!: ElementRef<HTMLDivElement>;
  @ViewChild('tip', { static: true }) tipRef!: ElementRef<HTMLDivElement>;

  @Input({ required: true }) graph!: SankeyGraph;
  /** uids to keep lit; everything else dims. Empty/null = show everything. */
  @Input() focus: Set<string> | null = null;
  @Input() selectedUid: string | null = null;
  /** Draw the 0.001 placeholder links. Off by default — they are layout only. */
  @Input() showPlaceholders = false;
  @Input() width = 1290;

  @Output() nodeClick = new EventEmitter<SankeyNodeDto>();
  @Output() backgroundClick = new EventEmitter<void>();

  private ready = false;

  ngAfterViewInit(): void { this.ready = true; this.render(); }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.ready) return;
    // A focus-only change just re-applies opacity; no need to re-layout.
    const keys = Object.keys(changes);
    if (keys.length && keys.every((k) => k === 'focus' || k === 'selectedUid')) {
      this.applyFocus();
      return;
    }
    this.render();
  }

  ngOnDestroy(): void { d3.select(this.hostRef.nativeElement).selectAll('*').remove(); }

  private colourOf(n: SankeyNodeDto): string {
    return LAYER_COLOUR[n.layerType] ?? FALLBACK[n.layer % FALLBACK.length];
  }

  // ------------------------------------------------------------------ render
  private render(): void {
    const host = d3.select(this.hostRef.nativeElement);
    host.selectAll('*').remove();
    if (!this.graph || !this.graph.nodes.length) return;

    const layers: LayerInfo[] = this.graph.layers;
    const nodes: SNode[] = this.graph.nodes.map((n) => ({ ...n }));
    const present = new Set(nodes.map((n) => n.uid));
    const links: SLink[] = this.graph.links
      .filter((l) => this.showPlaceholders || !l.placeholder)
      .filter((l) => present.has(l.source) && present.has(l.target))
      .map((l) => ({ ...l }));

    // Nodes with no link at all would be dropped by the layout, so re-attach
    // them with a zero-weight edge to keep the legacy "every node shows" rule.
    if (!this.showPlaceholders) {
      const touched = new Set<string>();
      links.forEach((l) => { touched.add(l.source as string); touched.add(l.target as string); });
      const byLayer = new Map<number, SNode[]>();
      nodes.forEach((n) => {
        const arr = byLayer.get(n.layer) ?? [];
        arr.push(n); byLayer.set(n.layer, arr);
      });
      nodes.forEach((n) => {
        if (touched.has(n.uid)) return;
        const prev = byLayer.get(n.layer - 1);
        const next = byLayer.get(n.layer + 1);
        if (prev && prev.length) {
          links.push({
            source: prev[0].uid, target: n.uid, value: 0.001, band: 'Unmapped',
            placeholder: true, sourceLayer: n.layer - 1, targetLayer: n.layer,
          });
        } else if (next && next.length) {
          links.push({
            source: n.uid, target: next[0].uid, value: 0.001, band: 'Unmapped',
            placeholder: true, sourceLayer: n.layer, targetLayer: n.layer + 1,
          });
        }
      });
    }

    const labelPad = 190;
    const inner = Math.max(400, this.width - labelPad);
    const tallest = Math.max(...layers.map((l) => l.nodeCount), 1);
    const height = Math.max(420, Math.min(4200, tallest * 26 + 60));

    const svg = host
      .append('svg')
      .attr('width', this.width)
      .attr('height', height + 30)
      .attr('viewBox', `0 0 ${this.width} ${height + 30}`)
      .style('min-width', `${this.width}px`)
      .on('click', () => this.backgroundClick.emit());

    // layer headers
    const step = layers.length > 1 ? (inner - 20) / (layers.length - 1) : 0;
    layers.forEach((l, i) => {
      svg.append('text')
        .attr('x', 8 + i * step).attr('y', 14)
        .attr('font-size', 10.5).attr('font-weight', 700)
        .attr('fill', LAYER_COLOUR[l.type] ?? FALLBACK[i % FALLBACK.length])
        .text(`${l.label.toUpperCase()} (${l.nodeCount})`);
    });

    const root = svg.append('g').attr('transform', 'translate(0,24)');

    const layout = sankey<SNode, SLink>()
      .nodeId((d) => d.uid)
      .nodeWidth(13)
      .nodePadding(nodes.length > 400 ? 2 : 8)
      .nodeAlign(sankeyLeft)
      .extent([[6, 6], [inner, height - 12]]);

    let data: { nodes: SNode[]; links: SLink[] };
    try {
      data = layout({ nodes, links } as never) as unknown as { nodes: SNode[]; links: SLink[] };
    } catch {
      host.append('div')
        .attr('class', 'py-10 text-center text-[12.5px] text-ink-400')
        .text('This map could not be laid out — it contains a cycle.');
      return;
    }

    // ---- links ------------------------------------------------------------
    const linkSel = root.append('g')
      .attr('fill', 'none')
      .selectAll<SVGPathElement, SLink>('path')
      .data(data.links)
      .join('path')
      .attr('class', 'link-path')
      .attr('d', sankeyLinkHorizontal<SNode, SLink>() as never)
      .attr('stroke', (d) => (d.placeholder ? '#D9D9E3' : BAND_COLOUR[d.band]))
      .attr('stroke-width', (d) => Math.max(1, d.width ?? 1))
      .attr('stroke-opacity', (d) => (d.placeholder ? 0.07 : d.band === 'Strong' ? 0.5 : 0.62))
      .on('mousemove', (e: MouseEvent, d) => {
        if (d.placeholder) return;
        const s = d.source as SNode, t = d.target as SNode;
        this.showTip(e, `<b>${esc(s.label || s.name)}</b> &rarr; <b>${esc(t.label || t.name)}</b>
          <br>${d.band} · score ${d.value.toFixed(2)}`);
      })
      .on('mouseleave', () => this.hideTip());

    // ---- nodes ------------------------------------------------------------
    const nodeG = root.append('g')
      .selectAll<SVGGElement, SNode>('g')
      .data(data.nodes)
      .join('g')
      .attr('class', 'nd');

    nodeG.append('rect')
      .attr('class', 'node-rect')
      .attr('x', (d) => d.x0 ?? 0)
      .attr('y', (d) => d.y0 ?? 0)
      .attr('width', (d) => (d.x1 ?? 0) - (d.x0 ?? 0))
      .attr('height', (d) => Math.max(3, (d.y1 ?? 0) - (d.y0 ?? 0)))
      .attr('rx', 2.5)
      .attr('fill', (d) => this.colourOf(d))
      .attr('opacity', (d) => (d.impacted ? 1 : 0.72))
      .on('mousemove', (e: MouseEvent, d) => this.showTip(e, this.tipHtml(d)))
      .on('mouseleave', () => this.hideTip())
      .on('click', (e: MouseEvent, d) => { e.stopPropagation(); this.nodeClick.emit(d); });

    // impact triangle — the legacy red marker, now on any impacted node
    nodeG.filter((d) => d.impacted)
      .append('polygon')
      .attr('class', 'tri')
      .attr('points', (d) => {
        const cx = ((d.x0 ?? 0) + (d.x1 ?? 0)) / 2;
        const y = (d.y0 ?? 0) - 3.5;
        return `${cx},${y - 7.5} ${cx + 6.2},${y} ${cx - 6.2},${y}`;
      })
      .attr('fill', '#CC0066')
      .attr('stroke', '#fff')
      .attr('stroke-width', 0.7)
      .style('cursor', 'pointer')
      .on('mousemove', (e: MouseEvent, d) =>
        this.showTip(e, `<b>&#9650; ${esc(d.layerType)} impacted</b><br>${esc(d.name)}
          <br><span style="color:#F7CFE2">Click to isolate everything connected to it.</span>`))
      .on('mouseleave', () => this.hideTip())
      .on('click', (e: MouseEvent, d) => { e.stopPropagation(); this.nodeClick.emit(d); });

    // labels: first column reads right-to-left, the rest left-to-right
    nodeG.append('text')
      .attr('x', (d) => (d.layer === 0 ? (d.x0 ?? 0) - 7 : (d.x1 ?? 0) + 6))
      .attr('y', (d) => (((d.y0 ?? 0) + (d.y1 ?? 0)) / 2))
      .attr('dy', '0.34em')
      .attr('text-anchor', (d) => (d.layer === 0 ? 'end' : 'start'))
      .attr('font-size', 8.6)
      .attr('fill', '#4A4A52')
      .style('pointer-events', 'none')
      .text((d) => {
        if ((d.y1 ?? 0) - (d.y0 ?? 0) < 7) return '';
        const s = d.label || d.name || '';
        return s.length > 26 ? `${s.slice(0, 25)}…` : s;
      });

    // keep the first column's labels inside the viewport
    root.attr('transform', `translate(${nodes.some((n) => n.layer === 0) ? 150 : 0},24)`);
    svg.attr('width', this.width + 150).attr('viewBox', `0 0 ${this.width + 150} ${height + 30}`);

    this.sel = { nodeG, linkSel };
    this.applyFocus();
  }

  private sel: {
    nodeG: d3.Selection<SVGGElement, SNode, SVGGElement, unknown>;
    linkSel: d3.Selection<SVGPathElement, SLink, SVGGElement, unknown>;
  } | null = null;

  /** Dim everything that is not in the connected sub-graph. */
  private applyFocus(): void {
    if (!this.sel) return;
    const keep = this.focus;
    const { nodeG, linkSel } = this.sel;
    if (!keep || !keep.size) {
      nodeG.selectAll<SVGRectElement, SNode>('rect').attr('opacity', (d) => (d.impacted ? 1 : 0.72));
      nodeG.selectAll('text').attr('opacity', 1);
      nodeG.selectAll('.tri').attr('opacity', 1);
      linkSel.attr('stroke-opacity', (d) =>
        d.placeholder ? 0.07 : d.band === 'Strong' ? 0.5 : 0.62);
      return;
    }
    nodeG.selectAll<SVGRectElement, SNode>('rect')
      .attr('opacity', (d) => (keep.has(d.uid) ? (d.uid === this.selectedUid ? 1 : 0.92) : 0.1));
    nodeG.selectAll<SVGTextElement, SNode>('text')
      .attr('opacity', (d) => (keep.has(d.uid) ? 1 : 0.16));
    nodeG.selectAll<SVGPolygonElement, SNode>('.tri')
      .attr('opacity', (d) => (keep.has(d.uid) ? 1 : 0.12));
    linkSel.attr('stroke-opacity', (d) => {
      const s = typeof d.source === 'string' ? d.source : d.source.uid;
      const t = typeof d.target === 'string' ? d.target : d.target.uid;
      if (d.placeholder) return keep.has(s) && keep.has(t) ? 0.14 : 0.03;
      return keep.has(s) && keep.has(t) ? 0.85 : 0.05;
    });
  }

  private tipHtml(d: SankeyNodeDto): string {
    const m = d.meta ?? {};
    const extra =
      d.layerType === 'Control' ? `<br>owner ${esc(String(m['owner'] ?? '—'))} · test ${esc(String(m['testResult'] ?? '—'))}`
      : d.layerType === 'Risk' ? `<br>residual ${esc(String(m['residual'] ?? '—'))} vs appetite ${esc(String(m['appetite'] ?? '—'))}`
      : d.layerType === 'Issue' ? `<br>${esc(String(m['statusLabel'] ?? ''))} ${m['due'] ? '· due ' + esc(String(m['due'])) : ''}`
      : d.layerType === 'Obligation' ? `<br>confidence ${esc(String(m['confidence'] ?? '—'))}%`
      : '';
    const quote = d.quote ? `<br><span style="opacity:.8">${esc(d.quote.slice(0, 160))}…</span>` : '';
    const flag = d.impacted
      ? '<br><span style="color:#F7CFE2">&#9650; impacted — click to isolate</span>'
      : '<br><span style="color:#B4B2A9">click to isolate</span>';
    return `<b>${esc(d.layerType)}: ${esc(d.label || d.name)}</b>
      <br>band ${d.band}${extra}${quote}${flag}`;
  }

  private showTip(e: MouseEvent, html: string): void {
    const t = this.tipRef.nativeElement;
    t.innerHTML = html;
    t.classList.remove('hidden');
    t.style.left = `${Math.min(window.innerWidth - 300, e.clientX + 12)}px`;
    t.style.top = `${Math.min(window.innerHeight - 120, e.clientY + 14)}px`;
  }
  private hideTip(): void { this.tipRef.nativeElement.classList.add('hidden'); }
}

function esc(s: string): string {
  return (s ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c] ?? c));
}
