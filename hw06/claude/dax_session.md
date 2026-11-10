# Part D: Claude-Assisted Measure Session (AUM-Weighted Alpha)

**Tool:** Claude Desktop (new chat)
**Measure chosen:** Measure 9, `AUM-Weighted Alpha`
**Workflow:** Draft → Test → Debug → Review

The prompt includes my exported model metadata (the same content as `model_metadata.md`, exported 11/4 before measures 9 and 10 existed), plus what the metadata can't show: the grain of `fact_portfolio_snapshot`, the additivity of `aum` and `active_alpha_ytd`, and the exact business definition.

---

## Prompt

````text
I'm building a DAX measure in Power BI for a portfolio analytics model. Here is my exported model metadata (INFO.VIEW.COLUMNS, INFO.VIEW.RELATIONSHIPS, INFO.VIEW.MEASURES):

# Model metadata (hw06.pbix)

## Columns

[Table]	[Column]	[DataType]	[DAX formula]	[IsHidden]
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Date	Date		true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Day	Integer	DAY([Date])	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Quarter	Text	"Qtr " & [QuarterNo]	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	QuarterNo	Integer	INT(([MonthNo] + 2) / 3)	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Month	Text	FORMAT([Date], "MMMM")	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	MonthNo	Integer	MONTH([Date])	true
DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa	Year	Integer	YEAR([Date])	true
dim_advisor	years_experience	Integer		false
dim_advisor	certifications	Text		false
dim_advisor	advisor_id	Integer		false
dim_advisor	first_name	Text		false
dim_advisor	last_name	Text		false
dim_advisor	region	Text		false
dim_advisor	aum_target_mm	Integer		false
dim_benchmark	ticker_proxy	Text		false
dim_benchmark	asset_class	Text		false
dim_benchmark	name	Text		false
dim_benchmark	benchmark_id	Integer		false
dim_client	client_since	Date		false
dim_client	first_name	Text		false
dim_client	primary_account_type	Text		false
dim_client	client_tier	Text		false
dim_client	risk_profile	Text		false
dim_client	zip_code	Text		false
dim_client	state	Text		false
dim_client	city	Text		false
dim_client	age	Integer		false
dim_client	last_name	Text		false
dim_client	initial_aum	Number		false
dim_client	client_id	Integer		false
dim_client	is_active	True/False		false
dim_client	advisor_id	Integer		false
dim_date	is_quarter_end	Integer		false
dim_date	is_year_end	Integer		false
dim_date	is_trading_day	Integer		false
dim_date	Year	Integer		false
dim_date	Date	Date		false
dim_date	date_id	Integer		false
dim_date	Month	Integer		false
dim_date	Quarter	Integer		false
dim_date	month_name	Text		false
dim_date	week_of_year	Integer		false
dim_date	day_of_week	Text		false
dim_date	is_month_end	Integer		false
dim_security	expense_ratio_bps	Integer		false
dim_security	security_id	Integer		false
dim_security	ticker	Text		false
dim_security	name	Text		false
dim_security	asset_class	Text		false
dim_security	sector	Text		false
dim_security	benchmark_id	Integer		false
dim_security	is_etf	True/False		false
fact_fees	fee_date	Date		false
fact_fees	fee_type	Text		false
fact_fees	aum_basis	Number		false
fact_fees	bps_charged	Number		false
fact_fees	amount	Number		false
fact_fees	fee_id	Integer		false
fact_fees	client_id	Integer		false
fact_fees	advisor_id	Integer		false
fact_portfolio_snapshot	Year	Integer		false
fact_portfolio_snapshot	snapshot_date	Date		false
fact_portfolio_snapshot	benchmark_id	Integer		false
fact_portfolio_snapshot	advisor_id	Integer		false
fact_portfolio_snapshot	client_id	Integer		false
fact_portfolio_snapshot	snapshot_id	Integer		false
fact_portfolio_snapshot	benchmark_return_ytd	Number		false
fact_portfolio_snapshot	is_return_suspect	Integer		false
fact_portfolio_snapshot	account_type	Text		false
fact_portfolio_snapshot	cash_pct	Number		false
fact_portfolio_snapshot	active_alpha_ytd	Number		false
fact_portfolio_snapshot	return_ytd	Number		false
fact_portfolio_snapshot	aum	Number		false
fact_portfolio_snapshot	Month	Integer		false
fact_transactions	security_id	Integer		false
fact_transactions	shares	Number		false
fact_transactions	is_post_departure_txn	Integer		false
fact_transactions	txn_type	Text		false
fact_transactions	txn_date	Date		false
fact_transactions	price	Number		false
fact_transactions	txn_id	Integer		false
fact_transactions	advisor_id	Integer		false
fact_transactions	client_id	Integer		false
fact_transactions	amount	Number		false
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Month	Text	FORMAT([Date], "MMMM")	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Date	Date		true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Year	Integer	YEAR([Date])	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	MonthNo	Integer	MONTH([Date])	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	QuarterNo	Integer	INT(([MonthNo] + 2) / 3)	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Quarter	Text	"Qtr " & [QuarterNo]	true
LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	Day	Integer	DAY([Date])	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Day	Integer	DAY([Date])	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Quarter	Text	"Qtr " & [QuarterNo]	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	QuarterNo	Integer	INT(([MonthNo] + 2) / 3)	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Month	Text	FORMAT([Date], "MMMM")	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	MonthNo	Integer	MONTH([Date])	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Year	Integer	YEAR([Date])	true
LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	Date	Date		true

