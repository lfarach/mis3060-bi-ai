# Business Context Exploration

## Question 1
**Prompt:** Wildcat's loan data includes credit score, debt-to-income ratio, and annual income for each borrower. In consumer lending, how do these three metrics typically get used together to assess risk, rather than looking at any one of them alone?

**Summary:** 1. Credit risk metrics (credit score, DTI, income together)
Credit score is backward-looking — it tells you whether this person has historically paid debts on time. DTI is a capacity check — how much of their income is already committed to debt payments right now. Income gives scale to that ratio, since a 40% DTI means something very different for someone earning $250K versus $35K. Lenders combine all three because each one alone can mislead: a high score with rising DTI signals a borrower getting overextended before their score reflects it, so underwriting models or tiered rules (credit score cutoffs × DTI thresholds) blend them rather than screening on any single one.

**Follow-up question:** How does Wildcat's underwriting actually weigh score vs. DTI?
---

## Question 2
**Prompt:** Wildcat's portfolio is split across five loan purposes — Auto, Personal, Home Improvement, Education, and Business. What would a portfolio committee typically want to see broken out by loan purpose in a quarterly review, and why does that breakdown matter more than looking at the portfolio as a whole?

**Summary:** Portfolio committee breakdown by loan purpose
A committee would want default/delinquency rates, average interest rate, average loan size, and total dollar exposure broken out separately for each of the five purposes, not just portfolio-wide averages. That's because purposes behave very differently — Business loans are larger and carry business-specific risk, Auto loans are secured by collateral, and Education loans (per Wildcat's data) show the highest DTI among defaults. A single blended number can hide a concentration problem — for example, a business could be quietly loading risk into one category while the overall portfolio still "looks fine" on average. Breaking it out is how leadership catches where the actual risk is building before it shows up in the aggregate numbers.

**Follow-up question:** Which loan purpose has the worst combo of default rate and exposure?

---

## Question 3
**Prompt:** Wildcat classifies loans into four statuses: Current, Paid Off, Default, and Delinquent. What's the actual difference between delinquency and default in consumer lending, and at what point does a loan typically move from one to the other?

**Summary:** 3. Delinquency vs. default
Delinquency means a payment is late but the loan is still considered active and recoverable — typically starting at 30, 60, or 90 days past due, with lenders still expecting the borrower to catch up. Default is a more severe classification, usually triggered after a loan has been delinquent for an extended period (often 90-180+ days, depending on the lender's policy and loan type) with no realistic expectation of the borrower bringing it current. Think of delinquency as "behind but still in the game" and default as "the lender no longer expects to be paid as originally agreed" — at that point the loan typically moves to collections, charge-off, or write-down. Not every delinquent loan becomes a default (many cure), but essentially every default passes through delinquency first.

**Follow-up question:** What days-past-due split does Wildcat use for Delinquent vs. Default?

---

## Question 4
**Prompt:** Business loans in Wildcat's portfolio tend to be larger than Auto or Personal loans. What credit risk considerations are specific to Business lending that wouldn't apply the same way to Auto or Personal loans?

**Summary:** Business loans — risk considerations specific to them
Business loans depend on the health and cash flow of an operating entity, not just an individual's paycheck, so lenders have to assess business revenue stability, industry risk, and how sensitive that business is to economic cycles — none of which applies to a personal Auto loan. They're also larger and often less standardized, meaning outcomes are more concentrated (losing one large business loan hurts more than losing one Personal loan) and harder to model with simple credit-score-based rules. Collateral and personal guarantees matter differently too, since a business loan might be backed by equipment, receivables, or the owner's personal assets rather than a straightforward asset like a car title. Finally, business borrowers are more exposed to conditions outside their personal financial history — a downturn in their specific industry can sink an otherwise creditworthy borrower.

**Follow-up question:** Are Wildcat's Business loans priced high enough for their risk?

---

## Question 5
**Prompt:** If Wildcat's Delinquent loans are concentrated in the Education category, what business or macroeconomic factors might explain that, and how should a BI analyst flag that pattern to leadership without overstating what the data alone can prove?

**Summary:** Delinquent loans concentrated in Education — factors and how to flag it
If Delinquent loans cluster in Education, plausible drivers include weaker post-graduation income relative to loan size, deferment/grace-period timing mismatches, or macro factors like a soft job market for recent grads — Wildcat's own data already shows Education loans running the highest DTI among defaults, which fits this story. As a BI analyst, the right move is to present the pattern as a correlation worth investigating, not a proven cause — say "Education loans show elevated delinquency and DTI; this warrants review of underwriting criteria for that segment" rather than asserting why it's happening. Recommend a concrete next step (e.g., segment DTI and income data further, or compare against external labor-market data) rather than letting the chart imply a conclusion the data can't support on its own. That distinction — flagging a pattern versus claiming causation — is exactly what separates a credible analyst from one whose findings get challenged in the room.

**Follow-up question:** How does DTI differ between Delinquent and Current Education loans?
