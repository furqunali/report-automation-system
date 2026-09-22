"""Validated business-reporting primitives."""

from .ingestion import (
    HeaderRules,
    IngestionError,
    MissingDependencyError,
    UnsupportedFormatError,
    read_csv,
    read_file,
    read_xlsx,
)
from .models import ReportRow, ReportSummary
from .validation import validate_row, validate_summary

__all__ = [
    "HeaderRules",
    "IngestionError",
    "MissingDependencyError",
    "ReportRow",
    "ReportSummary",
    "UnsupportedFormatError",
    "read_csv",
    "read_file",
    "read_xlsx",
    "validate_row",
    "validate_summary",
]
