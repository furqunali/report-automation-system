"""Top-N and bottom-N ranking of labeled values with an optional rollup.

"Top 5 stores by sales", "bottom 3 SKUs by margin", "biggest ten variances" -
almost every report ends with a leaderboard.  The mechanics look trivial until
two details bite: ties must break the same way every run (or the report diffs
noisily), and the long tail that did not make the cut usually needs to be
rolled into a single "others" line so the totals still reconcile.

This module ranks a list of :class:`Item` (a unique label plus a finite value)
and returns a :class:`Ranking`:

* :func:`top_n` - the ``n`` largest values, descending,
* :func:`bottom_n` - the ``n`` smallest values, ascending.

Ties on value are broken **deterministically by label** (ascending), so the
output never depends on input order or dict iteration.  Pass
``with_others=True`` to fold every item outside the top/bottom ``n`` into a
single :class:`Others` rollup carrying the summed value and the number of items
absorbed - handy for a "... and 42 others: $12,345" footer.  Everything is
deterministic, validated up front, and rounded on output.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class Item:
    """One rankable entry: a non-empty unique ``label`` and a finite ``value``."""

    label: str
    value: float


@dataclass(frozen=True)
class Others:
    """The rolled-up remainder of items outside the ranked slice.

    ``count`` is how many items were absorbed and ``total`` is the sum of their
    values (rounded).  ``None`` is returned instead of an ``Others`` when the
    remainder is empty.
    """

    count: int
    total: float


@dataclass(frozen=True)
class Ranking:
    """The result of a ranking call.

    ``items`` is the ranked slice (already ordered).  ``others`` is the rollup
    of everything not in the slice, or ``None`` when either ``with_others`` was
    not requested or nothing remained.
    """

    items: tuple[Item, ...]
    others: Others | None


def _validate_n(n: int) -> int:
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    return n


def _validate_digits(digits: int) -> int:
    if not isinstance(digits, int) or isinstance(digits, bool):
        raise TypeError("digits must be an integer")
    if digits < 0:
        raise ValueError("digits must be non-negative")
    return digits


def _validate_items(items: list[Item]) -> list[Item]:
    data = list(items)
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, Item):
            raise TypeError("items must contain Item instances")
        if not isinstance(item.label, str) or not item.label.strip():
            raise ValueError("each Item.label must be a non-empty string")
        if item.label in seen:
            raise ValueError(f"duplicate label in items: {item.label!r}")
        seen.add(item.label)
        if not isinstance(item.value, Real) or isinstance(item.value, bool):
            raise TypeError("each Item.value must be numeric")
        if not math.isfinite(float(item.value)):
            raise ValueError("each Item.value must be finite")
    return data


def _rank(items: list[Item], n: int, digits: int, *, largest: bool, with_others: bool) -> Ranking:
    # Sort primarily by value (descending for top, ascending for bottom) and
    # break ties by label ascending, so the order is a pure function of input.
    ordered = sorted(items, key=lambda it: (-float(it.value) if largest else float(it.value), it.label))
    selected = ordered[:n]
    remainder = ordered[n:]

    ranked = tuple(Item(label=it.label, value=round(float(it.value), digits)) for it in selected)

    others: Others | None = None
    if with_others and remainder:
        total = math.fsum(float(it.value) for it in remainder)
        others = Others(count=len(remainder), total=round(total, digits))
    return Ranking(items=ranked, others=others)


def top_n(
    items: list[Item],
    n: int,
    *,
    with_others: bool = False,
    digits: int = 2,
) -> Ranking:
    """The ``n`` largest items, descending, ties broken by label ascending.

    Parameters
    ----------
    items:
        The candidates.  May be empty.  Labels must be unique and non-empty,
        values finite.
    n:
        How many items to return.  Must be a non-negative integer; ``0`` returns
        an empty slice (and, with ``with_others``, rolls *everything* into
        others).  ``n`` larger than the input simply returns all items.
    with_others:
        When ``True``, everything past the top ``n`` is summed into an
        :class:`Others` rollup on the result (``None`` if nothing remains).
    digits:
        Decimal places for item values and the others total.

    Returns
    -------
    Ranking
        The ranked slice and optional rollup.
    """
    n = _validate_n(n)
    digits = _validate_digits(digits)
    data = _validate_items(items)
    if not isinstance(with_others, bool):
        raise TypeError("with_others must be a bool")
    return _rank(data, n, digits, largest=True, with_others=with_others)


def bottom_n(
    items: list[Item],
    n: int,
    *,
    with_others: bool = False,
    digits: int = 2,
) -> Ranking:
    """The ``n`` smallest items, ascending, ties broken by label ascending.

    Mirror of :func:`top_n`.  The rollup, when requested, absorbs everything
    *above* the bottom ``n`` - i.e. the items that were not among the smallest.

    Parameters
    ----------
    items:
        The candidates.  May be empty.  Labels unique/non-empty, values finite.
    n:
        How many items to return.  Non-negative; ``0`` yields an empty slice.
    with_others:
        When ``True``, fold the un-selected remainder into an :class:`Others`.
    digits:
        Decimal places for values and the others total.

    Returns
    -------
    Ranking
        The ranked slice and optional rollup.
    """
    n = _validate_n(n)
    digits = _validate_digits(digits)
    data = _validate_items(items)
    if not isinstance(with_others, bool):
        raise TypeError("with_others must be a bool")
    return _rank(data, n, digits, largest=False, with_others=with_others)
