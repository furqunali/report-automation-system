"""Serialize a validated ``ReportRow`` master to RFC-4180 CSV text.

:mod:`reporting_core.kpi` and :mod:`reporting_core.markdown_report` roll the
consolidated master up into figures a human reads.  Downstream systems - an
accounting import, a PDI load, a spreadsheet a manager opens in Excel - instead
want the *rows themselves*, and they want them in a shape they can parse without
guessing.  This module produces exactly that: a comma-separated document with a
fixed, published column order and correct RFC-4180 quoting.

Two properties are treated as correctness requirements rather than conveniences:

* **A stable column contract.**  The columns, their order, and their header
  names are fixed in :data:`CSV_COLUMNS` and never depend on the data.  Two
  exports of two different months always have the same header line and the same
  number of columns per row, so a consumer can bind to column positions once and
  trust them.
* **RFC-4180 escaping.**  Site and product names are free text and routinely
  contain a comma, a double quote, or an embedded newline - any of which
  silently corrupts a naively joined CSV.  Every field is quoted and escaped per
  RFC 4180 (https://www.rfc-editor.org/rfc/rfc4180): a field containing the
  delimiter, a double quote, CR, or LF is wrapped in double quotes and each
  interior double quote is doubled.  Records are terminated with CRLF, the line
  ending the RFC specifies.

Everything is deterministic: the same master always renders byte-for-byte
identical CSV (stable column order, fixed 2-decimal numeric formatting), so the
output is safe to diff in tests and in review.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .models import ReportRow
from .validation import validate_row

#: The published column contract.  Order and names are stable across releases;
#: consumers may bind to these positions.  Each entry maps 1:1 to a
#: :class:`~reporting_core.models.ReportRow` field.
CSV_COLUMNS: tuple[str, ...] = (
    "site",
    "category",
    "product",
    "quantity",
    "sales",
    "status",
)

# RFC-4180 line terminator for records.
_CRLF = "\r\n"

# The characters whose presence forces a field to be quoted.
_MUST_QUOTE = (",", '"', "\r", "\n")


def _fmt_num(value: float) -> str:
    """Format a numeric field as a fixed 2-decimal, separator-free string.

    Thousands separators are deliberately omitted: a comma inside a number would
    force quoting and, worse, make the value ambiguous to a downstream parser.
    ``-0.0`` is normalized to ``0.00`` so a rounded-to-zero figure never carries
    a misleading minus sign.
    """
    number = float(value)
    if number == 0:
        number = 0.0
    return f"{number:.2f}"


def _escape_field(value: object) -> str:
    r"""Return ``value`` as an RFC-4180-safe CSV field.

    The value is stringified first.  If it contains the delimiter (``,``), a
    double quote, or a CR/LF, it is wrapped in double quotes and every interior
    double quote is doubled (``"`` -> ``""``).  Fields without any special
    character are emitted verbatim, so a plain value stays unquoted and readable.

    Embedded newlines are *preserved* (a quoted field may legally span lines in
    RFC 4180) rather than flattened - a CSV consumer reassembles them correctly,
    unlike a Markdown table cell.
    """
    text = str(value)
    if any(ch in text for ch in _MUST_QUOTE):
        return '"' + text.replace('"', '""') + '"'
    return text


def _row_cells(row: ReportRow) -> tuple[str, ...]:
    """Project one validated ``ReportRow`` onto the ordered column contract."""
    return (
        _escape_field(row.site),
        _escape_field(row.category),
        _escape_field(row.product),
        _escape_field(_fmt_num(row.quantity)),
        _escape_field(_fmt_num(row.sales)),
        _escape_field(row.status),
    )


def render_rows_csv(
    rows: Sequence[ReportRow],
    *,
    include_header: bool = True,
) -> str:
    """Render a ``ReportRow`` master as an RFC-4180 CSV document.

    Parameters
    ----------
    rows:
        The consolidated master - a sequence of
        :class:`~reporting_core.models.ReportRow`.  Every row is validated with
        :func:`reporting_core.validation.validate_row` first, so malformed input
        fails fast rather than producing a corrupt export.  May be empty, in
        which case only the header line is emitted (unless ``include_header`` is
        ``False``, giving an empty string).
    include_header:
        When ``True`` (the default) the first line is the fixed
        :data:`CSV_COLUMNS` header.  Set ``False`` to emit data rows only, e.g.
        when appending to an existing file.

    Returns
    -------
    str
        The CSV document.  Records are separated by CRLF and the document ends
        with a trailing CRLF (each record, including the last, is terminated),
        which is the widely interoperable RFC-4180 shape.  An empty document
        (no rows, no header) is returned as ``""`` with no terminator.

    Raises
    ------
    TypeError
        If any element of ``rows`` is not a ``ReportRow``.
    ValueError
        If any row fails :func:`~reporting_core.validation.validate_row`.
    """
    row_list = list(rows)
    if any(not isinstance(item, ReportRow) for item in row_list):
        raise TypeError("rows must contain ReportRow instances")

    records: list[str] = []
    if include_header:
        records.append(",".join(_escape_field(name) for name in CSV_COLUMNS))
    for row in row_list:
        validate_row(row)
        records.append(",".join(_row_cells(row)))

    if not records:
        return ""
    return _CRLF.join(records) + _CRLF


def write_rows_csv(
    rows: Sequence[ReportRow],
    *,
    path: str,
    include_header: bool = True,
    bom: bool = False,
) -> str:
    """Render the CSV and write it to ``path``, returning ``path``.

    Parent directories are created as needed.  The file is written UTF-8 with
    ``newline=""`` so the RFC-4180 CRLF terminators are preserved verbatim
    (no platform newline translation).

    Parameters
    ----------
    bom:
        When ``True`` a UTF-8 byte-order mark is prepended.  Excel needs the BOM
        to recognize a UTF-8 CSV; strict RFC-4180 consumers usually do not want
        it, so it defaults to ``False``.
    """
    document = render_rows_csv(rows, include_header=include_header)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoding = "utf-8-sig" if bom else "utf-8"
    # newline="" keeps our explicit CRLFs intact across platforms.
    target.write_text(document, encoding=encoding, newline="")
    return str(target)
