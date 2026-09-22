"""Render a management report as a shareable Markdown summary.

:mod:`reporting_core.kpi` produces the :class:`~reporting_core.kpi.ManagementKPIs`
roll-up a manager reads, and :mod:`reporting_core.anomalies` flags the rows that
break validation.  Both are structured objects meant for further processing;
neither is something you can paste into an email, a pull request, a wiki, or a
chat thread.

This module bridges that gap.  It turns a ``ManagementKPIs`` roll-up plus its
``Anomaly`` list into a single GitHub-Flavored-Markdown document: a headline KPI
block, an optional budget/variance line, a per-location table, a top-products
table, and an anomaly table (or an explicit "no anomalies" line when the batch
is clean).

Two properties are treated as correctness requirements rather than nice-to-haves:

* **Table safety.**  Site and product names are free text and routinely contain
  a ``|`` or a stray newline, either of which silently corrupts a Markdown
  table.  Every cell is escaped so the rendered table always has the shape the
  numbers imply.
* **Determinism.**  The same report always renders byte-for-byte identical
  Markdown (stable ordering inherited from ``ManagementKPIs``, fixed number
  formatting), so the output is safe to diff in tests and in review.
"""
from __future__ import annotations

from collections.abc import Sequence

from .anomalies import Anomaly
from .kpi import ManagementKPIs

# Two decimals with thousands separators - readable in prose and stable to diff.
_MONEY = "{:,.2f}"


def _fmt_number(value: float) -> str:
    """Format a numeric KPI as a fixed 2-decimal, thousands-separated string.

    ``-0.0`` is normalized to ``0.00`` so a rounded-to-zero figure never renders
    with a misleading minus sign.
    """
    number = float(value)
    if number == 0:
        number = 0.0
    return _MONEY.format(number)


def _fmt_pct(value: float | None) -> str:
    """Format a percentage, or ``n/a`` when it is undefined (``None``)."""
    if value is None:
        return "n/a"
    return f"{float(value):+.2f}%"


def _fmt_optional_money(value: float | None) -> str:
    """Format an optional money figure, rendering ``None`` as an em dash."""
    if value is None:
        return "—"
    return _fmt_number(value)


def _escape_cell(text: object) -> str:
    r"""Make ``text`` safe to drop into a single Markdown table cell.

    A literal ``|`` ends a cell, and any newline ends the whole row, so both
    would silently misalign the table.  Backslashes are escaped first (so the
    escaping we add is not itself re-interpreted), pipes are escaped, and any
    CR/LF is collapsed to a single space.  Empty text becomes a non-breaking
    space so the cell still renders as a visible, correctly bordered column.
    """
    value = str(text).replace("\\", "\\\\").replace("|", "\\|")
    value = value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    value = value.strip()
    return value if value else " "


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    """Render a GitHub-Flavored-Markdown table as a list of lines."""
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(cells) + " |" for cells in rows)
    return lines