## Relationships

[ID]	[Name]	[Relationship]	[Model]	[IsActive]	[CrossFilteringBehavior]	[RelyOnReferentialIntegrity]	[FromTable]	[FromColumn]	[FromCardinality]	[ToTable]	[ToColumn]	[ToCardinality]	[State]	[SecurityFilteringBehavior]
2450	AutoDetected_47d2c78f-3915-4351-b30d-fc5f654a65f4	'fact_transactions'[advisor_id] *[<-]1 'dim_advisor'[advisor_id]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_transactions	advisor_id	Many	dim_advisor	advisor_id	One	Ready	Single
3424	AutoDetected_080dc0c9-a847-4102-8fe6-5527ad4e80b2	'fact_transactions'[client_id] *[<-]1 'dim_client'[client_id]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_transactions	client_id	Many	dim_client	client_id	One	Ready	Single
4453	AutoDetected_2f815d05-ddf4-42b9-bf11-303f56a168d6	'fact_transactions'[security_id] *[<-]1 'dim_security'[security_id]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_transactions	security_id	Many	dim_security	security_id	One	Ready	Single
4712	6deec966-5197-f019-8717-87cd3326e62d	'fact_transactions'[txn_date] *[<-]1 'dim_date'[date]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_transactions	txn_date	Many	dim_date	date	One	Ready	Single
2451	AutoDetected_515f758c-a4c4-4e3e-8414-fe1239270ac5	'fact_portfolio_snapshot'[advisor_id] *[<-]1 'dim_advisor'[advisor_id]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_portfolio_snapshot	advisor_id	Many	dim_advisor	advisor_id	One	Ready	Single
2639	AutoDetected_27290db9-48a2-4230-a18e-ac5fca16ab64	'fact_portfolio_snapshot'[benchmark_id] *[<-]1 'dim_benchmark'[benchmark_id]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_portfolio_snapshot	benchmark_id	Many	dim_benchmark	benchmark_id	One	Ready	Single
3425	AutoDetected_8da07bbb-379a-44b4-8620-2cb9df480b79	'fact_portfolio_snapshot'[client_id] *[<-]1 'dim_client'[client_id]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_portfolio_snapshot	client_id	Many	dim_client	client_id	One	Ready	Single
4695	aa81e5e4-13d7-2473-c80b-1050d4fb268e	'fact_portfolio_snapshot'[snapshot_date] *[<-]1 'dim_date'[date]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_portfolio_snapshot	snapshot_date	Many	dim_date	date	One	Ready	Single
2452	AutoDetected_13cb45f8-9f1d-42c6-9326-a4402ef86ceb	'fact_fees'[advisor_id] *[<-]1 'dim_advisor'[advisor_id]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_fees	advisor_id	Many	dim_advisor	advisor_id	One	Ready	Single
3426	AutoDetected_6b7ee019-ebcc-4ab0-a5f6-23016186f549	'fact_fees'[client_id] *[<-]1 'dim_client'[client_id]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_fees	client_id	Many	dim_client	client_id	One	Ready	Single
4678	fbd94a81-c893-0c31-c79a-9a0f84f664a0	'fact_fees'[fee_date] *[<-]1 'dim_date'[date]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	fact_fees	fee_date	Many	dim_date	date	One	Ready	Single
2662	371030ed-f05a-47f6-a233-06998810b983	'dim_client'[client_since] *[<-]1 'LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8'[Date]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	dim_client	client_since	Many	LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8	date	One	Ready	Single
3498	4ef23535-e977-479b-98bc-f80d9c25c9a5	'dim_date'[date] *[<-]1 'LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7'[Date]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	dim_date	date	Many	LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7	date	One	Ready	Single
4454	AutoDetected_031cb484-3962-4004-9c23-08d705a8563e	'dim_security'[benchmark_id] *[<-]1 'dim_benchmark'[benchmark_id]	8ff5b924-11c9-4d5f-96fd-43cc3d57b282	true	OneDirection	false	dim_security	benchmark_id	Many	dim_benchmark	benchmark_id	One	Ready	Single

