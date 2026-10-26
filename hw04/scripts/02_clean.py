"""
HW4 Part C: Cleaning program for the Wildcat Capital tables.

Reads the 8 raw files (never modifies them) and writes 8 clean files with the
same names and columns, plus 0/1 flag columns where a value is suspicious but
cannot be corrected without inventing data.

Every fix follows the same pattern:
    1. measure the problem (before)
    2. apply ONE transformation
    3. measure again (after), print rows affected
    4. assert the after-state -> the script stops if a fix did not work
    5. log it to the audit trail

Order (see decision_log.md):
    formats first -> remove duplicates/orphans -> fix values -> add flags

Outputs:
    data/clean/<8 tables>.csv
    data/audit/cleaning_log.csv, value_changes.csv, quarantine_*.csv
"""
import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
CLEAN = BASE / "data" / "clean"
AUDIT = BASE / "data" / "audit"
CLEAN.mkdir(parents=True, exist_ok=True)
AUDIT.mkdir(parents=True, exist_ok=True)

TABLE_NAMES = ["dim_advisor", "dim_benchmark", "dim_client", "dim_date", "dim_security",
               "fact_fees", "fact_portfolio_snapshot", "fact_transactions"]
PRIMARY_KEYS = {
    "dim_advisor": "advisor_id", "dim_benchmark": "benchmark_id", "dim_client": "client_id",
    "dim_date": "date_id", "dim_security": "security_id", "fact_fees": "fee_id",
    "fact_portfolio_snapshot": "snapshot_id", "fact_transactions": "txn_id",
}

# ---------------------------------------------------------------
# Audit-trail helpers
# ---------------------------------------------------------------
cleaning_log = []      # one row per transformation
value_changes = []     # one row per changed cell
quarantined = {}       # table -> number of rows quarantined


def num(series):
    return pd.to_numeric(series, errors="coerce")


def log_step(table, issue, action, rows_affected, note=""):
    cleaning_log.append({"table": table, "issue": issue, "action": action,
                         "rows_affected": int(rows_affected), "note": note})
    print(f"  -> {table}: {issue} | {action} | {rows_affected:,} rows")


def record_changes(table, df, mask, column, new_values):
    """Save old -> new for every changed cell, then apply the change."""
    key = PRIMARY_KEYS[table]
    old = df.loc[mask, column]
    changes = pd.DataFrame({
        "table": table, "key_column": key, "key": df.loc[mask, key],
        "column": column, "old_value": old, "new_value": new_values,
    })
    value_changes.append(changes)
    df.loc[mask, column] = new_values


def quarantine(table, df, mask, reason):
    """Move rows to data/audit/quarantine_<table>_<reason>.csv. Never silent."""
    bad = df[mask].copy()
    bad.insert(0, "quarantine_reason", reason)
    path = AUDIT / f"quarantine_{table}_{reason}.csv"
    bad.to_csv(path, index=False)
    quarantined[table] = quarantined.get(table, 0) + len(bad)
    print(f"  -> quarantined {len(bad):,} rows to {path.name}")
    return df[~mask].copy()


def header(step, title):
    print(f"\n[{step}] {title}")


# ---------------------------------------------------------------
# Load raw as text
# ---------------------------------------------------------------
raw = {t: pd.read_csv(RAW / f"{t}.csv", dtype=str, keep_default_na=False) for t in TABLE_NAMES}
raw_counts = {t: len(df) for t, df in raw.items()}
tables = {t: df.copy() for t, df in raw.items()}     # work on copies
print("Loaded raw tables:", raw_counts)

# =================================================================
# STAGE 1: FIX FORMATS
# =================================================================

# --- D1: security_id stored as '45.0' -----------------------------
header("D1", "fact_transactions.security_id: '45.0' -> '45'")
t = tables["fact_transactions"]
has_id = t.security_id != ""
float_fmt = has_id & t.security_id.str.fullmatch(r"\d+\.0")
before = float_fmt.sum()
# Safety: only convert if EVERY value is the harmless 'N.0' pattern
assert float_fmt.sum() == has_id.sum(), "some security_ids have a real decimal part, stop!"
record_changes("fact_transactions", t, float_fmt, "security_id",
               t.loc[float_fmt, "security_id"].str[:-2])
