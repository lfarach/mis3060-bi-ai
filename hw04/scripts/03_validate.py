"""
HW4 Part D: Referential integrity, rule checks, reconciliations, IQR outliers,
and a raw-vs-clean data-quality scorecard.

Runs every check on BOTH data/raw and data/clean.

Outputs (reports/):
    data_quality_scorecard.csv   one row per table per stage
    ri_results.csv               all 13 relationships, raw vs clean
    rule_results.csv             every business rule, raw vs clean
    reconciliations.csv          recomputed vs stored values
    iqr_outliers.csv             IQR outlier summary
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
STAGES = {"raw": BASE / "data" / "raw", "clean": BASE / "data" / "clean"}
REPORTS = BASE / "reports"
REPORTS.mkdir(exist_ok=True)

TABLE_NAMES = ["dim_advisor", "dim_benchmark", "dim_client", "dim_date", "dim_security",
               "fact_fees", "fact_portfolio_snapshot", "fact_transactions"]


def load(stage):
    return {t: pd.read_csv(STAGES[stage] / f"{t}.csv", dtype=str, keep_default_na=False)
            for t in TABLE_NAMES}


def num(series):
    return pd.to_numeric(series, errors="coerce")


# =================================================================
# 1. REUSABLE REFERENTIAL-INTEGRITY FUNCTION  (reuse in Assignment 5)
# =================================================================
def check_referential_integrity(fact_df, fact_key, dim_df, dim_key):
    """Check that every foreign key in fact_df[fact_key] exists in dim_df[dim_key].

    Keys are compared as text, exactly the way a BI tool joins them,
    so '45.0' does NOT match '45'. Blank keys are counted separately
    (null-key rate) and are not treated as orphans.

    Returns a dict:
        match_rate            share of non-null keys that find a match (0-1)
        orphan_rows           rows whose key has no match
        distinct_orphan_keys  number of different unmatched key values
        null_key_rate         share of rows with a blank key (0-1)
    """
    keys = fact_df[fact_key].astype(str)            # exact text, no trimming: ' 45' != '45'
    non_null = keys[keys != ""]
    valid_keys = set(dim_df[dim_key].astype(str))
    orphan_mask = ~non_null.isin(valid_keys)
    return {
        "match_rate": round(1 - orphan_mask.sum() / len(non_null), 6) if len(non_null) else 1.0,
        "orphan_rows": int(orphan_mask.sum()),
        "distinct_orphan_keys": int(non_null[orphan_mask].nunique()),
        "null_key_rate": round(1 - len(non_null) / len(keys), 6) if len(keys) else 0.0,
        "checked_rows": len(non_null),      # exact denominator, for pooling across FKs
    }


# 10 ID relationships + 3 date relationships: (child table, FK, parent table, PK)
RELATIONSHIPS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id"),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_fees", "client_id", "dim_client", "client_id"),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id"),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_transactions", "client_id", "dim_client", "client_id"),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_transactions", "security_id", "dim_security", "security_id"),
    ("fact_fees", "fee_date", "dim_date", "date"),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date"),
    ("fact_transactions", "txn_date", "dim_date", "date"),
]


# =================================================================
# 2. TABLE METADATA: keys, types, expected blanks
# =================================================================
PRIMARY_KEYS = {
    "dim_advisor": "advisor_id", "dim_benchmark": "benchmark_id", "dim_client": "client_id",
    "dim_date": "date_id", "dim_security": "security_id", "fact_fees": "fee_id",
    "fact_portfolio_snapshot": "snapshot_id", "fact_transactions": "txn_id",
}
# Business keys: one real-world thing per row (catches near-duplicates the PK misses)
NATURAL_KEYS = {
    "dim_client": ["first_name", "age", "city", "zip_code", "initial_aum", "client_since", "advisor_id"],
    "dim_date": ["date"],
    "dim_security": ["ticker"],
    "fact_fees": ["client_id", "fee_date", "fee_type"],
    "fact_portfolio_snapshot": ["client_id", "snapshot_date"],
}

INT, DEC, DATE, BOOL, BIT = r"-?\d+", r"-?\d+(\.\d+)?", r"\d{4}-\d{2}-\d{2}", r"True|False", r"[01]"
COLUMN_TYPES = {
    "dim_advisor": {"advisor_id": INT, "years_experience": INT, "aum_target_mm": INT},
    "dim_benchmark": {"benchmark_id": INT},
    "dim_client": {"client_id": INT, "age": INT, "zip_code": r"\d{5}", "initial_aum": DEC,
                   "client_since": DATE, "advisor_id": INT, "is_active": BOOL},
    "dim_date": {"date_id": INT, "date": DATE, "year": INT, "quarter": INT, "month": INT,
                 "week_of_year": INT, "is_month_end": BIT, "is_quarter_end": BIT,
                 "is_year_end": BIT, "is_trading_day": BIT},
    "dim_security": {"security_id": INT, "benchmark_id": INT, "is_etf": BOOL, "expense_ratio_bps": DEC},
    "fact_fees": {"fee_id": INT, "client_id": INT, "advisor_id": INT, "fee_date": DATE,
                  "aum_basis": DEC, "bps_charged": DEC, "amount": DEC},
    "fact_portfolio_snapshot": {"snapshot_id": INT, "client_id": INT, "advisor_id": INT,
                                "benchmark_id": INT, "snapshot_date": DATE, "year": INT, "month": INT,
                                "aum": DEC, "return_ytd": DEC, "benchmark_return_ytd": DEC,
                                "active_alpha_ytd": DEC, "cash_pct": DEC},
    "fact_transactions": {"txn_id": INT, "client_id": INT, "advisor_id": INT, "security_id": INT,
                          "txn_date": DATE, "shares": DEC, "price": DEC, "amount": DEC},
}


def expected_blank(table, df):
    """Cells that are SUPPOSED to be blank (legitimate structure).
    Returns {column: boolean mask of rows where blank is allowed}."""
    allowed = {}
    if table == "dim_security":
        allowed["sector"] = df.is_etf == "True"
        allowed["expense_ratio_bps"] = df.is_etf == "False"
    if table == "fact_transactions":
        cash = df.txn_type.isin(["Deposit", "Withdrawal", "Advisory Fee"])
        for col in ["security_id", "shares", "price"]:
            allowed[col] = cash
    return allowed


# =================================================================
# 3. BUSINESS RULES (natural bounds, allowed lists, sign rules)
#    Each rule returns a boolean Series: True = pass. NaN rows are skipped.
# =================================================================
US_STATES = set("""AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE
NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC""".split())
ACCOUNTS = {"Taxable", "IRA", "Roth IRA", "Trust", "529"}


def between(s, lo=None, hi=None):
    x = num(s)
    ok = pd.Series(True, index=s.index)
    if lo is not None:
        ok &= x >= lo
    if hi is not None:
        ok &= x <= hi
    return ok.where(x.notna())          # unparseable/blank -> not evaluated here


def in_list(s, allowed):
    return s.isin(allowed).where(s != "")


RULES = {
    "dim_advisor": [
        ("years_experience 0-50", lambda d: between(d.years_experience, 0, 50)),
        ("aum_target_mm > 0", lambda d: between(d.aum_target_mm, 1)),
        ("region in list", lambda d: in_list(d.region, {"Northeast", "Southeast", "Mid-Atlantic", "West", "Midwest"})),
    ],
    "dim_benchmark": [
        ("asset_class not blank", lambda d: d.asset_class != ""),
    ],
    "dim_client": [
        ("age 18-110", lambda d: between(d.age, 18, 110)),
        ("initial_aum > 0", lambda d: between(d.initial_aum, 0.01)),
        ("state is USPS code", lambda d: in_list(d.state, US_STATES)),
        ("risk_profile in list (not blank)", lambda d: d.risk_profile.isin(
            {"Conservative", "Moderately Conservative", "Balanced", "Moderately Aggressive", "Aggressive"})),
        ("client_tier in list", lambda d: in_list(d.client_tier, {"Retail", "HNW", "UHNW"})),
        ("account type in list", lambda d: in_list(d.primary_account_type, ACCOUNTS)),
        ("client_since <= 2024-12-31", lambda d: (d.client_since <= "2024-12-31").where(d.client_since != "")),
    ],
    "dim_date": [
        ("quarter 1-4", lambda d: between(d.quarter, 1, 4)),
        ("month 1-12", lambda d: between(d.month, 1, 12)),
        ("day_of_week matches date", lambda d: pd.to_datetime(d.date).dt.day_name() == d.day_of_week),
    ],
    "dim_security": [
        ("asset_class in list", lambda d: in_list(d.asset_class, {"Equity", "Fixed Income", "Alternative", "Cash Equivalent"})),
        ("expense_ratio_bps 0-300", lambda d: between(d.expense_ratio_bps, 0, 300)),
        ("sector blank iff ETF", lambda d: (d.sector == "") == (d.is_etf == "True")),
    ],
    "fact_fees": [
        ("fee_type in list", lambda d: in_list(d.fee_type, {"Advisory", "Management", "Custodial", "Performance"})),
        ("bps_charged 0-100", lambda d: between(d.bps_charged, 0, 100)),
        ("amount > 0", lambda d: between(d.amount, 0.01)),
        ("aum_basis > 0", lambda d: between(d.aum_basis, 0.01)),
    ],
    "fact_portfolio_snapshot": [
        ("aum > 0", lambda d: between(d.aum, 0.01)),
        ("cash_pct 0-1", lambda d: between(d.cash_pct, 0, 1)),
        ("return_ytd >= -100%", lambda d: between(d.return_ytd, -1)),
        ("account_type in list", lambda d: in_list(d.account_type, ACCOUNTS)),
        ("month 1-12", lambda d: between(d.month, 1, 12)),
    ],
    "fact_transactions": [
        ("txn_type in list", lambda d: in_list(d.txn_type, {"Buy", "Sell", "Dividend", "Deposit", "Withdrawal", "Advisory Fee"})),
        ("amount > 0", lambda d: between(d.amount, 0.01)),
        ("price > 0", lambda d: between(d.price, 0.01)),
        ("shares > 0 (sign rule)", lambda d: between(d.shares, 0.0001)),
        ("txn_date 2020-2024", lambda d: (d.txn_date >= "2020-01-01") & (d.txn_date <= "2024-12-31")),
    ],
}


# =================================================================
# 4. SCORECARD METRICS
# =================================================================
def pct(passed, total):
    return round(passed / total * 100, 2) if total else None


def completeness(table, df, columns):
    """columns = the RAW column list, so added flag columns don't change the denominator."""
    allowed = expected_blank(table, df)
    filled = expected = 0
    for col in columns:
        must_fill = ~allowed.get(col, pd.Series(False, index=df.index))
        expected += must_fill.sum()
        filled += (must_fill & (df[col].str.strip() != "")).sum()
    return pct(filled, expected)


