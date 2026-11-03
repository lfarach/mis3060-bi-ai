# HW5 — Wildcat Capital Star Schema in Power BI

MIS3060 Business Intelligence with AI · Lucas Farach

This folder models the eight clean Wildcat Capital tables as a star schema. It identifies keys, grain and measure types, proves them in Python, and builds the model in Power BI.

## Folder structure

```
hw05/
├── README.md                  # this file
├── star_design.md             # Parts A, B, C, E, F
├── check_star.py              # proves keys, grain and integrity in code
└── powerbi/
    ├── hw05.pbix              # saved Power BI model (~21 MB, under GitHub's 100 MB limit)
    ├── model_view.png         # Model view screenshot (13 relationships)
    └── blank_ticker_check.png # evidence for Part E(a): the one expected (Blank) ticker row
```

The eight source CSVs come from the course's `Wildcat Capital Clean/` folder and aren't duplicated here.

## How to run the check script

Requires Python 3 and pandas (`pip install pandas`).

The CSVs are gitignored, so pass the folder that holds the eight Wildcat Capital Clean files:

```bash
python hw05/check_star.py "C:\MIS3060\HW5"
```

If the CSVs aren't found, it says so and shows the command above. It prints PASS/FAIL for each check, then INFO lines, and exits with code 1 if anything fails.

**What it checks:**
- Row counts match the handout for all 8 tables
- Every primary key is unique and non-blank, including `dim_date[date]` (the join key)
- All 13 foreign keys have zero orphans, and the only blanks are `security_id` on cash rows
- Fee and snapshot grains are unique (`client_id` + month) and every date is the 1st of a month (bad dates fail instead of crashing)
- `txn_type` has exactly the six expected values; cash rows have no security, shares or price; every Buy/Sell/Dividend has a security
- `amount` is always positive (the direction is in `txn_type`)
- All three fact dates match `dim_date[date]` 100% and `dim_date[date_id]` 0%
- INFO only: how many fact rows have an `advisor_id` different from the client's advisor (Part E b)

**Current result:** `42/42 checks passed` (INFO: 0 advisor mismatches on all three facts)

## Power BI model summary

- 13 relationships: 12 active, 1 inactive (`dim_client → dim_advisor`), all Many-to-one, single direction
- Dates joined on `dim_date[date]`; `dim_date` marked as the date table
- Report page 1 holds the checks: Count of every primary key (matches handout), the ticker × amount table showing the one expected `(Blank)` row, and an advisor slicer that filters all three facts

## Claude Code findings

I asked Claude Code to review `check_star.py` against the HW5 requirements without changing files. It ran the script and probed the data. Here's what it found and what I did:

| # | Finding | What I did |
|---|---|---|
| 1 | The E(b) advisor check was hard-coded to pass, so it inflated the score | Changed it to an INFO line outside the pass/fail count. Both advisor paths are valid; the check just reports whether they differ (0 rows) |
| 2 | E(c) didn't actually show `date_id` fails, and only checked `txn_date` | Now checks all three fact dates: 100% match `date`, 0% match `date_id` |
| 3 | The `txn_id` grain check repeated the PK check | Removed it; the PK check already proves the event grain |
| 4 | Missing CSVs gave a traceback | Added a clear message with the correct command |
| 5 | An unparseable date would crash the script | Dates parse with `errors="coerce"` and a bad date now fails the check |
| 6 | Unknown or misspelled `txn_type` values would slip through | Added a check for exactly the six expected types |
| 7 | Cash rows having no shares or price wasn't tested | Added it (0 non-blank values) |
| 8 | "Every amount is positive" (used in Parts C and F) wasn't proven in code | Added it (0 rows ≤ 0) |
| 9 | `dim_date[date]` wasn't checked for blanks | Added to the join-key check |
| 10 | Said Part C names flag columns that don't exist | **Not a real issue.** Claude Code ran the script on my HW4 cleaned files, which have different flag columns. The official HW5 files do have `is_post_departure_txn` and `is_return_suspect`, so Part C is correct |
| 11 | Part C leaves out text columns `fee_type` and `account_type` | Part C only asks for numeric columns, so I left them out there. I added `fee_type` to the fee grain sentence in Part B |
| 12 | README claims didn't match the script, plus this TODO | Updated the README to match |

**Lesson:** the review was most useful for finding checks that *looked* like proof but couldn't fail (#1, #3). It also showed why you have to point the tool at the right data. Its one wrong finding came from reading a different dataset.
