"""
Terminal chat test with MULTIPLE documents — PDF + 2 Excel files zipped together.
Demonstrates that extract/analyze/RAG all handle a mixed-format doc set: each
finding/vendor/discrepancy is tagged with its correct source_doc, and RAG chunks
are tagged per-file so retrieval (and page lookup, for the PDF) still works.

Uses its own cache dir (.cache_multi/) so it doesn't touch the single-PDF demo cache.

Usage:
  python test_chat_multi.py           # uses cache if available
  python test_chat_multi.py --rebuild # forces full re-run and overwrites cache
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

AUDIT_DIR = r"C:\Users\arinj\OneDrive\Desktop\audit docs"
FILES = [
    "utswmc-fy-2024-annual-internal-audit-report-accessible.pdf",
    "vendor_risk_assessment.xlsx",
    "internal_audit_findings.xlsx",
]

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache_multi")
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
    print(f"Running pipeline on {len(FILES)} documents (this will take ~30s and call Gemini)...")
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with zipfile.ZipFile(tmp.name, "w") as zf:
        for f in FILES:
            zf.write(os.path.join(AUDIT_DIR, f), arcname=f)
    tmp.close()

    docs = extract_zip(tmp.name)
    for d in docs:
        print(f"  {d.filename}: {d.word_count} words, {len(d.tables)} tables")

    print("Building RAG index...")
    index, chunks = build_index(docs)
    print(f"Index built: {len(chunks)} chunks across {len(docs)} documents.")

    print("Analyzing with Gemini...")
    analysis = analyze(docs)
    print(f"Done. {len(analysis.findings)} findings, {len(analysis.risks)} risks, {len(analysis.vendors)} vendors.")

    open(CACHE_ANALYSIS, "w").write(analysis.model_dump_json())
    faiss.write_index(index, CACHE_INDEX)
    pickle.dump(chunks, open(CACHE_CHUNKS, "wb"))
    print("Cached to .cache_multi/ — next run will skip extraction and Gemini call.")
    os.unlink(tmp.name)

print()
print("Source docs in this session:")
for d in dict.fromkeys(c["source"] for c in chunks):
    print(f"  - {d}")

print()
print("=" * 55)
print("Multi-Doc Audit Chat — type your question, or 'quit' to exit")
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
