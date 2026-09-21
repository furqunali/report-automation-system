"""Command-line entry point for the report automation pipeline.

Runs the full end-to-end flow over a directory of dropped reports:

    ingestion  ->  reconciliation  ->  KPI aggregation  ->  master CSV

Every stage reuses the existing, individually-tested building blocks:

  * ingestion         -> ``process_reports._read_rows`` / ``_to_number``
  * validation        -> ``reporting_core.validation.validate_row``
  * KPI aggregation   -> ``reporting_core.kpis.aggregate_kpis``
  * reconciliation    -> ``reporting_core.reconciliation.reconcile_sales``
  * run summary       -> ``reporting_core.run_summary.build_run_summary``

The reconciliation stage is a genuine integrity gate: after the master CSV
is written it is read back from disk and its sales total is reconciled
against the freshly computed KPI total. A mismatch (a dropped row, an
encoding problem, a write bug) fails the run with a non-zero exit code
instead of silently shipping a corrupt master table.

Invocation (no packaging/console_scripts is configured in this repo, so run
it as a module with the project root on ``PYTHONPATH``)::

    python -m reporting_core.cli --input 01_input_reports --output 03_output

All paths are taken from the caller; nothing is hard-coded, so the CLI is
safe to point at any staging directory.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import process_reports
from .kpis import KPIResult, aggregate_kpis
from .models import ReportRow
from .reconciliation import ReconciliationResult, reconcile_sales
from .run_summary import RunSummary, build_run_summary
from .validation import validate_row

# Columns written to the consolidated master table (canonical schema plus the
# provenance columns produced by the batch processor).
MASTER_COLUMNS = [
    "Site", "Category", "Product", "Quantity", "Sales", "Status",
    "Report_Name", "Processing_Date",
]
_SUPPORTED_SUFFIXES = (".csv", ".xlsx", ".xlsm")
_NO_MOVEMENT = ("no movement", "inactive")


@dataclass(frozen=True)
class PipelineResult:
    """Outcome of a single CLI run, returned for programmatic/testing use."""

    master_csv: Path | None
    kpis: KPIResult
    reconciliation: ReconciliationResult
    run_summary: RunSummary


def _to_report_row(raw: dict) -> ReportRow:
    """Map a canonical ingestion dict onto a typed, validated ``ReportRow``."""
    status = str(raw.get("Status", "")).strip().lower()
    normalized = "No Movement" if status in _NO_MOVEMENT else "Active"
    return ReportRow(
        site=str(raw.get("Site", "")).strip(),
        category=str(raw.get("Category", "")).strip(),
        product=str(raw.get("Product", "")).strip(),
        quantity=process_reports._to_number(raw.get("Quantity", "")),
        sales=process_reports._to_number(raw.get("Sales", "")),
        status=normalized,
    )


def _write_master(
    ingested: list[tuple[ReportRow, str]], output_dir: Path, now: datetime
) -> Path:
    """Write validated rows to a timestamped master CSV and return its path."""
    stamp_file = now.strftime("%Y%m%d_%H%M%S")
    stamp_day = now.strftime("%Y-%m-%d")
    path = output_dir / f"master_data_{stamp_file}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MASTER_COLUMNS)
        writer.writeheader()
        for row, source in ingested:
            writer.writerow({
                "Site": row.site,
                "Category": row.category,
                "Product": row.product,
                "Quantity": row.quantity,
                "Sales": row.sales,
                "Status": row.status,
                "Report_Name": source,
                "Processing_Date": stamp_day,
            })
    return path


def run_pipeline(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    report_name: str | None = None,
    tolerance: float = 0.01,
    now: datetime | None = None,
) -> PipelineResult:
    """Ingest -> reconcile -> KPI -> master CSV over ``input_dir``.

    Args:
        input_dir: directory scanned for ``.csv``/``.xlsx``/``.xlsm`` reports.
        output_dir: directory the master CSV is written to (created if absent).
        report_name: override the per-file provenance label (defaults to the
            source file stem).
        tolerance: absolute tolerance for the persisted-vs-computed sales
            reconciliation.
        now: injectable clock for reproducible output filenames/timestamps.

    Raises:
        NotADirectoryError: if ``input_dir`` does not exist or is not a dir.
    """
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be a finite non-negative number")

    now = now or datetime.now()
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(f"input directory not found: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        p for p in input_dir.glob("*")
        if p.is_file() and p.suffix.lower() in _SUPPORTED_SUFFIXES
    )

    # ---- ingestion ------------------------------------------------------- #
    ingested: list[tuple[ReportRow, str]] = []
    rows_received = 0
    rows_invalid = 0
    for filepath in files:
        for raw in process_reports._read_rows(filepath):
            rows_received += 1
            try:
                row = _to_report_row(raw)
                validate_row(row)
            except (ValueError, TypeError):
                rows_invalid += 1
                continue
            ingested.append((row, report_name or filepath.stem))

    valid_rows = [row for row, _ in ingested]

    # ---- KPI aggregation ------------------------------------------------- #
    kpis = aggregate_kpis(valid_rows)

    # ---- master CSV ------------------------------------------------------ #
    master_csv = _write_master(ingested, output_dir, now) if ingested else None

    # ---- reconciliation (persisted master vs computed KPI total) --------- #
    persisted_sales = 0.0
    if master_csv is not None:
        for raw in process_reports._read_rows(master_csv):
            persisted_sales += process_reports._to_number(raw.get("Sales", ""))
    reconciliation = reconcile_sales(
        kpis.total_sales, round(persisted_sales, 2), tolerance=tolerance
    )

    # ---- run summary ----------------------------------------------------- #
    run_summary = build_run_summary(
        rows_received=rows_received,
        rows_valid=len(valid_rows),
        rows_invalid=rows_invalid,
        total_sales=kpis.total_sales,
    )

    return PipelineResult(
        master_csv=master_csv,
        kpis=kpis,
        reconciliation=reconciliation,
        run_summary=run_summary,
    )


def _print_report(result: PipelineResult) -> None:
    kpis = result.kpis
    recon = result.reconciliation
    run = result.run_summary
    print("=" * 52)
    print("  REPORT AUTOMATION SYSTEM - CLI pipeline")
    print("=" * 52)
    print(f"  rows received : {run.rows_received}")
    print(f"  rows valid    : {run.rows_valid}")
    print(f"  rows invalid  : {run.rows_invalid}")
    print(f"  total sales   : {kpis.total_sales:,.2f}")
    print(f"  sites         : {kpis.sites}")
    print(f"  products      : {kpis.products}")
    print(f"  top site      : {kpis.top_site}")
    print(f"  top product   : {kpis.top_product}")
    print("-" * 52)
    balance = "BALANCED" if recon.balanced else "OUT OF BALANCE"
    print(f"  reconciliation: {balance} (delta {recon.delta:+.2f})")
    if result.master_csv is not None:
        print(f"  master file   : {result.master_csv}")
    else:
        print("  master file   : (none - no recognizable rows)")


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the pipeline, and return a process exit code."""
    parser = argparse.ArgumentParser(
        prog="reporting_core.cli",
        description="Run ingestion -> reconciliation -> KPI -> master CSV "
                    "over a directory of dropped reports.",
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="directory of input reports (.csv/.xlsx/.xlsm)",
    )
    parser.add_argument(
        "-o", "--output", required=True,
        help="directory the master CSV is written to (created if absent)",
    )
    parser.add_argument(
        "--report-name", default=None,
        help="override the provenance label (defaults to each file's stem)",
    )
    parser.add_argument(
        "--tolerance", type=float, default=0.01,
        help="absolute tolerance for the sales reconciliation (default 0.01)",
    )
    args = parser.parse_args(argv)

    try:
        result = run_pipeline(
            args.input,
            args.output,
            report_name=args.report_name,
            tolerance=args.tolerance,
        )
    except (NotADirectoryError, ValueError) as exc:
        parser.error(str(exc))  # exits with code 2

    _print_report(result)
    # A reconciliation mismatch means the persisted master does not match the
    # computed KPIs -> surface it as a failing exit code for automation.
    return 0 if result.reconciliation.balanced else 1


if __name__ == "__main__":  # pragma: no cover - thin process shim
    sys.exit(main())
