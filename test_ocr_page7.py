"""
Tests OCR on page 7 of the UT Southwestern PDF.
Prints: (1) what PyMuPDF gets normally, (2) what Tesseract reads via OCR.
No LLM calls.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import fitz
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

PDF_PATH = r"C:\Users\arinj\OneDrive\Desktop\audit docs\utswmc-fy-2024-annual-internal-audit-report-accessible.pdf"
PAGE_NUM = 7  # 1-indexed

pdf = fitz.open(PDF_PATH)
page = pdf[PAGE_NUM - 1]  # PyMuPDF is 0-indexed

normal_text = page.get_text("text").strip()

print(f"=== Page {PAGE_NUM}: Normal text extraction ===")
if normal_text:
    print(f"({len(normal_text.split())} words found via normal extraction)\n")
    print(normal_text)
else:
    print("Empty — page has no text layer (scanned image)")

print()
print(f"=== Page {PAGE_NUM}: OCR via Tesseract ===")
pix = page.get_pixmap(dpi=300)
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
ocr_text = pytesseract.image_to_string(img).strip()

if ocr_text:
    print(f"({len(ocr_text.split())} words found via OCR)\n")
    print(ocr_text)
else:
    print("OCR also returned nothing.")

pdf.close()
