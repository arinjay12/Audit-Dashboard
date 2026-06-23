"""
Data models for the audit pipeline.

ParsedDoc     : one parsed file from the ZIP (produced by extract.py)
Finding       : a single audit finding with severity and recommendation
Risk          : a risk item with likelihood + impact scores (feeds the heatmap)
Vendor        : a vendor and their risk rating
Discrepancy   : a financial flag with an amount
Compliance    : overall compliance score and pass/fail counts
KPIs          : pre-computed numbers that go straight onto the dashboard cards
AuditAnalysis : top-level object containing everything above (produced by analyze.py)
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
from pydantic import BaseModel


# ── ParsedDoc (dataclass) ─────────────────────────────────────────────────────
# Produced by extract.py — our own code fills this, so no validation needed.

@dataclass
class ParsedDoc:
    filename: str           # original filename inside the ZIP
    doc_type: str           # "pdf", "docx", "xlsx", "csv", "txt"
    raw_text: str           # all readable text extracted from the file
    tables: list            # list of dicts — each dict is one table {headers, rows}
    page_count: int = 0     # meaningful for PDFs; 0 for other types
    word_count: int = 0     # auto-computed from raw_text
    warnings: list = field(default_factory=list)  # non-fatal issues e.g. scanned pages

    def __post_init__(self):
        if not self.word_count and self.raw_text:
            self.word_count = len(self.raw_text.split())


# ── Pydantic models (Gemini output) ──────────────────────────────────────────
# Gemini fills these in. Pydantic validates every field before the dashboard
# uses any of it — wrong type or missing field raises an error immediately.

class Finding(BaseModel):
    title: str                                          # short name of the finding
    description: str                                    # what the issue is
    severity: Literal["High", "Medium", "Low"]          # only these three values allowed
    category: str                                       # e.g. Financial, Compliance, Operational
    source_doc: str                                     # which file this came from
    status: Literal["Open", "In Progress", "Closed"]   # current status
    recommendation: str                                 # what should be done to fix it


class Risk(BaseModel):
    title: str
    description: str
    likelihood: int     # 1 to 5 — how likely is this risk to occur
    impact: int         # 1 to 5 — how bad would it be if it did
    category: str


class Vendor(BaseModel):
    name: str
    risk_rating: Literal["High", "Medium", "Low"]
    flags: list[str]    # list of specific concerns e.g. ["no contract", "delayed payments"]


class Discrepancy(BaseModel):
    description: str
    amount: Optional[float]     # the financial amount involved, if mentioned
    source_doc: str


class Compliance(BaseModel):
    score_pct: float        # overall compliance score as a percentage e.g. 74.5
    framework: str          # e.g. "ISO 27001", "SOX", "Internal Policy"
    items_passed: int
    items_failed: int
    details: list[str]      # short notes on key pass/fail items


class KPIs(BaseModel):
    total_findings: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    pending_action_items: int           # findings with status Open or In Progress
    financial_discrepancy_flags: int    # number of discrepancies found
    overall_vendor_risk: Literal["High", "Medium", "Low"]   # worst vendor rating


class AuditAnalysis(BaseModel):
    overall_summary: str            # 2-3 sentence summary of the entire audit
    findings: list[Finding]
    risks: list[Risk]
    vendors: list[Vendor]
    discrepancies: list[Discrepancy]
    compliance: Compliance
    kpis: KPIs
    recommendations: list[str]      # top-level recommendations from Gemini
