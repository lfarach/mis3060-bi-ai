"""
01_reconcile_measures.py  -  HW6 Part B: reconcile every DAX measure to pandas

What it does:
  1. Recomputes each HW6 measure in pandas straight from the Wildcat Capital
     Clean CSVs. Nothing here reads from Power BI.
  2. Reads the Power BI numbers from reports/powerbi_values.csv
     (columns: measure, slice, value), exported from DAX query view.
  3. Writes reports/measure_reconciliation.csv with
     measure, slice, powerbi_value, pandas_value, abs_diff, match

Tolerance: 0.01 for currency, 0.0001 for ratios (%, bps), exact for counts and text.
A blank on BOTH sides counts as a match (e.g. 2020 has no prior year).

How to run (from the repo root):
    python hw06/scripts/01_reconcile_measures.py
    python hw06/scripts/01_reconcile_measures.py "C:/MIS3060/Wildcat Capital Clean"

Exit code is 0 if every row matches, 1 if any row doesn't.
"""

import sys
from pathlib import Path

import pandas as pd

HW_DIR = Path(__file__).resolve().parent.parent          # .../hw06
REPORTS = HW_DIR / "reports"
DEFAULT_DATA = HW_DIR.parent.parent / "Wildcat Capital Clean"  # C:/MIS3060/Wildcat Capital Clean
DATA_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA


# ---------------------------------------------------------------------------
# 1. Load the CSVs
# ---------------------------------------------------------------------------
def find_csv(name):
    """Find name.csv, allowing for browser download copies like 'name (1).csv'."""
    for candidate in [DATA_DIR / f"{name}.csv", *sorted(DATA_DIR.glob(f"{name} (*).csv"))]:
        if candidate.exists():
            return candidate
    sys.exit(
        f"Can't find {name}.csv in {DATA_DIR}\n"
        'Pass the folder with the Wildcat Capital Clean CSVs, e.g.\n'
        '    python hw06/scripts/01_reconcile_measures.py "C:/MIS3060/Wildcat Capital Clean"'
    )


snap = pd.read_csv(find_csv("fact_portfolio_snapshot"), parse_dates=["snapshot_date"])
fees = pd.read_csv(find_csv("fact_fees"), parse_dates=["fee_date"])
txns = pd.read_csv(find_csv("fact_transactions"), parse_dates=["txn_date"])
clients = pd.read_csv(find_csv("dim_client"))
dates = pd.read_csv(find_csv("dim_date"), parse_dates=["date"])

# Attach client_tier to each fact (same path as the model: fact -> dim_client)
tier_of = clients.set_index("client_id")["client_tier"]
for fact in (snap, fees, txns):
    fact["client_tier"] = fact["client_id"].map(tier_of)


# ---------------------------------------------------------------------------
# 2. A "filter context" = a date range (from dim_date) plus an optional tier.
#    Each helper below mimics one DAX measure under that filter.
# ---------------------------------------------------------------------------
class Ctx:
    def __init__(self, start, end, tier=None):
        self.start, self.end, self.tier = pd.Timestamp(start), pd.Timestamp(end), tier

    def shift(self, **offset):
        """SAMEPERIODLASTYEAR / DATEADD: move the date range, keep the tier."""
        off = pd.DateOffset(**offset)
        return Ctx(self.start + off, self.end + off, self.tier)


def rows(df, date_col, ctx):
    """Rows of a fact table visible in this filter context."""
    keep = df[date_col].between(ctx.start, ctx.end)
    if ctx.tier is not None:
        keep &= df["client_tier"] == ctx.tier
    return df[keep]


def last_snapshot_rows(ctx, frame=None):
    """LASTNONBLANK: rows on the latest snapshot date that has data in this context."""
    s = rows(snap, "snapshot_date", ctx) if frame is None else frame
    if s.empty:
        return s
    return s[s["snapshot_date"] == s["snapshot_date"].max()]


def blank_if_empty(series_sum, frame):
    return None if frame.empty else series_sum


# Additive measures
def total_fees(ctx):
    f = rows(fees, "fee_date", ctx)
    return blank_if_empty(f["amount"].sum(), f)


def net_flows(ctx):
    t = rows(txns, "txn_date", ctx)
    dep = t.loc[t["txn_type"] == "Deposit", "amount"].sum()
    wd = t.loc[t["txn_type"] == "Withdrawal", "amount"].sum()
    return blank_if_empty(dep - wd, t)


def aum_naive_sum(ctx):  # Measure 0: the trap. Sums balances across months.
    s = rows(snap, "snapshot_date", ctx)
    return blank_if_empty(s["aum"].sum(), s)


# Semi-additive (last balance)
def ending_aum(ctx):
    last = last_snapshot_rows(ctx)
    return blank_if_empty(last["aum"].sum(), last)


def ending_clients(ctx):
    last = last_snapshot_rows(ctx)
    return blank_if_empty(last["client_id"].nunique(), last)