def key_uniqueness(table, df):
    dup = df[PRIMARY_KEYS[table]].duplicated(keep=False)
    if table in NATURAL_KEYS:
        dup |= df.duplicated(NATURAL_KEYS[table], keep=False)
    return pct((~dup).sum(), len(df))


def type_validity(table, df):
    ok = total = 0
    for col, pattern in COLUMN_TYPES[table].items():
        s = df[col][df[col] != ""]
        total += len(s)
        valid = s.str.fullmatch(pattern)
        if pattern == DATE:   # shape AND a real date (rejects 2024-99-99)
            valid &= pd.to_datetime(s, format="%Y-%m-%d", errors="coerce").notna()
        ok += valid.sum()
    return pct(ok, total)


def rule_pass(table, df, stage, rule_rows):
    ok = total = 0
    for name, rule in RULES[table]:
        result = rule(df).dropna().astype(bool)
        ok += result.sum()
        total += len(result)
        rule_rows.append({"stage": stage, "table": table, "rule": name,
                          "evaluated": len(result), "failed": int((~result).sum()),
                          "pass_pct": pct(result.sum(), len(result))})
    return pct(ok, total)


def referential_match(table, tables, stage, ri_rows):
    """Pooled match rate across every FK that starts in this table."""
    matched = checked = 0
    for child, fk, parent, pk in RELATIONSHIPS:
        if child != table:
            continue
        r = check_referential_integrity(tables[child], fk, tables[parent], pk)
        n = r["checked_rows"]
        checked += n
        matched += n - r["orphan_rows"]
        ri_rows.append({"stage": stage, "relationship": f"{child}.{fk} -> {parent}.{pk}", **r})
    return pct(matched, checked) if checked else None   # None = table has no FKs


