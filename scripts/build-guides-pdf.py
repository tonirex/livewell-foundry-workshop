"""Build deterministic PDFs for the LiveWell workshop knowledge guides.

Usage:
    python scripts/build-guides-pdf.py
    python scripts/build-guides-pdf.py --check
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml
from fpdf import FPDF


ROOT = Path(__file__).resolve().parents[1]
GUIDES_DIR = ROOT / "content" / "knowledge" / "livewell-guides"
PDF_DIR = GUIDES_DIR / "pdf"

TEXT_MAP = str.maketrans(
    {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2265": ">=",
        "\u2264": "<=",
        "\u00d7": "x",
        "\u2192": "->",
        "\u2022": "-",
        "\u00a0": " ",
    }
)


@dataclass(frozen=True)
class Guide:
    path: Path
    meta: dict
    body: str


class GuidePDF(FPDF):
    def __init__(self, guide_id: str) -> None:
        super().__init__()
        self.guide_id = guide_id
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(16, 16, 16)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        text = f"LiveWell Coach workshop - sample guidance - {self.guide_id} - page {self.page_no()}"
        self.cell(0, 8, sanitize(text), align="C")


def sanitize(text: str) -> str:
    text = text.translate(TEXT_MAP)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def strip_markdown(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return sanitize(text.strip())


def parse_guide(path: Path) -> Guide:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise ValueError(f"{path} missing front matter")
    _, front, body = raw.split("---", 2)
    meta = yaml.safe_load(front) or {}
    return Guide(path=path, meta=meta, body=body.strip())


def is_table_start(lines: list[str], idx: int) -> bool:
    return (
        idx + 1 < len(lines)
        and lines[idx].lstrip().startswith("|")
        and lines[idx + 1].lstrip().startswith("|")
        and "---" in lines[idx + 1]
    )


def collect_table(lines: list[str], idx: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    while idx < len(lines) and lines[idx].lstrip().startswith("|"):
        raw_cells = [strip_markdown(cell) for cell in lines[idx].strip().strip("|").split("|")]
        if not all(set(cell.replace(" ", "")) <= {"-"} for cell in raw_cells):
            rows.append(raw_cells)
        idx += 1
    return rows, idx


def render_table(pdf: GuidePDF, rows: list[list[str]]) -> None:
    if not rows:
        return
    cols = max(len(row) for row in rows)
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    widths = [usable / cols] * cols
    pdf.set_font("Helvetica", "", 8)
    for row_index, row in enumerate(rows):
        row = row + [""] * (cols - len(row))
        x = pdf.get_x()
        y = pdf.get_y()
        heights: list[float] = []
        for width, cell_text in zip(widths, row):
            text = sanitize(cell_text)
            lines = max(1, len(pdf.multi_cell(width, 4.5, text, dry_run=True, output="LINES")))
            heights.append(lines * 4.5)
        row_h = max(7.0, max(heights))
        if y + row_h > pdf.page_break_trigger:
            pdf.add_page()
            x = pdf.get_x()
            y = pdf.get_y()
        pdf.set_font("Helvetica", "B" if row_index == 0 else "", 8)
        for width, cell_text in zip(widths, row):
            pdf.set_xy(x, y)
            pdf.multi_cell(width, 4.5, sanitize(cell_text), border=1)
            x += width
        pdf.set_xy(pdf.l_margin, y + row_h)
    pdf.ln(2)


def render_paragraph(pdf: GuidePDF, text: str, bullet: bool = False) -> None:
    text = strip_markdown(text)
    if not text:
        return
    pdf.set_font("Helvetica", "", 10)
    prefix = "- " if bullet else ""
    pdf.multi_cell(0, 5.5, prefix + text)
    pdf.ln(1)


def render_body(pdf: GuidePDF, guide: Guide) -> None:
    lines = guide.body.splitlines()
    idx = 0
    pending_para: list[str] = []

    def flush_para() -> None:
        if pending_para:
            render_paragraph(pdf, " ".join(pending_para))
            pending_para.clear()

    while idx < len(lines):
        line = lines[idx].rstrip()
        stripped = line.strip()
        if not stripped:
            flush_para()
            idx += 1
            continue
        if stripped.startswith("# "):
            flush_para()
            idx += 1
            continue
        if stripped.startswith("## "):
            flush_para()
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 7, strip_markdown(stripped[3:]))
            pdf.ln(1)
            idx += 1
            continue
        if is_table_start(lines, idx):
            flush_para()
            rows, idx = collect_table(lines, idx)
            render_table(pdf, rows)
            continue
        if stripped.startswith("- "):
            flush_para()
            render_paragraph(pdf, stripped[2:], bullet=True)
            idx += 1
            continue
        pending_para.append(stripped)
        idx += 1
    flush_para()


def build_pdf(guide: Guide) -> Path:
    guide_id = str(guide.meta["id"])
    title = str(guide.meta["title"])
    reviewed = datetime.strptime(str(guide.meta["last_reviewed"]), "%Y-%m-%d")
    out_path = PDF_DIR / f"{guide_id}.pdf"

    pdf = GuidePDF(guide_id)
    pdf.set_title(sanitize(title))
    pdf.set_author("LiveWell workshop")
    pdf.set_subject("LiveWell Coach workshop sample guidance")
    pdf.set_creator("LiveWell workshop")
    pdf.set_creation_date(reviewed)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 9, sanitize(title))
    pdf.ln(2)
    render_body(pdf, guide)

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(out_path)
    print(f"wrote pdf/{out_path.name} ({pdf.page_no()} pages)")
    return out_path


def check_outputs(paths: list[Path]) -> int:
    missing_or_stale: list[str] = []
    for md_path in paths:
        guide = parse_guide(md_path)
        pdf_path = PDF_DIR / f"{guide.meta['id']}.pdf"
        if not pdf_path.exists() or pdf_path.stat().st_mtime < md_path.stat().st_mtime:
            missing_or_stale.append(pdf_path.name)
    if missing_or_stale:
        for name in missing_or_stale:
            print(f"stale {name}")
        return 1
    print("all pdfs up to date")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build LiveWell guide PDFs.")
    parser.add_argument("--check", action="store_true", help="Fail if any guide PDF is missing or stale.")
    args = parser.parse_args(argv)

    md_paths = sorted(GUIDES_DIR.glob("lg-*.md"))
    if args.check:
        return check_outputs(md_paths)

    for md_path in md_paths:
        build_pdf(parse_guide(md_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
