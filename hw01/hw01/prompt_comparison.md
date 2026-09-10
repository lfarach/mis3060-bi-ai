# Prompt Engineering Comparison

**Question used:** What are the most important metrics for measuring credit risk in a consumer loan portfolio?

---

## Strategy 1 — Zero-shot

**Prompt:**


**First 150 words of response:**
The most important credit risk metrics fall into a few categories: borrower-level indicators like credit score, debt-to-income ratio, and income stability; portfolio-level indicators like delinquency rate, default rate, and loss given default; and forward-looking indicators like probability of default and expected loss. Credit score gives a broad risk ranking, DTI shows how much of a borrower's income is already committed to debt, and income verification confirms repayment capacity. At the portfolio level, tracking delinquency (30/60/90-day buckets) helps catch early warning signs before loans move to default. Concentration risk also matters — how exposed the portfolio is to a single loan type, geography, or borrower segment.

**Evaluation:** This response was accurate and covered the right categories of metrics, but it read like a general textbook answer — it wasn't tailored to Wildcat, a lending audience, or any specific use case. It listed metrics without prioritizing which ones matter most or explaining how they'd actually be used in a decision-making context. Good starting point, but generic.

---

## Strategy 2 — Role-assigned

**Prompt:**

**First 150 words of response:**
Similar substance, but framed around what a committee needs to act on: leads with portfolio-level default and delinquency rates, then loss given default and net charge-offs, and explicitly ties each metric to a decision (for example, noting that rising delinquency in Business loans might prompt tighter underwriting standards). More audience-aware — less definitional, more decision-oriented.

**Evaluation:** Assigning the role and audience made a real difference — the response shifted from "here's what these metrics are" to "here's what you should do about them." It prioritized the metrics a committee would actually care about first, rather than listing everything equally. What was still missing was any reference to Wildcat's actual loan-purpose mix or specific numbers, since I didn't ask it to pull from the data.

---

## Strategy 3 — Few-shot

**Prompt:**

**First 150 words of response:**
Same underlying content as the zero-shot version, but reformatted — bolded metric names, each broken into "What it measures," "Why it matters," and a benchmark line (for example, noting that a debt-to-income ratio above roughly 43% is generally considered high risk).

**Evaluation:** This strategy didn't improve the substance of the answer at all — it was essentially the zero-shot content reorganized. What it did well was make the response scannable and dashboard-ready, which is actually useful for a BI analyst who needs to hand something off or build a slide. The tradeoff is it added structure without adding insight or business context.

---

## Conclusion

The role-assigned strategy produced the most useful output for a BI analyst, because it reframed the same underlying knowledge around an actual decision-maker's priorities rather than just listing facts. The zero-shot response was accurate but generic, and the few-shot response only changed formatting, not substance. For a real analyst task, the best approach is probably combining strategies: assign a role and audience to shape what gets emphasized, and provide a format to shape how it's presented. Formatting alone, without context, doesn't add much value on its own.

---

## Fact-Check

**Claim:** "A debt-to-income ratio above roughly 43% is generally considered high risk."

**Source:** Consumer Financial Protection Bureau (CFPB), "Consumer Financial Protection Bureau Issues Two Final Rules to Promote Access to Responsible, Affordable Mortgage Credit," consumerfinance.gov — https://www.consumerfinance.gov/about-us/newsroom/consumer-financial-protection-bureau-issues-two-final-rules-promote-access-responsible-affordable-mortgage-credit/

**What the source says:** The 43% DTI threshold originated from the Qualified Mortgage rule under Dodd-Frank, which required a back-end DTI of 43% or less for a mortgage to receive safe-harbor legal protection. In 2021, the CFPB actually replaced this hard 43% cap with a price-based standard (comparing a loan's APR to the average prime offer rate), partly because the DTI cap was found to restrict credit access for otherwise qualified borrowers. So 43% is no longer an official regulatory cutoff, but it remains a widely used industry rule of thumb.

**Do they agree?** Partially. Claude's claim wasn't wrong, but it was outdated and oversimplified — it presented 43% as a current, hard risk threshold, when the actual regulatory standard changed years ago and lenders now use it more as an informal benchmark than a real cutoff. This shows a broader pattern: Claude's numeric/regulatory claims can be directionally correct but need verification, since they may reflect an older rule that's no longer technically in force. For a BI analyst, this is exactly the kind of claim that should never go into a report without checking the primary source first.
