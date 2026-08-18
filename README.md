# 📊 Report Automation System

**Turn a folder of monthly store/commissary Excel reports into one clean master dataset and a live KPI dashboard — in one click.**

Built for multi-site retail/back-office finance operations, this tool eliminates
the manual copy-paste-consolidate cycle that eats hours every month. Drop the
reports in a folder, run one command, and get an analysis-ready dataset plus an
interactive dashboard.

> **Demo note:** This public repo ships with **sanitized sample data only**
> (`Demo Store 01…08`, generic products). No real company data is included.

---

## ✨ What it does

- **Ingests** every `.csv` / `.xlsx` report dropped into `01_input_reports/`
- **Normalizes** messy, inconsistent headers (`Qty`/`Quantity`, `Site`/`Location`,
  `Amount`/`Sales`, …) into one **tidy, canonical schema**
- **Consolidates** all files into a single master CSV
- **Computes KPIs** — total sales, quantity, active products, no-movement items
- **Generates** an interactive **HTML dashboard** (filters + charts + top-10 table)
- **Runs itself** — manual, auto file-watcher, or daily scheduled task

## 🖥️ Dashboard

Interactive dashboard (`dashboard/dashboard.html`) — KPI cards, Sales by Category,
Sales by Site, Top 10 Products, with Site/Category filters. Fully static: open the
HTML file directly, no server needed.

*(Screenshot: `docs/dashboard.png`)*

## 🏗️ Architecture

```
01_input_reports/   ← drop monthly reports here (.csv / .xlsx)
        │
        ▼
process_reports.py  ← normalize headers → consolidate → compute KPIs
        │
        ├── 03_output/master_data_<timestamp>.csv   (tidy master table)
        ├── 03_output/summary_report.json           (run summary)
        └── dashboard/data.js                        (feeds the dashboard)
                    │
                    ▼
        dashboard/dashboard.html  ← open in any browser
```

## 🚀 Quick start

```bash
# 1. (optional) install Excel support
pip install -r requirements.txt

# 2. generate sanitized demo data + build the dashboard
python process_reports.py --demo

# 3. open the dashboard
#    dashboard/dashboard.html
```

To run on **real** reports, drop them into `01_input_reports/` and run:

```bash
python process_reports.py
```

## 🔁 Automation (Windows)

| Script | Purpose |
|--------|---------|
| `automation/Run_All.ps1` | Process reports **and** open the dashboard |
| `automation/Process_Reports.ps1` | Process only |
| `automation/File_Watcher.ps1` | Auto-process any new file added to the input folder |
| `automation/Create_Scheduled_Task.ps1` | Schedule a daily 8 AM run |

## 🧱 Canonical schema

| Column | Description |
|--------|-------------|
| `Site` | Store / location |
| `Category` | Product group |
| `Product` | Item description |
| `Quantity` | Units moved |
| `Sales` | Sales / cost value |
| `Status` | `Active` or `No Movement` |

Header aliases are mapped automatically — extend the `ALIASES` map in
`process_reports.py` to support new report formats.

## 🛠️ Tech

Python (standard library + optional `openpyxl`), PowerShell automation,
vanilla-JS/SVG dashboard (zero runtime dependencies).

## 📄 License

MIT — see `LICENSE`.

---

*Built by **Furqan Ali** — Senior AI Engineer · finance & operations automation.*
