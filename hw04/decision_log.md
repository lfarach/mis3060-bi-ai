# HW4 Decision Log: Wildcat Capital Data Cleaning

Written **before** the cleaning code. Each entry is based on evidence from `reports/dq_summary_raw.csv` and `reports/profile_raw.csv` (produced by `scripts/01_profile.py`).

**Decision types:** convert · standardize · fill · flag · quarantine · leave as is

---

## Part 1: Defects to fix

### D1. fact_transactions / security_id: IDs stored as decimals
| Field | Entry |
|---|---|
| **Evidence** | 197,175 of 197,175 non-blank values are stored like `45.0` instead of `45`. Because of this, the FK check to `dim_security` matches 0%. After converting to whole numbers, 0 orphans remain. |
| **Dimension** | Validity, Referential Integrity |
| **Decision** | **Convert** `45.0` → `45` |
| **Justification** | It's the same ID in a different format, probably saved by a system that read the column as a float because of the blanks. Every trade has to link to its security, or holdings-by-sector reporting won't work. |
| **Risk** | Low. If a real ID had a decimal part (like `45.5`), converting would hide it. The script asserts that every value ends in `.0` before converting. |

### D2. fact_portfolio_snapshot / return_ytd: percent stored as text
| Field | Entry |
|---|---|
| **Evidence** | 300 values look like `9.28%` while the rest are decimals like `0.0195`. They fail numeric parsing. |
| **Dimension** | Validity, Consistency |
| **Decision** | **Convert**: strip the `%` and divide by 100 |
| **Justification** | Performance reporting needs one unit. Verified: for all 300 rows, `converted return − benchmark_return_ytd = active_alpha_ytd`, so the alpha column confirms that `/100` is the right conversion. |
| **Risk** | Low, because it's verified against alpha. If I stripped the `%` without dividing, those clients would show returns 100× too high. |

### D3. dim_client / state: full names mixed with codes
| Field | Entry |
|---|---|
| **Evidence** | 78 rows use full names (Pennsylvania 25, Florida 15, New York 14, New Jersey 13, …). The other 2,447 use 2-letter codes. |
| **Dimension** | Consistency, Validity |
| **Decision** | **Standardize** to USPS 2-letter codes |
| **Justification** | Otherwise "PA" and "Pennsylvania" show up as two different states in any regional report or map. |
| **Risk** | Very low. The mapping is 1-to-1, and the script asserts that every value is a valid code afterward. |

### D4. dim_client / risk_profile: blank values
| Field | Entry |
|---|---|
| **Evidence** | 76 blanks. In the snapshots, each risk profile maps to exactly one benchmark, and **Balanced is the only profile on benchmark 3**. All 75 blank-risk clients with activity are on benchmark 3. The 76th is one of the near-duplicate clients (see D5). |
| **Dimension** | Completeness |
| **Decision** | **Fill** with `Balanced`, only where the benchmark confirms it |
| **Justification** | This isn't a guess: the benchmark assigned to the account tells us the risk profile. Risk profile matters for suitability and compliance reporting. |
| **Risk** | If benchmark assignment doesn't actually follow risk profile in Wildcat's process, the fill would be wrong. That's why I'm adding a `risk_profile_inferred` flag (0/1) so the fill can be traced. |

### D5. dim_client: near-duplicate clients
| Field | Entry |
|---|---|
| **Evidence** | Clients 2501–2525 (25 rows) match an existing client on first name, age, city, ZIP, initial AUM, client_since and advisor. Only the last name differs, by exactly one letter at the end: 23 are cut off (`Taylo` vs `Taylor`, client 674) and 2 have an extra letter (`Leen` vs `Lee`, `Pacen` vs `Pace`). **None of the 25 appear in any fact table.** |
| **Dimension** | Uniqueness |
| **Decision** | **Quarantine** the 25 truncated copies |
| **Justification** | They're duplicate records of real clients, probably from a second load with a field-length limit. Keeping them would inflate client counts (2,525 vs the real 2,500) and the starting-AUM totals. |
| **Risk** | If they were real, different people, we'd lose 25 clients. That's unlikely, since 7 fields match exactly, and they're kept in the quarantine file, not deleted. |

### D6. fact_transactions / shares: negative shares on Buy rows
| Field | Entry |
|---|---|
| **Evidence** | 836 Buy rows have negative shares (e.g. `-261.9719`). All are Buys and no Sells are affected. The amount is still positive, and `|shares| × price = amount` holds for all 836. |
| **Dimension** | Validity, Consistency |
| **Decision** | **Convert** to the absolute value |
| **Justification** | In this table, direction comes from `txn_type`, not the sign. A negative Buy would cancel out real purchases in a holdings calculation. The amount column confirms the size of each trade. |
| **Risk** | Low. If some of these were actually Sells mislabeled as Buys, we'd be keeping the wrong type. But nothing else on those rows suggests that. |

### D7. fact_transactions / client_id: orphan transactions
| Field | Entry |
|---|---|
| **Evidence** | 200 rows (200 different client IDs, 2702–3192) point to clients that don't exist in `dim_client` (max ID is 2525). The rows cover all transaction types from 2020–2024. |
| **Dimension** | Referential Integrity |
| **Decision** | **Quarantine** |
| **Justification** | We can't tell whose money this is. Assigning it to a client would be inventing data. They'd also show up as "(Blank)" clients in Power BI. |
| **Risk** | Removes about 0.07% of transactions from totals. If these clients exist in another system, the missing master data needs to be requested, which is why they're kept in quarantine. |

