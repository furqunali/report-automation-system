"""End-to-end tests for the reporting_core CLI pipeline."""
from datetime import datetime
from pathlib import Path

import pytest

from reporting_core import cli

SAMPLE_DATA = Path(__file__).resolve().parent.parent / "sample_data"


def _sample_row_count() -> int:
    lines = (SAMPLE_DATA / "demo_commissary_report.csv").read_text(
        encoding="utf-8"
    ).splitlines()
    return len(lines) - 1  # minus the header


def test_run_pipeline_processes_sample_data_end_to_end(tmp_path):
    when = datetime(2026, 9, 21, 14, 30, 45)

    result = cli.run_pipeline(SAMPLE_DATA, tmp_path, now=when)

    expected_rows = _sample_row_count()
    # master CSV is written to the requested output dir with a stamped name
    assert result.master_csv == tmp_path / "master_data_20260921_143045.csv"
    assert result.master_csv.exists()

    contents = result.master_csv.read_text(encoding="utf-8").splitlines()
    assert contents[0] == ",".join(cli.MASTER_COLUMNS)
    assert len(contents) - 1 == expected_rows
    assert contents[1].endswith(",demo_commissary_report,2026-09-21")

    # KPIs are computed off the validated rows
    assert result.kpis.rows == expected_rows
    assert result.kpis.total_sales > 0
    assert result.kpis.sites == 8  # Demo Store 01..08

    # every sample row is valid -> run is successful
    assert result.run_summary.rows_received == expected_rows
    assert result.run_summary.rows_invalid == 0
    assert result.run_summary.successful is True

    # persisted master reconciles against the computed KPI total
    assert result.reconciliation.balanced is True
    assert abs(result.reconciliation.delta) <= 0.01


def test_main_returns_zero_and_writes_master(tmp_path, capsys):
    exit_code = cli.main([
        "--input", str(SAMPLE_DATA),
        "--output", str(tmp_path),
    ])

    assert exit_code == 0
    masters = list(tmp_path.glob("master_data_*.csv"))
    assert len(masters) == 1
    out = capsys.readouterr().out
    assert "BALANCED" in out
    assert "CLI pipeline" in out


def test_report_name_override_is_applied(tmp_path):
    result = cli.run_pipeline(
        SAMPLE_DATA, tmp_path, report_name="April Batch", now=datetime(2026, 4, 1)
    )
    rows = result.master_csv.read_text(encoding="utf-8").splitlines()
    assert all(",April Batch,2026-04-01" in line for line in rows[1:])


def test_invalid_rows_are_counted_but_valid_rows_still_written(tmp_path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    # one clean row, one row with negative sales that must fail validation
    (input_dir / "mixed.csv").write_text(
        "Site,Category,Product,Quantity,Sales,Status\n"
        "Store 1,Beverages,Cola,5,12.50,Active\n"
        "Store 1,Beverages,Bad,5,(99.00),Active\n",
        encoding="utf-8",
    )

    result = cli.run_pipeline(input_dir, output_dir, now=datetime(2026, 1, 1))

    assert result.run_summary.rows_received == 2
    assert result.run_summary.rows_valid == 1
    assert result.run_summary.rows_invalid == 1
    assert result.run_summary.successful is False
    assert result.kpis.rows == 1
    assert result.kpis.total_sales == 12.5

    body = result.master_csv.read_text(encoding="utf-8").splitlines()
    assert len(body) == 2  # header + the single valid row
    assert result.reconciliation.balanced is True


def test_empty_input_directory_produces_no_master(tmp_path):
    input_dir = tmp_path / "empty"
    output_dir = tmp_path / "out"
    input_dir.mkdir()

    result = cli.run_pipeline(input_dir, output_dir)

    assert result.master_csv is None
    assert result.kpis.rows == 0
    assert result.run_summary.rows_received == 0
    # nothing persisted and nothing computed -> trivially balanced at 0
    assert result.reconciliation.balanced is True


def test_missing_input_directory_errors_out(tmp_path):
    with pytest.raises(NotADirectoryError):
        cli.run_pipeline(tmp_path / "does-not-exist", tmp_path / "out")


def test_main_reports_missing_input_as_usage_error(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--input", str(tmp_path / "nope"), "--output", str(tmp_path)])
    assert excinfo.value.code == 2


@pytest.mark.parametrize("tolerance", [-1.0, float("nan"), float("inf")])
def test_invalid_tolerance_is_rejected(tolerance, tmp_path):
    with pytest.raises(ValueError, match="tolerance"):
        cli.run_pipeline(SAMPLE_DATA, tmp_path, tolerance=tolerance)


def test_main_reports_invalid_tolerance_as_usage_error(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "--input", str(SAMPLE_DATA),
            "--output", str(tmp_path),
            "--tolerance", "-1",
        ])
    assert excinfo.value.code == 2
