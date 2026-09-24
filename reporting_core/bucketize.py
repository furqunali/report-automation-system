"""Histogram binning of a numeric series into labeled buckets with counts.

Turning a raw column of numbers into a distribution - "how many orders fell in
each price band?", "how are response times spread across ranges?" - is a
binning problem, and reports need it in two flavours.  Fixed-width binning cuts
the value range into ``n`` equal slices, which is intuitive and comparable
across datasets.  Quantile binning cuts at the data's own quantiles so each
bucket holds roughly the same number of points, which reveals shape even when
the data is heavily skewed.

This module provides both, returning an ordered tuple of :class:`Bucket`:

* :func:`fixed_width_buckets` - ``n`` equal-width bins across ``[min, max]``,
* :func:`quantile_buckets` - ``n`` bins split at empirical quantiles.

Each :class:`Bucket` carries its half-open ``[lower, upper)`` range (the final
bucket is closed, ``[lower, upper]``, so the maximum lands somewhere), a
human-readable ``label``, and the ``count`` of values it captured.  The counts
always sum to the number of input values - every point lands in exactly one
bucket.  Everything is deterministic and validated up front.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class Bucket:
    """One histogram bin.

    Covers the half-open interval ``[lower, upper)`` except for the last bucket
    of a run, which is closed (``[lower, upper]``) so the series maximum is
    captured.  ``label`` is a display string like ``"[0.00, 10.00)"`` and
    ``count`` is how many values fell inside.
    """

    lower: float
    upper: float
    label: str
    count: int


def _validate_bins(bins: int) -> int:
    if not isinstance(bins, int) or isinstance(bins, bool):
        raise TypeError("bins must be an integer")
    if bins < 1:
        raise ValueError("bins must be a positive integer")
    return bins


def _validate_digits(digits: int) -> int:
    if not isinstance(digits, int) or isinstance(digits, bool):
        raise TypeError("digits must be an integer")
    if digits < 0:
        raise ValueError("digits must be non-negative")
    return digits


def _validate_values(values: list[float]) -> list[float]:
    items = list(values)
    if not items:
        raise ValueError("values must not be empty")
    out: list[float] = []
    for v in items:
        if not isinstance(v, Real) or isinstance(v, bool):
            raise TypeError("each value must be numeric")
        v = float(v)
        if not math.isfinite(v):
            raise ValueError("each value must be finite")
        out.append(v)
    return out


def _label(lower: float, upper: float, digits: int, *, closed: bool) -> str:
    close = "]" if closed else ")"
    return f"[{lower:.{digits}f}, {upper:.{digits}f}{close}"


def _assemble(edges: list[float], data: list[float], digits: int) -> tuple[Bucket, ...]:
    """Build buckets from ``len(edges)`` sorted edges and count ``data`` into them.

    ``edges`` holds ``bins + 1`` boundaries.  Every value lands in exactly one
    bucket: the last bucket is closed on the right so the maximum is included,
    and any value below the first edge (should not happen for our own edges)
    folds into the first bucket for safety.
    """
    n_buckets = len(edges) - 1
    counts = [0] * n_buckets
    for v in data:
        if v >= edges[-1]:
            idx = n_buckets - 1
        elif v <= edges[0]:
            idx = 0
        else:
            # Largest edge index whose edge is <= v, clamped to a valid bucket.
            idx = 0
            for i in range(n_buckets):
                if edges[i] <= v < edges[i + 1]:
                    idx = i
                    break
        counts[idx] += 1

    buckets: list[Bucket] = []
    for i in range(n_buckets):
        closed = i == n_buckets - 1
        buckets.append(
            Bucket(
                lower=round(edges[i], digits),
                upper=round(edges[i + 1], digits),
                label=_label(edges[i], edges[i + 1], digits, closed=closed),
                count=counts[i],
            )
        )
    return tuple(buckets)


def fixed_width_buckets(
    values: list[float],
    *,
    bins: int = 10,
    digits: int = 2,
) -> tuple[Bucket, ...]:
    """Bin a series into ``bins`` equal-width buckets across ``[min, max]``.

    Parameters
    ----------
    values:
        A non-empty list of finite numbers.
    bins:
        The number of equal-width buckets.  Must be a positive integer.
    digits:
        Decimal places for bucket edges and labels.

    Returns
    -------
    tuple[Bucket, ...]
        ``bins`` buckets in ascending order whose counts sum to
        ``len(values)``.  When every value is identical the range has zero
        width; a single degenerate bucket ``[v, v]`` holding all points is
        returned regardless of ``bins``, since equal-width slicing of a point is
        undefined.
    """
    bins = _validate_bins(bins)
    digits = _validate_digits(digits)
    data = _validate_values(values)

    lo = min(data)
    hi = max(data)
    if lo == hi:
        return (
            Bucket(
                lower=round(lo, digits),
                upper=round(hi, digits),
                label=_label(lo, hi, digits, closed=True),
                count=len(data),
            ),
        )
    width = (hi - lo) / bins
    edges = [lo + width * i for i in range(bins)] + [hi]
    return _assemble(edges, data, digits)


def quantile(values: list[float], q: float) -> float:
    """The ``q``-th quantile (``q`` in ``[0, 1]``) by linear interpolation.

    The same "type 7" definition used elsewhere in the toolkit: ``q=0`` is the
    minimum, ``q=1`` the maximum, interpolating linearly between order
    statistics in between.
    """
    if not isinstance(q, Real) or isinstance(q, bool):
        raise TypeError("q must be numeric")
    q = float(q)
    if not math.isfinite(q):
        raise ValueError("q must be finite")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be between 0 and 1 inclusive")
    data = sorted(_validate_values(values))
    if len(data) == 1:
        return data[0]
    rank = q * (len(data) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return data[low]
    return data[low] + (data[high] - data[low]) * (rank - low)


def quantile_buckets(
    values: list[float],
    *,
    bins: int = 4,
    digits: int = 2,
) -> tuple[Bucket, ...]:
    """Bin a series into ``bins`` buckets split at empirical quantiles.

    Each cut is placed at an evenly spaced quantile (``1/bins``, ``2/bins`` ...),
    so buckets hold roughly equal counts and the binning follows the data's own
    shape - the right choice for skewed distributions where fixed-width bins
    would leave most buckets nearly empty.

    Parameters
    ----------
    values:
        A non-empty list of finite numbers.
    bins:
        The requested number of quantile buckets.  Must be a positive integer.
    digits:
        Decimal places for bucket edges and labels.

    Returns
    -------
    tuple[Bucket, ...]
        Buckets in ascending order whose counts sum to ``len(values)``.  When
        repeated values collapse adjacent quantile edges, the degenerate
        zero-width buckets are merged out, so the result may contain *fewer*
        than ``bins`` buckets - this is expected for low-cardinality data.  When
        every value is identical a single ``[v, v]`` bucket is returned.
    """
    bins = _validate_bins(bins)
    digits = _validate_digits(digits)
    data = _validate_values(values)

    lo = min(data)
    hi = max(data)
    if lo == hi:
        return (
            Bucket(
                lower=round(lo, digits),
                upper=round(hi, digits),
                label=_label(lo, hi, digits, closed=True),
                count=len(data),
            ),
        )

    raw_edges = [quantile(data, i / bins) for i in range(bins + 1)]
    # Force the extremes exactly and drop collapsed (equal) interior edges so we
    # never emit an empty zero-width bucket.
    raw_edges[0] = lo
    raw_edges[-1] = hi
    edges: list[float] = []
    for e in raw_edges:
        if not edges or e > edges[-1]:
            edges.append(e)
    if len(edges) < 2:  # pragma: no cover - guarded by lo == hi above
        edges = [lo, hi]
    return _assemble(edges, data, digits)