def render_markdown_report(
    kpis: ManagementKPIs,
    anomalies: Sequence[Anomaly] = (),
    *,
    title: str = "Monthly Report Summary",
    generated_at: str | None = None,
) -> str:
    """Render a management report and its anomalies as a Markdown document.

    Parameters
    ----------
    kpis:
        The :class:`~reporting_core.kpi.ManagementKPIs` roll-up to render.
    anomalies:
        The anomalies detected for the same batch (see
        :func:`reporting_core.anomalies.find_anomalies`).  May be empty, in
        which case an explicit "no anomalies detected" line is emitted so a
        clean run is never mistaken for a missing section.
    title:
        The document's top-level heading.  Must be a non-empty string.
    generated_at:
        Optional timestamp (any string, e.g. an ISO date) rendered under the
        title.  When ``None`` no timestamp line is emitted, keeping the output
        deterministic for tests that do not want a clock in the diff.

    Returns
    -------
    str
        A Markdown document ending in a single trailing newline.

    Raises
    ------
    TypeError
        If ``kpis`` is not a ``ManagementKPIs``, ``title``/``generated_at`` are
        not strings, or ``anomalies`` contains a non-``Anomaly`` element.
    ValueError
        If ``title`` is empty or only whitespace.
    """
    if not isinstance(kpis, ManagementKPIs):
        raise TypeError("kpis must be a ManagementKPIs instance")
    if not isinstance(title, str):
        raise TypeError("title must be a string")
    if not title.strip():
        raise ValueError("title must be non-empty")
    if generated_at is not None and not isinstance(generated_at, str):
        raise TypeError("generated_at must be a string or None")
    anomaly_list = list(anomalies)
    if any(not isinstance(item, Anomaly) for item in anomaly_list):
        raise TypeError("anomalies must contain Anomaly instances")

    lines: list[str] = [f"# {title.strip()}", ""]
    if generated_at is not None and generated_at.strip():
        lines += [f"_Generated: {generated_at.strip()}_", ""]

    # --- Headline KPIs -----------------------------------------------------
    lines += ["## Key Metrics", ""]
    metric_rows = [
        ("Total sales", _fmt_number(kpis.total_sales)),
        ("Total quantity", _fmt_number(kpis.total_quantity)),
        ("Active products", str(kpis.active_products)),
        ("No-movement products", str(kpis.no_movement_products)),
        ("Sites reporting", str(kpis.site_count)),
        ("Distinct products", str(kpis.product_count)),
        ("Rows processed", str(kpis.row_count)),
    ]
    lines += _table(("Metric", "Value"), [(m, v) for m, v in metric_rows])
    lines += [""]

    # Budget/variance only when a budget was supplied to the KPI roll-up.
    if kpis.total_budget is not None:
        lines += ["## Budget Performance", ""]
        lines += _table(
            ("Metric", "Value"),
            [
                ("Total budget", _fmt_number(kpis.total_budget)),
                ("Variance", _fmt_optional_money(kpis.total_variance)),
                ("Variance %", _fmt_pct(kpis.total_variance_pct)),
            ],
        )
        lines += [""]

    # --- Per-location table ------------------------------------------------
    lines += ["## Locations", ""]
    if kpis.locations:
        # Widen the table with budget columns only if at least one site has one.
        has_budget = any(loc.budget is not None for loc in kpis.locations)
        if has_budget:
            header = ("Site", "Sales", "Quantity", "Products", "Budget", "Variance", "Variance %")
            loc_rows = [
                (
                    _escape_cell(loc.site),
                    _fmt_number(loc.sales),
                    _fmt_number(loc.quantity),
                    str(loc.products),
                    _fmt_optional_money(loc.budget),
                    _fmt_optional_money(loc.variance),
                    _fmt_pct(loc.variance_pct),
                )
                for loc in kpis.locations
            ]
        else:
            header = ("Site", "Sales", "Quantity", "Products")
            loc_rows = [
                (
                    _escape_cell(loc.site),
                    _fmt_number(loc.sales),
                    _fmt_number(loc.quantity),
                    str(loc.products),
                )
                for loc in kpis.locations
            ]
        lines += _table(header, loc_rows)
    else:
        lines += ["_No locations reported._"]
    lines += [""]

    # --- Top products ------------------------------------------------------
    lines += ["## Top Products", ""]
    if kpis.top_products:
        prod_rows = [
            (
                str(rank),
                _escape_cell(product.product),
                _fmt_number(product.sales),
                _fmt_number(product.quantity),
            )
            for rank, product in enumerate(kpis.top_products, start=1)
        ]
        lines += _table(("#", "Product", "Sales", "Quantity"), prod_rows)
    else:
        lines += ["_No products reported._"]
    lines += [""]

    # --- Anomalies ---------------------------------------------------------
    lines += ["## Anomalies", ""]
    if anomaly_list:
        lines += [f"**{len(anomaly_list)}** anomal{'y' if len(anomaly_list) == 1 else 'ies'} detected.", ""]
        anomaly_rows = [
            (str(a.row_index), _escape_cell(a.code), _escape_cell(a.message))
            for a in anomaly_list
        ]
        lines += _table(("Row", "Code", "Message"), anomaly_rows)
    else:
        lines += ["No anomalies detected."]
    lines += [""]

    return "\n".join(lines).rstrip("\n") + "\n"


def write_markdown_report(
    kpis: ManagementKPIs,
    anomalies: Sequence[Anomaly] = (),
    *,
    path: str,
    title: str = "Monthly Report Summary",
    generated_at: str | None = None,
) -> str:
    """Render the Markdown report and write it to ``path``, returning ``path``.

    Parent directories are created as needed.  The file is written UTF-8 with a
    single trailing newline, matching :func:`render_markdown_report`.
    """
    from pathlib import Path

    document = render_markdown_report(
        kpis, anomalies, title=title, generated_at=generated_at
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    return str(target)
