"""Data-completeness reporting for raw report records.

The ingestion layer (:mod:`reporting_core.ingestion`) is deliberately forgiving:
a blank quantity becomes ``0.0``, a missing site becomes ``""`` and unparseable
cells degrade rather than raise.  That resilience keeps a single junk cell from
aborting a multi-thousand-row ingest, but it also *erases the evidence* that a
column was sparse in the first place.  By the time a raw export has been coerced
into :class:`~reporting_core.models.ReportRow` records you can no longer tell a
genuine zero from a blank that was silently defaulted.

This module measures completeness *before* that coercion happens.  Point it at
the raw records - a list of ``{column: value}`` mappings, exactly what a CSV or
worksheet yields row-by-row - and it reports, per column, how many values are
present versus missing and the resulting fill rate, plus a whole-grid rollup.

A value counts as *missing* when it is ``None``, an empty/whitespace-only
string, or - for the tolerant readers real vendor files demand - one of a
configurable set of placeholder tokens such as ``"n/a"`` or ``"null"``.  A key
that is entirely absent from a record is missing too.  Everything is
deterministic and validated up front, so the same records always yield the same
report - safe to diff in tests and in the dashboard handoff.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

# Placeholder strings (compared case-insensitively after stripping) that vendor
# exports use to mean "no value here".  Callers can override or disable this via
# the ``missing_tokens`` argument when a literal "na" is meaningful data.
DEFAULT_MISSING_TOKENS: frozenset[str] = frozenset(
    {"n/a", "na", "null", "none", "nil", "-", "--"}
)


@dataclass(frozen=True)
class ColumnCompleteness:
    """Fill statistics for a single column across all analyzed records."""

    column: str
    total: int
    filled: int
    missing: int
    fill_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompletenessReport:
    """A per-column and whole-grid completeness summary.

    ``columns`` is ordered exactly as the columns were requested (or, when
    discovered automatically, in first-seen order across the records), so the
    report is stable and diff-friendly.
    """

    row_count: int
    columns: tuple[ColumnCompleteness, ...]
    total_cells: int
    filled_cells: int
    missing_cells: int
    fill_rate: float

    @property
    def is_complete(self) -> bool:
        """``True`` when no analyzed cell is missing."""
        return self.missing_cells == 0

    def column(self, name: str) -> ColumnCompleteness:
        """Return the :class:`ColumnCompleteness` for ``name``.

        Raises :class:`KeyError` if the column was not part of the analysis.
        """
        for item in self.columns:
            if item.column == name:
                return item
        raise KeyError(name)

    def incomplete_columns(self, threshold: float = 1.0) -> tuple[ColumnCompleteness, ...]:
        """Columns whose fill rate is *below* ``threshold``.

        The default ``1.0`` returns every column that is missing even a single
        value.  Results are ordered worst-first (lowest fill rate), ties broken
        by column name, so the neediest columns surface at the top of a report.

        ``threshold`` must be a number in the closed interval ``[0, 1]``.
        """
        limit = _ratio(threshold, "threshold")
        below = [item for item in self.columns if item.fill_rate < limit]
        below.sort(key=lambda item: (item.fill_rate, item.column))
        return tuple(below)

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "columns": [item.to_dict() for item in self.columns],
            "total_cells": self.total_cells,
            "filled_cells": self.filled_cells,
            "missing_cells": self.missing_cells,
            "fill_rate": self.fill_rate,
        }


def _ratio(value: Any, field: str) -> float:
    """Validate and return a fraction in ``[0, 1]``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be a number")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{field} must be between 0 and 1")
    return number


def is_missing(value: Any, *, missing_tokens: Iterable[str] = DEFAULT_MISSING_TOKENS) -> bool:
    """Return whether ``value`` should count as missing.

    A value is missing when it is ``None``, an empty or whitespace-only string,
    or a string that matches one of ``missing_tokens`` (compared lower-cased and
    stripped).  Numbers - including ``0`` and ``0.0`` - are always present:
    a genuine zero is data, not a gap.  Pass an empty ``missing_tokens`` to treat
    only ``None`` and blank strings as missing.
    """
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return True
        tokens = {token.strip().lower() for token in missing_tokens}
        return stripped.lower() in tokens
    return False


def _resolve_columns(
    records: Sequence[Mapping[str, Any]],
    columns: Sequence[str] | None,
) -> tuple[str, ...]:
    """Determine the column set: explicit if given, else first-seen union."""
    if columns is not None:
        resolved = tuple(columns)
        if not resolved:
            raise ValueError("columns must be non-empty when provided")
        for name in resolved:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("column names must be non-empty strings")
        if len(set(resolved)) != len(resolved):
            raise ValueError("columns must not contain duplicates")
        return resolved

    seen: dict[str, None] = {}
    for record in records:
        for key in record:
            if not isinstance(key, str):
                raise TypeError("record keys must be strings")
            seen.setdefault(key, None)
    return tuple(seen)


def analyze_records(
    records: Iterable[Mapping[str, Any]],
    columns: Sequence[str] | None = None,
    *,
    missing_tokens: Iterable[str] = DEFAULT_MISSING_TOKENS,
) -> CompletenessReport:
    """Build a :class:`CompletenessReport` for ``records``.

    Parameters
    ----------
    records:
        The raw rows to profile, each a mapping of column name to cell value -
        exactly the shape a CSV ``DictReader`` or a worksheet yields.  Consumed
        once, so a generator is fine.
    columns:
        The columns to score, in report order.  When omitted, every key seen
        across the records is scored in first-seen order.  Naming the columns
        explicitly is what lets a column that is *entirely* absent from the data
        (every value missing) still appear in the report - otherwise it could
        never be discovered.
    missing_tokens:
        Placeholder strings that count as missing (see :func:`is_missing`).
        Defaults to :data:`DEFAULT_MISSING_TOKENS`.

    Returns
    -------
    A :class:`CompletenessReport`.  A column's ``fill_rate`` is ``filled /
    total``; with zero records every rate is ``1.0`` (vacuously complete),
    mirroring :func:`reporting_core.quality_metrics.completeness_rate`.
    """
    tokens = frozenset(token.strip().lower() for token in missing_tokens)

    materialized: list[Mapping[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise TypeError("each record must be a mapping")
        materialized.append(record)

    resolved = _resolve_columns(materialized, columns)
    row_count = len(materialized)

    column_stats: list[ColumnCompleteness] = []
    filled_cells = 0
    for name in resolved:
        filled = 0
        for record in materialized:
            if name in record and not is_missing(record[name], missing_tokens=tokens):
                filled += 1
        missing = row_count - filled
        filled_cells += filled
        column_stats.append(
            ColumnCompleteness(
                column=name,
                total=row_count,
                filled=filled,
                missing=missing,
                fill_rate=filled / row_count if row_count else 1.0,
            )
        )

    total_cells = row_count * len(resolved)
    missing_cells = total_cells - filled_cells
    return CompletenessReport(
        row_count=row_count,
        columns=tuple(column_stats),
        total_cells=total_cells,
        filled_cells=filled_cells,
        missing_cells=missing_cells,
        fill_rate=filled_cells / total_cells if total_cells else 1.0,
    )