def ending_aum_ly(ctx):
    return ending_aum(ctx.shift(years=-1))


def ending_aum_pm(ctx):
    return ending_aum(ctx.shift(months=-1))


# Non-additive (recompute from parts)
def divide(num, den):
    """DAX DIVIDE: blank if either side is blank or the denominator is 0."""
    if num is None or den is None or den == 0:
        return None
    return num / den


def avg_aum_per_client(ctx):
    return divide(ending_aum(ctx), ending_clients(ctx))


def aum_yoy(ctx):
    cur, ly = ending_aum(ctx), ending_aum_ly(ctx)
    return None if cur is None else divide(cur - ly if ly is not None else None, ly)


def aum_mom(ctx):
    cur, pm = ending_aum(ctx), ending_aum_pm(ctx)
    return None if cur is None else divide(cur - pm if pm is not None else None, pm)


def avg_monthly_aum(ctx):
    s = rows(snap, "snapshot_date", ctx)
    return divide(s["aum"].sum(), s["snapshot_date"].nunique()) if not s.empty else None


def fee_yield_bps(ctx):
    tf = total_fees(ctx)
    s = rows(snap, "snapshot_date", ctx)
    return divide(tf * 12 * 10_000 if tf is not None else None, s["aum"].sum() if not s.empty else None)


def organic_growth(ctx):
    return divide(net_flows(ctx), ending_aum_ly(ctx))


def aum_weighted_alpha(ctx, include_suspect=False):
    # Last date is found on ALL rows first, then suspect rows are dropped (same as the DAX)
    last = last_snapshot_rows(ctx)
    if not include_suspect:
        last = last[last["is_return_suspect"] != 1]
    if last.empty:
        return None
    return divide((last["aum"] * last["active_alpha_ytd"]).sum(), last["aum"].sum())


def alpha_signal(ctx):
    a = aum_weighted_alpha(ctx)
    if a is None:
        return None
    if a >= 0.02:
        return "Outperforming"
    if a <= -0.02:
        return "Lagging"
    return "In line"


def ending_aum_by_client(ctx):
    """[Ending AUM] evaluated once per client: each client's OWN last snapshot in the context."""
    s = rows(snap, "snapshot_date", ctx)
    last_date = s.groupby("client_id")["snapshot_date"].transform("max")
    return s[s["snapshot_date"] == last_date].groupby("client_id")["aum"].sum()


def top10_share(ctx):
    per_client = ending_aum_by_client(ctx)
    return divide(per_client.nlargest(10).sum(), ending_aum(ctx))


MEASURES = {
    "Total Fees": total_fees,
    "Net Flows": net_flows,
    "AUM (naive SUM)": aum_naive_sum,
    "Ending AUM": ending_aum,
    "Ending Clients": ending_clients,
    "Avg AUM per Client": avg_aum_per_client,
    "Ending AUM LY": ending_aum_ly,
    "AUM YoY %": aum_yoy,
    "Ending AUM PM": ending_aum_pm,
    "AUM MoM %": aum_mom,
    "Avg Monthly AUM": avg_monthly_aum,
    "Fee Yield (bps)": fee_yield_bps,
    "Organic Growth Rate": organic_growth,
    "AUM-Weighted Alpha": aum_weighted_alpha,
    "Alpha Signal": alpha_signal,
    "Top 10 Client Share": top10_share,
}

# Tolerance by measure type
CURRENCY = {"Total Fees", "Net Flows", "AUM (naive SUM)", "Ending AUM", "Avg AUM per Client",
            "Ending AUM LY", "Ending AUM PM", "Avg Monthly AUM"}
COUNT = {"Ending Clients"}
TEXT = {"Alpha Signal"}


def tolerance(measure):
    if measure in CURRENCY:
        return 0.01
    if measure in COUNT:
        return 0
    return 0.0001  # ratios: %, bps, alpha, share


# ---------------------------------------------------------------------------
# 3. Slices: map each slice label in powerbi_values.csv to a filter context
# ---------------------------------------------------------------------------
ALL = Ctx(dates["date"].min(), dates["date"].max())


def ctx_for(slice_label):
    if slice_label == "Grand Total":
        return ALL
    if slice_label.startswith("Year "):
        y = int(slice_label.split()[1])
        return Ctx(f"{y}-01-01", f"{y}-12-31")
    if slice_label.startswith("Tier 2024 "):
        return Ctx("2024-01-01", "2024-12-31", tier=slice_label.replace("Tier 2024 ", ""))
    if slice_label.startswith("Month "):
        y, m = map(int, slice_label.split()[1].split("-"))
        start = pd.Timestamp(y, m, 1)
        return Ctx(start, start + pd.offsets.MonthEnd(0))
    raise ValueError(f"Unknown slice: {slice_label}")


