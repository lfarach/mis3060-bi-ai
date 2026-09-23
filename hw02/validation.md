# HW2 Validation: fact_transactions.csv

## Part 1C: Script Run Notes

The script `hw02/hw02_eda.py` ran without errors on the first try.

One environment issue came up before running it: `verify_setup.py` reported that pandas, matplotlib, and seaborn failed with "DLL load failed ... An Application Control policy has blocked this file." This was Windows Smart App Control blocking the newly installed library files. I turned Smart App Control off, reopened VS Code, and `verify_setup.py` then reported 14/14 libraries OK.

---

## 2A: Known-Answer Benchmarks

| Check | Expected | Your Script Produced | Match? | Notes |
|---|---|---|---|---|
| Dataset shape | (298772, 9) | (298772, 9) | Yes | Shape warning did not trigger |
| Null count — `security_id` | 101,597 | 101,597 | Yes | `shares` and `price` also have exactly 101,597 nulls |
| Null count — `amount` | 0 | 0 | Yes | |
| Unique `txn_type` values | 6 | 6 | Yes | Buy, Sell, Dividend, Deposit, Advisory Fee, Withdrawal |
| Count of `Buy` transactions | 83,556 | 83,556 | Yes | 27.97% of all rows |
| `txn_date` data type | object | str | Yes (same meaning) | pandas 3.0 labels text columns `str` instead of `object`. Either way the dates are stored as text, not as a date type. See note below. |
| Earliest `txn_date` | 2020-01-01 | 2020-01-01 | Yes | |
| Latest `txn_date` | 2024-12-30 | 2024-12-30 | Yes | |
| Duplicate `txn_id` count | 0 | 0 | Yes | |
| Mean `amount` | $54,075.17 | $54,075.17 | Yes | |
| Median `amount` | $41,220.48 | $41,220.49 | Yes (rounding) | Off by one cent. The true median is the average of the two middle values and likely ends in a half cent, so it rounds differently. See note below. |
| Skewness of `amount` | 1.15 | 1.15 | Yes | Right-skewed; mean > median |
| Correlation `shares`–`amount` | 0.65 | 0.65 | Yes | Strongest correlation |
| Correlation `price`–`amount` | 0.64 | 0.64 | Yes | |
| Correlation `shares`–`price` | 0.00 | 0.00 | Yes | No relationship |
| Negative `shares` count (Buy only) | 836 | 836 | Yes | All 836 are Buy; min = −499.63 |
| Profile file created | Yes | Yes | Yes | `hw02/hw02_profile.txt` |
| Chart files created (3) | Yes | Yes | Yes | All three PNGs in `hw02/charts/` |

### Discrepancy notes

**`txn_date` type (object vs. str):** Not a real mismatch. When I asked Claude (new session) to predict the output, it said: "txn_date shows str in pandas 3.0; older versions called it object. Either way, the dates are stored as text." I'm on pandas 3.0.6, which uses a dedicated string type by default. The important part of the benchmark still holds: the column is text, not a datetime.

**Median $41,220.48 vs. $41,220.49:** My script actually prints both values: 41,220.48 in the describe() table (Section 4) and $41,220.49 in Section 9. Claude (new session) explained it: "The true median is exactly 41,220.485, the average of the two middle values (41,219.90 and 41,221.07). The computer stores it as a hair above .485. The f-string here rounds that normally, up to .49. describe().round(2) uses NumPy's rounding, which ... sees an exact half, and rounds to the even number, .48. So neither value is wrong; they're two rounding rules." So this is a rounding difference, not a bug.

---

## 2B: Explain the Code and Output (new Claude session)

1. Did Claude's predicted outputs match what I saw in the terminal?
   Yes. Every value Claude predicted matched my terminal output exactly: shape, nulls, type counts, unique counts, date range, grouping table, correlations, and the 836 negative shares. It even predicted the one spot where two numbers disagree (median shows 41,220.48 in describe() but $41,220.49 in Section 9) and explained it was two different rounding rules, not an error. The only other "difference" from the benchmark was txn_date showing `str` instead of `object`, which Claude said is just how pandas 3.0 labels text.

2. What did Claude flag as unexpected or worth investigating?
   - **836 negative-share Buys (biggest flag):** the amount on these rows is still positive and equals |shares| × price, so the minus sign only exists in shares. They're spread across all 25 advisors, 692 clients, and every year, which looks more like a systemic sign error than real reversals.
   - **Dividend amounts look way too big:** Dividends have the highest average amount ($64,077), and the amount equals shares × price. That's the value of the position, not a dividend payment.
   - **Advisory fees are very spread out:** median $859 but mean $7,375, with some fees over $140K.
   - **txn_date stored as text.**
   - Smaller things: client_id goes up to 3,192 but only 2,700 are used, the data ends Dec 30 (Dec 31, 2024 was a business day), and transaction volume changes a lot by year (about 42K in 2020 vs. 73K in 2023).

