# Data Schema & Normalization Rules

This document is the authoritative reference for the **canonical schema** the
Report Automation System maps every input onto, and for the exact
**normalization rules** applied during ingest, aggregation, and validation.

Everything below is derived directly from the code:

- `reporting_core/models.py` — the typed, validated in-memory schema.
- `process_reports.py` — the ingest pipeline (`CANONICAL`, `ALIASES`, `_norm`,
  `_read_rows`, `_to_number`, `_write_outputs`).
- `reporting_core/validation.py` — strict row/summary validation rules.

---

## 1. Canonical schema

### 1.1 Processing columns (`process_reports.py`)

Every raw row read from an input file is projected onto this fixed,
ordered set of columns (`CANONICAL`):

| Column     | Meaning              |
|------------|----------------------|
| `Site`     | Store / location     |
| `Category` | Product group        |
| `Product`  | Item description      |
| `Quantity` | Units moved          |
| `Sales`    | Sales / cost value    |
| `Status`   | Movement status       |

The consolidated master CSV (`03_output/master_data_<timestamp>.csv`) appends
two provenance columns that the processor adds per row, so the full written
header is:

```
Site, Category, Product, Quantity, Sales, Status, Report_Name, Processing_Date
```

- `Report_Name` — the source file's stem (filename without extension).
- `Processing_Date` — the run date as `YYYY-MM-DD`, taken from the injected
  processing clock (see [USER_GUIDE](USER_GUIDE.md) for the deterministic-clock
  note).

> **Cell values are preserved as read.** During ingest, `Quantity` and `Sales`
> are **not** coerced to numbers — CSV cells arrive as strings (e.g. `"3"`,
> `"$12.50"`) and Excel cells keep whatever type `openpyxl` returns. Numeric
> interpretation happens later, only where a number is actually needed
> (see §3, "Numeric coercion"). A `None` cell becomes an empty string `""`.

### 1.2 Typed model (`reporting_core/models.py`)

For validated, in-memory analytics the same six fields are expressed as a
frozen dataclass with real types:

```python
@dataclass(frozen=True)
class ReportRow:
    site: str
    category: str
    product: str
    quantity: float
    sales: float
    status: Status          # Literal["Active", "No Movement"]
```

`Status` is a `Literal["Active", "No Movement"]` — those are the only two
values the typed model recognizes.

The run-level rollup is:

```python
@dataclass(frozen=True)
class ReportSummary:
    total_sales: float
    total_quantity: float
    active_products: int
    no_movement_products: int

    @property
    def product_count(self) -> int:            # active + no_movement
        return self.active_products + self.no_movement_products
```

Both dataclasses are `frozen=True` (immutable, hashable).

---

## 2. Header normalization

Real-world reports spell the same column many different ways. Normalization
folds those variants into the canonical names in three steps.

### 2.1 Header key canonicalization (`_norm`)

Each raw header string is reduced to a lookup key:

1. Lower-cased and stripped.
2. Every run of non-alphanumeric characters is collapsed to a single space
   (`re.sub(r"[^a-z0-9]+", " ", ...)`), then stripped again.

So `"Sales ($)"` → `"sales"`, `"Qty Sold"` → `"qty sold"`,
`"Product_Description"` → `"product description"`.

The key is looked up in the `ALIASES` table. **An unknown header returns
`None` and that column is dropped** — only recognized headers contribute to a
row.

### 2.2 Alias table (`ALIASES`)

The current mappings (raw key → canonical column):

| Canonical  | Recognized header variants |
|------------|----------------------------|
| `Site`     | `site`, `location`, `store`, `branch` |
| `Category` | `category`, `group`, `product group`, `department` |
| `Product`  | `product`, `item`, `description`, `product name`, `product description`, `sku` |
| `Quantity` | `quantity`, `qty`, `units`, `qty sold`, `units sold`, `qty ordered`, `movement` |
| `Sales`    | `sales`, `amount`, `total`, `cost`, `net sales`, `sales amount`, `extended cost`, `value` |
| `Status`   | `status`, `movement status`, `state` |

Adding support for a new report format is a **one-line change**: add the new
raw key to this table. Keep keys lower-cased and space-separated (that is the
form `_norm` produces).

### 2.3 Row mapping & signal filtering (`_read_rows`)

For each raw input row:

1. Start from a template with all six canonical columns set to `""`.
2. For every raw header/value pair, resolve the header via `_norm`; if it maps
   to a canonical column, copy the value into that column (mapping `None` →
   `""`) and mark the row as having a recognized column (`hit`).