### D8. fact_portfolio_snapshot / return_ytd and active_alpha_ytd: scientific notation
| Field | Entry |
|---|---|
| **Evidence** | 135 `return_ytd` and 756 `active_alpha_ytd` values are stored like `9.9e-05` instead of `0.000099`. **Found during Part D validation** (type validity was 99.94%, not 100%). I then added a generic scientific-notation check to the audit script. |
| **Dimension** | Consistency, Validity |
| **Decision** | **Standardize** to plain decimals (6 places, same as the rest of the column) |
| **Justification** | They're valid numbers, so this is a format problem, not a value problem. But a column should have one format. Some tools and Excel imports treat `9.9e-05` as text. |
| **Risk** | Basically none. The script asserts each value is numerically identical (to 1e-9) after reformatting. |

---

## Part 2: Suspicious values to flag (not change)

### F1. fact_portfolio_snapshot / aum and fact_fees / aum_basis = 1,000.00
| Field | Entry |
|---|---|
| **Evidence** | 420 snapshot rows and 386 fee rows have exactly `1000.0`. That's the minimum value in both columns and shows up across many clients and months. Example: client 29's AUM goes 16,704 → 1,000 → recovers later. The two tables agree with each other, so the placeholder exists at the source. |
| **Dimension** | Accuracy / Plausibility |
| **Decision** | **Flag** with `aum_placeholder_flag` |
| **Justification** | It looks like a system floor rather than a real balance. But I don't know the real AUM, and filling it would be inventing data. The flag lets analysts exclude these rows. |
| **Risk** | If left unflagged, it understates AUM and the fees calculated from it. If it's actually real (a nearly empty account), the flag is just extra information. |

### F2. fact_portfolio_snapshot / return_ytd above 100%
| Field | Entry |
|---|---|
| **Evidence** | 976 rows (144 clients) have YTD returns above 100% (max ≈ 9,467%). They're internally consistent (alpha matches), so this isn't a typo. 67% of these rows are accounts under $100K, versus 7% of all rows, and the AUM jumps at the same time (client 29: $9.1K → $52K). |
| **Dimension** | Accuracy / Plausibility |
| **Decision** | **Flag** with `return_outlier_flag` |
| **Justification** | It looks like deposits are being counted as investment gains on small accounts. The real return can't be recomputed without cash-flow-adjusted data, so I'm flagging it rather than changing it. |
| **Risk** | Unflagged, these would badly distort average returns and alpha by advisor. |

### F3. fact_fees / bps_charged = 100.38
| Field | Entry |
|---|---|
| **Evidence** | 1 row is above 100 bps (1%). It's a Retail client, and the Retail range is 74.87–100.38. The amount still matches `aum × bps / 10000 / 12`. |
| **Dimension** | Accuracy / Plausibility |
| **Decision** | **Leave as is** (documented) |
| **Justification** | It's barely above the Retail band and the fee math reconciles, so it's probably a real rate rather than an error. |
| **Risk** | Minimal: one row, $90.68. |

### F4. fact_transactions / txn_date: Buy/Sell on weekends
| Field | Entry |
|---|---|
| **Evidence** | 40,649 of 143,311 Buy/Sell rows (28%, which is about 2 out of 7 days) fall on days where `is_trading_day = 0`. |
| **Dimension** | Accuracy / Plausibility |
| **Decision** | **Leave as is**, documented as a known limitation |
| **Justification** | An even 2/7 share suggests these are booking or entry dates rather than true trade dates. I can't recover the real trade date, and shifting dates would be inventing data. |
| **Risk** | Daily trading-volume reports would show weekend activity. Monthly and yearly reporting isn't affected. |

---

## Part 3: Legitimate structure (leave as is)

| # | Table / column | Evidence | Why it's NOT a defect |
|---|---|---|---|
| L1 | dim_security / sector | 219 blanks, all `is_etf = True` | ETFs hold many stocks, so they don't have a single sector |
| L2 | dim_security / expense_ratio_bps | 281 blanks, all `is_etf = False` | Only funds charge an expense ratio |
| L3 | fact_transactions / security_id, shares, price | 101,597 blanks, all Deposit/Withdrawal/Advisory Fee | Cash movements don't involve a security |
| L4 | dim_advisor / certifications | 6 advisors with the text `None` | Means "no certification." Keep it as text, not null |
| L5 | dim_client / zip_code | Values like `03897` | Leading zeros are real. Keep as text, never as a number |
| L6 | dim_client / is_active | 176 inactive clients, 175 of them have transaction history | Former clients keep their historical records |

---

## Cleaning order (and why)
1. **Fix formats first** (D1 security_id, D2 return_ytd, D8 scientific notation). Joins and math can't be checked until values parse correctly.
2. **Remove duplicates and orphans** (D5, D7), so later fixes and checks only run on valid rows.
3. **Fix values** (D3 state, D4 risk_profile, D6 shares). D4 depends on joining to snapshots, so it comes after the key cleanup.
4. **Add flags last** (F1, F2), on the final clean rows.

**Effect of the order:** because duplicates and orphans are quarantined before values are fixed, the fix counts are 1 lower than the audit counts for D3 (77 vs 78), D4 (75 vs 76) and D6 (835 vs 836). Each of those rows was in a quarantined record. Also, F2 flags 977 rows (vs 976 in the audit), because one of the `%` values from D2 is above 100% once converted.

**Found while testing:** my first version of the duplicate rule only looked for cut-off last names, so it caught 23 of 25. The script's own `assert` stopped it, and that's how the 2 "extra letter" cases were found. The rule was widened to "differ by one letter at the end."