3. Did Claude mention the 101,597 nulls in `security_id`? What explanation did it give?
   Yes. It said they are probably fine: they come from exactly three types, Deposit (35,981) + Advisory Fee (35,766) + Withdrawal (29,850) = 101,597. Those are cash movements with no stock involved, so there's no security, shares, or price. It still warned that these nulls affect averages (the shares and price means only cover trades and dividends), so you should filter by transaction type instead of blindly dropping nulls.

4. Did Claude flag `txn_date` as a concern? Why does it matter for time-series analysis?
   Yes. Sorting and min/max happen to work because the dates are in YYYY-MM-DD format. But as text, you can't subtract dates, group by month or quarter, or calculate days between transactions. Any time-series analysis (like monthly trends) needs `pd.to_datetime()` first.

5. Do the three charts match Claude's explanation?
   Yes, all three matched.
   - **Histogram:** tall pile on the left and a long tail out to about $250K, with the red mean line (~$54K) to the right of the orange median line (~$41K). That's right skew. One thing Claude didn't mention: there's a visible drop in bar height right at $100K.
   - **Box plot:** Dividend, Buy, and Sell look almost identical with lots of outliers on the right. Deposit and Withdrawal are similar to each other and stop at about $100K (which explains the drop in the histogram). Advisory Fee is squashed against the left.
   - **Scatter:** only Buy, Dividend, and Sell appear, in a fan shape. There's a mirror-image group of Buy points to the left of zero that still have positive amounts. Those are the 836 negative-share rows.

6. Follow-up question I asked and Claude's answer:

   **My question:** "For flag #2, is it typical for a dividend transaction's amount to equal shares × price? What would a realistic dividend payment look like for a position of that size? Cite a source."

   **Claude's answer (summary):** No. A dividend payment is shares × dividend per share, not shares × share price. Shares × price is the market value of the position. Dividend yield (annual dividends per share ÷ share price) is the standard measure (Fidelity), and the S&P 500 yield during 2020–2024 was about 1.24% to 1.71% (Multpl). For the median Dividend row ($48,805.60), a 1.5% yield gives about $732 a year, or about $183 per quarterly payment. Even at a 4% yield it would be about $488 per quarter. So the recorded amounts are roughly 100–270× too large. Every one of the 53,864 Dividend rows has amount = shares × price, so the system likely used the same formula for all security transactions. Totals that include dividends (including the overall $54,075 mean) are inflated, so dividend amounts should be excluded from money totals or clearly flagged.

   Sources: Fidelity, "Dividend yield: What it is and how to calculate it"; Multpl, "S&P 500 Dividend Yield by Year".

---

## 2C: Business Check & Cross-Validation

### Business-reasonableness questions (my own words)

1. Which three transaction types have no security? Do the counts add up to 101,597?
   1. Deposits, withdrawals, and advisory fees don't have a security listed because they aren't trades. It's just money being added or taken out of an account, or a fee being charged. Since no stock is involved, there wouldn't be a security ID, number of shares, or price. The numbers also add up: 35,981 + 29,850 + 35,766 = 101,597.

2. What does having more Buys (83,556) than Sells (59,755) mean?
   2. More buys than sells probably means clients are investing their money and keeping it invested instead of selling it. That seems like a good sign for the firm because it could mean the amount of money it manages is growing. There are also more deposits than withdrawals, which supports the idea that more money is coming in than going out.

3. What goes wrong if `txn_date` stays a string when computing average days between transactions?
   3. If the dates are stored as strings, Python treats them like words instead of dates. That means subtracting them to find the number of days between transactions wouldn't work correctly. I would first use pd.to_datetime() to turn the column into actual dates, and then do the calculation.

4. Is ~108 clients per advisor plausible?
   4. I think 108 clients per advisor sounds pretty reasonable. An advisor might have around 50 to 150 clients, depending on how much attention each client needs and whether the advisor has a support team. Since 108 is in that range, I wouldn't see it as a problem by itself.

5. Two explanations for 836 negative-share Buys, and what I'd do next:
   5. The negative shares on Buy transactions could just be a mistake where the minus sign was entered accidentally. They could also be corrections that cancel out earlier buys. I think a sign mistake is more likely because the dollar amounts are still positive. To check, I'd look for an earlier Buy with the same client, security, and number of shares. If there's a matching transaction, the negative one could be a reversal. If there isn't, it's probably an error.

### Cross-validation

6. What did each script return?
   Prompt A (`hw02/crossval_a.py`, direct filter) returned **83,556**. Prompt B (`hw02/crossval_b.py`, total rows minus non-Buy rows) returned 298,772 − 215,216 = **83,556**.

7. Do they agree?
   Yes, both gave 83,556, which also matches the benchmark. So neither one is wrong.

8. Why verify a count using subtraction?
   Subtraction checks the same number from a totally different direction. If the data had something messy like "buy" or "Buy " with an extra space, the direct filter would skip those rows, but the subtraction method would still count them as Buys since they aren't in the other five categories. Then the two numbers wouldn't match and I'd know something was off. Since they matched, it tells me there are no hidden typos or extra categories in txn_type.
