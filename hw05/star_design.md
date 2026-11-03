# HW5 — Star Schema Design: Wildcat Capital

Lucas Farach · MIS3060 Business Intelligence with AI

Everything below is checked in `check_star.py` (42/42 checks pass). Row counts, key uniqueness, orphan checks and grain checks all come from that script, not from eyeballing the data.

---

## Part A — Keys

| Table | Type | Primary key | Foreign keys (column → table[column]) |
|---|---|---|---|
| dim_advisor | Dimension | `advisor_id` | — |
| dim_benchmark | Dimension | `benchmark_id` | — |
| dim_client | Dimension | `client_id` | `advisor_id` → dim_advisor[advisor_id] |
| dim_date | Dimension | `date_id` (the facts join on `date`, which is also unique) | — |
| dim_security | Dimension | `security_id` | `benchmark_id` → dim_benchmark[benchmark_id] |
| fact_fees | Fact | `fee_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`fee_date` → dim_date[date] |
| fact_portfolio_snapshot | Fact | `snapshot_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`benchmark_id` → dim_benchmark[benchmark_id]<br>`snapshot_date` → dim_date[date] |
| fact_transactions | Fact | `txn_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`security_id` → dim_security[security_id] *(can be blank)*<br>`txn_date` → dim_date[date] |

**Notes**
- All eight primary keys are unique and never blank, and every foreign key matches a row in its dimension (0 orphans).
- The fact dates (`txn_date`, `fee_date`, `snapshot_date`) are calendar dates, so they match `dim_date[date]`, not `dim_date[date_id]`. `date_id` is just a counter (1, 2, 3 …).
- **One key can legitimately be blank:** `fact_transactions[security_id]` is empty on 101,528 rows. Every one of them is a Deposit, Withdrawal or Advisory Fee. Those are cash movements, so there's no security to point to (see Part E a).

---

## Part B — Grain

- **fact_transactions:** One row represents a single transaction event (a buy, sell, dividend, deposit, withdrawal or advisory-fee debit) for one client on one date.
- **fact_fees:** One row represents the single fee charged to one client for one month, labeled with its `fee_type` (Management, Advisory, Custodial or Performance). (`client_id` + `fee_date` is unique, and every `fee_date` is the 1st of a month.)
- **fact_portfolio_snapshot:** One row represents one client's account position at the start of one month. (`client_id` + `snapshot_date` is unique, and every `snapshot_date` is the 1st of a month.)

The first is an event (transaction) grain. The other two are periodic (monthly) grains, which matters a lot for how their numbers can be added up in Part C.

---

## Part C — Measures

The test for each column: if I add it up across clients, across months, or both, does the total still mean something?

### fact_transactions

| Column | Type | What that means |
|---|---|---|
| `amount` | Additive (within a `txn_type`) | You can sum it across clients, securities and dates, but only inside one transaction type. Every amount is stored as a positive number, so adding Buys + Sells or Deposits + Withdrawals together gives a meaningless total. |
| `shares` | Additive (within a security and `txn_type`) | Summing shares bought of one security over time works. Summing shares across different securities, or Buys with Sells, doesn't mean anything. |
| `price` | Non-additive | A price per share can't be summed. If you need an average, it should be weighted by shares, not a plain average. |

### fact_fees

| Column | Type | What that means |
|---|---|---|
| `amount` | Additive | Fee dollars can be summed across clients, advisors and months, e.g. total fee revenue for 2023. |
| `aum_basis` | Semi-additive | It's a balance. You can sum it across clients for one month, but summing it across months counts the same money over and over. Over time, use the month-end (last) value or an average. |
| `bps_charged` | Non-additive | It's a rate. Summing basis points is meaningless. The real average rate is total fee amount ÷ total AUM basis, not a plain average of `bps_charged`. |

### fact_portfolio_snapshot

| Column | Type | What that means |
|---|---|---|
| `aum` | Semi-additive | Sum across clients for one month (total firm AUM in March). Never sum across months. For a year or quarter, take the last month's value. |
| `return_ytd` | Non-additive | A percentage that already accumulates year-to-date. You can't sum it across clients or months. Read the latest month, and weight by AUM if averaging across clients. |
| `benchmark_return_ytd` | Non-additive | Same as above: a YTD percentage. Read it, don't sum it. |
| `active_alpha_ytd` | Non-additive | Return minus benchmark return, so it's also a YTD percentage. Same rules. |
| `cash_pct` | Non-additive | A share of the account. Averaging across clients should be AUM-weighted; summing is meaningless. |

### Numeric columns that are not measures
- **Keys:** `txn_id`, `fee_id`, `snapshot_id`, `client_id`, `advisor_id`, `security_id`, `benchmark_id`. These are identifiers; you count them, never sum them.
- **Date parts:** `fact_portfolio_snapshot[year]`, `[month]`. These are labels, and they duplicate what `dim_date` already provides.
- **Flags:** `fact_transactions[is_post_departure_txn]`, `fact_portfolio_snapshot[is_return_suspect]`. They're 0/1 filters. Summing them only gives a count of flagged rows, which is useful as a count but isn't a business measure.

### Numeric attributes in the dimensions that should never be summed
- **dim_advisor:** `advisor_id`, `years_experience`, `aum_target_mm` (a target per advisor; once it's joined to facts, a sum repeats it for every fact row)
- **dim_client:** `client_id`, `age`, `zip_code` (a code, should be Text), `initial_aum` (a one-time starting balance, not a flow), `advisor_id`
- **dim_date:** `date_id`, `year`, `quarter`, `month`, `week_of_year`, `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day`
- **dim_security:** `security_id`, `benchmark_id`, `expense_ratio_bps` (a rate)
- **dim_benchmark:** `benchmark_id`

---

## Part E — Relationships and design questions

**What I built (Part D):** 13 relationships, all Many-to-one (\*:1), all single direction (dimension filters fact). 12 are active and 1 is inactive (`dim_client → dim_advisor`). `dim_date` is marked as the date table on `date`. Row-count cards reconcile with the handout for all 8 tables, and an advisor slicer filters all three facts.

**Conformed dimensions:** `dim_client`, `dim_advisor` and `dim_date` are shared by all three fact tables, so one slicer on any of them filters transactions, fees and snapshots consistently. `dim_benchmark` is shared by `fact_portfolio_snapshot` and (through `dim_security`) `fact_transactions`.

**(a) Blank `security_id`.** 101,528 transaction rows have no `security_id`, and every one is a Deposit, Withdrawal or Advisory Fee. Money moving in or out of an account, or a fee being taken, doesn't involve a stock or ETF, so there's nothing for the key to point to. Every Buy, Sell and Dividend does have a valid security. So it's not a defect: it's the structure of the business showing up in the data. In Power BI this shows as one `(Blank)` ticker row, and that's expected. A blank on any other dimension would mean a broken key, and the script confirms there are none.

**(b) Which `advisor_id` relationship is active.** I kept the three direct relationships active: `fact_transactions`, `fact_fees` and `fact_portfolio_snapshot` each go to `dim_advisor`. `dim_client → dim_advisor` is inactive. Power BI only allows one active path between two tables, and the fact-level advisor is the better one. It records which advisor was responsible when that transaction, fee or snapshot happened, while `dim_client[advisor_id]` is just the client's current advisor. If a client is ever reassigned, the fact-level key keeps history correct. In this data the two agree on every row (the script reports 0 mismatches), so no numbers change today. The inactive relationship is still there if I ever need "clients by advisor" from the dimension side, using `USERELATIONSHIP` in DAX.

**(c) Joining on `date`, not `date_id`.** The facts store real calendar dates like `2020-01-01`, and `dim_date[date]` holds the same values. `date_id` is a counter starting at 1, so joining a date to it would match nothing. I joined all three fact dates to `dim_date[date]`. The script shows 100% of each fact's dates match `date` and 0% match `date_id`.

**(d) Star or snowflake?** Two dimensions point to other dimensions: `dim_security → dim_benchmark` and `dim_client → dim_advisor`. I kept `dim_security → dim_benchmark` active. It's the only way to group trades by benchmark, and it doesn't create a second path to any fact. I kept `dim_client → dim_advisor` but inactive, for the reason in (b). So the model is a star with one small snowflake branch. I didn't flatten benchmark into security because the assignment says not to build new columns, and because `dim_benchmark` is also used directly by the snapshot fact.

---

## Part F — Reflection

**1. Transactions: "How much did clients deposit and withdraw each month in 2024, and what was the net flow?"**
The first half works in one visual: a matrix with month on rows, `txn_type` on columns and Sum of `amount`, filtered to Deposit and Withdrawal. **Net flow does not.** Every amount is stored as positive, so Deposits − Withdrawals needs a DAX workaround. *Fix:* store a signed amount (negative for withdrawals, sells and fees) or add a +1/−1 direction column to the fact.

**2. Fees: "Which advisors earned the most fee revenue in 2023?"**
This works in one visual with no DAX: a bar chart of `dim_advisor[last_name]` by Sum of `fact_fees[amount]`, with a year slicer from `dim_date`. Fee amount is fully additive and the advisor relationship is active, so the default sum is correct.

**3. Snapshots: "How has total AUM per advisor changed each year?"**
By month this works: a line chart with month on the axis and Sum of `aum`. **By year it gives the wrong answer.** Power BI would add 12 monthly balances together, overstating AUM about 12×, and the same happens with an average return or cash %. Getting the year-end balance needs DAX (e.g. a `LASTDATE` / closing-balance measure). *Fix:* add a period-end flag on the snapshot (or keep a separate year-end snapshot table) so a report can filter to one balance per period. Storing AUM-weighted return inputs would also make firm-level returns possible without DAX.

**Takeaway:** the event and flow facts (transactions, fees) are easy to report on with default sums. The balance fact (snapshots) is where a naive model gives confident but wrong totals, which is exactly what Assignment 6's DAX measures need to handle.