after = (has_id & ~t.security_id.str.fullmatch(r"\d+")).sum()
print(f"  before: {before:,} float-formatted | after: {after}")
assert after == 0
# Reconcile: every converted ID must now exist in dim_security
orphans = (has_id & ~t.security_id.isin(tables["dim_security"].security_id)).sum()
print(f"  reconcile: security_id orphans after fix = {orphans}")
assert orphans == 0
log_step("fact_transactions", "security_id stored as float text ('45.0')", "convert to whole number",
         before, "verified: 100% now match dim_security")

# --- D2: return_ytd stored as '9.28%' ------------------------------
header("D2", "fact_portfolio_snapshot.return_ytd: '9.28%' -> 0.0928")
s = tables["fact_portfolio_snapshot"]
pct = s.return_ytd.str.endswith("%")
before = pct.sum()
exact = num(s.loc[pct, "return_ytd"].str.rstrip("%")) / 100
converted = exact.round(6)
# Precision check: rounding to 6 places must not lose any digits of the original
assert ((converted - exact).abs() < 1e-12).all(), "6-decimal rounding would change a value, stop!"
# Reconcile BEFORE applying: converted return - benchmark must equal stored alpha
gap = (converted - num(s.loc[pct, "benchmark_return_ytd"]) - num(s.loc[pct, "active_alpha_ytd"])).abs()
print(f"  reconcile: {(gap < 1e-4).sum()} of {before} converted values satisfy alpha formula")
assert (gap < 1e-4).all(), "percent conversion does not reconcile with alpha, stop!"
record_changes("fact_portfolio_snapshot", s, pct, "return_ytd", converted.map(lambda v: f"{v:.6f}"))
after = num(s.return_ytd).isna().sum()
print(f"  before: {before} text percents | after: {after} unparseable")
assert after == 0
log_step("fact_portfolio_snapshot", "return_ytd stored as percent text", "convert: strip % and /100",
         before, "verified: alpha = return - benchmark holds for all converted rows")

# --- D8: scientific notation ('9.9e-05') -> plain decimal ----------
header("D8", "fact_portfolio_snapshot: scientific notation -> plain decimal")
SCI = r"-?\d+(\.\d+)?[eE][-+]?\d+"
for col in ["return_ytd", "active_alpha_ytd"]:
    sci = s[col].str.fullmatch(SCI)
    before = sci.sum()
    old_vals = num(s.loc[sci, col])
    new_vals = old_vals.map(lambda v: f"{v:.6f}")
    # Reconcile: the number must be identical, only the text format changes
    assert ((num(new_vals) - old_vals).abs() < 1e-9).all(), "value changed during reformat, stop!"
    record_changes("fact_portfolio_snapshot", s, sci, col, new_vals)
    after = s[col].str.fullmatch(SCI).sum()
    print(f"  {col}: before {before} | after {after}")
    assert after == 0
    log_step("fact_portfolio_snapshot", f"{col} in scientific notation", "standardize to plain decimal",
             before, "numeric value unchanged (checked to 1e-9)")

# =================================================================
# STAGE 2: REMOVE DUPLICATES AND ORPHANS (to quarantine)
# =================================================================

# --- D5: near-duplicate clients ------------------------------------
header("D5", "dim_client: near-duplicate clients (last name off by one letter)")
c = tables["dim_client"]
match_cols = ["first_name", "age", "city", "zip_code", "initial_aum", "client_since", "advisor_id"]
used = set(tables["fact_transactions"].client_id) | set(tables["fact_fees"].client_id) \
    | set(tables["fact_portfolio_snapshot"].client_id)
c["_active"] = c.client_id.isin(used)

# Every pair of records that match on all 7 attributes, ignoring last name
all_pairs = c.merge(c, on=match_cols, suffixes=("", "_other"))
all_pairs = all_pairs[all_pairs.client_id != all_pairs.client_id_other]


# Confirm it's a typo-level difference: last names differ by ONE letter at the end
# ('Taylo' vs 'Taylor' = truncated, 'Leen' vs 'Lee' = extra letter)
def one_letter_apart(a, b):
    short, long_ = sorted([a, b], key=len)
    return len(long_) - len(short) == 1 and long_.startswith(short)


name_ok = all_pairs.apply(lambda r: one_letter_apart(r.last_name, r.last_name_other), axis=1)
# Coverage check: the name rule must explain EVERY attribute match, so no
# duplicate with a different kind of typo slips through unreviewed
assert name_ok.all(), f"{(~name_ok).sum() // 2} attribute-matched pairs have a different name difference, review!"

