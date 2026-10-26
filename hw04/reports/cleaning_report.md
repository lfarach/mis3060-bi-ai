# Wildcat Capital: Data Cleaning Report
**To:** Portfolio Committee  **From:** Lucas Farach  **Re:** Data warehouse extract (8 tables, 2020–2024)

## Executive summary
The data warehouse extract had problems that would have broken reporting. The biggest one: **none of the 197,175 trades could be linked to the security they were in** (0% match), because security IDs were stored as `45.0` instead of `45`. That pulled the transaction table's overall referential match down to 81.95%. There were also 25 duplicate client records, 200 transactions for clients that don't exist, and several formatting issues in the return data.

After cleaning, **all 8 tables score 100% on completeness, key uniqueness, type validity and referential match**, and all 13 table relationships join correctly. No data was invented. Values that looked wrong but couldn't be proven wrong were **flagged, not changed**, and every removed row was saved to a quarantine file. Row counts reconcile exactly for every table (raw = clean + quarantined).

## What changed
| Issue | Rows | Action | How it was verified |
|---|---:|---|---|
| Security IDs stored as `45.0` | 197,175 | Converted to `45` | 100% now match the security table |
| Returns stored as `9.28%` text | 300 | Converted to 0.0928 | Return − benchmark = alpha for all 300 |
| Returns/alpha in scientific notation (`9.9e-05`) | 891 | Standardized to plain decimals | Values identical before and after |
| Duplicate clients (last name off by one letter) | 25 | Quarantined | 7 fields match the original; no activity |
| Transactions for non-existent clients | 200 | Quarantined | Client IDs 2702–3192 aren't in the client table |
| State as full name ("Pennsylvania") | 77 | Standardized to "PA" | All values now valid USPS codes |
| Blank risk profile | 75 | Filled with "Balanced" + flagged | Benchmark 3 is only used by Balanced clients |
| Negative shares on Buy trades | 835 | Made positive | \|shares\| × price = amount on every row |
| **Total** | **199,353 cells changed, 225 rows quarantined** | | |

### Before vs. after (from `data_quality_scorecard.csv`)
| Table | Metric | Raw | Clean |
|---|---|---:|---:|
| fact_transactions | Referential match | 81.95% | 100% |
| fact_transactions | Type validity | 90.54% | 100% |
| dim_client | Key uniqueness | 98.02% | 100% |
| dim_client | Rule pass | 99.13% | 100% |
| fact_portfolio_snapshot | Type validity | 99.92% | 100% |

All five cross-table reconciliations (fee math, fee AUM vs. snapshot AUM, alpha, trade amounts, advisor assignment) are at 100% on the clean data.

## Key judgment calls

**1. Filling blank risk profiles instead of leaving them blank.** Normally I wouldn't fill a missing value, because that's guessing. In this case the data answered the question: every risk profile maps to a specific benchmark, and benchmark 3 is used *only* by Balanced clients. All 75 blank-profile clients are on benchmark 3. I filled them and added a `risk_profile_inferred` flag so anyone can see which ones were filled.
*Risk:* if benchmark assignment doesn't actually follow risk profile in Wildcat's process, these 75 clients could be misclassified for suitability reporting. The flag makes them easy to review.

**2. Flagging (not fixing) returns above 100%.** 977 monthly snapshots show YTD returns above 100% (as high as 9,467%). They aren't typos, because the alpha math still works on them. 67% of these rows are accounts under $100K (vs. 7% of all rows), and AUM jumps at the same time. That points to deposits being counted as investment gains. I can't calculate the true return without cash-flow data, so I added a `return_outlier_flag`.
*Risk:* if they're included unflagged, average returns and advisor alpha rankings would be badly distorted. **The committee should exclude flagged rows from performance analysis.**

**3. Quarantining the 200 orphan transactions.** These rows have real dollar amounts but point to client IDs that don't exist. Assigning them to a client would be making data up, so they were set aside in `quarantine_fact_transactions_orphan_client.csv`.
*Risk:* totals are understated by 200 of 298,772 transactions (about 0.07%). If these clients exist in another system, that client data needs to be requested.

**4. Letting the safety checks find what I missed.** Two problems were caught by the scripts' own checks rather than by me. My first duplicate rule only found 23 of the 25 duplicates, and an `assert` stopped the script, which is how I found that 2 had an *extra* letter (`Leen` vs. `Lee`). Validation also showed type validity at 99.94% instead of 100%, which led to the scientific-notation fix.

## Limitations (known, not fixed)
- **$1,000 placeholder balances:** 420 snapshots and 386 fee records show AUM of exactly $1,000.00, which looks like a system floor. The real balance is unknown. Flagged with `aum_placeholder_flag`; exclude these from AUM totals.
- **Weekend trade dates:** 40,630 Buy/Sell transactions (28% of trades) are dated on non-trading days. These are probably booking dates, not trade dates. This is fine for monthly or annual reporting but misleading for daily trading volume.
- **One fee at 100.38 bps:** slightly above 1%, but within the Retail range and the fee math checks out. Left as is.
- **IQR outliers are not errors:** IQR flags about 10% of AUM values as outliers, but wealth data is naturally skewed (one large UHNW account isn't an error). These were reported, not changed.

---
*AI-assisted report — reviewed for factual accuracy on 2026-10-25 by Lucas Farach*