# ---------------------------------------------------------------------------
# 4. Compare to Power BI
# ---------------------------------------------------------------------------
pbi = pd.read_csv(REPORTS / "powerbi_values.csv", dtype={"value": str}, keep_default_na=False)
pbi.columns = [c.strip("[] ") for c in pbi.columns]
for col in ("measure", "slice", "value"):
    pbi[col] = pbi[col].str.strip()

# Coverage check: the Power BI export must have exactly the rows Part B asks for.
# Built here from the requirements, not from the CSV, so a dropped or duplicated row fails.
YEARS = [f"Year {y}" for y in range(2020, 2025)]
TIERS = [f"Tier 2024 {t}" for t in ("HNW", "Retail", "UHNW")]
EXPECTED = (
    [(m, "Grand Total") for m in MEASURES]                                    # every measure
    + [(m, s) for s in YEARS for m in (                                       # 1, 4, 6-10 by year
        "Ending AUM", "Ending AUM LY", "AUM YoY %", "Avg Monthly AUM", "Fee Yield (bps)",
        "Organic Growth Rate", "AUM-Weighted Alpha", "Alpha Signal")]
    + [(m, s) for s in TIERS for m in (                                       # 1, 3, 4, 7-11 by tier, 2024
        "Ending AUM", "Avg AUM per Client", "Ending AUM LY", "AUM YoY %", "Fee Yield (bps)",
        "Organic Growth Rate", "AUM-Weighted Alpha", "Alpha Signal", "Top 10 Client Share")]
    + [(m, "Month 2024-12") for m in ("Ending AUM", "Ending AUM PM", "AUM MoM %")]  # 5 for Dec 2024
)
got = list(zip(pbi["measure"], pbi["slice"]))
missing = sorted(set(EXPECTED) - set(got))
extra = sorted(set(got) - set(EXPECTED))
dupes = sorted({k for k in got if got.count(k) > 1})
if missing or extra or dupes:
    print(f"COVERAGE FAILED: expected {len(EXPECTED)} rows, got {len(got)}")
    for label, items in (("Missing", missing), ("Not expected", extra), ("Duplicated", dupes)):
        for m, s in items:
            print(f"  {label}: {m} | {s}")
    sys.exit(1)

out = []
for _, r in pbi.iterrows():
    measure, slice_label, raw = r["measure"], r["slice"], r["value"]
    pandas_value = MEASURES[measure](ctx_for(slice_label))
    pbi_blank, pd_blank = raw == "", pandas_value is None

    if measure in TEXT:
        powerbi_value = raw or None
        abs_diff = None
        match = powerbi_value == pandas_value
    elif pbi_blank or pd_blank:
        powerbi_value = None if pbi_blank else float(raw)
        abs_diff = None
        match = pbi_blank and pd_blank  # blank on both sides is a match
    else:
        powerbi_value = float(raw)
        if measure in COUNT and powerbi_value.is_integer():
            powerbi_value = int(powerbi_value)  # write 2325, not 2325.0
        abs_diff = abs(powerbi_value - pandas_value)
        match = abs_diff <= tolerance(measure) + 1e-9

    out.append({
        "measure": measure, "slice": slice_label,
        "powerbi_value": powerbi_value, "pandas_value": pandas_value,
        "abs_diff": abs_diff, "match": bool(match),
    })

recon = pd.DataFrame(out)
# No float_format: write full precision so tiny diffs (e.g. 1.2e-13) stay visible instead of 0.000000
recon.to_csv(REPORTS / "measure_reconciliation.csv", index=False)

# ---------------------------------------------------------------------------
# 5. Summary
# ---------------------------------------------------------------------------
n, ok = len(recon), recon["match"].sum()
print(f"Coverage OK: all {len(EXPECTED)} expected measure/slice rows present, no extras or duplicates")
print(f"Reconciled {n} rows: {ok} match, {n - ok} don't")
print(f"Wrote {REPORTS / 'measure_reconciliation.csv'}")

slice_type = recon["slice"].str.extract(r"^(Grand Total|Year|Tier 2024|Month)", expand=False)
coverage = recon.groupby(slice_type)["measure"].nunique()
print("\nMeasures covered per slice type:")
for kind, count in coverage.items():
    print(f"  {kind:<12} {count}")
print(f"Largest currency diff: {recon.loc[recon.measure.isin(CURRENCY), 'abs_diff'].max():.6f}  "
      f"| largest ratio diff: {recon.loc[~recon.measure.isin(CURRENCY | COUNT | TEXT), 'abs_diff'].max():.2e}")

if n - ok:
    print("\nMISMATCHES:")
    print(recon.loc[~recon["match"]].to_string(index=False))
    sys.exit(1)

naive = recon.query("measure == 'AUM (naive SUM)'").iloc[0]
print(f"\nNaive SUM twin: Power BI {naive.powerbi_value:,.2f} vs pandas {naive.pandas_value:,.2f}"
      " - both tools make the same mistake (about 44.5x the real Ending AUM).")
