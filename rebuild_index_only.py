"""
Rebuilds ONLY the RAG index + chunks from the source documents, reusing the
existing cached analysis. Use this when a change affects chunking/retrieval but
NOT the analysis — it avoids spending a Gemini request on a fresh analyze() call.

Usage: python rebuild_index_only.py
"""
import os
import sys
import pickle
import zipfile
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

import faiss
from core.extract import extract_zip
from core.rag import build_index

PDF_PATH = r"C:\Users\arinj\OneDrive\Desktop\audit docs\utswmc-fy-2024-annual-internal-audit-report-accessible.pdf"

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
CACHE_INDEX = os.path.join(CACHE_DIR, "rag.index")
CACHE_CHUNKS = os.path.join(CACHE_DIR, "chunks.pkl")

tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
with zipfile.ZipFile(tmp.name, "w") as zf:
    zf.write(PDF_PATH, arcname=os.path.basename(PDF_PATH))
tmp.close()

print("Re-extracting documents (local, no Gemini call)...")
docs = extract_zip(tmp.name)

print("Rebuilding RAG index with fixed page tracking...")
index, chunks = build_index(docs)

faiss.write_index(index, CACHE_INDEX)
pickle.dump(chunks, open(CACHE_CHUNKS, "wb"))

# Report the page ranges so we can confirm tracking is fixed
from collections import Counter
ranges = Counter(c["pages"] for c in chunks)
print(f"Done. {len(chunks)} chunks. Distinct page ranges: {len(ranges)}")
print("Sample ranges:", sorted(ranges.keys())[:12])
os.unlink(tmp.name)
