# HW6 — DAX Measure Library: AUM & Performance

MIS3060 Business Intelligence with AI · Lucas Farach

All measures live in the `_Measures` table of `powerbi/hw06.pbix`. Every number here is reconciled to pandas in `reports/measure_reconciliation.csv` (86 rows, all match).

**The three additivity patterns (from HW5 Part C):**
- **SUM**: the column is additive, so a plain SUM is right in any filter (fee dollars, deposits).
- **Last balance**: the column is a balance (`aum`), so summing across months is wrong. Take the value at the last snapshot date in the filter. Snapshots are dated the 1st of the month, so I use `LASTNONBLANK` instead of `LASTDATE`.
- **Recompute and weight**: the result is a rate or ratio, so I never sum or average it. I rebuild it from additive parts, with a weight where needed.

---

## Part A — Measure library

### Base measures (from the ICEs)

| Measure | DAX | Format | Pattern |
|---|---|---|---|
| `Total Fees` | `SUM ( fact_fees[amount] )` | Currency, 2 dp | SUM |
| `Net Flows` | `CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" ) - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )` | Currency, 2 dp | SUM |

### 0. `AUM (naive SUM)` — ⚠️ wrong on purpose, never on a report

```DAX
AUM (naive SUM) = SUM ( fact_portfolio_snapshot[aum] )
```
- **Format:** Currency, 2 dp
- **Pattern:** SUM, which is the **wrong** pattern for a balance
- **Meaning:** It adds every client's balance in every month together, so the same dollars get counted up to 60 times. With no filters it shows **$566.68B**, about 44.5× what Wildcat actually manages. It's only here to show the trap, and pandas makes the exact same mistake (reconciliation row 3).

### 1. `Ending AUM`

