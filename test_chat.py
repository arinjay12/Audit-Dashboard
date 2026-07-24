"""
Terminal chat test — runs the full pipeline then opens an interactive chat.
On first run, extracts + analyzes + builds RAG index, then caches to disk.
On subsequent runs, loads from cache (skips extraction and Gemini call).

Usage:
  python test_chat.py           # uses cache if available
  python test_chat.py --rebuild # forces full re-run and overwrites cache
"""
import os
import sys
import pickle
import zipfile
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
with open(secrets_path) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import faiss
from core.extract import extract_zip
from core.analyze import analyze
from core.chat import chat
from core.rag import build_index
from core.schema import AuditAnalysis

PDF_PATH = r"C:\Users\arinj\OneDrive\Desktop\audit docs\utswmc-fy-2024-annual-internal-audit-report-accessible.pdf"

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
CACHE_ANALYSIS = os.path.join(CACHE_DIR, "analysis.json")
CACHE_INDEX    = os.path.join(CACHE_DIR, "rag.index")
CACHE_CHUNKS   = os.path.join(CACHE_DIR, "chunks.pkl")

force_rebuild = "--rebuild" in sys.argv

os.makedirs(CACHE_DIR, exist_ok=True)

cache_exists = all(os.path.exists(p) for p in [CACHE_ANALYSIS, CACHE_INDEX, CACHE_CHUNKS])

if cache_exists and not force_rebuild:
    print("Loading from cache...")
    analysis = AuditAnalysis.model_validate_json(open(CACHE_ANALYSIS).read())
    index = faiss.read_index(CACHE_INDEX)
    chunks = pickle.load(open(CACHE_CHUNKS, "rb"))
    print(f"Loaded. {len(analysis.findings)} findings, {len(analysis.risks)} risks, {len(analysis.vendors)} vendors.")
else:
    print("Running pipeline (this will take ~30s and call Gemini)...")
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with zipfile.ZipFile(tmp.name, "w") as zf:
        zf.write(PDF_PATH, arcname=os.path.basename(PDF_PATH))
    tmp.close()

    docs = extract_zip(tmp.name)
    print(f"Extracted {len(docs)} documents. Building RAG index...")
    index, chunks = build_index(docs)
    print(f"Index built: {len(chunks)} chunks. Analyzing with Gemini...")
    analysis = analyze(docs)
    print(f"Done. {len(analysis.findings)} findings, {len(analysis.risks)} risks, {len(analysis.vendors)} vendors.")

    open(CACHE_ANALYSIS, "w").write(analysis.model_dump_json())
    faiss.write_index(index, CACHE_INDEX)
    pickle.dump(chunks, open(CACHE_CHUNKS, "wb"))
    print("Cached to .cache/ — next run will skip extraction and Gemini call.")

print()
print("=" * 55)
print("Audit Chat — type your question, or 'quit' to exit")
print("=" * 55)

history = []
while True:
    try:
        user_input = input("\nYou: ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not user_input:
        continue
    if user_input.lower() in ("quit", "exit", "q"):
        break
    response = chat(user_input, analysis, history, index=index, chunks=chunks)
    print(f"\nAuditor: {response}")
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response})
