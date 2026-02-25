# AutoClean

**Intelligent Data Quality & Cleaning Tool**

AutoClean is a general-purpose CSV data cleaning pipeline that profiles your data, fixes what's broken, and hands you back a clean dataset — no configuration needed. Point it at any CSV and it handles missing values, outliers, type issues, and duplicate detection automatically, then writes a full before/after report so you know exactly what changed.

---

## What It Does

- Scans every column and builds a full profile — missing %, outliers, data types, cardinality, skew, entropy
- Fills missing numbers using the column median, booleans by mode, and text columns with `"Unknown"`
- Caps outliers using IQR so extreme values don't skew your analysis
- Normalizes messy missing markers like `"?"`, `"N/A"`, `"null"`, `"none"` across all columns
- Parses dates and booleans automatically when it recognizes the column
- If your data has `price_per_unit`, `quantity`, and `total_spent` — it fills in whichever one is missing using the other two
- Gives you a 0–100 **health score** before and after so you can see the improvement at a glance
- Outputs a JSON report and a Markdown report alongside your cleaned CSV

---

## Project Structure

```
autoclean/
├── autoclean/
│   ├── __init__.py
│   ├── main.py         — pipeline entry point (load → profile → clean → save → report)
│   ├── cli.py          — command-line interface
│   ├── cleaner.py      — all cleaning logic
│   ├── profiler.py     — column-by-column data profiling
│   ├── metrics.py      — health score formula
│   └── reporter.py     — generates JSON + Markdown reports
├── data/
│   ├── raw/            — drop your input CSVs here
│   └── cleaned/        — cleaned CSVs land here
├── reports/            — run_report.json and run_report.md saved here
├── .gitignore
└── requirements.txt
```

---

## Installation

Requires Python 3.9+

```bash
pip install -r requirements.txt
```

---

## How to Run

### Command Line

```bash
python -m autoclean.cli --input data/raw/your_file.csv
```

With all options:

```bash
python -m autoclean.cli \
  --input  data/raw/sales.csv \
  --output data/cleaned/sales_clean.csv \
  --report reports/run_report.json
```

| Flag | Required | What it does |
|---|---|---|
| `--input` | ✅ | Path to your raw CSV |
| `--output` | ❌ | Where to save the cleaned CSV. Auto-generates as `data/cleaned/<name>_cleaned.csv` if not set |
| `--report` | ❌ | Where to save the JSON report. A matching `.md` report is always written alongside it |

### Python

```python
from autoclean import run_pipeline

before, after, changes = run_pipeline(
    input_path="data/raw/sales.csv",
    output_path="data/cleaned/sales_clean.csv",
    report_path="reports/run_report.json",
)

print(f"Health score: {before['data_health_score']} → {after['data_health_score']}")
print(f"Missing %:    {before['missing_percent']} → {after['missing_percent']}")
```

---

## Real Example

Here's AutoClean running on a retail sales dataset with 12,575 rows:

```
╭─────────────────────────────────╮
│ AutoClean++                     │
│ Intelligent Data Quality Engine │
╰─────────────────────────────────╯

       Data Quality Summary
┌──────────────┬────────┬────────┐
│ Metric       │ Before │  After │
├──────────────┼────────┼────────┤
│ Rows         │  12575 │  12575 │
│ Missing %    │   5.23 │   0.00 │
│ Duplicate %  │   0.00 │   0.00 │
│ Outlier %    │   0.04 │   0.00 │
│ Health Score │  97.90 │ 100.00 │
└──────────────┴────────┴────────┘

Cleaning Actions
  • normalize_strings: stripped whitespace + standardized missing markers
  • try_parse_datetime: transaction_date (na 0->0)
  • try_parse_bool: discount_applied
  • reconcile: filled 609 values across price/qty/total
  • fill_missing: quantity (median) (na 604->0)
  • fill_missing: total_spent (median) (na 604->0)
  • fill_missing: discount_applied (mode=True) (na 4199->0)
  • fill_missing: item (categorical='Unknown') (na 1213->0)
  • cap_outliers: total_spent (changed 157)

✔ Cleaned dataset saved to data/cleaned/retail_store_sales_cleaned.csv
✔ Report saved to reports/run_report.json
```

---

## Health Score

A single number (0–100) that tells you how clean your data is. Higher is better.

```
score = 100 − (missing_penalty + duplicate_penalty + outlier_penalty)

  missing_penalty   = (missing cells / total cells) × 40    [max 40]
  duplicate_penalty = (duplicate rows / total rows) × 20    [max 20]
  outlier_penalty   = (outliers / total cells) × 30         [max 30]
```

---

## Reports

Every run can produce two report files:

**`run_report.json`** — full machine-readable output with before/after stats and column-level profiles

**`run_report.md`** — human-readable summary table, cleaning actions list, and per-column breakdown

Example report summary from the retail dataset:

| Metric | Before | After | Δ |
|---|---:|---:|---:|
| Rows | 12575 | 12575 | 0 |
| Missing % | 5.23 | 0.00 | −5.23 |
| Duplicate % | 0.00 | 0.00 | 0.00 |
| Outlier % | 0.04 | 0.00 | −0.04 |
| Health Score | 97.90 | 100.00 | +2.10 |

---

## Good to Know

- AutoClean never drops rows — it only fills, coerces, and caps
- Duplicates are flagged in the report but not removed by default
- The retail math reconciliation (`price × qty = total`) only fires if all three columns exist with those exact names
- Every cleaning step is a no-op if the relevant column isn't there — safe to run on any schema
- All steps are wrapped in error handling so it won't crash on weird or unexpected data

---

## Contributing

Contributions are welcome! If you find a bug, have a feature request, or want to improve the code, feel free to open an issue or submit a pull request.

1. Fork the repo
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Commit your changes (`git commit -m "Add your feature"`)
5. Push to the branch (`git push origin feature/your-feature`)
6. Open a Pull Request

Please keep PRs focused — one feature or fix per PR makes reviewing much easier.

---


## Roadmap

- [ ] Excel (`.xlsx`) and JSON input support
- [ ] `--drop-duplicates` flag
- [ ] Config file for per-column cleaning rules (e.g. `autoclean.yaml`)
- [ ] Web UI for non-technical users
- [ ] Batch processing across multiple files
- [ ] Auto-detect date columns beyond just `transaction_date`
- [ ] ydata-profiling integration for extended EDA

---

## Author

**Syed Mohammad Husain**  
[LinkedIn](https://www.linkedin.com/in/syedmohammadhusain/)