"""Render the evaluation knowledge base from Markdown to PDF.

The Markdown files in rag/evaluation/data/kb_source/ are the source of truth
(diffable, reviewable); the PDFs in data/testset_files/ are what gets uploaded
through the real ingestion pipeline. Run from the repo root:

    uv run python rag/evaluation/scripts/build_kb.py
"""
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCE_DIR = DATA_DIR / "kb_source"
OUTPUT_DIR = DATA_DIR / "testset_files"


def render(markdown_text: str) -> FPDF:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(20, 18, 20)
    pdf.add_page()

    for line in markdown_text.splitlines():
        line = line.rstrip()
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 8, line[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        elif line.startswith("## "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, line[3:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif line.startswith("- "):
            pdf.set_font("Helvetica", "", 10.5)
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(0, 5.5, "- " + line[2:], new_x="LMARGIN", new_y="NEXT")
        elif line:
            pdf.set_font("Helvetica", "", 10.5)
            pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.ln(2.5)
    return pdf


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = sorted(SOURCE_DIR.glob("*.md"))
    expected = {f"{source.stem}.pdf" for source in sources}

    # Drop PDFs whose source was removed, so the corpus always matches kb_source/.
    for stale in OUTPUT_DIR.glob("*.pdf"):
        if stale.name not in expected:
            stale.unlink()
            print(f"removed {stale.name}")

    for source in sources:
        pdf = render(source.read_text(encoding="utf-8"))
        # Fixed creation date so rebuilding unchanged sources gives identical files.
        pdf.set_creation_date(datetime(2026, 1, 1))
        pdf.output(str(OUTPUT_DIR / f"{source.stem}.pdf"))
        print(f"built {source.stem}.pdf")


if __name__ == "__main__":
    main()