# Which copy to remove is decided by EVIDENCE, not by ID order:
# keep the record the business actually uses (has fact activity), quarantine the unused copy
assert (all_pairs._active != all_pairs._active_other).all(), \
    "a pair where both or neither copy has activity, can't tell which is real, stop!"
pairs = all_pairs[~all_pairs._active]          # this side is the unused copy
dup_ids = set(pairs.client_id)
print(f"  found {len(dup_ids)} duplicates, e.g. {pairs[['client_id','last_name','client_id_other','last_name_other']].head(2).values.tolist()}")
assert not (dup_ids & used), "a duplicate client has activity, stop and merge instead!"
c = c.drop(columns="_active")
before = len(c)
c = quarantine("dim_client", c, c.client_id.isin(dup_ids), "near_duplicate")
assert len(c) == before - len(dup_ids)
assert not c.duplicated(match_cols).any()
tables["dim_client"] = c
log_step("dim_client", "near-duplicate clients (last name off by one letter)", "quarantine", len(dup_ids),
         "verified: 7 fields identical; kept the copy with fact activity, quarantined the unused copy")

# --- D7: transactions for clients that don't exist -----------------
header("D7", "fact_transactions: orphan client_ids")
t = tables["fact_transactions"]
orphan = ~t.client_id.isin(tables["dim_client"].client_id)
before = orphan.sum()
t = quarantine("fact_transactions", t, orphan, "orphan_client")
after = (~t.client_id.isin(tables["dim_client"].client_id)).sum()
print(f"  before: {before} orphan rows | after: {after}")
assert after == 0
tables["fact_transactions"] = t
log_step("fact_transactions", "client_id not in dim_client", "quarantine", before,
         "cannot assign the money to a client without inventing data")

# =================================================================
# STAGE 3: FIX VALUES
# =================================================================

# --- D3: state full names -> USPS codes ----------------------------
header("D3", "dim_client.state: full names -> 2-letter codes")
STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
}
c = tables["dim_client"]
full = c.state.isin(STATE_CODES.keys())
before = full.sum()
print(f"  values to map: {c.loc[full, 'state'].value_counts().to_dict()}")
record_changes("dim_client", c, full, "state", c.loc[full, "state"].map(STATE_CODES))
after = (~c.state.isin(set(STATE_CODES.values()))).sum()
print(f"  before: {before} full names | after: {after} invalid codes")
assert after == 0
log_step("dim_client", "state stored as full name", "standardize to USPS code", before)

# --- D4: blank risk_profile, filled only where benchmark confirms --
header("D4", "dim_client.risk_profile: fill blanks verified by benchmark")
c = tables["dim_client"]
snap = tables["fact_portfolio_snapshot"]
client_bench = snap.groupby("client_id").benchmark_id.agg(lambda x: set(x))
# Learn the mapping from clients whose profile IS known
known = c[c.risk_profile != ""].assign(bench=lambda d: d.client_id.map(client_bench))
known = known.dropna(subset=["bench"]).explode("bench")
profiles_per_bench = known.groupby("bench").risk_profile.unique()
# A benchmark can only confirm a profile if exactly ONE profile uses it
unique_map = {b: p[0] for b, p in profiles_per_bench.items() if len(p) == 1}
print(f"  benchmarks that identify exactly one profile: {unique_map}")
blank = c.risk_profile == ""
before = blank.sum()
blank_bench = c.loc[blank, "client_id"].map(client_bench)
fillable = blank_bench.map(lambda b: isinstance(b, set) and len(b) == 1 and next(iter(b)) in unique_map)
fill_idx = fillable[fillable].index
c["risk_profile_inferred"] = "0"
record_changes("dim_client", c, c.index.isin(fill_idx), "risk_profile",
               blank_bench[fill_idx].map(lambda b: unique_map[next(iter(b))]))
c.loc[fill_idx, "risk_profile_inferred"] = "1"
after = (c.risk_profile == "").sum()
print(f"  before: {before} blank | filled: {len(fill_idx)} | still blank: {after}")
assert after == before - len(fill_idx)
assert (c.risk_profile_inferred == "1").sum() == len(fill_idx)
log_step("dim_client", "risk_profile blank", "fill from benchmark + flag risk_profile_inferred",
         len(fill_idx), f"filled values: {c.loc[fill_idx, 'risk_profile'].value_counts().to_dict()}; "
                        f"{after} left blank (no benchmark evidence)")