3. **Keep the row only if** it both had at least one recognized column (`hit`)
   **and** has a non-empty `Product` **or** non-empty `Site`.

This is what keeps blank rows, footers, and totals lines out of the master
table — a row with no `Site` and no `Product` signal is discarded even if some
other column matched.

### 2.4 File readers

`_read_rows` dispatches on the file extension:

- `.csv` — read with the standard-library `csv.DictReader` using
  `utf-8-sig` encoding (so a UTF-8 BOM is stripped). All values are strings.
- `.xlsx` / `.xlsm` — read with `openpyxl` (`read_only=True, data_only=True`)
  if it is installed. **Every worksheet** is read; the first row of each sheet
  is treated as headers. If `openpyxl` is not installed, the file is skipped
  with a printed hint and processing continues.
- Any other extension — skipped (returns no rows).

---

## 3. Numeric coercion (`_to_number`)

Where a numeric value is genuinely required (summing `Sales` and `Quantity`
for the run summary), values pass through `_to_number`, which is tolerant of
real-world formatting:

1. Cast to `str`, remove thousands separators (`,`) and currency signs (`$`),
   and strip whitespace.
2. An empty string returns `0.0`.
3. **Accounting-style negatives** wrapped in parentheses — `"(123.45)"` — are
   converted to a leading-minus form (`-123.45`).
4. Parse as `float`. **Anything unparseable returns `0.0`** (never raises).

Examples (verified by the test suite):

| Input           | Result     |
|-----------------|------------|
| `"123.45"`      | `123.45`   |
| `"(123.45)"`    | `-123.45`  |
| `"$ (1,234.50)"`| `-1234.50` |
| `""`            | `0.0`      |
| `"n/a"`         | `0.0`      |

---

## 4. Status normalization in the run summary (`_write_outputs`)

The run summary written to `03_output/summary_report.json` and
`dashboard/data.js` classifies each master row as active or not-moving:

- A row counts as **no-movement** when `str(row["Status"]).strip().lower()` is
  either `"no movement"` **or** `"inactive"`.
- Every other row (including blank or unrecognized status) counts as
  **active** (`active = total_records - no_movement`).

The emitted summary object is:

```json
{
  "processing_date": "YYYY-MM-DD HH:MM:SS",
  "total_records": <int>,
  "total_sales": <float, 2dp>,
  "total_quantity": <float, 2dp>,
  "active_products": <int>,
  "no_movement": <int>,
  "master_file": "master_data_<timestamp>.csv"
}
```

`total_sales` and `total_quantity` are the `_to_number` sums, rounded to 2
decimal places.

---

## 5. Validation rules (`reporting_core/validation.py`)

The typed `ReportRow` / `ReportSummary` model is validated **strictly** (this
is separate from the lenient ingest above — ingest keeps messy raw values,
while the validated model enforces business invariants and raises `ValueError`
on violation).

`validate_row(row)` raises `ValueError` unless **all** hold:

- `site` is non-empty after stripping.
- `product` is non-empty after stripping.
- `quantity` is finite and **non-negative** (`>= 0`).
- `sales` is finite and **non-negative** (`>= 0`).
- `status` is exactly `"Active"` or `"No Movement"`.

`validate_summary(summary)` raises `ValueError` unless:

- `total_sales` is finite and non-negative.
- `total_quantity` is finite and non-negative.
- `active_products` and `no_movement_products` are both non-negative.

> Note the deliberate difference in sign handling: `_to_number` **can** yield a
> negative (accounting parentheses), but `validate_row` **rejects** negative
> `quantity`/`sales`. The lenient parser exists to read whatever a source
> produces; the validator exists to gate what the typed analytics layer will
> accept.

---

## 6. Related modules

Downstream `reporting_core` modules consume the validated schema:

| Module | Uses the schema for |
|--------|--------------------|
| `kpis.py` | Site/product breakdowns and headline KPIs over validated rows |
| `quality.py` / `quality_summary.py` | Valid/invalid row profiling and an export gate |
| `duplicates.py` | Exact-duplicate detection keyed on all six fields |
| `anomalies.py` | Negative-quantity / negative-sales / invalid-status flags |
| `reconciliation.py` | Expected-vs-observed sales delta within a tolerance |

See [USER_GUIDE.md](USER_GUIDE.md) for how to run the pipeline end to end.
