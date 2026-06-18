"""
Data models for the audit pipeline.

ParsedDoc  : output of the parsing stage (one per file in the ZIP)
AuditAnalysis and its sub-models are defined here too (week 2 — placeholders for now).
"""

from dataclasses import dataclass, field


@dataclass
class ParsedDoc:
    """
    Represents one parsed file from the uploaded ZIP.
    Produced by core.extract; consumed by core.analyze.
    """
    filename: str           # original filename inside the ZIP
    doc_type: str           # "pdf", "docx", "xlsx", "csv", "txt"
    raw_text: str           # all readable text extracted from the file
    tables: list            # list of dicts (each dict = one table as {headers, rows})
    page_count: int = 0     # meaningful for PDFs; 0 for other types
    word_count: int = 0     # computed from raw_text after extraction
    warnings: list = field(default_factory=list)  # non-fatal issues (e.g. scanned page)

    def __post_init__(self):
        if not self.word_count and self.raw_text:
            self.word_count = len(self.raw_text.split())


# AuditAnalysis models will be added here in week 2 once the
# parsing pipeline is validated against real documents.