# --- D6: negative shares on Buy rows -------------------------------
header("D6", "fact_transactions.shares: negative on Buy rows")
t = tables["fact_transactions"]
neg = (t.txn_type == "Buy") & (num(t.shares) < 0)
before = neg.sum()
# Reconcile BEFORE applying: |shares| x price must equal amount for these rows
gap = (num(t.loc[neg, "shares"]).abs() * num(t.loc[neg, "price"]) - num(t.loc[neg, "amount"])).abs()
print(f"  reconcile: {(gap <= 0.05).sum()} of {before} rows satisfy |shares| x price = amount")
assert (gap <= 0.05).all(), "amount does not confirm share size, stop!"
record_changes("fact_transactions", t, neg, "shares", t.loc[neg, "shares"].str.lstrip("-"))
after = ((t.txn_type.isin(["Buy", "Sell", "Dividend"])) & (num(t.shares) < 0)).sum()
print(f"  before: {before} negative | after: {after}")
assert after == 0
log_step("fact_transactions", "negative shares on Buy rows", "convert to absolute value", before,
         "verified against amount = |shares| x price")

# =================================================================
# STAGE 4: FLAG WHAT CANNOT BE FIXED
# =================================================================

# --- F1: AUM placeholder 1,000.00 -----------------------------------
header("F1", "aum_placeholder_flag on snapshots and fees")
for table, col in [("fact_portfolio_snapshot", "aum"), ("fact_fees", "aum_basis")]:
    df = tables[table]
    df["aum_placeholder_flag"] = (num(df[col]) == 1000).astype(int).astype(str)
    n = (df.aum_placeholder_flag == "1").sum()
    assert n == (num(df[col]) == 1000).sum()
    print(f"  {table}: {n} rows flagged")
    log_step(table, f"{col} = 1000.0 placeholder", "flag aum_placeholder_flag", n,
             "real AUM unknown; value kept")

# --- F2: return_ytd above 100% --------------------------------------
header("F2", "return_outlier_flag on snapshots")
s = tables["fact_portfolio_snapshot"]
s["return_outlier_flag"] = (num(s.return_ytd).abs() > 1).astype(int).astype(str)
n = (s.return_outlier_flag == "1").sum()
assert n == (num(s.return_ytd).abs() > 1).sum()
print(f"  {n} rows flagged")
log_step("fact_portfolio_snapshot", "return_ytd beyond +/-100%", "flag return_outlier_flag", n,
         "internally consistent with alpha; likely deposits counted as gains on small accounts")

# --- Documented, left as is -----------------------------------------
for table, issue, note in [
    ("fact_fees", "bps_charged 100.38 (1 row)", "inside Retail band; fee math reconciles"),
    ("fact_transactions", "Buy/Sell dated on weekends", "likely booking dates; true trade date unknown"),
    ("dim_security", "sector/expense_ratio blanks", "legitimate: ETF vs non-ETF structure"),
    ("fact_transactions", "security/shares/price blank on cash rows", "legitimate: no security on cash moves"),
    ("dim_advisor", "certifications = 'None'", "legitimate value meaning no certification"),
]:
    log_step(table, issue, "leave as is", 0, note)

# =================================================================
# SAVE AND PROVE: raw rows = clean rows + quarantined rows
# =================================================================
print("\n[SAVE] writing clean tables")
for name in TABLE_NAMES:
    df = tables[name]
    # Same columns as raw, in the same order, plus any added flag columns at the end
    raw_cols = list(raw[name].columns)
    assert list(df.columns[:len(raw_cols)]) == raw_cols, f"{name}: columns changed!"
    clean_n, q_n = len(df), quarantined.get(name, 0)
    assert raw_counts[name] == clean_n + q_n, f"{name}: rows lost!"
    print(f"  {name:<25} raw {raw_counts[name]:>7,} = clean {clean_n:>7,} + quarantined {q_n:>4}")
    df.to_csv(CLEAN / f"{name}.csv", index=False)

pd.DataFrame(cleaning_log).to_csv(AUDIT / "cleaning_log.csv", index=False)
changes = pd.concat(value_changes, ignore_index=True)
changes.to_csv(AUDIT / "value_changes.csv", index=False)
pd.DataFrame([{"table": t, "raw_rows": raw_counts[t], "clean_rows": len(tables[t]),
               "quarantined_rows": quarantined.get(t, 0)} for t in TABLE_NAMES]) \
    .to_csv(AUDIT / "row_reconciliation.csv", index=False)

print(f"\nDone. {len(cleaning_log)} log entries, {len(changes):,} cell changes, "
      f"{sum(quarantined.values())} rows quarantined.")
