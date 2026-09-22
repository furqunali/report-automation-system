import pytest

from reporting_core.anomalies import Anomaly, find_anomalies
from reporting_core.kpi import compute_management_kpis
from reporting_core.markdown_report import (
    render_markdown_report,
    write_markdown_report,
)
from reporting_core.models import ReportRow


def row(site, product, quantity, sales, status="Active", category="General"):
    return ReportRow(
        site=site,
        category=category,
        product=product,
        quantity=quantity,
        sales=sales,
        status=status,
    )


BASIC = compute_management_kpis(
    [
        row("Store A", "Cola", 10, 100.00),
        row("Store A", "Chips", 5, 40.50),
        row("Store B", "Cola", 8, 80.00),
    ]
)


def _section(markdown, heading):
    """Return the lines of one '## heading' section (excluding the heading)."""
    lines = markdown.splitlines()
    start = lines.index(f"## {heading}")
    body = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    return body


def test_renders_title_and_all_sections():
    md = render_markdown_report(BASIC, [], title="September 2026")
    assert md.startswith("# September 2026\n")
    for heading in ("## Key Metrics", "## Locations", "## Top Products", "## Anomalies"):
        assert heading in md
    # Deterministic single trailing newline.
    assert md.endswith("\n")
    assert not md.endswith("\n\n")


def test_generated_at_line_is_optional():
    with_ts = render_markdown_report(BASIC, [], title="X", generated_at="2026-09-22")
    assert "_Generated: 2026-09-22_" in with_ts
    without_ts = render_markdown_report(BASIC, [], title="X")
    assert "Generated:" not in without_ts


def test_deterministic_output():
    a = render_markdown_report(BASIC, [], title="X", generated_at="2026-09-22")
    b = render_markdown_report(BASIC, [], title="X", generated_at="2026-09-22")
    assert a == b


def test_key_metrics_values_are_formatted_with_separators():
    kpis = compute_management_kpis([row("Store A", "Cola", 1000, 1234567.5)])
    md = render_markdown_report(kpis, [], title="X")
    metrics = "\n".join(_section(md, "Key Metrics"))
    assert "| Total sales | 1,234,567.50 |" in metrics
    assert "| Total quantity | 1,000.00 |" in metrics
    assert "| Sites reporting | 1 |" in metrics
    assert "| Rows processed | 1 |" in metrics


def test_locations_table_without_budget_has_four_columns():
    md = render_markdown_report(BASIC, [], title="X")
    locs = _section(md, "Locations")
    header = next(line for line in locs if line.startswith("| Site"))
    assert header == "| Site | Sales | Quantity | Products |"
    # Store A: 100 + 40.50 = 140.50 across 2 products.
    assert any("| Store A | 140.50 | 15.00 | 2 |" == line for line in locs)


def test_locations_table_with_budget_adds_variance_columns():
    kpis = compute_management_kpis(
        [row("Store A", "Cola", 10, 100.00), row("Store B", "Cola", 8, 80.00)],
        budget={"Store A": 120.00, "Store B": 80.00},
    )
    md = render_markdown_report(kpis, [], title="X")
    locs = _section(md, "Locations")
    header = next(line for line in locs if line.startswith("| Site"))
    assert header == "| Site | Sales | Quantity | Products | Budget | Variance | Variance % |"
    # Store A under budget by 20 -> -16.67%.
    assert any("| Store A | 100.00 | 10.00 | 1 | 120.00 | -20.00 | -16.67% |" == line for line in locs)
    # Budget performance section appears with a total variance.
    assert "## Budget Performance" in md
    assert "| Variance | -20.00 |" in md


def test_no_budget_means_no_budget_section_or_columns():
    md = render_markdown_report(BASIC, [], title="X")
    assert "## Budget Performance" not in md
    assert "Variance" not in _section(md, "Locations")[0:2]


def test_top_products_ranked_and_numbered():
    md = render_markdown_report(BASIC, [], title="X")
    prods = _section(md, "Top Products")
    header = next(line for line in prods if line.startswith("| #"))
    assert header == "| # | Product | Sales | Quantity |"
    data = [line for line in prods if line.startswith("| ") and not line.startswith("| #") and "---" not in line]
    # Cola (180.00) ranks above Chips (40.50).
    assert data[0] == "| 1 | Cola | 180.00 | 18.00 |"
    assert data[1] == "| 2 | Chips | 40.50 | 5.00 |"


