# User Guide

How to turn a folder of messy monthly store reports into one clean master
dataset and an interactive KPI dashboard — end to end.

The whole workflow is three steps: **drop files → run one command → read the
dashboard.**

---

## Prerequisites

- **Python 3** (CI runs on 3.11).
- **CSV input needs nothing extra** — the processor uses only the standard
  library for `.csv`.
- **Excel input (`.xlsx` / `.xlsm`) needs `openpyxl`.** Install it once:

  ```bash
  pip install -r requirements.txt
  ```

  If `openpyxl` is missing, CSV files still process normally and any Excel file
  is skipped with a printed hint.

All paths are resolved relative to `process_reports.py`, so the project runs
from any location — no hard-coded paths, nothing to configure.

---

## Step 1 — Drop your reports in

Put each monthly export into the input folder:

```
01_input_reports/
```

Supported file types: **`.csv`, `.xlsx`, `.xlsm`**. You can drop in as many
files as you like; every file is read and consolidated into one table. Files
are processed in sorted filename order.

Your reports do **not** need matching column names. The processor normalizes
common header variants (`Qty` / `Quantity` / `Units`, `Site` / `Location` /
`Store`, `Amount` / `Cost` / `Sales`, …) into a fixed six-column schema. The
full list of recognized headers and the exact rules are in
[DATA_SCHEMA.md](DATA_SCHEMA.md).

> **No sample of your own yet?** Generate anonymized demo data instead — see
> [Demo mode](#demo-mode) below.

---

## Step 2 — Run the processor

From the project root, run the **real command**:

```bash
python process_reports.py
```

That single command reads every file in `01_input_reports/`, normalizes and
consolidates the rows, computes the KPIs, and writes all outputs.

You will see a run report like this on the console:

```
====================================================
  REPORT AUTOMATION SYSTEM - processing
====================================================
  + 01 - Commissary Movement Report (DEMO).csv      216 rows
----------------------------------------------------
  master rows : 216
  written     : master_data_20260921_092406.csv, summary_report.json, dashboard/data.js
  open dashboard/dashboard.html to view the KPIs
```

Each `+` line shows a source file and how many recognized rows it contributed.

### What gets written

| Output | Location | Purpose |
|--------|----------|---------|
| Consolidated master table | `03_output/master_data_<timestamp>.csv` | Tidy, analysis-ready rows (canonical columns + `Report_Name`, `Processing_Date`) |
| Run summary | `03_output/summary_report.json` | Totals and KPIs for the run |
| Dashboard payload | `dashboard/data.js` | `window.REPORT_DATA` — the data the dashboard reads |

The `summary_report.json` looks like:

```json
{
  "processing_date": "2026-09-21 09:24:06",
  "total_records": 216,
  "total_sales": 298214.04,
  "total_quantity": 26662.0,
  "active_products": 196,
  "no_movement": 20,
  "master_file": "master_data_20260921_092406.csv"
}
```

> Outputs under `03_output/` and the generated `dashboard/data.js` are working
> artifacts; `.gitignore` keeps real `03_output/` files out of version control.

---

## Step 3 — Read the dashboard

Open the dashboard in any browser:

```
dashboard/dashboard.html
```

It is fully static — it reads the generated `dashboard/data.js` directly, so it
works straight off the filesystem (`file://`) with no server and no internet.
Just double-click the file (or open the hosted demo linked in the
[README](../README.md)).

The dashboard shows:

- **KPI cards** — total sales, total quantity, active vs. no-movement products.
- **Sales by Category** and **Sales by Site** bar charts.
- **Category Share** donut.
- **Top-10 Products** table.
- **Live filters** — narrow everything by Site and/or Category.

Re-run Step 2 whenever you drop in new reports; refresh the browser to see the
updated numbers.

---

## Demo mode

To try the pipeline with fully anonymized, reproducible sample data (generic
store names, generic products, deterministically generated figures — no real
business data):

```bash
python process_reports.py --demo
```

This regenerates the demo report in `01_input_reports/` (and a reference copy
in `sample_data/`), then processes it exactly like a real run. The demo
produces **216 records** across **8 stores** and **8 categories**.

---

## Automation (Windows)

For hands-off monthly runs, the `automation/` folder provides PowerShell
wrappers:

| Script | Purpose |
|--------|---------|
| `automation/Run_All.ps1` | Process reports **and** open the dashboard |
| `automation/Process_Reports.ps1` | Process only |
| `automation/File_Watcher.ps1` | Auto-process any new file added to `01_input_reports/` |
| `automation/Create_Scheduled_Task.ps1` | Register a daily 8 AM run (run once, elevated) |

---

## Troubleshooting

| Symptom (console) | Cause & fix |
|-------------------|-------------|
| `No input files in ...` | `01_input_reports/` has no `.csv`/`.xlsx`/`.xlsm` file. Add reports, or run `python process_reports.py --demo`. |
| `No recognizable rows found. Check the report headers.` | Files were read but no headers matched the alias table, or no row carried a `Site`/`Product` signal. Check your headers against [DATA_SCHEMA.md](DATA_SCHEMA.md) and, if needed, add the new header to the `ALIASES` table (a one-line change). |
| `! openpyxl not installed - skipping Excel file (...)` | Excel support isn't installed. Run `pip install -r requirements.txt`. CSV files still process without it. |
| Dashboard shows old numbers | The browser cached `data.js`. Re-run Step 2 and hard-refresh the page. |

### A note on reproducible timestamps

`process(now=...)` accepts an optional processing clock. Passing a fixed
`datetime` makes the output filename, `Processing_Date`, and
`processing_date` fully deterministic — used by the test suite to assert exact
outputs. In normal use you omit it and the current time is used.

---

## See also

- [DATA_SCHEMA.md](DATA_SCHEMA.md) — canonical schema, header aliases, and the
  exact normalization / validation rules.
- [../README.md](../README.md) — project overview, architecture, and live demo.
- [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) — reporting-integrity
  and testing standards.
