import pytest

from reporting_core.completeness import (
    DEFAULT_MISSING_TOKENS,
    ColumnCompleteness,
    CompletenessReport,
    analyze_records,
    is_missing,
)

# --- is_missing ------------------------------------------------------------


def test_none_is_missing():
    assert is_missing(None)


def test_blank_and_whitespace_strings_are_missing():
    assert is_missing("")
    assert is_missing("   ")
    assert is_missing("\t\n")


def test_default_placeholder_tokens_are_missing():
    for token in ("N/A", "na", "NULL", "none", "nil", "-", "--"):
        assert is_missing(token), token
    # case-insensitive and whitespace-tolerant
    assert is_missing("  N/a ")


def test_zero_is_present_not_missing():
    # A genuine zero is data, not a gap - the whole reason to profile pre-ingest.
    assert not is_missing(0)
    assert not is_missing(0.0)
    assert not is_missing(False)


def test_ordinary_values_are_present():
    assert not is_missing("Rice")
    assert not is_missing(3.5)


def test_empty_missing_tokens_keeps_only_none_and_blanks_missing():
    # With no placeholder tokens, "n/a" is ordinary data...
    assert not is_missing("n/a", missing_tokens=frozenset())
    # ...but None and blank strings are still missing regardless.
    assert is_missing("", missing_tokens=frozenset())
    assert is_missing(None, missing_tokens=frozenset())


def test_custom_missing_tokens_override_default():
    assert is_missing("tbd", missing_tokens={"tbd"})
    # a default token is no longer missing under a custom set
    assert not is_missing("n/a", missing_tokens={"tbd"})


# --- analyze_records: core counting ----------------------------------------


def _records():
    return [
        {"site": "A", "product": "Rice", "sales": 10},
        {"site": "B", "product": "", "sales": 5},
        {"site": "", "product": "Tea", "sales": None},
    ]


def test_report_shape_and_types():
    report = analyze_records(_records())
    assert isinstance(report, CompletenessReport)
    assert all(isinstance(col, ColumnCompleteness) for col in report.columns)
    assert report.row_count == 3


def test_per_column_fill_counts():
    report = analyze_records(_records())
    site = report.column("site")
    assert (site.total, site.filled, site.missing) == (3, 2, 1)
    product = report.column("product")
    assert (product.filled, product.missing) == (2, 1)
    sales = report.column("sales")
    assert (sales.filled, sales.missing) == (2, 1)


def test_fill_rate_is_exact_ratio():
    report = analyze_records(_records())
    assert report.column("site").fill_rate == pytest.approx(2 / 3)


def test_grid_rollup_totals():
    report = analyze_records(_records())
    # 3 rows x 3 columns = 9 cells, 3 missing (one per column).
    assert report.total_cells == 9
    assert report.filled_cells == 6
    assert report.missing_cells == 3
    assert report.fill_rate == pytest.approx(6 / 9)


def test_column_order_is_first_seen():
    report = analyze_records(_records())
    assert [c.column for c in report.columns] == ["site", "product", "sales"]


