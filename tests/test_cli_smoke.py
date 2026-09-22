
import process_reports


def test_demo_generation_is_reproducible_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(process_reports, "BASE", tmp_path)
    monkeypatch.setattr(process_reports, "INPUT_DIR", tmp_path / "01_input_reports")
    monkeypatch.setattr(process_reports, "OUTPUT_DIR", tmp_path / "03_output")
    monkeypatch.setattr(process_reports, "DASHBOARD_DIR", tmp_path / "dashboard")
    process_reports.make_demo()
    demo=tmp_path / "01_input_reports" / "01 - Commissary Movement Report (DEMO).csv"
    lines=demo.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("Site,Category,Product")
    assert len(lines)>200

def test_process_cli_symbols_remain_importable():
    assert callable(process_reports.process)
    assert callable(process_reports.make_demo)
