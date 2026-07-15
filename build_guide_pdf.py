#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_guide_pdf.py — reusable ReportLab helpers for self-host installation guides.

This module implements the house style described in references/document-format.md:
a plain formal document, title-metadata table, numbered sections, NOTE/IMPORTANT
callout boxes, and safe code-block chunking (long docker-compose.yml / config
listings are split into page-sized pieces automatically, which avoids the
"Flowable too large" LayoutError that a single giant shaded Table can raise).

USAGE
-----
Import this module from a small per-guide script, build a `story` list using the
helper functions below, then call `build(output_path, title, subtitle, meta_rows, story)`.

    from build_guide_pdf import h1, h2, body, bullets, code_block, note_box, simple_table, build

    story = []
    story.append(h1("Overview", 1))
    story.append(body("This guide explains how to self-host Example App..."))
    story += code_block("apt update && apt upgrade -y")
    story += note_box("DNS propagation can take 5-30 minutes.", kind="note")

    build(
        output_path="/mnt/user-data/outputs/ExampleApp_Installation_Guide.pdf",
        title="Example App",
        subtitle="Installation Guide with Caddy Reverse Proxy Integration",
        header_left="Example App Installation Guide | Confidential",
        header_right="example.com — Example App (Self-Hosted)",
        footer_note="Example App is community software — verify current config against the upstream repo before production use.",
        meta_rows=[
            ("Server", "example.com (YOUR_SERVER_IP)"),
            ("Operating System", "Debian 13 (Trixie)"),
            ("Reverse Proxy", "Caddy v2 (automatic HTTPS)"),
            ("Date", "July 2026"),
        ],
        intro_note="The official stack uses Traefik; this guide substitutes Caddy because...",
        story=story,
    )

See the bottom of this file for a minimal runnable self-test.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, HRFlowable,
)
from reportlab.pdfgen import canvas as pdfcanvas

# ---------------------------------------------------------------
# Palette — plain / formal house style
# ---------------------------------------------------------------
INK = colors.HexColor("#1A1A1A")
HEAD_BG = colors.HexColor("#2E2E2E")
ROW_ALT = colors.HexColor("#F2F2F2")
RULE = colors.HexColor("#BFBFBF")
CODE_BG = colors.HexColor("#EDEDED")
CODE_BORDER = colors.HexColor("#C9C9C9")
WARN_BG = colors.HexColor("#FDEEDC")
WARN_BORDER = colors.HexColor("#E3A248")
NOTE_BG = colors.HexColor("#E7EEF7")
NOTE_BORDER = colors.HexColor("#4472A8")
MUTED = colors.HexColor("#5B5B5B")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
MAX_LINES_PER_CHUNK = 34  # keeps any single code block within one page's height

ss = getSampleStyleSheet()
styles = {
    "TitleMain": ParagraphStyle("TitleMain", fontName="Helvetica-Bold", fontSize=22,
                                 textColor=INK, leading=27, spaceAfter=4),
    "TitleSub": ParagraphStyle("TitleSub", fontName="Helvetica", fontSize=13.5,
                                textColor=colors.HexColor("#404040"), leading=18, spaceAfter=14),
    "H1": ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=15.5, textColor=INK,
                          spaceBefore=6, spaceAfter=9, leading=19),
    "H2": ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=11.5, textColor=INK,
                          spaceBefore=12, spaceAfter=5, leading=15),
    "Body": ParagraphStyle("Body", fontName="Helvetica", fontSize=9.7, textColor=INK,
                            leading=14, spaceAfter=6),
    "Bullet": ParagraphStyle("Bullet", fontName="Helvetica", fontSize=9.7, textColor=INK,
                              leading=13.8, spaceAfter=3),
    "Code": ParagraphStyle("Code", fontName="Courier", fontSize=8.6, textColor=INK, leading=12.2),
    "CodeCaption": ParagraphStyle("CodeCaption", fontName="Helvetica-Oblique", fontSize=8.4,
                                   textColor=MUTED, leading=11, spaceAfter=2),
    "TableHead": ParagraphStyle("TableHead", fontName="Helvetica-Bold", fontSize=8.6,
                                 textColor=colors.white, leading=11),
    "TableCell": ParagraphStyle("TableCell", fontName="Helvetica", fontSize=8.6,
                                 textColor=INK, leading=11.8),
    "TableCellMono": ParagraphStyle("TableCellMono", fontName="Courier", fontSize=8.1,
                                     textColor=INK, leading=11),
    "NoteBody": ParagraphStyle("NoteBody", fontName="Helvetica", fontSize=8.9,
                                textColor=INK, leading=12.8),
    "Caption": ParagraphStyle("Caption", fontName="Helvetica-Oblique", fontSize=8,
                               textColor=MUTED, leading=10.5, spaceBefore=2, spaceAfter=8),
}


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nbsp_code(text: str) -> str:
    out = []
    for line in text.split("\n"):
        stripped = line.lstrip(" ")
        n_lead = len(line) - len(stripped)
        out.append("&nbsp;" * n_lead + stripped)
    return "<br/>".join(out)


