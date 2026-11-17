"""Exports.

Your legacy page built the XLS client-side from a hidden HTML table and the PDF
with jsPDF + canvg, which means the export only contains what the browser had
rendered. Doing it on the server means the full map is exported, the numbers
match the API, and a scheduled job can produce the same file without a browser.

* CSV  – always available
* XLSX – requires openpyxl (summary sheet + full traceability register)
* PDF  – requires reportlab
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import BAND_MINIMAL, BAND_PARTIAL, BAND_STRONG, BAND_UNMAPPED
from app.services.sankey_service import ComplianceGraph


def _register_rows(graph: ComplianceGraph, limit: int = 20000) -> (List[str], List[List[Any]]):
    """One row per traced path through the map."""
    cols = [li.label for li in graph.layer_infos()]
    header = cols + ["Weakest band", "Impacted"]
    rows: List[List[Any]] = []
    firsts = [n for n in graph.nodes if n.layer == 0]
    rank = {BAND_STRONG: 0, BAND_PARTIAL: 1, BAND_MINIMAL: 2, BAND_UNMAPPED: 3}

    def walk(uid: str, acc: List[str]) -> None:
        if len(rows) >= limit:
            return
        nxt = graph.out_links.get(uid, [])
        if not nxt:
            cells: List[Any] = [""] * len(cols)
            worst, impacted = BAND_STRONG, False
            for cuid in acc:
                n = graph.by_uid[cuid]
                cells[n.layer] = n.label or n.name
                impacted = impacted or n.impacted
                if rank.get(n.band, 3) > rank.get(worst, 0):
                    worst = n.band
            rows.append(cells + [worst, "Yes" if impacted else "No"])
            return
        for li in nxt:
            t = graph.links[li].target
            acc.append(t)
            walk(t, acc)
            acc.pop()

    for n in firsts:
        walk(n.uid, [n.uid])
    return header, rows


def to_csv(graph: ComplianceGraph) -> bytes:
    header, rows = _register_rows(graph)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return ("﻿" + buf.getvalue()).encode("utf-8")


def to_xlsx(graph: ComplianceGraph) -> Optional[bytes]:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:  # pragma: no cover
        return None

    wb = Workbook()
    head_fill = PatternFill("solid", fgColor="EEEEFA")
    head_font = Font(bold=True, color="43439B")

    # --- summary sheet ----------------------------------------------------
    ws = wb.active
    ws.title = "Summary"
    s = graph.summary()
    ws.append(["AAVA GRC — compliance map summary"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append(["Map", graph.name])
    ws.append(["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
    ws.append([])
    ws.append(["Coverage score", f"{s.coverageScore}%"])
    ws.append(["Nodes", s.totalNodes])
    ws.append(["Real links", s.realLinks])
    ws.append(["Placeholder links", s.totalLinks - s.realLinks])
    ws.append(["Impacted nodes", s.impacted])
    ws.append([])
    ws.append(["Layer", "Type", "Nodes", "Strong", "Partial", "Minimal", "Unmapped"])
    for c in ws[ws.max_row]:
        c.fill, c.font = head_fill, head_font
    for row in s.byLayer:
        ws.append([row["label"], row["type"], row["nodes"], row["strong"],
                   row["partial"], row["minimal"], row["unmapped"]])
    for col, width in zip("ABCDEFG", (26, 18, 10, 10, 10, 10, 12)):
        ws.column_dimensions[col].width = width

    # --- register sheet ---------------------------------------------------
    ws2 = wb.create_sheet("Traceability register")
    header, rows = _register_rows(graph)
    ws2.append(header)
    for c in ws2[1]:
        c.fill, c.font = head_fill, head_font
        c.alignment = Alignment(vertical="center")
    for r in rows:
        ws2.append(r)
    for i, _ in enumerate(header):
        ws2.column_dimensions[chr(65 + i) if i < 26 else "A"].width = 34
    ws2.freeze_panes = "A2"

    # --- unmapped sheet ---------------------------------------------------
    ws3 = wb.create_sheet("Gaps")
    ws3.append(["Layer", "Node", "Name", "Band", "In", "Out", "Findings"])
    for c in ws3[1]:
        c.fill, c.font = head_fill, head_font
    for n in graph.nodes:
        if n.band == BAND_UNMAPPED or n.impacted:
            ws3.append([
                graph.layer_infos()[n.layer].label, n.label or n.sourceId, n.name,
                n.band, n.inDegree, n.outDegree,
                "; ".join(graph.findings_for(n.uid)),
            ])
    for col, width in zip("ABCDEFG", (16, 26, 48, 12, 7, 7, 60)):
        ws3.column_dimensions[col].width = width

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def to_pdf(graph: ComplianceGraph) -> Optional[bytes]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError:  # pragma: no cover
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"AAVA GRC — {graph.name}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#212121"), alignment=0)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=8.5, leading=11)
    muted = ParagraphStyle("muted", parent=body, textColor=colors.HexColor("#71758A"))

    s = graph.summary()
    story: List[Any] = [
        Paragraph(f"Compliance map — {graph.name}", h1),
        Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
            f"{s.totalNodes} nodes · {s.realLinks} mapped links · coverage {s.coverageScore}%",
            muted,
        ),
        Spacer(1, 8),
    ]

    data = [["Layer", "Nodes", "Strong", "Partial", "Minimal", "Unmapped"]]
    for row in s.byLayer:
        data.append([row["label"], row["nodes"], row["strong"], row["partial"],
                     row["minimal"], row["unmapped"]])
    t = Table(data, hAlign="LEFT", colWidths=[70 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 24 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEFA")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#43439B")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9D9E3")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [t, Spacer(1, 12), Paragraph("Gaps and impacted nodes", styles["Heading3"])]

    gaps = [["Layer", "Node", "Band", "Findings"]]
    for n in graph.nodes:
        if n.band == BAND_UNMAPPED or n.impacted:
            gaps.append([
                graph.layer_infos()[n.layer].label,
                Paragraph((n.label or n.sourceId)[:60], body),
                n.band,
                Paragraph("; ".join(graph.findings_for(n.uid))[:220] or "—", body),
            ])
            if len(gaps) > 120:
                break
    gt = Table(gaps, hAlign="LEFT", colWidths=[26 * mm, 62 * mm, 22 * mm, 150 * mm], repeatRows=1)
    gt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FBE6F0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#A30052")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9D9E3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(gt)
    story += [
        Spacer(1, 10),
        Paragraph(
            "Generated by AAVA GRC Intelligence. Every AI-proposed mapping in this report carries a "
            "confidence score and is subject to reviewer sign-off before it is treated as evidence.",
            muted,
        ),
    ]
    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------- impact + mitigation plan
_ACTION = {
    "Obligation": "Confirm the obligation was read correctly, then map it to a policy clause",
    "Policy": "Draft or extend a policy clause that does what the rule says, and get the owner to approve it",
    "Control": "Design a control with an owner, frequency and evidence, then add it to the test plan",
    "Risk": "Link the risk to the control that mitigates it and record the residual rating",
    "Issue": "Raise a remediation issue with an owner and a due date",
}


def to_plan_html(graph: ComplianceGraph) -> bytes:
    """Impact and mitigation plan: what the map says is weak, what to do, and which rules changed. Rebuild the map after the fixes."""
    import html as h
    e = h.escape
    s = graph.summary()
    infos = graph.layer_infos()
    weak_rank = {BAND_MINIMAL: 1, BAND_UNMAPPED: 2}
    actions, changed = [], []
    for n in graph.nodes:
        if n.impacted:
            changed.append(n)
        if n.band in weak_rank and n.layer > 0:
            ltype = infos[n.layer].type
            feeders = [graph.by_uid[graph.links[i].source].label or graph.by_uid[graph.links[i].source].name for i in graph.in_links.get(n.uid, []) if not graph.links[i].placeholder]
            actions.append((weak_rank[n.band], ltype, n.label or n.name, n.band, _ACTION.get(ltype, "Review and strengthen the mapping"), ", ".join(feeders[:3]) or "nothing mapped to it yet"))
    actions.sort(key=lambda a: -a[0])
    layer_rows = "".join(f'<tr><td>{e(l["label"])}</td><td>{l["nodes"]}</td><td>{l["strong"]}</td><td>{l["partial"]}</td><td>{l["minimal"]}</td><td>{l["unmapped"]}</td></tr>' for l in s.byLayer) if hasattr(s, "byLayer") else ""
    act_rows = "".join(f"<tr><td>{i + 1}</td><td>{e(a[1])}</td><td>{e(a[2])}</td><td>{e(a[3])}</td><td>{e(a[4])}</td><td>{e(a[5])}</td></tr>" for i, a in enumerate(actions[:200]))
    chg_rows = "".join(f'<tr><td>{e(n.label or n.name)}</td><td>{e(infos[n.layer].type)}</td></tr>' for n in changed[:100])
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Impact and mitigation plan: {e(graph.name)}</title>
<style>body{{font-family:Segoe UI,sans-serif;max-width:1040px;margin:34px auto;padding:0 24px;line-height:1.55;color:#212121}}h1{{font-size:22px;margin:0}}h2{{font-size:15px;margin:26px 0 8px;border-bottom:2px solid #6666CC;padding-bottom:4px}}
.m{{color:#71758A;font-size:12px}}table{{width:100%;border-collapse:collapse;font-size:11.5px}}th{{background:#F2F2F4;text-align:left;padding:7px;font-size:10px;color:#71758A}}td{{padding:7px;border-bottom:1px solid #e6e6ea;vertical-align:top}}.n{{background:#EEEEFA;border-left:3px solid #6666CC;padding:10px 13px;margin:12px 0;font-size:12px}}</style></head><body>
<h1>Impact and mitigation plan</h1><div class="m">{e(graph.name)} · generated {when} · AAVA GRC Intelligence</div>
<div class="n"><b>Coverage score {s.coverageScore}%.</b> {len(actions)} nodes are weak or unmapped and {len(changed)} items are flagged as impacted by a regulatory change. Work the list from the top, then rebuild the map in AAVA and download this plan again to see the score move.</div>
<h2>1. Coverage by layer</h2><table><tr><th>LAYER</th><th>NODES</th><th>STRONG</th><th>PARTIAL</th><th>MINIMAL</th><th>UNMAPPED</th></tr>{layer_rows}</table>
<h2>2. Mitigation plan, most urgent first</h2><table><tr><th>#</th><th>LAYER</th><th>ITEM</th><th>STATE</th><th>WHAT TO DO</th><th>CURRENTLY FED BY</th></tr>{act_rows or '<tr><td colspan=6>Nothing weak. Every node is mapped.</td></tr>'}</table>
<h2>3. Impacted by a change</h2><table><tr><th>ITEM</th><th>LAYER</th></tr>{chg_rows or '<tr><td colspan=2>No impacted items.</td></tr>'}</table>
</body></html>"""
    return page.encode("utf-8")
