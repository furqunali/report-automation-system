#!/usr/bin/env python3
"""
Report Automation System - core processor
=========================================
Consolidates monthly retail/commissary Excel or CSV reports dropped into
`01_input_reports/` into ONE clean, analysis-ready master table, then emits:

  * 03_output/master_data_<timestamp>.csv   - tidy consolidated data
  * 03_output/summary_report.json           - run summary (counts, KPIs)
  * dashboard/data.js                        - powers the HTML dashboard

Unlike a naive "dump every sheet" approach, this normalizes messy header
variants (Site/Location, Qty/Quantity, Sales/Amount, ...) into a fixed,
tidy schema so the output is actually usable for analytics.

Portable: all paths are resolved relative to THIS file, so the project can
live anywhere. No hard-coded user paths.

Usage:
    python process_reports.py            # process files in 01_input_reports/
    python process_reports.py --demo     # (re)generate sanitized demo data
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
INPUT_DIR = BASE / "01_input_reports"
OUTPUT_DIR = BASE / "03_output"
DASHBOARD_DIR = BASE / "dashboard"

# Canonical schema every input row is mapped onto.
CANONICAL = ["Site", "Category", "Product", "Quantity", "Sales", "Status"]

# Header aliases -> canonical column. Add more as new report formats appear.
ALIASES = {
    "site": "Site", "location": "Site", "store": "Site", "branch": "Site",
    "category": "Category", "group": "Category", "product group": "Category",
    "department": "Category",
    "product": "Product", "item": "Product", "description": "Product", "product name": "Product", "product description": "Product", "sku": "Product",
    "quantity": "Quantity", "qty": "Quantity", "units": "Quantity", "qty sold": "Quantity", "units sold": "Quantity",
    "qty ordered": "Quantity", "movement": "Quantity",
    "sales": "Sales", "amount": "Sales", "total": "Sales", "cost": "Sales", "net sales": "Sales", "sales amount": "Sales",
    "extended cost": "Sales", "value": "Sales",
    "status": "Status", "movement status": "Status", "state": "Status",
}


def _norm(h: str) -> str | None:
    """Map a raw header to a canonical column name (or None if unknown)."""
    key = re.sub(r"[^a-z0-9]+", " ", (h or "").strip().lower()).strip()
    return ALIASES.get(key)


def _read_rows(path: Path) -> list[dict]:
    """Read a .csv or .xlsx file into a list of canonical-schema dicts."""
    raw_rows: list[dict] = []
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            raw_rows = list(csv.DictReader(f))
    elif path.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
        except ImportError:
            print("   ! openpyxl not installed - skipping Excel file "
                  f"({path.name}). Run: pip install openpyxl")
            return []
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            for ws in wb.worksheets:
                rows = ws.iter_rows(values_only=True)
                try:
                    headers = [str(c) if c is not None else "" for c in next(rows)]
                except StopIteration:
                    continue
                for r in rows:
                    raw_rows.append({headers[i]: r[i] for i in range(len(headers))
                                     if i < len(r)})
        finally:
            wb.close()
    else:
        return []

    clean: list[dict] = []
    for rr in raw_rows:
        mapped = {c: "" for c in CANONICAL}
        hit = False
        for raw_h, val in rr.items():
            col = _norm(str(raw_h))
            if col:
                mapped[col] = _to_number(val) if col == "Quantity" and val not in (None, "") else (val if val is not None else "")
                hit = True
        # keep only rows that carried at least a product/site signal
        if hit and (mapped["Product"] or mapped["Site"]):
            clean.append(mapped)
    return clean


def _to_number(v) -> float:
    # Single source of truth for messy-cell parsing, shared with the dashboard
    # payload builder so the CSV, summary and data.js always agree.
    from reporting_core.dashboard import coerce_number
    return coerce_number(v)


def process(now: datetime | None = None) -> Path | None:
    """Process input reports using an injectable clock for reproducible runs."""
    if now is not None and not isinstance(now, datetime):
        raise TypeError("now must be a datetime or None")
    now = now or datetime.now()
    OUTPUT_DIR.mkdir(exist_ok=True)
    DASHBOARD_DIR.mkdir(exist_ok=True)

    files = sorted([p for p in INPUT_DIR.glob("*")
                    if p.suffix.lower() in (".csv", ".xlsx", ".xlsm")])
    print("=" * 52)
    print("  REPORT AUTOMATION SYSTEM - processing")
    print("=" * 52)
    if not files:
        print(f"No input files in {INPUT_DIR}.")
        print("Add reports there, or run:  python process_reports.py --demo")
        return

    master: list[dict] = []
    for fp in files:
        rows = _read_rows(fp)
        stamp = now.strftime("%Y-%m-%d")
        for row in rows:
            row["Report_Name"] = fp.stem
            row["Processing_Date"] = stamp
        master.extend(rows)
        print(f"  + {fp.name:<45} {len(rows):>5} rows")

    if not master:
        print("No recognizable rows found. Check the report headers.")
        return

    ts = now.strftime("%Y%m%d_%H%M%S")
    out_csv = OUTPUT_DIR / f"master_data_{ts}.csv"
    cols = CANONICAL + ["Report_Name", "Processing_Date"]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(master)

    _write_outputs(master, out_csv, now)
    print("-" * 52)
    print(f"  master rows : {len(master)}")
    print(f"  written     : {out_csv.name}, summary_report.json, dashboard/data.js")
    print("  open dashboard/dashboard.html to view the KPIs")
    return out_csv


def _write_outputs(master: list[dict], out_csv: Path, processed_at: datetime) -> None:
    from reporting_core.dashboard import build_dashboard_payload, render_data_js

    payload = build_dashboard_payload(
        master,
        processing_date=processed_at.strftime("%Y-%m-%d %H:%M:%S"),
        master_file=out_csv.name,
    )

    (OUTPUT_DIR / "summary_report.json").write_text(
        json.dumps(payload["summary"], indent=2), encoding="utf-8")

    # data.js keeps the dashboard fully static (works via file://)
    (DASHBOARD_DIR / "data.js").write_text(
        render_data_js(payload), encoding="utf-8")


# --------------------------------------------------------------------------- #
#  Sanitized demo data generator (NO real company data)
# --------------------------------------------------------------------------- #
def make_demo() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    sites = [f"Demo Store {i:02d}" for i in range(1, 9)]
    categories = ["Beverages", "Snacks", "Tobacco", "Grocery",
                  "Frozen", "Dairy", "Automotive", "Health & Beauty"]
    products = {
        "Beverages": ["Cola 20oz", "Energy Drink", "Bottled Water", "Iced Coffee"],
        "Snacks": ["Potato Chips", "Chocolate Bar", "Trail Mix", "Beef Jerky"],
        "Tobacco": ["Cigarettes Pack", "Cigar Single", "Vape Pod"],
        "Grocery": ["Bread Loaf", "Canned Soup", "Pasta 1lb", "Cooking Oil"],
        "Frozen": ["Ice Cream Tub", "Frozen Pizza", "Frozen Burrito"],
        "Dairy": ["Milk Gallon", "Cheese Block", "Yogurt Cup"],
        "Automotive": ["Motor Oil 1qt", "Windshield Fluid", "Air Freshener"],
        "Health & Beauty": ["Pain Reliever", "Hand Sanitizer", "Lip Balm"],
    }
    # deterministic pseudo-values (no randomness needed, reproducible demo)
    rows_out = []
    seed = 7
    for si, site in enumerate(sites):
        for cat in categories:
            for pi, prod in enumerate(products[cat]):
                seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
                qty = (seed % 240) + (10 if cat != "Tobacco" else 40)
                price = 2 + ((seed >> 5) % 1800) / 100.0
                sales = round(qty * price, 2)
                status = "No Movement" if (seed % 11 == 0) else "Active"
                if status == "No Movement":
                    qty, sales = 0, 0.0
                rows_out.append({
                    "Site": site, "Category": cat, "Product": prod,
                    "Quantity": qty, "Sales": sales, "Status": status,
                })
    demo_csv = INPUT_DIR / "01 - Commissary Movement Report (DEMO).csv"
    with demo_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CANONICAL)
        w.writeheader()
        w.writerows(rows_out)
    # also keep a copy in sample_data for reference
    (BASE / "sample_data").mkdir(exist_ok=True)
    with (BASE / "sample_data" / "demo_commissary_report.csv").open(
            "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CANONICAL)
        w.writeheader()
        w.writerows(rows_out)
    print(f"Demo data written: {demo_csv.name} ({len(rows_out)} rows)")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        make_demo()
    process()