def _code_chunk_table(chunk_text: str):
    p = Paragraph(nbsp_code(esc(chunk_text)), styles["Code"])
    t = Table([[p]], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, CODE_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def code_block(code: str, caption: str = None):
    """Shaded, monospace code block. Long content is split into page-sized
    chunks automatically -- always extend `story` with this (story += code_block(...)),
    never story.append(...), since it returns a list of flowables."""
    flow = []
    if caption:
        flow.append(Paragraph(esc(caption), styles["CodeCaption"]))
    lines = code.split("\n")
    for start in range(0, len(lines), MAX_LINES_PER_CHUNK):
        chunk = "\n".join(lines[start:start + MAX_LINES_PER_CHUNK])
        flow.append(_code_chunk_table(chunk))
        flow.append(Spacer(1, 2))
    flow.append(Spacer(1, 6))
    return flow


def note_box(body_text: str, kind: str = "note"):
    """kind is 'note' or 'warn'. Returns a list -- extend story with +=, not append()."""
    bg = NOTE_BG if kind == "note" else WARN_BG
    border = NOTE_BORDER if kind == "note" else WARN_BORDER
    label = "NOTE" if kind == "note" else "IMPORTANT"
    label_hex = "#2E5A94" if kind == "note" else "#8A5A12"
    style = styles["NoteBody"]
    inner = [
        Paragraph(f'<font color="{label_hex}"><b>{label}</b></font>', style),
        Paragraph(esc(body_text).replace("\n", "<br/>"), style),
    ]
    t = Table([[inner]], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [t, Spacer(1, 8)]


def simple_table(headers, rows, col_widths, zebra=True):
    """rows: list of lists of strings. Wrap a cell value in backticks, e.g. '`docker ps`',
    to render it in monospace."""
    data = [[Paragraph(h, styles["TableHead"]) for h in headers]]
    for r in rows:
        row = []
        for cell in r:
            mono = cell.startswith("`") and cell.endswith("`") and len(cell) > 1
            row.append(Paragraph(esc(cell[1:-1] if mono else cell),
                                  styles["TableCellMono"] if mono else styles["TableCell"]))
        data.append(row)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if zebra:
        cmds.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]))
    t.setStyle(TableStyle(cmds))
    return t


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(esc(i), styles["Bullet"]), leftIndent=6) for i in items],
        bulletType="bullet", start="•", leftIndent=14, spaceBefore=2, spaceAfter=8,
    )


def h1(text, num=None):
    return Paragraph(esc(f"{num}. {text}" if num else text), styles["H1"])


def h2(text, num=None):
    return Paragraph(esc(f"{num} {text}" if num else text), styles["H2"])


def body(text):
    """text may contain simple <b>/<i>/<font> tags -- it is NOT escaped, so escape
    plain text yourself with esc() first if it contains literal < or &."""
    return Paragraph(text, styles["Body"])


def rule():
    return HRFlowable(width="100%", thickness=0.5, color=RULE, spaceBefore=3, spaceAfter=8)


def end_of_document():
    return Paragraph("— End of Document —", styles["Caption"])


