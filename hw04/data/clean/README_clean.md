# Wildcat Capital: Clean Data README

Produced by `scripts/02_clean.py` from the 8 raw files in `data/raw/` (raw files are never modified).
Each decision is explained in `decision_log.md`. Each change is traced in `data/audit/`.

## Row counts: raw = clean + quarantined

| Table | Raw | Clean | Quarantined | Quarantine file |
|---|---:|---:|---:|---|
| dim_advisor | 25 | 25 | 0 | |
| dim_benchmark | 8 | 8 | 0 | |
| dim_client | 2,525 | 2,500 | 25 | `quarantine_dim_client_near_duplicate.csv` |
| dim_date | 1,827 | 1,827 | 0 | |
| dim_security | 500 | 500 | 0 | |
| fact_fees | 122,197 | 122,197 | 0 | |
| fact_portfolio_snapshot | 129,547 | 129,547 | 0 | |
| fact_transactions | 298,772 | 298,572 | 200 | `quarantine_fact_transactions_orphan_client.csv` |

## Relationships (star schema)

All relationships are many-to-one, from the fact (or child dimension) to the dimension.

| From (many) | To (one) | Notes |
|---|---|---|
| fact_fees.client_id | dim_client.client_id | |
| fact_fees.advisor_id | dim_advisor.advisor_id | |
| fact_fees.fee_date | dim_date.date | always the 1st of the month |
| fact_portfolio_snapshot.client_id | dim_client.client_id | |
| fact_portfolio_snapshot.advisor_id | dim_advisor.advisor_id | |
| fact_portfolio_snapshot.benchmark_id | dim_benchmark.benchmark_id | |
| fact_portfolio_snapshot.snapshot_date | dim_date.date | always the 1st of the month |
| fact_transactions.client_id | dim_client.client_id | |
| fact_transactions.advisor_id | dim_advisor.advisor_id | |
| fact_transactions.security_id | dim_security.security_id | blank on Deposit / Withdrawal / Advisory Fee rows (expected) |
| fact_transactions.txn_date | dim_date.date | |
| dim_client.advisor_id | dim_advisor.advisor_id | |
| dim_security.benchmark_id | dim_benchmark.benchmark_id | |

**BI tip:** join facts to `dim_date` on the `date` column (not `date_id`). The fact tables store dates, not date IDs. `advisor_id` appears both on the facts and on `dim_client`. Use one path to `dim_advisor` (the fact column) to avoid ambiguous relationships in Power BI.

## Column type settings for a BI tool

| Type | Columns |
|---|---|
| **Whole number** | all `*_id` columns, `age`, `year`, `month`, `quarter`, `week_of_year`, `years_experience`, `aum_target_mm`, all `*_flag` / `is_month_end` / `is_quarter_end` / `is_year_end` / `is_trading_day`, `risk_profile_inferred` |
| **Text (do NOT convert)** | `zip_code` (leading zeros, e.g. `03897`), `primary_account_type` / `account_type` (`529` is a plan name, not a number), `certifications` (`None` is a real value), `ticker`, `ticker_proxy` |
| **Decimal** | `initial_aum`, `aum`, `aum_basis`, `amount`, `price`, `shares`, `bps_charged`, `expense_ratio_bps` |
| **Decimal shown as %** | `return_ytd`, `benchmark_return_ytd`, `active_alpha_ytd`, `cash_pct` (stored as decimals: 0.0928 = 9.28%) |
| **Date** (YYYY-MM-DD) | `date`, `client_since`, `fee_date`, `snapshot_date`, `txn_date` |
| **True/False** | `is_active`, `is_etf` |

## Flag columns added (0 = normal, 1 = flagged)

| Table | Column | Rows = 1 | Meaning |
|---|---|---:|---|
| dim_client | `risk_profile_inferred` | 75 | risk_profile was blank and was filled with `Balanced`, confirmed by the client's benchmark (benchmark 3 is used only by Balanced clients) |
| fact_portfolio_snapshot | `aum_placeholder_flag` | 420 | AUM is exactly 1,000.00, a likely system placeholder. Exclude from AUM totals |
| fact_fees | `aum_placeholder_flag` | 386 | aum_basis is exactly 1,000.00 (same placeholder as snapshots) |
| fact_portfolio_snapshot | `return_outlier_flag` | 977 | return_ytd is beyond ±100%. Exclude from average-return and alpha analysis |

## Changes made (see `data/audit/value_changes.csv` for every cell)

| Table.column | Cells changed | Change |
|---|---:|---|
| fact_transactions.security_id | 197,175 | `45.0` → `45` (now 100% match dim_security) |
| fact_portfolio_snapshot.return_ytd | 300 | `9.28%` → `0.092800` (verified with alpha formula) |
| dim_client.state | 77 | full name → USPS code |
| dim_client.risk_profile | 75 | blank → `Balanced` (flagged) |
| fact_transactions.shares | 835 | negative Buy shares → positive (verified with amount = shares × price) |
| fact_portfolio_snapshot.return_ytd / active_alpha_ytd | 135 / 756 | scientific notation (`9.9e-05`) → plain decimal (`0.000099`), value unchanged |
| **Total** | **199,353** | |

The audit counted 78 / 76 / 836 for the last three. In each case, 1 problem row was in a quarantined record (a duplicate client or an orphan transaction), so it was removed instead of fixed.

## Known limitations (not fixed, on purpose)

| Limitation | Rows | Why it was not fixed |
|---|---:|---|
| AUM placeholders of 1,000.00 | 420 snapshots / 386 fees | The real balance is unknown. Filling it would be inventing data. Flagged instead |
| return_ytd beyond ±100% | 977 | Internally consistent with alpha. Most likely deposits counted as gains on small accounts. A true return needs cash-flow data we don't have. Flagged instead |
| Buy/Sell on weekends / non-trading days | 40,630 (40,649 in raw) | Probably booking dates. The true trade date can't be recovered. Fine for monthly/annual reporting, misleading for daily volume |
| One fee at 100.38 bps | 1 | Within the Retail band and the fee math reconciles. Likely a real rate |
| 200 quarantined transactions | 200 | Client IDs 2702–3192 don't exist in dim_client. Totals exclude about 0.07% of transactions until the client master data is found |
| Clients with is_active = False | 175 | Former clients. Their history is kept on purpose |
