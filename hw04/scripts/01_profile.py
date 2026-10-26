"""
HW4 Part A: Audit of the raw Wildcat Capital tables.

Section 1 - generic column profiler (works on ANY table)
Section 2 - data-quality checks in four groups:
    1. Column level        (type, allowed values, ranges, key uniqueness)
    2. Single-table rules  (duplicates, near-duplicates, row contradictions)
    3. Referential integrity (every foreign key must find its primary key)
    4. Cross-table rules   (facts that disagree with dimensions or each other)

Every finding is tagged:
    ERROR = wrong, or will break a join / calculation
    WARN  = probably wrong, investigate
    INFO  = worth knowing (often legitimate structure)

Outputs: reports/profile_raw.csv, reports/dq_summary_raw.csv
"""
import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
REPORTS = BASE / "reports"
REPORTS.mkdir(exist_ok=True)


# =================================================================
# SECTION 1: GENERIC PROFILER
# =================================================================
def load_table(path):
    """Read a CSV as pure text so pandas can't silently change anything."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def value_shape(value):
    """Digits -> 9, letters -> a.  '2020-01-01' -> '9999-99-99'."""
    shape = re.sub(r"[0-9]", "9", value)
    return re.sub(r"[A-Za-z]", "a", shape)


def guess_type(values):
    """Guess the intended type from the majority of non-blank values."""
    if len(values) == 0:
        return "text"
    # Codes with leading zeros (ZIPs like '03897') are identifiers, not numbers
    if values.str.match(r"^0\d").any():
        return "text"
    if pd.to_numeric(values, errors="coerce").notna().mean() >= 0.9:
        return "numeric"
    if values.str.match(r"^\d{4}-\d{2}-\d{2}$").mean() >= 0.9:
        return "date"
    return "text"


def profile_column(table_name, col_name, series):
    total = len(series)
    non_blank = series[series.str.strip() != ""]
    expected = guess_type(non_blank)

    if expected == "numeric":
        nums = pd.to_numeric(non_blank, errors="coerce")
        failed, col_min, col_max = nums.isna().sum(), nums.min(), nums.max()
    elif expected == "date":
        parsed = pd.to_datetime(non_blank, format="%Y-%m-%d", errors="coerce")
        failed, col_min, col_max = parsed.isna().sum(), parsed.min(), parsed.max()
    else:
        failed, col_min, col_max = 0, None, None

    shapes = non_blank.map(value_shape).value_counts()
    return {
        "table": table_name,
        "column": col_name,
        "rows": total,
        "blank_count": total - len(non_blank),
        "blank_pct": round((total - len(non_blank)) / total * 100, 2),
        "distinct_count": series.nunique(),
        "expected_type": expected,
        "parse_fail_count": int(failed),
        "parse_fail_pct": round(failed / max(len(non_blank), 1) * 100, 2),
        "whitespace_issues": int((series != series.str.strip()).sum()),
        "shape_count": len(shapes),
        "top_shapes": "; ".join(f"{s} ({n})" for s, n in shapes.head(4).items()),
        "min": col_min,
        "max": col_max,
        "sample_values": "; ".join(non_blank.drop_duplicates().head(5)),
    }


def profile_table(table_name, df):
    return [profile_column(table_name, c, df[c]) for c in df.columns]


# =================================================================
# SECTION 2: DATA-QUALITY CHECKS
# =================================================================
# The check FUNCTIONS below are generic. The RULES (which column has
# which allowed values, which key points where) are business knowledge,
# so they live in small dictionaries you can read and edit.

findings = []


def add_finding(severity, group, table, column, check, failed, total, example="", note=""):
    """Record one check result. Passing checks are kept too (as INFO 'pass')
    so the summary shows what was tested, not just what broke."""
    findings.append({
        "severity": severity if (failed or severity == "INFO") else "PASS",
        "group": group,
        "table": table,
        "column": column,
        "check": check,
        "failed_rows": int(failed),
        "total_rows": int(total),
        "failed_pct": round(failed / max(total, 1) * 100, 3),
        "example": str(example)[:120],
        "note": note,
    })


def examples(series, n=3):
    return "; ".join(series.astype(str).head(n))


def num(series):
    """Convert text to numbers on purpose; bad values become NaN."""
    return pd.to_numeric(series, errors="coerce")


# ---------------- Rule dictionaries ----------------
PRIMARY_KEYS = {
    "dim_advisor": "advisor_id", "dim_benchmark": "benchmark_id",
    "dim_client": "client_id", "dim_date": "date_id",
    "dim_security": "security_id", "fact_fees": "fee_id",
    "fact_portfolio_snapshot": "snapshot_id", "fact_transactions": "txn_id",
}

US_STATES = set("""AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS
MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC""".split())

ACCOUNT_TYPES = {"Taxable", "IRA", "Roth IRA", "Trust", "529"}

# (table, column) -> set of allowed values
ALLOWED_VALUES = {
    ("dim_advisor", "region"): {"Northeast", "Southeast", "Mid-Atlantic", "West", "Midwest"},
    ("dim_client", "state"): US_STATES,
    ("dim_client", "risk_profile"): {"Conservative", "Moderately Conservative", "Balanced",
                                     "Moderately Aggressive", "Aggressive"},
    ("dim_client", "client_tier"): {"Retail", "HNW", "UHNW"},
    ("dim_client", "primary_account_type"): ACCOUNT_TYPES,
    ("dim_client", "is_active"): {"True", "False"},
    ("dim_security", "asset_class"): {"Equity", "Fixed Income", "Alternative", "Cash Equivalent"},
    ("dim_security", "is_etf"): {"True", "False"},
    ("fact_fees", "fee_type"): {"Advisory", "Management", "Custodial", "Performance"},
    ("fact_portfolio_snapshot", "account_type"): ACCOUNT_TYPES,
    ("fact_transactions", "txn_type"): {"Buy", "Sell", "Dividend", "Deposit",
                                        "Withdrawal", "Advisory Fee"},
}

# (table, column) -> (min, max, severity). None = no bound on that side.
RANGES = {
    ("dim_advisor", "years_experience"): (0, 50, "ERROR"),
    ("dim_client", "age"): (18, 110, "ERROR"),
    ("dim_client", "initial_aum"): (0.01, None, "ERROR"),
    ("dim_security", "expense_ratio_bps"): (0, 300, "WARN"),
    ("fact_fees", "bps_charged"): (0, 100, "WARN"),       # >1% a year is unusual
    ("fact_fees", "amount"): (0.01, None, "ERROR"),
    ("fact_fees", "aum_basis"): (0.01, None, "ERROR"),
    ("fact_portfolio_snapshot", "aum"): (0.01, None, "ERROR"),
    ("fact_portfolio_snapshot", "cash_pct"): (0, 1, "ERROR"),
    ("fact_portfolio_snapshot", "return_ytd"): (-1, 1, "WARN"),  # >100% YTD is implausible
    ("fact_portfolio_snapshot", "benchmark_return_ytd"): (-1, 1, "WARN"),
    ("fact_transactions", "price"): (0.01, None, "ERROR"),
    ("fact_transactions", "amount"): (0.01, None, "ERROR"),
}

# Columns that must hold whole-number IDs (e.g. '45', not '45.0')
INTEGER_ID_COLUMNS = [
    ("fact_transactions", "security_id"), ("fact_transactions", "client_id"),
    ("fact_fees", "client_id"), ("fact_portfolio_snapshot", "client_id"),
    ("dim_client", "advisor_id"), ("dim_security", "benchmark_id"),
]

# Columns that must never be blank
REQUIRED = [
    ("dim_client", "risk_profile"), ("dim_client", "state"), ("dim_client", "advisor_id"),
    ("fact_transactions", "client_id"), ("fact_transactions", "amount"),
    ("fact_fees", "amount"), ("fact_portfolio_snapshot", "aum"),
]

# The 10 ID relationships + 3 date relationships
# (fact table, fact column, dim table, dim column)
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


# ---------------- Group 1: column level ----------------
def check_column_level(tables, profile):
    G = "1 Column"
    # Type validity: anything the profiler could not parse
    for _, p in profile[profile.parse_fail_count > 0].iterrows():
        df = tables[p.table]
        col = df[p.column]
        nb = col[col.str.strip() != ""]
        if p.expected_type == "numeric":
            bad = nb[num(nb).isna()]
        else:   # date: show only the values that actually failed
            bad = nb[pd.to_datetime(nb, format="%Y-%m-%d", errors="coerce").isna()]
        # Denominator = non-blank values, i.e. the values actually tested
        add_finding("ERROR", G, p.table, p.column, f"values not parseable as {p.expected_type}",
                    p.parse_fail_count, len(nb), examples(bad))

    # Whitespace problems
    for _, p in profile[profile.whitespace_issues > 0].iterrows():
        add_finding("WARN", G, p.table, p.column, "leading/trailing spaces",
                    p.whitespace_issues, p.rows)

    # Mixed number formats: scientific notation ('9.9e-05') among plain decimals
    for table, df in tables.items():
        for col in df.columns:
            sci = df[col][df[col].str.fullmatch(r"-?\d+(\.\d+)?[eE][-+]?\d+")]
            if len(sci):
                add_finding("WARN", G, table, col, "number stored in scientific notation",
                            len(sci), len(df), examples(sci),
                            "valid number, but inconsistent with plain decimals in the same column")

    # Primary-key uniqueness and blanks
    for table, key in PRIMARY_KEYS.items():
        k = tables[table][key]
        dupes = k.duplicated(keep=False).sum()
        add_finding("ERROR", G, table, key, "primary key unique", dupes, len(k))
        add_finding("ERROR", G, table, key, "primary key not blank", (k.str.strip() == "").sum(), len(k))

    # Allowed values (blanks are handled by the REQUIRED check)
    for (table, col), allowed in ALLOWED_VALUES.items():
        s = tables[table][col]
        bad = s[(s != "") & ~s.isin(allowed)]
        add_finding("ERROR", G, table, col, "value in allowed list", len(bad), len(s),
                    examples(bad.value_counts().index.to_series()))

    # Required (not blank)
    for table, col in REQUIRED:
        s = tables[table][col]
        add_finding("ERROR", G, table, col, "required field not blank",
                    (s.str.strip() == "").sum(), len(s))

    # Ranges
    for (table, col), (lo, hi, sev) in RANGES.items():
        s = num(tables[table][col])
        bad = pd.Series(False, index=s.index)
        if lo is not None:
            bad |= s < lo
        if hi is not None:
            bad |= s > hi
        add_finding(sev, G, table, col, f"range [{lo}, {hi}]", bad.sum(), s.notna().sum(),
                    examples(tables[table].loc[bad, col]))

    # Integer-ID format ('45.0' breaks text joins and looks like a float)
    for table, col in INTEGER_ID_COLUMNS:
        s = tables[table][col]
        bad = s[(s != "") & ~s.str.fullmatch(r"\d+")]
        add_finding("ERROR", G, table, col, "ID stored as whole number", len(bad), (s != "").sum(),
                    examples(bad), "float-formatted IDs ('45.0') will not join to '45'")


# ---------------- Group 2: single-table rules ----------------
def check_single_table(tables):
    G = "2 Single-table"
    # Exact duplicate rows (ignoring the surrogate key)
    for table, key in PRIMARY_KEYS.items():
        df = tables[table]
        dup = df.drop(columns=key).duplicated(keep=False).sum()
        add_finding("ERROR", G, table, "(all)", "exact duplicate rows (excluding key)", dup, len(df))

    c = tables["dim_client"]
    # Near-duplicate clients: same person, slightly different spelling
    match_cols = ["first_name", "age", "city", "zip_code", "initial_aum", "client_since"]
    near = c[c.duplicated(match_cols, keep=False)].sort_values(match_cols)
    add_finding("ERROR", G, "dim_client", "last_name",
                "near-duplicate clients (all fields equal except name spelling)",
                len(near), len(c), examples(near.client_id + ":" + near.last_name, 4),
                "pairs share every attribute; one copy has a truncated last name")

    # Grain checks: one row per client per period
    s = tables["fact_portfolio_snapshot"]
    add_finding("ERROR", G, "fact_portfolio_snapshot", "client_id+snapshot_date",
                "one snapshot per client per month",
                s.duplicated(["client_id", "snapshot_date"], keep=False).sum(), len(s))
    f = tables["fact_fees"]
    add_finding("WARN", G, "fact_fees", "client_id+fee_date+fee_type",
                "one fee per client/month/type",
                f.duplicated(["client_id", "fee_date", "fee_type"], keep=False).sum(), len(f))

    # Snapshot year/month must agree with snapshot_date
    d = pd.to_datetime(s.snapshot_date, errors="coerce")
    bad = (d.dt.year.astype("Int64").astype(str) != s.year) | (d.dt.month.astype("Int64").astype(str) != s.month)
    add_finding("ERROR", G, "fact_portfolio_snapshot", "year/month", "year & month match snapshot_date",
                bad.sum(), len(s))

    # Alpha must equal return minus benchmark return (recompute and compare)
    ret = num(s.return_ytd)
    alpha_gap = (ret - num(s.benchmark_return_ytd) - num(s.active_alpha_ytd)).abs()
    unchecked = alpha_gap.isna().sum()   # NaN = an input was unparseable, so the row was NOT tested
    add_finding("ERROR", G, "fact_portfolio_snapshot", "active_alpha_ytd",
                "alpha = return_ytd - benchmark_return_ytd", (alpha_gap > 1e-4).sum(), alpha_gap.notna().sum(),
                note=f"{unchecked} rows could not be checked (unparseable input, e.g. '%' text); "
                     f"they are re-checked after cleaning in 03_validate.py")

    # Placeholder values: AUM of exactly 1,000.00 is a system floor, not a real balance
    for table, col in [("fact_portfolio_snapshot", "aum"), ("fact_fees", "aum_basis")]:
        bad = num(tables[table][col]) == 1000
        add_finding("WARN", G, table, col, "placeholder value 1000.0", bad.sum(), len(tables[table]),
                    note="identical floor value across many clients/months")

    # Fee amount = AUM x bps / 10,000 / 12 (monthly)
    calc = num(f.aum_basis) * num(f.bps_charged) / 10000 / 12
    gap = (calc - num(f.amount)).abs()
    add_finding("ERROR", G, "fact_fees", "amount", "amount = aum_basis x bps / 10000 / 12",
                (gap > 0.05).sum(), len(f))

    t = tables["fact_transactions"]
    sh, px, amt = num(t.shares), num(t.price), num(t.amount)
    trade_types = {"Buy", "Sell", "Dividend"}
    is_trade = t.txn_type.isin(trade_types)

    # Trade rows need security/shares/price; cash rows must not have them
    missing = is_trade & ((t.security_id == "") | (t.shares == "") | (t.price == ""))
    add_finding("ERROR", G, "fact_transactions", "security_id/shares/price",
                "trade rows have security, shares and price", missing.sum(), is_trade.sum())
    extra = ~is_trade & ((t.security_id != "") | (t.shares != "") | (t.price != ""))
    add_finding("ERROR", G, "fact_transactions", "security_id/shares/price",
                "cash rows (Deposit/Withdrawal/Fee) have no security", extra.sum(), (~is_trade).sum())
    add_finding("INFO", G, "fact_transactions", "security_id/shares/price",
                "blanks on cash rows are legitimate structure", 0, (~is_trade).sum(),
                note=f"{(~is_trade).sum():,} Deposit/Withdrawal/Advisory Fee rows correctly blank")

    # Sign rule: share counts should be positive (direction lives in txn_type)
    neg = is_trade & (sh < 0)
    add_finding("ERROR", G, "fact_transactions", "shares", "shares positive (direction is in txn_type)",
                neg.sum(), is_trade.sum(), examples(t.loc[neg, "txn_type"] + " " + t.loc[neg, "shares"]),
                f"by type: {t.loc[neg, 'txn_type'].value_counts().to_dict()}")

    # Amount = |shares| x price for trades
    gap = ((sh.abs() * px) - amt).abs()
    add_finding("ERROR", G, "fact_transactions", "amount", "trade amount = |shares| x price",
                (is_trade & (gap > 0.05)).sum(), is_trade.sum())

    # Security: ETF flag must line up with sector / expense ratio
    sec = tables["dim_security"]
    etf = sec.is_etf == "True"
    bad = (etf & (sec.sector != "")) | (~etf & (sec.sector == ""))
    add_finding("ERROR", G, "dim_security", "sector", "sector blank if and only if ETF", bad.sum(), len(sec),
                note="219 blank sectors are all ETFs -> legitimate structure")
    bad = (etf & (sec.expense_ratio_bps == "")) | (~etf & (sec.expense_ratio_bps != ""))
    add_finding("ERROR", G, "dim_security", "expense_ratio_bps", "expense ratio present if and only if ETF",
                bad.sum(), len(sec), note="281 blanks are all non-ETFs -> legitimate structure")

    # Advisor certifications: the text 'None' is a real value, not a null
    a = tables["dim_advisor"]
    add_finding("INFO", G, "dim_advisor", "certifications", "literal 'None' = advisor has no certification",
                0, len(a), note=f"{(a.certifications == 'None').sum()} advisors; keep as text, not null")

    # Calendar table must agree with itself
    dd = tables["dim_date"]
    dt = pd.to_datetime(dd.date, errors="coerce")
    flag = lambda s: s.astype(int).astype(str)
    bad = ((dt.dt.day_name() != dd.day_of_week)
           | (dt.dt.year.astype(str) != dd.year)
           | (dt.dt.month.astype(str) != dd.month)
           | (dt.dt.month_name() != dd.month_name)
           | (dt.dt.quarter.astype(str) != dd.quarter)
           | (dt.dt.isocalendar().week.astype(str) != dd.week_of_year)
           | (flag(dt.dt.is_month_end) != dd.is_month_end)
           | (flag(dt.dt.is_quarter_end) != dd.is_quarter_end)
           | (flag(dt.dt.is_year_end) != dd.is_year_end)
           | (flag(dt.dt.weekday < 5) != dd.is_trading_day))   # trading day = weekday in this dataset
    add_finding("ERROR", G, "dim_date", "(derived cols)", "calendar attributes match the date", bad.sum(), len(dd))


# ---------------- Group 3: referential integrity ----------------
def check_referential_integrity(fact_df, fact_key, dim_df, dim_key):
    """Generic FK check, compared as TEXT (the way a BI tool joins)."""
    keys = fact_df[fact_key]
    non_null = keys[keys.str.strip() != ""]
    valid = set(dim_df[dim_key])
    orphans = non_null[~non_null.isin(valid)]
    return {
        "match_rate": round(1 - len(orphans) / max(len(non_null), 1), 4),
        "orphan_rows": len(orphans),
        "distinct_orphan_keys": orphans.nunique(),
        "null_key_rate": round(1 - len(non_null) / max(len(keys), 1), 4),
        "orphan_examples": examples(orphans.drop_duplicates()),
        "checked_rows": len(non_null),
    }


def check_ri_all(tables):
    G = "3 Referential"
    for fact, fk, dim, pk in RELATIONSHIPS:
        r = check_referential_integrity(tables[fact], fk, tables[dim], pk)
        note = f"match {r['match_rate']:.2%}, {r['distinct_orphan_keys']} distinct orphan keys, null-key rate {r['null_key_rate']:.2%}"
        # Diagnose: would the orphans match if the format were fixed?
        if r["orphan_rows"]:
            fixed = num(tables[fact][fk]).dropna().astype("int64").astype(str)
            still = (~fixed.isin(set(tables[dim][pk]))).sum()
            if still < r["orphan_rows"]:
                note += f"; after int conversion only {still} orphans remain (format problem)"
        add_finding("ERROR", G, fact, fk, f"FK -> {dim}.{pk}", r["orphan_rows"], r["checked_rows"],
                    r["orphan_examples"], note)
        if r["null_key_rate"] > 0:
            add_finding("INFO", G, fact, fk, f"null FK -> {dim}.{pk}",
                        round(r["null_key_rate"] * len(tables[fact])), len(tables[fact]),
                        note="see single-table check: nulls on cash rows are expected")

    # Unused dimension rows (not wrong by itself)
    c = tables["dim_client"]
    used = set(tables["fact_portfolio_snapshot"].client_id) | set(tables["fact_transactions"].client_id) \
        | set(tables["fact_fees"].client_id)
    unused = c[~c.client_id.isin(used)]
    add_finding("WARN", G, "dim_client", "client_id", "client has activity in at least one fact table",
                len(unused), len(c), examples(unused.client_id + ":" + unused.last_name),
                "check against near-duplicate finding")


# ---------------- Group 4: cross-table rules ----------------
def check_cross_table(tables):
    G = "4 Cross-table"
    c = tables["dim_client"][["client_id", "advisor_id", "primary_account_type", "client_since", "risk_profile"]]

    # Fact advisor must equal the client's advisor in dim_client
    for fact in ["fact_fees", "fact_portfolio_snapshot", "fact_transactions"]:
        m = tables[fact].merge(c, on="client_id", how="inner", suffixes=("", "_dim"))
        add_finding("ERROR", G, fact, "advisor_id", "advisor matches dim_client.advisor_id",
                    (m.advisor_id != m.advisor_id_dim).sum(), len(m))

    # Snapshot account type must equal client's primary account type
    s = tables["fact_portfolio_snapshot"]
    m = s.merge(c, on="client_id", how="inner")
    add_finding("ERROR", G, "fact_portfolio_snapshot", "account_type",
                "account_type matches dim_client.primary_account_type",
                (m.account_type != m.primary_account_type).sum(), len(m))

    # Snapshot AUM and fee AUM basis describe the same fact
    f = tables["fact_fees"]
    m = f.merge(s, left_on=["client_id", "fee_date"], right_on=["client_id", "snapshot_date"], how="inner")
    add_finding("ERROR", G, "fact_fees", "aum_basis", "fee aum_basis = snapshot aum (same client, month)",
                (num(m.aum_basis) - num(m.aum)).abs().gt(0.01).sum(), len(m))

    # Benchmark in snapshots should follow the client's risk profile
    m = s.drop_duplicates("client_id").merge(c, on="client_id")
    mapping = m[m.risk_profile != ""].groupby("risk_profile").benchmark_id.nunique()
    add_finding("INFO", G, "fact_portfolio_snapshot", "benchmark_id",
                "each risk_profile maps to exactly one benchmark", (mapping > 1).sum(), len(mapping),
                note=str(m[m.risk_profile != ""].groupby("risk_profile").benchmark_id.first().to_dict()))
    blank = m[m.risk_profile == ""]
    add_finding("WARN", G, "dim_client", "risk_profile", "clients with blank risk_profile (benchmark known)",
                len(blank), len(m), note=f"their snapshot benchmark_ids: {blank.benchmark_id.value_counts().to_dict()}")

    # No activity before the client relationship started
    t = tables["fact_transactions"]
    m = t.merge(c, on="client_id", how="inner")
    add_finding("ERROR", G, "fact_transactions", "txn_date", "txn_date on/after client_since",
                (m.txn_date < m.client_since).sum(), len(m))

    # Trades on non-trading days (weekends)
    d = tables["dim_date"][["date", "is_trading_day"]]
    m = t.merge(d, left_on="txn_date", right_on="date", how="inner")
    trades = m.txn_type.isin({"Buy", "Sell"})
    bad = trades & (m.is_trading_day == "0")
    add_finding("WARN", G, "fact_transactions", "txn_date", "Buy/Sell on a trading day",
                bad.sum(), trades.sum(), note="weekend trades may be booking dates, not trade dates")

    # Fee rates should sit inside the client's tier band
    m = f.merge(tables["dim_client"][["client_id", "client_tier"]], on="client_id")
    band = m.groupby("client_tier").bps_charged.apply(lambda x: f"{num(x).min()}-{num(x).max()}")
    add_finding("INFO", G, "fact_fees", "bps_charged", "bps range by client tier", 0, len(m),
                note=str(band.to_dict()))


# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    tables = {}
    profile_rows = []
    for path in sorted(RAW.glob("*.csv")):
        df = load_table(path)
        tables[path.stem] = df
        print(f"Profiling {path.stem}: {len(df):,} rows x {len(df.columns)} cols")
        profile_rows.extend(profile_table(path.stem, df))

    profile = pd.DataFrame(profile_rows)
    profile.to_csv(REPORTS / "profile_raw.csv", index=False)
    print(f"Saved {len(profile)} column profiles -> reports/profile_raw.csv\n")

    check_column_level(tables, profile)
    check_single_table(tables)
    check_ri_all(tables)
    check_cross_table(tables)

    dq = pd.DataFrame(findings)
    order = {"ERROR": 0, "WARN": 1, "INFO": 2, "PASS": 3}
    dq = dq.sort_values(["severity", "group", "table"], key=lambda s: s.map(order) if s.name == "severity" else s)
    dq.to_csv(REPORTS / "dq_summary_raw.csv", index=False)

    print("Findings by severity:", dq.severity.value_counts().to_dict())
    print("\nProblems found:")
    print(dq[dq.severity.isin(["ERROR", "WARN"])][["severity", "table", "column", "check", "failed_rows"]]
          .to_string(index=False))
    print("\nSaved -> reports/dq_summary_raw.csv")