class _NumberedCanvas(pdfcanvas.Canvas):
    """Draws the running header/footer on every page at save time."""
    def __init__(self, *args, header_left="", header_right="", footer_note="", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self._header_left = header_left
        self._header_right = header_right
        self._footer_note = footer_note

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_chrome()
            super().showPage()
        super().save()

    def _draw_chrome(self):
        self.saveState()
        self.setFont("Helvetica", 7.8)
        self.setFillColor(MUTED)
        self.drawString(MARGIN, PAGE_H - 12 * mm, self._header_left)
        self.drawRightString(PAGE_W - MARGIN, PAGE_H - 12 * mm,
                              f"{self._header_right}  Page {self._pageNumber}")
        self.setStrokeColor(RULE)
        self.setLineWidth(0.5)
        self.line(MARGIN, PAGE_H - 13.5 * mm, PAGE_W - MARGIN, PAGE_H - 13.5 * mm)
        if self._footer_note:
            self.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
            self.setFont("Helvetica", 7.6)
            self.drawCentredString(PAGE_W / 2, 9.5 * mm, self._footer_note)
        self.restoreState()


def build(output_path, title, subtitle, meta_rows, story,
          header_left=None, header_right=None, footer_note="", intro_note=None):
    """
    output_path : where to write the PDF
    title       : big title on page 1, e.g. "AstraDraw"
    subtitle    : one-line subtitle, e.g. "Installation Guide with Caddy Reverse Proxy Integration"
    meta_rows   : list of (label, value) tuples for the title-page metadata table
    story       : list of flowables for the body (built with the helpers in this module,
                  starting from Section 1 -- do NOT include the title page, it's built here)
    header_left / header_right : running page header text (defaults derived from title/subtitle)
    footer_note : one-line disclaimer shown centered in the footer of every page
    intro_note  : optional NOTE box text shown directly under the metadata table
                  (use this for "official proxy differs" disclosures)
    """
    header_left = header_left or f"{title} Installation Guide | Confidential"
    header_right = header_right or title

    doc = BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"{title} — {subtitle}", author="Self-Host Deployment Reference",
    )
    frame = Frame(MARGIN, 18 * mm, PAGE_W - 2 * MARGIN, PAGE_H - 18 * mm - 18 * mm, id="content")
    doc.addPageTemplates([PageTemplate(id="Normal", frames=[frame], onPage=lambda c, d: None)])

    full_story = []
    full_story.append(Spacer(1, 6))
    full_story.append(Paragraph(esc(title), styles["TitleMain"]))
    full_story.append(Paragraph(esc(subtitle), styles["TitleSub"]))
    full_story.append(rule())

    meta_table = Table(
        [[Paragraph(f"<b>{esc(k)}</b>", styles["TableCell"]), Paragraph(esc(v), styles["TableCell"])]
         for k, v in meta_rows],
        colWidths=[42 * mm, 108 * mm]
    )
    meta_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, RULE),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F5F5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    full_story.append(meta_table)
    full_story.append(Spacer(1, 10))
    if intro_note:
        full_story += note_box(intro_note, kind="note")
    full_story.append(PageBreak())
    full_story.extend(story)

    def _make_canvas(*args, **kwargs):
        return _NumberedCanvas(*args, header_left=header_left, header_right=header_right,
                                footer_note=footer_note, **kwargs)

    doc.build(full_story, canvasmaker=_make_canvas)


# ---------------------------------------------------------------
# Minimal self-test -- run `python3 build_guide_pdf.py` directly to confirm
# the environment can render a guide before wiring up real content.
# ---------------------------------------------------------------
if __name__ == "__main__":
    demo_story = []
    demo_story.append(h1("Overview", 1))
    demo_story.append(body("This is a self-test of build_guide_pdf.py."))
    demo_story.append(h2("1.1 Architecture"))
    demo_story.append(simple_table(
        ["Component", "Port", "Role"],
        [["App", "8080", "Main application"], ["Database", "5432", "Storage"]],
        [60 * mm, 30 * mm, 80 * mm],
    ))
    demo_story += note_box("This is a NOTE callout.", kind="note")
    demo_story += note_box("This is an IMPORTANT callout.", kind="warn")
    demo_story += code_block("apt update && apt upgrade -y", caption="Example command")
    demo_story.append(bullets(["First prerequisite", "Second prerequisite"]))
    demo_story.append(end_of_document())

    build(
        output_path="/tmp/self_test_guide.pdf",
        title="Example App",
        subtitle="Installation Guide with Caddy Reverse Proxy Integration",
        meta_rows=[
            ("Server", "example.com (YOUR_SERVER_IP)"),
            ("Operating System", "Debian 13 (Trixie)"),
            ("Reverse Proxy", "Caddy v2 (automatic HTTPS)"),
            ("Date", "July 2026"),
        ],
        story=demo_story,
        footer_note="Self-test output -- not a real guide.",
        intro_note="This is a demonstration of the title-page NOTE box.",
    )
    print("Self-test PDF written to /tmp/self_test_guide.pdf")
