"""
02_part_c_evidence.py  -  HW6 Part C: the pandas evidence behind the design answers

Prints the numbers used in powerbi/measures.md, Part C (a)-(d).

How to run (from the repo root):
    python hw06/scripts/02_part_c_evidence.py
    python hw06/scripts/02_part_c_evidence.py "C:/MIS3060/Wildcat Capital Clean"
"""

import sys
from pathlib import Path

import pandas as pd

HW_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else HW_DIR.parent.parent / "Wildcat Capital Clean"


def load(name, **kw):
    for p in [DATA_DIR / f"{name}.csv", *sorted(DATA_DIR.glob(f"{name} (*).csv"))]:
        if p.exists():
            return pd.read_csv(p, **kw)
    sys.exit(f"Can't find {name}.csv in {DATA_DIR}")


snap = load("fact_portfolio_snapshot", parse_dates=["snapshot_date"])
fees = load("fact_fees", parse_dates=["fee_date"])
txns = load("fact_transactions", parse_dates=["txn_date"])
clients = load("dim_client")
snap["client_tier"] = snap["client_id"].map(clients.set_index("client_id")["client_tier"])
txns["client_tier"] = txns["client_id"].map(clients.set_index("client_id")["client_tier"])

LAST = snap["snapshot_date"].max()


def money(x):
    return f"${x:,.2f}"


# ---------------------------------------------------------------------------
# (a) Ending AUM vs SUMX over clients
# ---------------------------------------------------------------------------
print("=== (a) Ending AUM vs SUMX ( VALUES ( client_id ), [Ending AUM] ) ===")
ending_aum = snap.loc[snap["snapshot_date"] == LAST, "aum"].sum()
client_last = snap.groupby("client_id")["snapshot_date"].transform("max")
per_client = snap[snap["snapshot_date"] == client_last]
sumx = per_client["aum"].sum()
stale = per_client[per_client["snapshot_date"] < LAST]
stale = stale.merge(clients[["client_id", "is_active"]], on="client_id")
print(f"Ending AUM (one shared last date, {LAST:%Y-%m-%d}): {money(ending_aum)}")
print(f"SUMX (each client's own last date):         {money(sumx)}")
print(f"Difference:                                 {money(sumx - ending_aum)}")
print(f"Clients whose last snapshot is before {LAST:%b %Y}: {len(stale)} "
      f"(is_active = False: {(~stale['is_active']).sum()}), "
      f"last seen by year: {stale['snapshot_date'].dt.year.value_counts().sort_index().to_dict()}")
print(f"Their stale balances add up to:             {money(stale['aum'].sum())}")

# ---------------------------------------------------------------------------
# (b) 2024 Fee Yield vs Effective Fee Rate
# ---------------------------------------------------------------------------
print("\n=== (b) 2024 Fee Yield (bps) vs Effective Fee Rate (bps) ===")
s24 = snap[snap["snapshot_date"].dt.year == 2024]
f24 = fees[fees["fee_date"].dt.year == 2024]
fee_yield = f24["amount"].sum() * 12 * 10_000 / s24["aum"].sum()
eff_rate = f24["amount"].sum() * 12 * 10_000 / f24["aum_basis"].sum()
print(f"Fee Yield = fees / SUM(snapshot aum):       {fee_yield:.2f} bps   (denominator {money(s24['aum'].sum())})")
print(f"Effective Fee Rate = fees / SUM(aum_basis): {eff_rate:.2f} bps   (denominator {money(f24['aum_basis'].sum())})")

m = s24.merge(f24, left_on=["client_id", "snapshot_date"], right_on=["client_id", "fee_date"],
              how="left", indicator=True)
billed, unbilled = m[m["_merge"] == "both"], m[m["_merge"] == "left_only"]
print(f"2024 snapshot client-months: {len(m):,} | with a fee row: {len(billed):,} | with NO fee row: {len(unbilled):,}")
print(f"AUM in client-months with no fee row: {money(unbilled['aum'].sum())} "
      f"({unbilled['aum'].sum() / s24['aum'].sum():.2%} of the denominator), "
      f"{unbilled['client_id'].nunique():,} different clients")
print(f"Where both exist, aum == aum_basis on {((billed['aum'] - billed['aum_basis']).abs() < 0.01).mean():.0%} of rows")
print(f"Fee Yield using only client-months that have a fee row: "
      f"{f24['amount'].sum() * 12 * 10_000 / billed['aum'].sum():.2f} bps (= Effective Fee Rate)")
