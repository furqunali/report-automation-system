from datetime import datetime

import process_reports


def test_process_uses_injected_clock_for_all_output_timestamps(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    dashboard_dir = tmp_path / "dashboard"
    input_dir.mkdir()
    (input_dir / "report.csv").write_text(
        "Site,Product,Quantity,Sales,Status\nStore 1,Item A,2,10,Active\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(process_reports, "INPUT_DIR", input_dir)
    monkeypatch.setattr(process_reports, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(process_reports, "DASHBOARD_DIR", dashboard_dir)

    when = datetime(2026, 9, 21, 14, 30, 45)
    out = process_reports.process(now=when)

    assert out == output_dir / "master_data_20260921_143045.csv"
    rows = out.read_text(encoding="utf-8").splitlines()
    assert rows[1].endswith(",2026-09-21")
    summary = (output_dir / "summary_report.json").read_text(encoding="utf-8")
    assert '"processing_date": "2026-09-21 14:30:45"' in summary


def test_to_number_parses_accounting_negative_values():
    assert process_reports._to_number("(123.45)") == -123.45
    assert process_reports._to_number("$ (1,234.50)") == -1234.50
    assert process_reports._to_number("123.45") == 123.45