def test_is_complete_property():
    complete = analyze_records([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
    assert complete.is_complete
    incomplete = analyze_records([{"a": 1, "b": None}])
    assert not incomplete.is_complete


# --- explicit columns & absent keys ----------------------------------------


def test_explicit_columns_restrict_and_order_output():
    report = analyze_records(_records(), columns=["sales", "site"])
    assert [c.column for c in report.columns] == ["sales", "site"]
    # "product" excluded entirely
    with pytest.raises(KeyError):
        report.column("product")


def test_absent_key_counts_as_missing_for_all_rows():
    records = [{"site": "A"}, {"site": "B"}]
    report = analyze_records(records, columns=["site", "phone"])
    assert report.column("site").filled == 2
    phone = report.column("phone")
    assert phone.filled == 0
    assert phone.missing == 2
    assert phone.fill_rate == 0.0


def test_missing_key_in_some_rows():
    records = [{"site": "A", "note": "x"}, {"site": "B"}]
    report = analyze_records(records)
    note = report.column("note")
    assert note.filled == 1
    assert note.missing == 1


# --- incomplete_columns ordering & threshold -------------------------------


def test_incomplete_columns_worst_first():
    records = [
        {"a": 1, "b": None, "c": None},
        {"a": 2, "b": 2, "c": None},
        {"a": 3, "b": 3, "c": None},
    ]
    report = analyze_records(records)
    incomplete = report.incomplete_columns()
    # c fully empty (0.0) before b (2/3); a is complete and excluded.
    assert [c.column for c in incomplete] == ["c", "b"]


def test_incomplete_columns_threshold_filters():
    records = [
        {"a": 1, "b": None},
        {"a": 2, "b": 2},
    ]
    report = analyze_records(records)
    # b fill rate is 0.5; a is 1.0
    assert [c.column for c in report.incomplete_columns(0.5)] == []
    assert [c.column for c in report.incomplete_columns(0.6)] == ["b"]


def test_incomplete_columns_ties_broken_by_name():
    records = [{"m": None, "z": None, "a": None}]
    report = analyze_records(records)
    # all fill rate 0.0 -> ordered by name
    assert [c.column for c in report.incomplete_columns()] == ["a", "m", "z"]


def test_incomplete_columns_rejects_out_of_range_threshold():
    report = analyze_records([{"a": 1}])
    with pytest.raises(ValueError):
        report.incomplete_columns(1.5)
    with pytest.raises(ValueError):
        report.incomplete_columns(-0.1)


def test_incomplete_columns_rejects_non_numeric_threshold():
    report = analyze_records([{"a": 1}])
    with pytest.raises(TypeError):
        report.incomplete_columns("high")
    with pytest.raises(TypeError):
        report.incomplete_columns(True)


# --- placeholder tokens in analysis ----------------------------------------


def test_placeholder_tokens_reduce_fill_rate():
    records = [{"phone": "555-1000"}, {"phone": "N/A"}, {"phone": "-"}]
    report = analyze_records(records)
    phone = report.column("phone")
    assert phone.filled == 1
    assert phone.missing == 2


def test_disabling_tokens_keeps_placeholders_as_data():
    records = [{"phone": "555-1000"}, {"phone": "N/A"}]
    report = analyze_records(records, missing_tokens=frozenset())
    assert report.column("phone").filled == 2


# --- empty / edge inputs ---------------------------------------------------


def test_no_records_auto_columns_is_vacuous():
    report = analyze_records([])
    assert report.row_count == 0
    assert report.columns == ()
    assert report.total_cells == 0
    assert report.fill_rate == 1.0
    assert report.is_complete


def test_no_records_with_explicit_columns_reports_full_rate():
    report = analyze_records([], columns=["site", "sales"])
    assert report.row_count == 0
    assert [c.column for c in report.columns] == ["site", "sales"]
    for col in report.columns:
        assert col.total == 0
        assert col.fill_rate == 1.0


def test_generator_input_is_consumed_once():
    gen = ({"a": i} for i in range(3))
    report = analyze_records(gen)
    assert report.row_count == 3
    assert report.column("a").filled == 3


def test_to_dict_roundtrips_structure():
    report = analyze_records([{"a": 1, "b": None}])
    data = report.to_dict()
    assert data["row_count"] == 1
    assert data["missing_cells"] == 1
    assert isinstance(data["columns"], list)
    assert data["columns"][0]["column"] == "a"
    assert set(data["columns"][0]) == {"column", "total", "filled", "missing", "fill_rate"}


# --- validation ------------------------------------------------------------


def test_non_mapping_record_rejected():
    with pytest.raises(TypeError):
        analyze_records([{"a": 1}, ["not", "a", "mapping"]])


def test_empty_columns_sequence_rejected():
    with pytest.raises(ValueError):
        analyze_records([{"a": 1}], columns=[])


def test_blank_column_name_rejected():
    with pytest.raises(ValueError):
        analyze_records([{"a": 1}], columns=["a", "   "])


def test_duplicate_columns_rejected():
    with pytest.raises(ValueError):
        analyze_records([{"a": 1}], columns=["a", "a"])


def test_non_string_record_key_rejected_in_auto_discovery():
    with pytest.raises(TypeError):
        analyze_records([{1: "x"}])


def test_default_tokens_are_frozen_and_lowercase():
    assert isinstance(DEFAULT_MISSING_TOKENS, frozenset)
    assert all(token == token.lower() for token in DEFAULT_MISSING_TOKENS)
