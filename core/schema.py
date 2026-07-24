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
from pydantic import BaseModel, field_validator, model_validator


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

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v):
        # Same defence as status/risk_rating: Gemini occasionally echoes a source
        # document's own scale ("Critical", "Severe", lowercase variants). Map to
        # the closest allowed value instead of failing the whole analysis.
        if v in ("High", "Medium", "Low"):
            return v
        # Substring matching so compounds like "Medium-High" or "Critical risk"
        # still land sensibly (High outranks, checked first).
        s = str(v).strip().lower()
        if any(k in s for k in ("critical", "severe", "major", "significant", "high")):
            return "High"
        if any(k in s for k in ("medium", "moderate")):
            return "Medium"
        if any(k in s for k in ("low", "minor", "informational", "info", "trivial")):
            return "Low"
        # Log the coercion so a systematic problem (e.g. Gemini nulling the
        # field) is visible in the server console instead of silently flattening
        # every finding to Medium.
        print(f"[schema] unrecognised severity {v!r} — defaulting to Medium")
        return "Medium"

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        # Source documents sometimes use their own wording (e.g. "Partially
        # Implemented" from a raw findings log) instead of our three-value enum.
        # Map common variants to the closest allowed value rather than failing.
        if v in ("Open", "In Progress", "Closed"):
            return v
        s = str(v).lower()
        if "progress" in s or "partial" in s or "ongoing" in s:
            return "In Progress"
        if ("closed" in s or "resolved" in s or "complete" in s
                or "remediat" in s or "implemented" in s or "fixed" in s):
            return "Closed"
        return "Open"


class Risk(BaseModel):
    title: str
    description: str
    likelihood: int     # 1 to 5 — how likely is this risk to occur
    impact: int         # 1 to 5 — how bad would it be if it did
    category: str

    @field_validator("likelihood", "impact", mode="before")
    @classmethod
    def clamp_1_to_5(cls, v):
        # Keep scores on the 1-5 grid (the heatmap plots positions from these);
        # an out-of-range or non-numeric value becomes a sane middle default.
        try:
            return max(1, min(5, int(round(float(v)))))
        except (TypeError, ValueError):
            return 3


class Vendor(BaseModel):
    name: str
    risk_rating: Literal["High", "Medium", "Low"]
    flags: list[str]    # list of specific concerns e.g. ["no contract", "delayed payments"]

    @field_validator("risk_rating", mode="before")
    @classmethod
    def default_risk_rating(cls, v):
        return v if v in ("High", "Medium", "Low") else "Medium"


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

    @model_validator(mode="after")
    def reconcile_kpis(self):
        """
        The KPIs are defined as derived numbers (see the KPI DERIVATION section
        of the analysis prompt). The prompt asks Gemini to tie them out, but
        nothing guarantees it — so recompute them here from the actual lists.
        The dashboard can then never show a total that contradicts the findings
        it sits next to.
        """
        f = self.findings
        self.kpis.total_findings = len(f)
        self.kpis.high_risk_count = sum(1 for x in f if x.severity == "High")
        self.kpis.medium_risk_count = sum(1 for x in f if x.severity == "Medium")
        self.kpis.low_risk_count = sum(1 for x in f if x.severity == "Low")
        self.kpis.pending_action_items = sum(1 for x in f if x.status in ("Open", "In Progress"))
        self.kpis.financial_discrepancy_flags = len(self.discrepancies)
        if self.vendors:
            ratings = {v.risk_rating for v in self.vendors}
            self.kpis.overall_vendor_risk = ("High" if "High" in ratings
                                             else "Medium" if "Medium" in ratings else "Low")
        return self
