# Part D — Verifying Claude's `AUM-Weighted Alpha`

**Measure:** 9, `AUM-Weighted Alpha` · **Prompt and full response:** `claude/dax_session.md` · **Metadata:** `claude/model_metadata.md`

## Did it run as written? What did the test query return?

Yes. I pasted Claude Desktop's measure into `_Measures` with no changes, and Power BI accepted it with no errors. The only difference is whitespace: Apporto's lag meant it went in as one line instead of indented, but the formula is identical.

Claude's test query (it defines the measure inside the query, so you can test it before adding it) ran on the first try. It returned:

| Result | Year | Last Snapshot | AUM-Weighted Alpha |
|---|---|---|---:|
| 1 (grand total) | — | 12/1/2024 | 0.014479946800564277 |
| 2 | 2020 | 12/1/2020 | −0.006801702781131989 |
| 2 | 2021 | 12/1/2021 | −0.0015743692248397741 |
| 2 | 2022 | 12/1/2022 | 0.02849406991081533 |
| 2 | 2023 | 12/1/2023 | 0.01768904713557521 |
| 2 | 2024 | 12/1/2024 | 0.014479946800564277 |

Every year used its December 1 snapshot. That's direct proof that `LASTNONBLANK` found the last date *with data* and not Dec 31, where `LASTDATE` would have returned a blank.

## Which reconciliation rows prove it?

In `reports/measure_reconciliation.csv`, these 9 `AUM-Weighted Alpha` rows all match pandas to within about 1e-13 (tolerance 0.0001):

- `Grand Total`
- `Year 2020` through `Year 2024`
- `Tier 2024 HNW`, `Tier 2024 Retail`, `Tier 2024 UHNW`

The 9 `Alpha Signal` rows also match. They're built on this measure, so they test the ±2% thresholds too.

The pandas side (`aum_weighted_alpha()` in `scripts/01_reconcile_measures.py`) was written separately from the definition. It finds the last snapshot date on all rows, drops `is_return_suspect = 1`, then computes Σ(aum × alpha) ÷ Σ(aum). It never reads anything from Power BI.

## Edge cases I checked

1. **Grand total (no filters).** It should equal the latest year, not an average of the years. Result: 1.45%, identical to 2024 down to the last digit. ✅ An average of the five years would be 1.05%, so this confirms it's a point-in-time value.
2. **`dim_date[year] = 2022`.** This is the only year above the +2% line, so it tests whether each year row uses its own last snapshot. Result: 2.85% from the 12/1/2022 snapshot, Alpha Signal "Outperforming". ✅ Both match pandas.
3. **The 2024 tier table**, with the tier filter coming through `dim_client` on top of the year filter. Results: HNW 1.40%, Retail 2.40% ("Outperforming"), UHNW 1.41%. All three match pandas. ✅ The 2024 total (1.45%) is between the tier values and close to UHNW, which holds 76% of the AUM. That's what a weighted average should do.
4. **Including vs excluding suspects** (pandas). With suspect rows left in, the 2024 value would be 1.67% instead of 1.45%. So the filter really changes the answer. It isn't just there for show.

## What I changed, and why

**Nothing.** The measure matched every slice on the first run, so there was nothing to fix. I didn't swap in the reference version from `POWERBI_STEPS.md`, which uses `= 0` instead of `<> 1`. On this data the two are identical (see below), and Claude's version is safer if a blank flag ever shows up.

One small note: my first attempt went to Claude without the metadata by mistake (the placeholder got sent). I re-ran the prompt with the full metadata and used that second response. Both are in `dax_session.md`.

## A claim I confirmed, and one that didn't apply

- **Confirmed:** Claude said "the grand-total value should exactly match the latest year's row" and that the grand total "is the most recent month's alpha, not an average across years." In Power BI, the grand total and the 2024 row are both 0.014479946800564277. Pandas gives the same value from the 12/1/2024 rows only.
- **True, but it doesn't matter here:** Claude said using `<> 1` instead of `= 0` "also keeps any blank flags." That's correct DAX logic, but in pandas `is_return_suspect` has **0 blanks** out of 129,547 rows (only 0s and 1s). So on this data `<> 1` and `= 0` give exactly the same result.

## My judgment of Claude's output

Claude's output was correct and well-reasoned. It used only real table and column names from the metadata. It handled both traps the measure has, the semi-additive `aum` and the YTD `active_alpha_ytd`, and it explained why. It also flagged a real design choice: if every row on the last date were suspect, the measure returns blank instead of falling back to an earlier month. The test query was the most useful part, because the "Last Snapshot" column let me see the filter context directly instead of trusting a single number.
