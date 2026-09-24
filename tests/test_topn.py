import pytest

from reporting_core.topn import (
    Item,
    Others,
    Ranking,
    bottom_n,
    top_n,
)


def items(pairs):
    return [Item(label, float(v)) for label, v in pairs]


# --- top_n: core behaviour -------------------------------------------------


def test_top_n_descending():
    data = items([("a", 10), ("b", 30), ("c", 20)])
    res = top_n(data, 2)
    assert [i.label for i in res.items] == ["b", "c"]
    assert [i.value for i in res.items] == [30.0, 20.0]


def test_top_n_larger_than_input_returns_all():
    data = items([("a", 1), ("b", 2)])
    res = top_n(data, 10)
    assert len(res.items) == 2


def test_top_n_zero_returns_empty():
    res = top_n(items([("a", 1), ("b", 2)]), 0)
    assert res.items == ()


def test_top_n_result_type():
    res = top_n(items([("a", 1)]), 1)
    assert isinstance(res, Ranking)
    assert isinstance(res.items[0], Item)


# --- bottom_n --------------------------------------------------------------


def test_bottom_n_ascending():
    data = items([("a", 10), ("b", 30), ("c", 20)])
    res = bottom_n(data, 2)
    assert [i.label for i in res.items] == ["a", "c"]
    assert [i.value for i in res.items] == [10.0, 20.0]


def test_bottom_n_negative_values():
    data = items([("a", -5), ("b", 0), ("c", -10)])
    res = bottom_n(data, 1)
    assert res.items[0].label == "c"


# --- deterministic tie-breaking --------------------------------------------


def test_ties_broken_by_label_ascending_top():
    # three equal values: label order decides who ranks first
    data = items([("zed", 5), ("amy", 5), ("bob", 5)])
    res = top_n(data, 2)
    assert [i.label for i in res.items] == ["amy", "bob"]


def test_ties_broken_by_label_ascending_bottom():
    data = items([("zed", 5), ("amy", 5), ("bob", 5)])
    res = bottom_n(data, 2)
    assert [i.label for i in res.items] == ["amy", "bob"]


def test_ranking_independent_of_input_order():
    a = items([("a", 1), ("b", 2), ("c", 3)])
    b = items([("c", 3), ("a", 1), ("b", 2)])
    assert top_n(a, 2).items == top_n(b, 2).items


# --- others rollup ---------------------------------------------------------


def test_others_rolls_up_remainder():
    data = items([("a", 10), ("b", 20), ("c", 30), ("d", 40)])
    res = top_n(data, 2, with_others=True)
    assert [i.label for i in res.items] == ["d", "c"]
    assert isinstance(res.others, Others)
    assert res.others.count == 2
    assert res.others.total == 30.0  # a(10) + b(20)


def test_others_none_when_nothing_remains():
    data = items([("a", 10), ("b", 20)])
    res = top_n(data, 5, with_others=True)
    assert res.others is None


def test_others_absent_without_flag():
    data = items([("a", 10), ("b", 20), ("c", 30)])
    res = top_n(data, 1)
    assert res.others is None


def test_others_rolls_up_everything_when_n_zero():
    data = items([("a", 10), ("b", 20)])
    res = top_n(data, 0, with_others=True)
    assert res.items == ()
    assert res.others.count == 2
    assert res.others.total == 30.0


def test_bottom_others_rollup():
    data = items([("a", 10), ("b", 20), ("c", 30), ("d", 40)])
    res = bottom_n(data, 2, with_others=True)
    assert [i.label for i in res.items] == ["a", "b"]
    assert res.others.count == 2
    assert res.others.total == 70.0  # c(30) + d(40)


# --- edge cases ------------------------------------------------------------


def test_empty_items():
    res = top_n([], 3, with_others=True)
    assert res.items == ()
    assert res.others is None


# --- validation ------------------------------------------------------------


def test_n_must_be_non_negative():
    with pytest.raises(ValueError):
        top_n(items([("a", 1)]), -1)


def test_n_must_be_int_not_bool():
    with pytest.raises(TypeError):
        top_n(items([("a", 1)]), True)


def test_rejects_non_item():
    with pytest.raises(TypeError):
        top_n([("a", 1.0)], 1)


def test_rejects_duplicate_labels():
    with pytest.raises(ValueError):
        top_n([Item("a", 1.0), Item("a", 2.0)], 1)


def test_rejects_empty_label():
    with pytest.raises(ValueError):
        top_n([Item("  ", 1.0)], 1)


def test_rejects_boolean_value():
    with pytest.raises(TypeError):
        top_n([Item("a", True)], 1)


def test_rejects_non_finite_value():
    with pytest.raises(ValueError):
        bottom_n([Item("a", float("inf"))], 1)


def test_with_others_must_be_bool():
    with pytest.raises(TypeError):
        top_n(items([("a", 1)]), 1, with_others="yes")


def test_digits_must_be_non_negative():
    with pytest.raises(ValueError):
        top_n(items([("a", 1)]), 1, digits=-1)