## Measures

[Table]	[Measure]	[DAX formula]	[FormatString]	[State]
_Measures	Total Fees	SUM ( fact_fees[amount] )		Valid
_Measures	Net Flows	CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" ) - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )		Valid
_Measures	AUM (naive SUM)	SUM ( fact_portfolio_snapshot[aum] )		Valid
_Measures	Ending AUM	CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ) )		Valid
_Measures	Ending Clients	CALCULATE ( DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ), LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ) )		Valid
_Measures	Avg AUM per Client	DIVIDE ( [Ending AUM], [Ending Clients] )		Valid
_Measures	Ending AUM LY	CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )		Valid
_Measures	AUM YoY %	DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] )		Valid
_Measures	Ending AUM PM	CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )		Valid
_Measures	AUM MoM %	DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] )		Valid
_Measures	Avg Monthly AUM	DIVIDE ( SUM ( fact_portfolio_snapshot[aum] ), DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] ) )		Valid
_Measures	Fee Yield (bps)	DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) )		Valid
_Measures	Organic Growth Rate	DIVIDE ( [Net Flows], [Ending AUM LY] )		Valid
_Measures	Top 10 Client Share	VAR Top10Clients = TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM], DESC ) RETURN DIVIDE ( SUMX ( Top10Clients, [Ending AUM] ), [Ending AUM] )		Valid

What the metadata can't tell you:
- Grain: one row of fact_portfolio_snapshot = one client at the start of one month. snapshot_date is always the 1st of the month.
- Additivity: aum is a balance (semi-additive, so summing across months is wrong). active_alpha_ytd is a year-to-date return (a rate, so it is non-additive).
- dim_date is marked as the date table and filters fact_portfolio_snapshot. Existing measures are in a _Measures table. [Ending AUM] uses LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ) to find the last snapshot date.

Business definition (measure 9, "AUM-Weighted Alpha"): active_alpha_ytd weighted by aum, at the last snapshot in the current filter, excluding rows where is_return_suspect = 1.

Please give me:
1. The DAX measure, using only table and column names from my metadata
2. A plain-English explanation of its filter context: how the last-snapshot logic works in a table by dim_date[year], in a table by dim_client[client_tier] filtered to 2024, and at the grand total
3. A DAX test query (EVALUATE ...) I can run in DAX query view that returns the measure at the grand total and by dim_date[year]
````

---

## Claude's full response

Here’s the measure, how it behaves in each visual, and a test query.

1. The measure

