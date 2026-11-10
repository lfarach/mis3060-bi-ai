# HW6 — DAX Measure Library: AUM & Performance

MIS3060 Business Intelligence with AI · Lucas Farach

This folder builds the 12 measures in the assignment's table (0–11), which is 16 DAX measures in `_Measures` counting the pairs and base measures, on the Wildcat Capital star model. It proves every number in pandas and uses Claude to draft and verify one measure.

## Folder structure

```
hw06/
├── README.md                          # this file
├── powerbi/
│   ├── hw06.pbix                      # posted model + _Measures table + "Measures" report page (~21 MB)
│   └── measures.md                    # Part A (DAX, pattern, meaning) and Part C answers
├── scripts/
│   ├── 01_reconcile_measures.py       # Part B: recomputes every measure in pandas and compares to Power BI
│   └── 02_part_c_evidence.py          # Part C: prints the pandas evidence used in measures.md
├── reports/
│   ├── powerbi_values.csv             # 86 values exported from Power BI DAX query view
│   └── measure_reconciliation.csv     # 86 rows: powerbi_value vs pandas_value, abs_diff, match
└── claude/
    ├── model_metadata.md              # INFO.VIEW.COLUMNS / RELATIONSHIPS / MEASURES export
    ├── dax_session.md                 # Part D prompt + Claude Desktop's full response
    └── verification.md                # Part D verification
```

The Wildcat Capital Clean CSVs aren't copied into the repo. The scripts read them from `C:\MIS3060\Wildcat Capital Clean` by default.

## How to run

Requires Python 3 and pandas. From the repo root (`C:\MIS3060\mis3060-bi-ai`):

```bash
python hw06/scripts/01_reconcile_measures.py
python hw06/scripts/02_part_c_evidence.py
```

If your CSVs are somewhere else, pass the folder: `python hw06/scripts/01_reconcile_measures.py "path/to/Wildcat Capital Clean"`. Both scripts also accept browser-download names like `dim_date (1).csv`.

**Current result:** `Reconciled 86 rows: 86 match, 0 don't` (largest currency diff $0.0002, largest ratio diff 1.2e-13). Exit code is 1 if any row doesn't match.

## Reconciliation coverage

| Slice | Measures | Rows |
|---|---|---:|
| Grand Total | all 16 (incl. base measures, naive SUM, LY/PM) | 16 |
| By year 2020–2024 | 1, 4, 6, 7, 8, 9, 10 (+ `Ending AUM LY`) | 40 |
| By tier, 2024 | 1, 3, 4, 7, 8, 9, 10, 11 (+ `Ending AUM LY`) | 27 |
| December 2024 | 5 (`Ending AUM`, `Ending AUM PM`, `AUM MoM %`) | 3 |

**Tolerance:** 0.01 for currency, 0.0001 for ratios and bps, exact for the client count and for `Alpha Signal` text. A blank on **both** sides is a match. This covers the three 2020 rows (`Ending AUM LY`, `AUM YoY %`, `Organic Growth Rate`), which are blank because there's no 2019 data.

**Naive SUM:** Power BI and pandas both give **$566,681,084,542.48**, which is about 44.5× the real Ending AUM of $12.73B. Both tools make the same mistake when you sum a balance across months.

## Mismatches and fixes

**None.** All 86 rows matched on the first run, so neither side needed fixing. Two things nearly caused false mismatches, and the script handles both:
- **Blanks:** the three 2020 rows are blank in Power BI. The script treats blank-on-both-sides as a match instead of comparing `NaN` to `NaN`, which is always False.
- **Float noise:** Power BI exports full precision (e.g. `12729572078.859997` instead of `12729572078.86`). That's why the comparison uses a tolerance, not exact equality.

The pandas side has to copy two DAX behaviors exactly to match:
- `Top 10 Client Share` evaluates `[Ending AUM]` per client, so each client gets **their own** last snapshot date.
- `Ending AUM LY` / `PM` shift the whole date range, then find the last snapshot inside it. For the grand total, that means Dec 2023 for LY and Nov 2024 for PM.

## Process notes

- **Power BI:** built on the Apporto virtual desktop, with Claude in Chrome doing the clicking. Apporto's Power BI is older than the version that last saved the file, so it can't draw the new Card visual. The 4 cards show blank there but are set up correctly in the file. The values were exported with DAX query view. Excel on Apporto is unlicensed, so the CSV was assembled in Notepad++ at full precision.
- **Part D:** Claude Desktop drafted `AUM-Weighted Alpha` from the exported metadata. It ran as written and matched everywhere. Details are in `claude/verification.md`.
- **Scripts:** drafted with Claude and run locally. Claude Code reviewed them before commit (below).

## Claude Code findings

I asked Claude Code to review `scripts/01_reconcile_measures.py` and `scripts/02_part_c_evidence.py` against the HW6 Part B requirements without changing any files. It ran both scripts and checked the data. It found no real bugs: pandas never uses Power BI values in its math, all 86 required rows are there, and the columns, tolerances and blank handling are right. Here's what it found and what I did:

| # | Finding | What I did |
|---|---|---|
| 1 | The script only checked the rows that happened to be in `powerbi_values.csv`. If a row was missing or duplicated, it would still say "all match". The coverage printout was just a display, not a check | Added a list of the 86 required measure/slice rows built from the Part B requirements. The script now stops with exit code 1 if anything is missing, extra or duplicated. I tested it by deleting one row and it failed like it should |
| 2 | "About 44.5x" in the naive SUM message is typed in, not calculated | Left it. It's correct (44.52×) and doesn't affect results on this data. It's just a printed sentence |
| 3 | The CSV rounded everything to 6 decimals, so the tiny ratio diffs showed as `0.000000` and the "1e-13" only showed in the console. Ending Clients showed as `2325.0` | Removed the rounding so the CSV keeps full precision, and the client count is written as `2325` |
| 4 | The README said "12 DAX measures", but `_Measures` has 16 | Reworded: it's the 12 measures in the assignment's table (0–11), which is 16 DAX measures in `_Measures` counting the pairs and base measures |
| 5 | `measures.md` Part C(b) says the script shows "2,261 of 2,500 clients missing about 3 months each" and that the gaps aren't in any particular month, but the script didn't print those. Same for "129,547 rows" in `verification.md` | Added those lines to `02_part_c_evidence.py`. The numbers were already right: 2,261 clients, 3.25 months on average, and 534–706 gaps in every calendar month |
| 6 | Part C(a) joins to `dim_client` with an inner merge, which could silently drop clients | Left it. Every snapshot client is in `dim_client` (0 missing), so it doesn't affect results on this data |
| 7 | Part C(b) assumes one fee row per client-month. Duplicates would double count | Left it. Claude Code checked and there are 0 duplicate fee or snapshot client-months, so it doesn't affect results on this data |
| 8 | Shifting a date range back a month turns Nov 30 into Oct 30, so it would miss Oct 31 (DAX `DATEADD` wouldn't) | Left it. Every snapshot is on the 1st, so it can't change a result |
| 9 | pandas `nlargest(10)` keeps exactly 10, but DAX `TOPN` keeps ties at #10 | Left it. There are no ties, and Top 10 Client Share matches to about 1e-13 |

After the fixes I reran both scripts: still `Reconciled 86 rows: 86 match, 0 don't`.

**Lesson:** the biggest gap wasn't a wrong number. It was a check that couldn't fail (#1). The script proved the rows it was given, but nothing proved it was given the right rows.