```DAX
Ending AUM =
CALCULATE (
    SUM ( fact_portfolio_snapshot[aum] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
- **Format:** Currency, 2 dp · **Pattern:** last balance
- **Meaning:** How much money Wildcat manages at the end of whatever period you're looking at. Right now that's **$12.73B** (Dec 1, 2024).

### 2. `Ending Clients`

```DAX
Ending Clients =
CALCULATE (
    DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
- **Format:** Whole number · **Pattern:** last balance (a count of who's on the books at the last date)
- **Meaning:** How many clients the firm has at the end of the period: **2,325** today.

### 3. `Avg AUM per Client`

```DAX
Avg AUM per Client = DIVIDE ( [Ending AUM], [Ending Clients] )
```
- **Format:** Currency, 2 dp · **Pattern:** recompute (ratio of two last-balance measures)
- **Meaning:** The typical relationship size, about **$5.48M** per client, which helps a manager compare tiers or advisors' books.

### 4. `Ending AUM LY` and `AUM YoY %`

```DAX
Ending AUM LY = CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )

AUM YoY % = DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] )
```
- **Format:** Currency, 2 dp / Percentage, 2 dp · **Pattern:** last balance (shifted a year) / recompute
- **Meaning:** The balance a year earlier, and how much the book grew since then. 2024 grew **19.58%**. 2020 is blank because there's no 2019 data. I left out DIVIDE's third argument so it shows blank instead of a fake 0%.

### 5. `Ending AUM PM` and `AUM MoM %`

```DAX
Ending AUM PM = CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )

AUM MoM % = DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] )
```
- **Format:** Currency, 2 dp / Percentage, 2 dp · **Pattern:** last balance (shifted a month) / recompute
- **Meaning:** The balance a month earlier, and the month-over-month change. December 2024 was up **4.25%** from November.

### 6. `Avg Monthly AUM`

```DAX
Avg Monthly AUM =
DIVIDE (
    SUM ( fact_portfolio_snapshot[aum] ),
    DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] )
)
```
- **Format:** Currency, 2 dp · **Pattern:** recompute (Σ balances ÷ number of months = average balance)
- **Meaning:** The average amount managed across the months in the period. It's a fairer base than the ending balance for anything earned over the whole year. In 2024 it was **$11.29B**, versus $12.73B at year-end.

### 7. `Fee Yield (bps)`

```DAX
Fee Yield (bps) =
DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) )
```
- **Format:** Decimal, 2 dp · **Pattern:** recompute across **two fact tables** (fees from `fact_fees`, AUM from `fact_portfolio_snapshot`, both filtered through the shared `dim_date` and `dim_client`)
- **Meaning:** How many basis points of AUM Wildcat earns in fees per year. 2024: **43.15 bps**. Retail clients pay the most per dollar (82.81 bps) and UHNW the least (36.14 bps). See Part C(b) for why this runs lower than the ICE 9 rate.

### 8. `Organic Growth Rate`

```DAX
Organic Growth Rate = DIVIDE ( [Net Flows], [Ending AUM LY] )
```
- **Format:** Percentage, 2 dp · **Pattern:** recompute (additive flows ÷ last-year balance)
- **Meaning:** New money from clients (deposits minus withdrawals) as a share of where we started the year. 2024: **0.73%**. So almost all of the 19.58% growth came from somewhere other than new money (Part C(d)).

### 9. `AUM-Weighted Alpha` — drafted by Claude Desktop (Part D)

```DAX
AUM-Weighted Alpha =
VAR LastSnapshot =
    LASTNONBLANK (
        dim_date[Date],
        CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) )
    )
RETURN
    CALCULATE (
        DIVIDE (
            SUMX (
                fact_portfolio_snapshot,
                fact_portfolio_snapshot[active_alpha_ytd] * fact_portfolio_snapshot[aum]
            ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        LastSnapshot,
        fact_portfolio_snapshot[is_return_suspect] <> 1
    )
```
- **Format:** Percentage, 2 dp · **Pattern:** recompute and weight (Σ aum × alpha ÷ Σ aum, at the last snapshot only)
- **Meaning:** How much the firm beat its benchmarks year-to-date, with bigger accounts counting more, so it reflects what happened to the average *dollar*, not the average client. 2024: **+1.45%**.

### 10. `Alpha Signal`

```DAX
Alpha Signal =
VAR Alpha = [AUM-Weighted Alpha]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( Alpha ), BLANK (),
        Alpha >= 0.02, "Outperforming",
        Alpha <= -0.02, "Lagging",
        "In line"
    )
```
- **Format:** Text · **Pattern:** recompute (from measure 9), then label
- **Meaning:** A plain-English flag a manager can scan without reading percentages. Only 2022 (+2.85%) and the 2024 Retail tier (+2.40%) show "Outperforming". Nothing is "Lagging".

### 11. `Top 10 Client Share`

```DAX
Top 10 Client Share =
VAR Top10Clients =
    TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM], DESC )
RETURN
    DIVIDE ( SUMX ( Top10Clients, [Ending AUM] ), [Ending AUM] )
```
- **Format:** Percentage, 2 dp · **Pattern:** recompute within the current filter
- **Meaning:** Concentration risk: how much of the book walks out the door if the 10 biggest clients leave. **6.16%** firm-wide, and 8.13% within UHNW. `VALUES` (not `ALL`) keeps it to the clients in the current filter, so in the tier table it's the top 10 *of that tier*.

### Report page

`hw06.pbix` → page **Measures**: 4 cards (Ending AUM, Ending Clients, Avg AUM per Client, Top 10 Client Share), a table by `dim_date[year]`, and a table by `dim_client[client_tier]` with a visual-level filter `year = 2024`. `AUM (naive SUM)` is not on the page.

---

## Part C — Design questions

### (a) `Ending AUM` vs `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )`

| | Value |
|---|---:|
| `Ending AUM` (no filters) | **$12,729,572,078.86** |
| `SUMX` over clients | **$13,149,297,713.80** |
| Difference | **$419,725,634.94** |

The difference comes from *when* each version takes the "last" balance.

- `Ending AUM` finds **one** last date for the whole filter (Dec 1, 2024) and adds up everyone's balance on that date.
- Inside `SUMX`, `[Ending AUM]` runs once **per client**, so each client gets their **own** last date. For a client who left the firm, that's their final snapshot from months or years ago.

In pandas, 175 clients have their last snapshot before December 2024: 13 left in 2022 and 162 in 2023. All 175 are `is_active = False` in `dim_client`. Their old balances add up to exactly **$419,725,634.94**, which is the whole gap. SUMX counts money that isn't at the firm anymore.

**"How much do we manage today?" → `Ending AUM` ($12.73B).** The SUMX version mixes balances from different dates, so it doesn't describe any single point in time.

### (b) Why 2024 Fee Yield (43.15 bps) is lower than the ICE 9 Effective Fee Rate (45.53 bps)

Both have the same numerator (2024 fees × 12 × 10,000). The difference is the denominator:

| | Denominator | bps |
|---|---:|---:|
| Fee Yield | Σ snapshot `aum` = $135,459,843,783.73 | **43.15** |
| Effective Fee Rate | Σ fee `aum_basis` = $128,385,303,527.10 | **45.53** |

What pandas shows (`scripts/02_part_c_evidence.py`):
- I matched every 2024 snapshot row to `fact_fees` on `client_id` + month. Out of 27,900 client-months, **1,684 have AUM but no fee row at all**, and **0** fee rows lack a snapshot.
- Those 1,684 client-months hold **$7.07B** of AUM, which is 5.22% of the Fee Yield denominator.
- Where both rows exist, `aum` equals `aum_basis` on **100%** of rows.
- If I recompute Fee Yield using only the client-months that have a fee row, I get **45.53 bps**, exactly the Effective Fee Rate.

So the whole gap comes from AUM that has no fee recorded against it. Fee Yield counts it, and the Effective Fee Rate never sees it.

**The data limitation:** `fact_fees` doesn't have a row for every client-month. The gaps are scattered, not a policy: 2,261 of 2,500 clients are missing about 3 months each. It happens every year (1,139 to 1,684 client-months a year), across all tiers and account types, and not in any particular month like onboarding. Because there's no "$0 fee" row, **we can't tell a waived fee from a missing record**. That means:
- **Effective Fee Rate** overstates what Wildcat earns on its whole book, because it only looks at billed AUM.
- **Fee Yield** is the honest firm-wide number *if* those months really weren't billed. If they're missing records, it understates revenue.

Someone needs to ask billing which one it is before either number goes in front of leadership.

### (c) Why `AUM-Weighted Alpha` uses the last snapshot only, and drops suspect rows

**Last snapshot only:** `active_alpha_ytd` is *year-to-date*. The December row already includes January through November. If you average across months, you blend a 1-month YTD number with an 11-month one, which doesn't mean anything. The weights would be off too, because `aum` is a balance, so every client would get counted 12 times. In pandas, weighting across all 12 months of 2024 gives **0.32%**. The correct December-only value is **1.45%**.

**Excluding `is_return_suspect = 1`:** At Dec 1, 2024 there are 148 suspect rows out of 2,325, and they're only **0.12% of AUM**. But their alpha runs from **−120.90% to +7,133.78%**. Clean rows stay between about −50% and +50%. Those values are data errors, not real performance.

| Dec 1, 2024 rows | AUM-weighted | Simple mean |
|---|---:|---:|
| Suspects excluded (the measure) | **1.45%** | **0.88%** |
| Suspects included | **1.67%** | 15.56% |

- Even at 0.12% of AUM, the suspects push the weighted number up by **0.22 points**. That's enough to move a tier across the ±2% Alpha Signal line.
- On a simple mean, where a tiny account counts as much as a $50M one, they blow it up to 15.56%.
- The weighted (1.45%) vs simple (0.88%) gap on clean rows also tells us something: bigger accounts did better than small ones.

### (d) Organic Growth Rate by tier, 2024

| Tier | Organic Growth | AUM YoY % | Growth *not* from net flows | Net new money |
|---|---:|---:|---:|---:|
| HNW | 1.18% | 19.64% | 18.46% | $25.2M |
| Retail | **9.87%** | 19.13% | 9.26% | **$44.2M** |
| UHNW | **0.10%** | 19.59% | 19.49% | $8.1M |
| Firm | 0.73% | 19.58% | 18.85% | $77.5M |

**What it says:**
- All three tiers grew about 19–20%, but for different reasons.
- **Retail** is where the new money comes from. About half its growth (51.6%) was net deposits, and it brought in the most new dollars ($44.2M) even though it's only 4% of AUM.
- **UHNW** grew almost entirely from market moves. Its clients added just $8.1M net on an $8.1B book, so only 0.5% of its growth came from flows.
- So Wildcat's headline 19.58% growth is mostly the market, not clients giving it more money. If markets flatten, UHNW and HNW growth stalls, while Retail keeps adding assets.

**What it doesn't tell you:**
- **Dollars vs percent.** Retail's 9.87% sounds big, but it's on a small base. $44M is under half a percent of the firm's AUM.
- **What the non-flow part actually is.** YoY minus organic lumps together market returns, dividends and anything else that isn't a deposit or withdrawal. It doesn't show skill (that's alpha, measure 9).
- **Gross vs net.** A tier with $0 net flow could have huge deposits *and* huge withdrawals. Net flows hide churn.
- **New vs existing clients.** It can't separate money from new clients from existing clients adding more. It also uses each client's *current* tier from `dim_client`, so a client who grew from HNW into UHNW during the year is counted under UHNW the whole time.
- **Profitability.** Retail pays 82.81 bps and UHNW 36.14 bps, so a dollar of Retail growth earns more than twice the fees of a dollar of UHNW growth.
