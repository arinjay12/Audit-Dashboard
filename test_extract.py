"""
Quick test for the parsing pipeline.
Usage:
    python test_extract.py path/to/any/file.pdf
    python test_extract.py path/to/any/file.docx
    python test_extract.py path/to/file.zip
"""

import sys
import os
import zipfile
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from core.extract import extract_zip


def wrap_in_zip(file_path):
    """If a single file is passed, wrap it in a temp ZIP so extract_zip can read it."""
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with zipfile.ZipFile(tmp.name, "w") as zf:
        zf.write(file_path, arcname=os.path.basename(file_path))
    return tmp.name


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_extract.py <path_to_any_file>")
        sys.exit(1)

    input_path = sys.argv[1]

    if not input_path.endswith(".zip"):
        zip_path = wrap_in_zip(input_path)
        cleanup = True
    else:
        zip_path = input_path
        cleanup = False

    docs = extract_zip(zip_path)

    for doc in docs:
        print(f"\nFile    : {doc.filename}")
        print(f"Type    : {doc.doc_type}")
        print(f"Words   : {doc.word_count}")
        print(f"Tables  : {len(doc.tables)}")
        print(f"Preview : {doc.raw_text[:300]!r}")
        if doc.warnings:
            print(f"Warnings: {doc.warnings}")

    if cleanup:
        os.unlink(zip_path)
