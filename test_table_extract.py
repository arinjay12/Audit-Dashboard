"""
Demonstrates how a PDF table is extracted and re-labelled for Gemini.

For a chosen page it prints, side by side:
  (1) the raw table as pandas first reads it, and
  (2) the clearly-labelled [TABLE]...[END TABLE] text that we actually feed to
      Gemini — explicit column names and each row's values stated in full.

This is the same rendering logic used in core/extract.py (_parse_pdf).
No LLM calls, no full pipeline — just the table step.

Usage:
    python test_table_extract.py            # defaults to page 6 (a clean Service/Provider table)
    python test_table_extract.py 6          # show tables on a specific page
"""
import sys

import fitz   # PyMuPDF

PDF_PATH = r"C:\Users\arinj\OneDrive\Desktop\audit docs\utswmc-fy-2024-annual-internal-audit-report-accessible.pdf"
DEFAULT_PAGE = 6   # this page holds a clean two-column "Service | Provider" table


def render_for_gemini(df, filename, page_num):
    """The exact labelling logic from extract.py — turns a table into tagged text."""
    # Empty cells -> "" (so they don't show up as the noise token "nan")
    df = df.fillna("").astype(str)

    col_names = " | ".join(df.columns.tolist())
    lines = [
        f"[TABLE from {filename} page {page_num}]",
        f"Columns: {col_names}",
    ]
    for row_idx, row in df.iterrows():
        row_text = " | ".join(f"{col}: {val}" for col, val in row.items())
        lines.append(f"Row {row_idx + 1}: {row_text}")
    lines.append("[END TABLE]")
    return "\n".join(lines)


if __name__ == "__main__":
    page_num = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PAGE

    pdf = fitz.open(PDF_PATH)
    page = pdf[page_num - 1]   # PyMuPDF is 0-indexed
    filename = PDF_PATH.split("\\")[-1]

    tables = page.find_tables()
    if not tables.tables:
        print(f"No tables detected on page {page_num}. Try another page.")
        pdf.close()
        sys.exit(0)

    for t_index, table in enumerate(tables, start=1):
        df = table.to_pandas()
        if df.empty:
            continue

        print("=" * 72)
        print(f"PAGE {page_num} — TABLE {t_index}: raw, as pandas first reads it "
              f"({df.shape[0]} rows x {df.shape[1]} cols)")
        print("=" * 72)
        print(df.to_string())
        print()

        print("-" * 72)
        print("WHAT GEMINI ACTUALLY RECEIVES (labelled form):")
        print("-" * 72)
        print(render_for_gemini(df, filename, page_num))
        print()

    pdf.close()