# =================================================================
# 5. CROSS-TABLE RECONCILIATIONS
# =================================================================
def reconciliations(tables, stage):
    rows = []
    f, s, t = tables["fact_fees"], tables["fact_portfolio_snapshot"], tables["fact_transactions"]

    # R1: fee amount recomputed from AUM x bps / 10,000 / 12
    calc = num(f.aum_basis) * num(f.bps_charged) / 10000 / 12
    ok = (calc - num(f.amount)).abs() <= 0.05
    rows.append(("R1 fee amount = aum_basis x bps / 10000 / 12", len(f), ok.sum()))

    # R2: fee AUM basis must equal the snapshot AUM for the same client and month (two tables)
    snap_keys = s[["client_id", "snapshot_date", "aum"]]
    assert not snap_keys.duplicated(["client_id", "snapshot_date"]).any(), "duplicate snapshot keys would multiply rows"
    m = f.merge(snap_keys, left_on=["client_id", "fee_date"], right_on=["client_id", "snapshot_date"], how="left")
    ok = (num(m.aum_basis) - num(m.aum)).abs() <= 0.01      # fee with no snapshot -> NaN -> counts as a miss
    assert len(m) == len(f)
    rows.append(("R2 fees.aum_basis = snapshot.aum (same client & month)", len(m), ok.sum()))

    # R3: active alpha recomputed from return - benchmark return
    ok = (num(s.return_ytd) - num(s.benchmark_return_ytd) - num(s.active_alpha_ytd)).abs() <= 1e-4
    rows.append(("R3 alpha = return_ytd - benchmark_return_ytd", len(s), ok.sum()))

    # R4: trade amount recomputed from shares x price (signed shares, as stored)
    tr = t[t.txn_type.isin(["Buy", "Sell", "Dividend"])]
    ok = (num(tr.shares) * num(tr.price) - num(tr.amount)).abs() <= 0.05
    rows.append(("R4 trade amount = shares x price", len(tr), ok.sum()))

    # R5: fact advisor must equal the client's advisor in dim_client (fact vs dimension)
    m = t.merge(tables["dim_client"][["client_id", "advisor_id"]], on="client_id", how="left", suffixes=("", "_dim"))
    ok = m.advisor_id == m.advisor_id_dim                     # no matching client -> counts as a miss
    assert len(m) == len(t)
    rows.append(("R5 transactions.advisor_id = dim_client.advisor_id", len(m), ok.sum()))

    return [{"stage": stage, "reconciliation": n, "rows_compared": int(c), "matched": int(k),
             "match_pct": pct(k, c)} for n, c, k in rows]


