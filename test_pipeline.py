"""
End-to-end pipeline test: ZIP -> extract -> analyze -> AuditAnalysis

Usage:
    python test_pipeline.py path/to/audit.zip
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

# Load secrets manually so this runs outside Streamlit
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    with open(secrets_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from core.extract import extract_zip
from core.analyze import analyze


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pipeline.py <path_to_zip>")
        sys.exit(1)

    zip_path = sys.argv[1]

    print("Step 1: Extracting documents...")
    docs = extract_zip(zip_path)
    print(f"  Extracted {len(docs)} documents")
    for doc in docs:
        print(f"  - {doc.filename}: {doc.word_count} words, {len(doc.tables)} tables")

    print("\nStep 2: Sending to Gemini for analysis...")
    analysis = analyze(docs)

    print("\nStep 3: Results")
    print(f"  Summary    : {analysis.overall_summary[:200]}")
    print(f"  Findings   : {len(analysis.findings)}")
    print(f"  Risks      : {len(analysis.risks)}")
    print(f"  Vendors    : {len(analysis.vendors)}")
    print(f"  Compliance : {analysis.compliance.score_pct}%")
    print(f"  KPIs       : Total={analysis.kpis.total_findings}, High={analysis.kpis.high_risk_count}, Medium={analysis.kpis.medium_risk_count}, Low={analysis.kpis.low_risk_count}")

    print("\nFindings:")
    for f in analysis.findings:
        print(f"  [{f.severity}] {f.title} — {f.source_doc}")

    print("\nAll tests passed. Pipeline is working end to end.")
