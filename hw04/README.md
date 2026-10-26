# HW4: Cleaning the Wildcat Capital Data
MIS3060 Business Intelligence with AI · Lucas Farach

Audits, cleans and validates the 8-table Wildcat Capital warehouse extract. Raw files are never modified. Every change is logged, and every removed row is quarantined.

## Folder structure
```
hw04/
├── README.md                  this file
├── decision_log.md            one entry per issue (written before the cleaning code)
├── scripts/
│   ├── 01_profile.py          Part A: generic profiler + 4 groups of DQ checks
│   ├── 02_clean.py            Part C: one fix at a time, asserted and logged
│   └── 03_validate.py         Part D: RI function, rules, reconciliations, IQR, scorecard
├── data/
│   ├── raw/                   the 8 original CSVs (read-only, not committed)
│   ├── clean/                 8 cleaned CSVs + README_clean.md
│   └── audit/                 cleaning_log.csv, value_changes.csv, row_reconciliation.csv,
│                              quarantine_dim_client_near_duplicate.csv,
│                              quarantine_fact_transactions_orphan_client.csv
└── reports/
    ├── profile_raw.csv, dq_summary_raw.csv          (Part A)
    ├── data_quality_scorecard.csv                    (Part D)
    ├── ri_results.csv, rule_results.csv,
    │   reconciliations.csv, iqr_outliers.csv         (Part D detail)
    └── cleaning_report.md                            (Part E)
```

## How to run
Requires Python 3 with pandas. **The 8 raw CSVs are not committed** (they are the course-provided Wildcat Capital extract, and the repo's `.gitignore` keeps raw data out of git). To reproduce, copy them into `data/raw/` with these names: `dim_advisor`, `dim_benchmark`, `dim_client`, `dim_date`, `dim_security`, `fact_fees`, `fact_portfolio_snapshot`, `fact_transactions` (`.csv`).

Run from the `hw04` folder, in this order (each script uses the previous one's output):
```
python scripts/01_profile.py     # -> reports/profile_raw.csv, dq_summary_raw.csv
python scripts/02_clean.py       # -> data/clean/, data/audit/
python scripts/03_validate.py    # -> reports/data_quality_scorecard.csv (+ detail files)
```
`02_clean.py` stops with an `AssertionError` if any fix doesn't do what it claims. `03_validate.py` stops if any clean table scores lower than raw on any metric.

## Results at a glance
- 17 cleaning-log entries, 199,353 cells changed, 225 rows quarantined (25 duplicate clients, 200 orphan transactions)
- raw = clean + quarantined for all 8 tables
- All 8 clean tables: 100% completeness, key uniqueness, type validity and referential match. All 13 relationships join at 100%

## Code review findings (GitHub Copilot)
Each script was reviewed by GitHub Copilot (Ask mode) in VS Code before committing. Copilot was used because it's the AI assistant built into my VS Code setup. Every fix was re-run, and the final outputs (cell changes, quarantine counts, scorecard) were unchanged unless noted.

| Script | What Copilot flagged | What I did about it |
|---|---|---|
| 01_profile.py | Alpha check silently skipped 300 rows it couldn't calculate (NaN) | **Fixed**: the finding now reports how many rows could not be checked; they are re-checked after cleaning in 03_validate.py |
| 01_profile.py | Calendar check skipped month, month_name, week, quarter/year-end and trading-day columns | **Fixed**: all derived columns are now checked (still 0 errors) |
| 01_profile.py | ZIP codes were profiled as numeric | **Fixed**: values with leading zeros are now treated as text identifiers |
| 01_profile.py | Date parse-failure examples showed valid dates; failure % used total rows instead of non-blank rows | **Fixed** both |
| 01_profile.py | Range checks skip unparseable values; near-duplicate check doesn't verify name spelling; fee-tier check is informational only | **Kept**: unparseable values are reported separately as parse failures; the audit only detects duplicates, while 02_clean.py verifies the spelling and asserts it; the fee-tier item is INFO on purpose |
| 02_clean.py | Duplicate removal assumed the higher client ID was the copy | **Fixed**: the copy to quarantine is now chosen by evidence (the record with no fact activity), with an assert that each pair has exactly one active record |
| 02_clean.py | Rounding percent returns to 6 decimals could lose precision | **Fixed**: added an assert that rounding changes no value |
| 02_clean.py | The one-letter name rule could miss other kinds of typos | **Fixed**: added a coverage assert, so every pair matching on all 7 attributes must be explained by the name rule |
| 03_validate.py | RI function trimmed spaces, which contradicts "exact text, like a BI join" | **Fixed**: keys are compared as exact text |
| 03_validate.py | Pooled RI rate rebuilt its denominator from a rounded rate | **Fixed**: the function now also returns the exact checked-row count |
| 03_validate.py | R2 and R5 used inner joins, so unmatched rows disappeared | **Fixed**: left joins, and unmatched rows count as misses (raw R5 is now 99.93%, showing the 200 orphan transactions) |
| 03_validate.py | Date "type validity" only checked the shape (2024-99-99 would pass) | **Fixed**: dates must also parse as real calendar dates |
| 03_validate.py | Completeness denominators differed because clean tables have extra flag columns | **Fixed**: completeness uses the raw column list for both stages |
| 03_validate.py | "Clean >= raw" could pass just by dropping rows | **Fixed**: added an assert that raw rows = clean + quarantined for every table |
| 03_validate.py | Rule-pass % skips blank/unparseable values | **Kept**: those values are counted by the type-validity metric, so each problem is scored once, in one place |

Issues caught by the scripts' own checks during development:
- `02_clean.py`: the first duplicate rule (truncated last names only) found 23 of 25 duplicates. The `assert` stopped the script, and the rule was widened to "differs by one letter at the end."
- `03_validate.py`: snapshot type validity was 99.94% instead of 100%, which revealed 891 values in scientific notation. A check was added to `01_profile.py` and a fix (D8) to `02_clean.py`.