print("Unbilled client-months by tier:", unbilled["client_tier"].value_counts().to_dict())
print("Unbilled client-months by account_type:", unbilled["account_type"].value_counts().to_dict())
print("Fee rows with no matching snapshot:",
      (f24.merge(s24, left_on=["client_id", "fee_date"], right_on=["client_id", "snapshot_date"],
                 how="left", indicator=True)["_merge"] == "left_only").sum())
all_m = snap.merge(fees, left_on=["client_id", "snapshot_date"], right_on=["client_id", "fee_date"],
                   how="left", indicator=True)
gaps = all_m[all_m["_merge"] == "left_only"]
print("Client-months with no fee row, every year:",
      gaps.groupby(gaps["snapshot_date"].dt.year).size().to_dict())
per_client_gaps = gaps.groupby("client_id").size()
print(f"Clients with at least one missing fee month (2020-2024): {len(per_client_gaps):,} of "
      f"{snap['client_id'].nunique():,}, missing {per_client_gaps.mean():.2f} months each on average")
print("Missing fee months by calendar month (1 = Jan):",
      gaps["snapshot_date"].dt.month.value_counts().sort_index().to_dict())

# ---------------------------------------------------------------------------
# (c) AUM-Weighted Alpha: last snapshot, suspects
# ---------------------------------------------------------------------------
print("\n=== (c) AUM-Weighted Alpha at the last snapshot ===")


def weighted(d):
    return (d["aum"] * d["active_alpha_ytd"]).sum() / d["aum"].sum()


last = snap[snap["snapshot_date"] == LAST]
clean = last[last["is_return_suspect"] != 1]
suspect = last[last["is_return_suspect"] == 1]
print(f"Rows at {LAST:%Y-%m-%d}: {len(last):,} | suspect: {len(suspect)} "
      f"({suspect['aum'].sum() / last['aum'].sum():.2%} of AUM)")
print(f"Weighted, suspects excluded (the measure): {weighted(clean):.4%}")
print(f"Simple mean, same rows:                    {clean['active_alpha_ytd'].mean():.4%}")
print(f"Weighted, suspects included:               {weighted(last):.4%}")
print(f"Simple mean, suspects included:            {last['active_alpha_ytd'].mean():.4%}")
print(f"Suspect alpha range: {suspect['active_alpha_ytd'].min():.2%} to {suspect['active_alpha_ytd'].max():.2%} "
      f"(clean rows: {clean['active_alpha_ytd'].min():.2%} to {clean['active_alpha_ytd'].max():.2%})")
all24 = snap[(snap["snapshot_date"].dt.year == 2024) & (snap["is_return_suspect"] != 1)]
print(f"Wrong way - weighted across all 12 months of 2024: {weighted(all24):.4%}")
print(f"Blank is_return_suspect flags in the whole table: {snap['is_return_suspect'].isna().sum()} "
      f"of {len(snap):,} rows")

# ---------------------------------------------------------------------------
# (d) Organic growth vs YoY by tier, 2024
# ---------------------------------------------------------------------------
print("\n=== (d) 2024 by tier: Organic Growth Rate vs AUM YoY % ===")
dec23, dec24 = pd.Timestamp("2023-12-01"), LAST
rows = []
for tier in ["HNW", "Retail", "UHNW", "All"]:
    s = snap if tier == "All" else snap[snap["client_tier"] == tier]
    t = txns if tier == "All" else txns[txns["client_tier"] == tier]
    t24 = t[t["txn_date"].dt.year == 2024]
    ly = s.loc[s["snapshot_date"] == dec23, "aum"].sum()
    cy = s.loc[s["snapshot_date"] == dec24, "aum"].sum()
    flows = (t24.loc[t24["txn_type"] == "Deposit", "amount"].sum()
             - t24.loc[t24["txn_type"] == "Withdrawal", "amount"].sum())
    rows.append({
        "tier": tier, "AUM Dec-23": ly, "AUM Dec-24": cy, "net flows": flows,
        "organic %": flows / ly, "YoY %": cy / ly - 1, "non-flow growth %": (cy / ly - 1) - flows / ly,
        "share of growth from flows": flows / (cy - ly),
    })
d = pd.DataFrame(rows).set_index("tier")
pd.set_option("display.width", 200)
print(d.to_string(formatters={
    "AUM Dec-23": money, "AUM Dec-24": money, "net flows": money,
    "organic %": "{:.2%}".format, "YoY %": "{:.2%}".format,
    "non-flow growth %": "{:.2%}".format, "share of growth from flows": "{:.1%}".format,
}))