```dax
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

Put it in _Measures and format it as a percentage.

What each part does:

LastSnapshot: This is the same logic as your [Ending AUM]. It goes through the dates visible in the current filter and keeps the last one that has at least one snapshot row. The CALCULATE inside is what makes it check each date one at a time.
SUMX(... alpha * aum): This multiplies each client’s alpha by that client’s AUM, row by row, and then adds the results. A $10M client counts 10 times as much as a $1M client.
/ SUM(aum): Dividing by total AUM turns the weighted sum back into a rate. DIVIDE returns blank instead of an error if the AUM is 0.
CALCULATE(..., LastSnapshot, ...): This limits both the top and bottom of the division to that one snapshot date. It’s how the measure handles both problems in your notes:
AUM is semi-additive, so it shouldn’t be summed across months.
YTD alpha is a rate, so it shouldn’t be summed at all.
is_return_suspect <> 1: This drops suspect rows from both the top and bottom. If you only dropped them from the top, the average would be pulled toward zero. Using <> 1 instead of = 0 also keeps any blank flags.
Common mistakes this avoids:

SUM(alpha) * SUM(aum) multiplies the totals, not each row.
AVERAGE(active_alpha_ytd) weights every client equally.
Leaving out the last-snapshot filter averages 12 months of YTD figures together, which means nothing.
One design choice to know about: the last date is found before the suspect filter is applied. That keeps this measure on the same date as [Ending AUM]. The side effect is that if every row on that date were suspect, you’d get a blank instead of falling back to an earlier month. I think that’s the right behavior, because silently reporting a stale month would be worse. Also, its denominator is non-suspect AUM only, so it won’t match [Ending AUM] exactly. That’s expected.

2. How the filter context works
Table by dim_date[Year]

Each row filters dim_date to one year. LASTNONBLANK finds the last date in that year with snapshots, which is normally Dec 1.
Each row is the weighted alpha of every client on that date.
For a year that isn’t complete in your data, it’s whatever month was loaded last.
Because snapshots are taken on the 1st, the “Dec 1” figure reflects YTD performance going into December, not a true full-year number.
Table by dim_client[client_tier], filtered to 2024

Each row has two filters: year = 2024 and tier = (that tier).
The COUNTROWS check inside LASTNONBLANK sees both filters. So it finds the last 2024 date where that tier has snapshot rows. In practice that’s probably Dec 1, 2024 for every tier, but it’s worked out separately for each tier.
Only clients who have a row on that date are included. A client who left in June 2024 has no Dec 1 row, so they don’t count.
The total row (all tiers, 2024) is the weighted alpha across all clients on the last 2024 date. It’s not an average of the tier rows. It’s recalculated from scratch, which gives the correct AUM-weighted result.
Grand total (no filters)

LASTNONBLANK looks at the whole date table and picks the latest snapshot in the entire dataset.
So the grand total is the most recent month’s alpha, not an average across years.
This is the part people most often get wrong. In your by-year table, the total will equal the latest year’s row, not the average of all the rows. That’s correct, because a balance-weighted, year-to-date figure only makes sense at a single point in time.
3. Test query
Paste this into DAX query view. The DEFINE line means it works even before you’ve added the measure to the model. The “Last Snapshot” column lets you check which date each row actually used.


```dax
DEFINE
    MEASURE _Measures[AUM-Weighted Alpha] =
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

-- Grand total
EVALUATE
ROW (
    "Last Snapshot", MAX ( fact_portfolio_snapshot[snapshot_date] ),
    "AUM-Weighted Alpha", [AUM-Weighted Alpha]
)

