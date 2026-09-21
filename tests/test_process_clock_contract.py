import pytest

from process_reports import process


def test_process_rejects_non_datetime_clock():
    with pytest.raises(TypeError, match="datetime or None"):
        process(now="2026-09-21")
