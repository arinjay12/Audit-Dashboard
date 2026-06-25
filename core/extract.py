"""
Document extraction: ZIP -> list[ParsedDoc]. No LLM calls here.

Entry point: extract_zip(zip_path) -> list[ParsedDoc]

Supported formats: PDF, DOCX, XLSX, CSV, TXT.
Unsupported files are skipped with a warning (no crash).
"""

import io
import os
import tempfile
import zipfile

import fitz                         # PyMuPDF — PDF parsing
import pandas as pd
import pytesseract
from PIL import Image
from docx import Document           # python-docx — DOCX parsing

# Point pytesseract at the Tesseract executable (Windows default install path)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from core.schema import ParsedDoc

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt"}


# ── ZIP handler ───────────────────────────────────────────────────────────────

def extract_zip(zip_path: str) -> list[ParsedDoc]:
    """
    Open a ZIP file, parse every supported file inside it, and return
    a list of ParsedDoc objects — one per supported file found.
    """
    results = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        entries = [
            name for name in zf.namelist()  
            if not name.endswith("/")
            and not os.path.basename(name).startswith(".")
        ]

        for entry in entries:
            ext = os.path.splitext(entry)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                print(f"  [skip] {entry} — unsupported format")
                continue

            file_bytes = zf.read(entry)
            filename = os.path.basename(entry)

            print(f"  [parse] {filename} ({ext})")
            try:
                doc = _parse_file(filename, ext, file_bytes)
                results.append(doc)
            except Exception as e:
                print(f"  [error] {filename}: {e}")
                results.append(ParsedDoc(
                    filename=filename,
                    doc_type=ext.lstrip("."),
                    raw_text="",
                    tables=[],
                    warnings=[f"Parsing failed: {e}"],
                ))

    return results


def list_zip_contents(zip_path: str) -> list[dict]:
    """
    Return a summary of files inside a ZIP without parsing them.
    Used by Page 1 to show the user what's in their upload before processing.
    """
    contents = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            ext = os.path.splitext(info.filename)[1].lower()
            contents.append({
                "name": os.path.basename(info.filename),
                "extension": ext,
                "size_kb": round(info.file_size / 1024, 1),
                "supported": ext in SUPPORTED_EXTENSIONS,
            })
    return contents


# ── format dispatcher ─────────────────────────────────────────────────────────

def _parse_file(filename: str, ext: str, file_bytes: bytes) -> ParsedDoc:
    if ext == ".pdf":
        return _parse_pdf(filename, file_bytes)
    elif ext == ".docx":
        return _parse_docx(filename, file_bytes)
    elif ext == ".xlsx":
        return _parse_xlsx(filename, file_bytes)
    elif ext == ".csv":
        return _parse_csv(filename, file_bytes)
    elif ext == ".txt":
        return _parse_txt(filename, file_bytes)
    else:
        raise ValueError(f"No parser for extension: {ext}")


# ── per-format parsers ────────────────────────────────────────────────────────

def _parse_pdf(filename: str, file_bytes: bytes) -> ParsedDoc:
    warnings = []
    text_parts = []
    tables = []

    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    page_count = len(pdf)

    for page_num, page in enumerate(pdf, start=1):
        page_text = page.get_text("text").strip()

        if not page_text:
            # Page is a scanned image — run OCR via Tesseract
            try:
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_text = pytesseract.image_to_string(img).strip()
                if page_text:
                    warnings.append(f"Page {page_num} was a scanned image — OCR applied.")
                else:
                    warnings.append(f"Page {page_num}: OCR returned no text.")
                    continue
            except Exception as e:
                warnings.append(f"Page {page_num}: OCR failed — {e}")
                continue

        lines = [ln for ln in page_text.splitlines() if ln.strip()]
        text_parts.append("\n".join(lines))

        for table in page.find_tables():
            df = table.to_pandas()
            if not df.empty:
                tables.append(_df_to_dict(df, source=f"{filename} p{page_num}"))

                # Render the table as clearly labelled text so Gemini understands
                # its structure — columns, and each row with its values explicitly stated.
                df = df.astype(str)
                col_names = " | ".join(df.columns.tolist())
                table_lines = [
                    f"[TABLE from {filename} page {page_num}]",
                    f"Columns: {col_names}",
                ]
                for row_idx, row in df.iterrows():
                    row_text = " | ".join(f"{col}: {val}" for col, val in row.items())
                    table_lines.append(f"Row {row_idx + 1}: {row_text}")
                table_lines.append("[END TABLE]")
                text_parts.append("\n".join(table_lines))

    pdf.close()

    return ParsedDoc(
        filename=filename,
        doc_type="pdf",
        raw_text="\n\n".join(text_parts),
        tables=tables,
        page_count=page_count,
        warnings=warnings,
    )


def _parse_docx(filename: str, file_bytes: bytes) -> ParsedDoc:
    doc = Document(io.BytesIO(file_bytes))
    text_parts = []
    tables = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            text_parts.append(text)

    for i, table in enumerate(doc.tables, start=1):
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        if rows:
            headers = rows[0]
            data_rows = rows[1:]
            tables.append({
                "source": f"{filename} table {i}",
                "headers": headers,
                "rows": data_rows,
            })
            table_lines = [" | ".join(headers)]
            table_lines += [" | ".join(r) for r in data_rows]
            text_parts.append("\n".join(table_lines))

    return ParsedDoc(
        filename=filename,
        doc_type="docx",
        raw_text="\n\n".join(text_parts),
        tables=tables,
    )


def _parse_xlsx(filename: str, file_bytes: bytes) -> ParsedDoc:
    text_parts = []
    tables = []

    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    for sheet_name in xl.sheet_names:
        df = xl.parse(sheet_name).fillna("")

        if df.empty:
            continue

        tables.append(_df_to_dict(df, source=f"{filename} [{sheet_name}]"))
        text_parts.append(f"=== Sheet: {sheet_name} ===")
        text_parts.append(df.to_string(index=False))

    return ParsedDoc(
        filename=filename,
        doc_type="xlsx",
        raw_text="\n\n".join(text_parts),
        tables=tables,
    )


def _parse_csv(filename: str, file_bytes: bytes) -> ParsedDoc:
    df = pd.read_csv(io.BytesIO(file_bytes)).fillna("")
    return ParsedDoc(
        filename=filename,
        doc_type="csv",
        raw_text=df.to_string(index=False),
        tables=[_df_to_dict(df, source=filename)],
    )


def _parse_txt(filename: str, file_bytes: bytes) -> ParsedDoc:
    raw_text = file_bytes.decode("utf-8", errors="replace").strip()
    return ParsedDoc(
        filename=filename,
        doc_type="txt",
        raw_text=raw_text,
        tables=[],
    )


# ── helpers ───────────────────────────────────────────────────────────────────

def _df_to_dict(df: pd.DataFrame, source: str) -> dict:
    df = df.astype(str)
    return {
        "source": source,
        "headers": df.columns.tolist(),
        "rows": df.values.tolist(),
    }
