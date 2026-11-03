"""
check_star.py  -  HW5 star schema checks for the Wildcat Capital clean tables

What it proves (rubric: "uniqueness and integrity proven in code"):
  1. Row counts match the handout
  2. Every primary key is unique and never blank        (Part A)
  3. Every foreign key matches a row in its dimension   (Part A, no orphans)
  4. Each fact table's grain is unique                  (Part B)
  5. The only blank FK is security_id on cash rows      (Part E a)
  6. Fact dates match dim_date[date], not date_id        (Part E c)

How to run (from the hw05 folder):
    python check_star.py                      # CSVs are in the same folder as this script
    python check_star.py "path/to/Wildcat Capital Clean"

Exit code is 0 if every check passes, 1 if any fails.
"""

import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 1. Load the eight tables
# ---------------------------------------------------------------------------
DATA_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent

TABLES = [
    "dim_advisor", "dim_benchmark", "dim_client", "dim_date", "dim_security",
    "fact_fees", "fact_portfolio_snapshot", "fact_transactions",
]

# The CSVs are gitignored, so give a clear message instead of a traceback
missing = [t for t in TABLES if not (DATA_DIR / f"{t}.csv").exists()]
if missing:
    sys.exit(
        f"Can't find {', '.join(m + '.csv' for m in missing)} in {DATA_DIR.resolve()}\n"
        'Pass the folder that holds the 8 Wildcat Capital Clean CSVs, e.g.\n'
        '    python check_star.py "C:\\MIS3060\\HW5"'
    )

df = {name: pd.read_csv(DATA_DIR / f"{name}.csv") for name in TABLES}

results = []  # (check name, passed?, detail)
info = []     # informational lines that are not pass/fail


def check(name, passed, detail=""):
    results.append((name, bool(passed), detail))


# ---------------------------------------------------------------------------
# 2. Row counts vs. the handout
# ---------------------------------------------------------------------------
EXPECTED_ROWS = {
    "dim_advisor": 25, "dim_benchmark": 8, "dim_client": 2_500,
    "dim_date": 1_827, "dim_security": 500, "fact_fees": 122_197,
    "fact_portfolio_snapshot": 129_547, "fact_transactions": 298_572,
}
for name, expected in EXPECTED_ROWS.items():
    actual = len(df[name])
    check(f"rows  {name}", actual == expected, f"{actual:,} (expected {expected:,})")

# ---------------------------------------------------------------------------
# 3. Primary keys: unique and not blank
# ---------------------------------------------------------------------------
PRIMARY_KEYS = {
    "dim_advisor": "advisor_id", "dim_benchmark": "benchmark_id",
    "dim_client": "client_id", "dim_date": "date_id",
    "dim_security": "security_id", "fact_fees": "fee_id",
    "fact_portfolio_snapshot": "snapshot_id", "fact_transactions": "txn_id",
}
for table, pk in PRIMARY_KEYS.items():
    col = df[table][pk]
    ok = col.notna().all() and col.is_unique
    check(f"PK    {table}[{pk}]", ok, f"{col.nunique():,} unique / {len(col):,} rows")

# dim_date[date] is the column the facts actually join to, so it must be unique and not blank
date_col = df["dim_date"]["date"]
check("PK    dim_date[date] (join key)", date_col.notna().all() and date_col.is_unique,
      f"{date_col.nunique():,} unique dates, blanks={date_col.isna().sum()}")

# ---------------------------------------------------------------------------
# 4. Foreign keys: every non-blank value exists in the dimension
#    (fact/dim, fk column, dim table, dim column, may it be blank?)
# ---------------------------------------------------------------------------
FOREIGN_KEYS = [
    ("fact_transactions", "client_id", "dim_client", "client_id", False),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_transactions", "security_id", "dim_security", "security_id", True),
    ("fact_transactions", "txn_date", "dim_date", "date", False),
    ("fact_fees", "client_id", "dim_client", "client_id", False),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_fees", "fee_date", "dim_date", "date", False),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id", False),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date", False),
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id", False),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id", False),
]
for src, fk, dim, dim_col, blank_ok in FOREIGN_KEYS:
    values = df[src][fk]
    blanks = values.isna().sum()
    orphans = (~values.dropna().isin(df[dim][dim_col])).sum()
    ok = orphans == 0 and (blank_ok or blanks == 0)
    check(f"FK    {src}[{fk}] -> {dim}[{dim_col}]", ok,
          f"orphans={orphans:,}, blanks={blanks:,}")