def test_anomalies_rendered_from_find_anomalies():
    rows = [
        ReportRow("Store A", "General", "Cola", -1.0, 10.0, "Active"),
        ReportRow("Store B", "General", "Chips", 1.0, -5.0, "Active"),
    ]
    anomalies = find_anomalies(rows)
    md = render_markdown_report(BASIC, anomalies, title="X")
    section = "\n".join(_section(md, "Anomalies"))
    assert "**2** anomalies detected." in section
    assert "| Row | Code | Message |" in section
    assert "| 0 | negative_quantity | quantity must be non-negative |" in section
    assert "| 1 | negative_sales | sales must be non-negative |" in section


def test_single_anomaly_uses_singular_wording():
    anomalies = [Anomaly(3, "invalid_status", "status is not recognized")]
    md = render_markdown_report(BASIC, anomalies, title="X")
    assert "**1** anomaly detected." in md


def test_no_anomalies_states_so_explicitly():
    md = render_markdown_report(BASIC, [], title="X")
    section = "\n".join(_section(md, "Anomalies"))
    assert "No anomalies detected." in section
    assert "| Row | Code | Message |" not in section


def test_empty_report_still_renders_every_section():
    empty = compute_management_kpis([])
    md = render_markdown_report(empty, [], title="Empty")
    assert "_No locations reported._" in md
    assert "_No products reported._" in md
    assert "No anomalies detected." in md
    assert "| Total sales | 0.00 |" in md


def test_pipe_in_site_name_is_escaped_to_preserve_table():
    kpis = compute_management_kpis([row("A | B Mart", "Cola", 1, 10.0)])
    md = render_markdown_report(kpis, [], title="X")
    # The literal pipe must be escaped, not left to split the cell.
    assert r"A \| B Mart" in md
    # And the location row still has exactly the 4 expected columns.
    locs = _section(md, "Locations")
    data = next(line for line in locs if "A \\| B Mart" in line)
    assert data.count(" | ") == 3  # 4 cells -> 3 internal separators


def test_newline_in_message_is_flattened():
    anomalies = [Anomaly(0, "weird", "line one\nline two")]
    md = render_markdown_report(BASIC, anomalies, title="X")
    assert "line one line two" in md
    # No stray extra row was introduced by the embedded newline.
    section = _section(md, "Anomalies")
    data = [line for line in section if line.startswith("| ") and "---" not in line and "Row" not in line]
    assert len(data) == 1


def test_negative_zero_variance_normalized():
    # A variance that rounds to zero must not render as "-0.00".
    kpis = compute_management_kpis(
        [row("Store A", "Cola", 1, 100.00)], budget={"Store A": 100.00}
    )
    md = render_markdown_report(kpis, [], title="X")
    assert "-0.00" not in md
    assert "| 100.00 | 0.00 |" in md.replace("Store A ", "")  # variance rendered 0.00


def test_write_markdown_report_round_trips(tmp_path):
    target = tmp_path / "nested" / "report.md"
    returned = write_markdown_report(BASIC, [], path=str(target), title="Written")
    assert returned == str(target)
    assert target.read_text(encoding="utf-8") == render_markdown_report(BASIC, [], title="Written")
    assert target.read_text(encoding="utf-8").startswith("# Written\n")


def test_rejects_non_kpis_input():
    with pytest.raises(TypeError):
        render_markdown_report({"total_sales": 1}, [], title="X")


def test_rejects_empty_title():
    with pytest.raises(ValueError):
        render_markdown_report(BASIC, [], title="   ")


def test_rejects_non_string_title():
    with pytest.raises(TypeError):
        render_markdown_report(BASIC, [], title=123)


def test_rejects_non_string_generated_at():
    with pytest.raises(TypeError):
        render_markdown_report(BASIC, [], title="X", generated_at=20260922)


def test_rejects_non_anomaly_elements():
    with pytest.raises(TypeError):
        render_markdown_report(BASIC, [{"code": "x"}], title="X")