# =================================================================
# 6. IQR OUTLIERS (columns with no natural upper bound)
# =================================================================
IQR_COLUMNS = [("fact_transactions", "amount"), ("fact_fees", "amount"),
               ("fact_portfolio_snapshot", "aum")]


def iqr_outliers(tables, stage):
    rows = []
    for table, col in IQR_COLUMNS:
        x = num(tables[table][col]).dropna()
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        flagged = (x < lo) | (x > hi)
        rows.append({"stage": stage, "table": table, "column": col, "q1": round(q1, 2), "q3": round(q3, 2),
                     "lower_fence": round(lo, 2), "upper_fence": round(hi, 2),
                     "outliers": int(flagged.sum()), "outlier_pct": pct(flagged.sum(), len(x)),
                     "max_value": round(x.max(), 2)})
    return rows


# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    scorecard, ri_rows, rule_rows, recon_rows, iqr_rows = [], [], [], [], []
    RAW_COLUMNS = {t: list(df.columns) for t, df in load("raw").items()}

    for stage in STAGES:
        tables = load(stage)
        for t in TABLE_NAMES:
            df = tables[t]
            scorecard.append({
                "table": t, "stage": stage, "rows": len(df),
                "pct_completeness": completeness(t, df, RAW_COLUMNS[t]),
                "pct_key_uniqueness": key_uniqueness(t, df),
                "pct_type_validity": type_validity(t, df),
                "pct_rule_pass": rule_pass(t, df, stage, rule_rows),
                "pct_referential_match": referential_match(t, tables, stage, ri_rows),
            })
        recon_rows += reconciliations(tables, stage)
        iqr_rows += iqr_outliers(tables, stage)

    sc = pd.DataFrame(scorecard).sort_values(["table", "stage"], ascending=[True, False])
    sc.to_csv(REPORTS / "data_quality_scorecard.csv", index=False)
    pd.DataFrame(ri_rows).to_csv(REPORTS / "ri_results.csv", index=False)
    pd.DataFrame(rule_rows).to_csv(REPORTS / "rule_results.csv", index=False)
    pd.DataFrame(recon_rows).to_csv(REPORTS / "reconciliations.csv", index=False)
    pd.DataFrame(iqr_rows).to_csv(REPORTS / "iqr_outliers.csv", index=False)

    pd.set_option("display.width", 200)
    print("=== DATA QUALITY SCORECARD (raw vs clean) ===")
    print(sc.to_string(index=False))

    ri = pd.DataFrame(ri_rows)
    ri_wide = ri.pivot(index="relationship", columns="stage", values="match_rate")[["raw", "clean"]]
    print("\n=== REFERENTIAL INTEGRITY: match rate (13 relationships) ===")
    print(ri_wide.to_string())

    print("\n=== RULES THAT FAIL IN EITHER STAGE ===")
    rr = pd.DataFrame(rule_rows).pivot_table(index=["table", "rule"], columns="stage", values="failed")
    print(rr[(rr.raw > 0) | (rr.clean > 0)][["raw", "clean"]].to_string())

    print("\n=== CROSS-TABLE RECONCILIATIONS (% matched) ===")
    print(pd.DataFrame(recon_rows).pivot(index="reconciliation", columns="stage", values="match_pct")[["raw", "clean"]].to_string())

    print("\n=== IQR OUTLIERS (clean) ===")
    print(pd.DataFrame(iqr_rows).query("stage == 'clean'").drop(columns="stage").to_string(index=False))
    print("\nNote: 'flagged' by IQR does NOT mean 'wrong'. Wealth data is heavily right-skewed, "
          "so a $40M UHNW account or a large rebalancing trade lands outside the fences while being "
          "completely real; IQR flags tell us where to look, and only a business rule or a "
          "reconciliation can prove a value is an error.")

    # The clean data must be at least as good as raw on every metric
    for metric in ["pct_completeness", "pct_key_uniqueness", "pct_type_validity",
                   "pct_rule_pass", "pct_referential_match"]:
        w = sc.pivot(index="table", columns="stage", values=metric).dropna()
        assert (w.clean >= w.raw).all(), f"clean is worse than raw on {metric}!"
    # Better scores must not come from silently dropping rows: raw = clean + quarantined
    recon = pd.read_csv(BASE / "data" / "audit" / "row_reconciliation.csv")
    for _, r in recon.iterrows():
        clean_rows = sc[(sc.table == r.table) & (sc.stage == "clean")].rows.iloc[0]
        raw_rows = sc[(sc.table == r.table) & (sc.stage == "raw")].rows.iloc[0]
        assert raw_rows == clean_rows + r.quarantined_rows, f"{r.table}: rows unaccounted for!"
    print("\nAll metrics: clean >= raw for every table, and raw rows = clean + quarantined. Saved reports to /reports.")