# ---------------------------------------------------------------------------
# 5. Grain: the columns that define "one row" must be unique together
# ---------------------------------------------------------------------------
# fact_transactions is event grain (one row per txn_id), already proven by its PK check above
GRAIN = {
    "fact_portfolio_snapshot": ["client_id", "snapshot_date"],
    "fact_fees": ["client_id", "fee_date"],
}
for table, cols in GRAIN.items():
    dupes = df[table].duplicated(subset=cols).sum()
    check(f"grain {table} {cols}", dupes == 0, f"duplicates={dupes:,}")

# Snapshots and fees are monthly: every date is the 1st of a month.
# errors="coerce" turns a bad date into NaT so it fails the check instead of crashing.
for table, col in [("fact_portfolio_snapshot", "snapshot_date"), ("fact_fees", "fee_date")]:
    parsed = pd.to_datetime(df[table][col], errors="coerce")
    ok = parsed.notna().all() and (parsed.dt.day == 1).all()
    check(f"grain {table}[{col}] is 1st of month", ok, f"unparseable={parsed.isna().sum()}")

# ---------------------------------------------------------------------------
# 6. Blank security_id only on cash rows (Part E a)
# ---------------------------------------------------------------------------
txn = df["fact_transactions"]
cash_types = {"Deposit", "Withdrawal", "Advisory Fee"}
security_types = {"Buy", "Sell", "Dividend"}

# Only the six expected transaction types exist (catches typos like "buy" or new types)
actual_types = set(txn["txn_type"].dropna())
check("E(a)  txn_type has exactly the 6 expected values",
      actual_types == cash_types | security_types and txn["txn_type"].notna().all(),
      f"types={sorted(actual_types)}")

blank_types = set(txn.loc[txn["security_id"].isna(), "txn_type"])
check("E(a)  blank security_id only on cash rows", blank_types <= cash_types,
      f"{txn['security_id'].isna().sum():,} blank rows, types={sorted(blank_types)}")
has_sec = txn.loc[txn["txn_type"].isin(security_types), "security_id"].notna().all()
check("E(a)  every Buy/Sell/Dividend has a security_id", has_sec)

# Cash rows also have no shares or price: there is genuinely no security involved
cash = txn[txn["txn_type"].isin(cash_types)]
filled = cash["shares"].notna().sum() + cash["price"].notna().sum()
check("E(a)  cash rows have blank shares and price", filled == 0, f"non-blank values={filled}")

# ---------------------------------------------------------------------------
# 7. Part C: amounts are always positive (direction lives in txn_type)
# ---------------------------------------------------------------------------
bad_amounts = (txn["amount"].isna() | (txn["amount"] <= 0)).sum()
check("C     fact_transactions[amount] is always > 0", bad_amounts == 0,
      f"blank or <= 0: {bad_amounts}")

# ---------------------------------------------------------------------------
# 8. Why we join on date, not date_id (Part E c) - all three fact dates
# ---------------------------------------------------------------------------
dim_date = df["dim_date"]
for table, col in [("fact_transactions", "txn_date"), ("fact_fees", "fee_date"),
                   ("fact_portfolio_snapshot", "snapshot_date")]:
    on_date = df[table][col].isin(dim_date["date"]).mean()
    on_date_id = df[table][col].astype(str).isin(dim_date["date_id"].astype(str)).mean()
    check(f"E(c)  {table}[{col}] matches date, not date_id",
          on_date == 1.0 and on_date_id == 0.0,
          f"match date={on_date:.0%}, match date_id={on_date_id:.0%}")

# ---------------------------------------------------------------------------
# 9. Two advisor paths (Part E b) - informational, not pass/fail.
#    The model keeps the fact-level advisor active either way; this shows
#    whether the inactive dim_client path would give different answers today.
# ---------------------------------------------------------------------------
client_adv = df["dim_client"].set_index("client_id")["advisor_id"]
for table in ["fact_transactions", "fact_fees", "fact_portfolio_snapshot"]:
    f = df[table]
    mismatch = (f["advisor_id"] != f["client_id"].map(client_adv)).sum()
    info.append(f"E(b)  {table}: rows where advisor_id differs from client's advisor = {mismatch:,}")

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
width = max(len(r[0]) for r in results)
for name, passed, detail in results:
    print(f"{'PASS' if passed else 'FAIL'}  {name:<{width}}  {detail}")
for line in info:
    print(f"INFO  {line}")

failed = sum(not r[1] for r in results)
print(f"\n{len(results) - failed}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