-- By year
EVALUATE
SUMMARIZECOLUMNS (
    dim_date[Year],
    "Last Snapshot", MAX ( fact_portfolio_snapshot[snapshot_date] ),
    "AUM-Weighted Alpha", [AUM-Weighted Alpha]
)
ORDER BY dim_date[Year]
```

You’ll get two result tabs. Check two things:

Each year’s “Last Snapshot” should be Dec 1 of that year, except possibly the latest year.
The grand-total value should exactly match the latest year’s row.
If both are true, the last-snapshot logic is working.

---

## Appendix: earlier attempt (sent without metadata)

My first try accidentally sent the prompt with a `[PASTE model_metadata.md HERE]` placeholder instead of the metadata. I kept the response for transparency. It drafted an equivalent measure (a `CALCULATETABLE` of clean rows, filtered with `is_return_suspect <> 1`), but I used the session above because that prompt had the full metadata.

<details>
<summary>Attempt 1 response</summary>

The metadata didn’t come through (only the placeholder did), so I checked the column names in the copy of hw06 that’s open in Apporto. fact_portfolio_snapshot has aum, active_alpha_ytd, is_return_suspect, snapshot_date and client_id. I didn’t change anything in the file.

1. The measure
DAX
AUM-Weighted Alpha =
VAR LastSnap =
    LASTNONBLANK (
        dim_date[date],
        CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) )
    )
VAR CleanRows =
    CALCULATETABLE (
        fact_portfolio_snapshot,
        LastSnap,
        fact_portfolio_snapshot[is_return_suspect] <> 1
    )
RETURN
    DIVIDE (
        SUMX ( CleanRows, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
        SUMX ( CleanRows, fact_portfolio_snapshot[aum] )
    )

Put it in _Measures and format it as a percentage (0.00%).

What each part does:

LastSnap uses the same logic as [Ending AUM]. It finds the latest date in the current filter that has snapshot rows. This keeps both measures pointing at the same month.
CleanRows keeps only the rows on that one date where is_return_suspect isn’t 1. Using <> 1 instead of = 0 means blank flags stay in.
DIVIDE is the weighted average: sum of (AUM × alpha) divided by sum of AUM. Bigger accounts count more.

Common mistakes this avoids:

Don’t use [Ending AUM] as the denominator. It includes the suspect rows, so the weights wouldn’t match the numerator and the result would be too small.
Don’t use SUM or AVERAGE on alpha. Alpha is a rate, so adding it up is meaningless, and a plain average treats a $10K account the same as a $50M one.
Don’t drop the LastSnap filter. Without it you’d be weighting across every month, which double-counts AUM, since AUM is a balance.

One judgment call: I find the last snapshot using all rows, then remove the suspect ones. If a month were 100% suspect, you’d get BLANK instead of falling back to an earlier month. I think that’s the more honest behavior. Separately, if some rows have AUM but a blank alpha, they still count in the denominator and pull the result toward 0. If you’d rather drop them, add NOT ISBLANK ( fact_portfolio_snapshot[active_alpha_ytd] ) as another filter in CleanRows.

2. How the filter context plays out

The key idea is that LastSnap gets worked out separately for each cell, using whatever filters that cell has.

Table by dim_date[year]: Each row only sees dates in that year, so LastSnap lands on that year’s last snapshot (probably Dec 1). Each row is that year’s year-to-date alpha as of its last month. It’s one month in time, not an average over the year.
Table by dim_client[client_tier], filtered to 2024: The year filter limits dates to 2024, and the tier filters rows through dim_client. LastSnap is found within that tier’s own rows, so normally every tier lands on the same last 2024 month. Each row is the weighted alpha of only that tier’s clients. The Total row is not the average of the three tiers. It re-weights all clients together, so UHNW (most of the AUM) dominates it. It should match the 2024 row in the year table.
Grand total (no filters): LastSnap is the latest snapshot in the whole dataset. Your Ending AUM total matched the 2024 row, so this total should match the 2024 row too. That’s expected, not a bug.
3. Test query

This defines the measure inside the query itself, so you can test it before adding it to the model. Paste the whole thing into a new DAX query tab and run it:

DAX
DEFINE
    MEASURE _Measures[AUM-Weighted Alpha] =
        VAR LastSnap =
            LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
        VAR CleanRows =
            CALCULATETABLE (
                fact_portfolio_snapshot,
                LastSnap,
                fact_portfolio_snapshot[is_return_suspect] <> 1
            )
        RETURN
            DIVIDE (
                SUMX ( CleanRows, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
                SUMX ( CleanRows, fact_portfolio_snapshot[aum] )
            )

EVALUATE
ROW ( "AUM-Weighted Alpha (Grand Total)", [AUM-Weighted Alpha] )

EVALUATE
SUMMARIZECOLUMNS (
    dim_date[year],
    "Last Snapshot", CALCULATE ( MAX ( fact_portfolio_snapshot[snapshot_date] ) ),
    "AUM-Weighted Alpha", [AUM-Weighted Alpha]
)
ORDER BY dim_date[year]

You’ll get “Result 1 of 2” and “Result 2 of 2” in the dropdown above the results grid.

What to check:

The Last Snapshot column shows which month each year used, so you can confirm the last-snapshot logic.
The grand total should equal the 2024 row.

If you want to check the tier view too, add this third block at the end:

DAX
EVALUATE
SUMMARIZECOLUMNS (
    dim_client[client_tier],
    TREATAS ( { 2024 }, dim_date[year] ),
    "AUM-Weighted Alpha", [AUM-Weighted Alpha]
)

Once the numbers look right, create the measure in _Measures with the same formula. If the model already has a measure with that name, remove the DEFINE block before running the query, or you’ll get a duplicate-name error.

</details>
