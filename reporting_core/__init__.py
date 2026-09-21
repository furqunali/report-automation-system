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
    "ReportRow",
    "ReportSummary",
    "validate_row",
    "validate_summary",
    "HeaderRules",
    "read_csv",
    "read_xlsx",
    "read_file",
    "IngestionError",
    "UnsupportedFormatError",
    "MissingDependencyError",
]
