"""
Quick pipeline test for the Excel + PDF combination.
Usage: python test_pipeline_excel.py
"""
import os
import sys
import zipfile
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

# Load .streamlit/secrets.toml into env vars
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
with open(secrets_path) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from core.extract import extract_zip
from core.analyze import analyze

AUDIT_DIR = r"C:\Users\arinj\OneDrive\Desktop\audit docs"
FILES = [
    "vendor_risk_assessment.xlsx",
    "internal_audit_findings.xlsx",
    "appc09.pdf",
]

tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
with zipfile.ZipFile(tmp.name, "w") as zf:
    for f in FILES:
        zf.write(os.path.join(AUDIT_DIR, f), arcname=f)

print("Extracting documents...")
docs = extract_zip(tmp.name)
for d in docs:
    print(f"  {d.filename}: {d.word_count} words, {len(d.tables)} tables")

print("\nAnalyzing with Gemini (this may take ~30s)...")
analysis = analyze(docs)

print("\n=== RESULT ===")
print(f"Summary: {analysis.overall_summary[:200]}")
print(f"Findings: {len(analysis.findings)}")
print(f"Risks: {len(analysis.risks)}")
print(f"Vendors: {len(analysis.vendors)}")
print(f"Discrepancies: {len(analysis.discrepancies)}")
print(f"Compliance: {analysis.compliance.score_pct}% ({analysis.compliance.framework})")
print(f"KPIs: High={analysis.kpis.high_risk_count} Med={analysis.kpis.medium_risk_count} Low={analysis.kpis.low_risk_count}")
print(f"Vendor risk: {analysis.kpis.overall_vendor_risk}")

print("\nTop findings:")
for f in analysis.findings[:4]:
    print(f"  [{f.severity}] {f.title} — {f.status} — {f.source_doc}")

print("\nTop recommendations:")
for r in analysis.recommendations[:3]:
    print(f"  - {r}")

print("\nAll validation passed.")
os.unlink(tmp.name)
