"""
===============================================================================
Script:     hw02_eda.py
Dataset:    fact_transactions.csv (Wildcat Capital client transactions, 2020-2024)
Author:     Lucas Farach
Generated:  2026-09-23 with Claude Cowork
Purpose:    Exploratory data analysis (EDA) for MIS3060 HW2. Loads the data,
            checks its structure and quality, summarizes distributions and
            relationships, saves three charts, and writes a text profile.
Run with:   python hw02/hw02_eda.py   (from the repository root)
===============================================================================
"""

import os

import matplotlib
matplotlib.use("Agg")  # save charts to files instead of opening pop-up windows
import matplotlib.pyplot as plt
import pandas as pd

# ---------------------------------------------------------------------------
# File paths (relative to the repository root)
# ---------------------------------------------------------------------------
DATA_PATH = "data/raw/fact_transactions.csv"
CHART_DIR = "hw02/charts"
PROFILE_PATH = "hw02/hw02_profile.txt"
EXPECTED_SHAPE = (298772, 9)

os.makedirs(CHART_DIR, exist_ok=True)

# Everything printed through out() is also saved for the profile file (item 16)
profile_lines = []


def out(text=""):
    """Print to the terminal AND remember the line for the profile file."""
    print(text)
    profile_lines.append(str(text))


def header(title):
    """Print a clear section header."""
    out()
    out("=" * 70)
    out(title)
    out("=" * 70)


def find_col(keyword):
    """Find the first column whose name contains the keyword (e.g. 'client')."""
    for col in df.columns:
        if keyword in col.lower():
            return col
    return None


# ---------------------------------------------------------------------------
# 1. Load the data
# ---------------------------------------------------------------------------
df = pd.read_csv(DATA_PATH)

# ---------------------------------------------------------------------------
# 2. Shape  +  14. Shape warning
# ---------------------------------------------------------------------------
header("1. DATASET SHAPE")
out(f"Rows: {df.shape[0]:,}   Columns: {df.shape[1]}")
out(f"Shape: {df.shape}")
if df.shape != EXPECTED_SHAPE:
    out(f"WARNING: expected shape {EXPECTED_SHAPE} but got {df.shape}")
else:
    out(f"Shape matches expected {EXPECTED_SHAPE}")

# ---------------------------------------------------------------------------
# 3. Column names and data types
# ---------------------------------------------------------------------------
header("2. COLUMN NAMES AND DATA TYPES")
for col, dtype in df.dtypes.items():
    out(f"{col:<20} {dtype}")

# ---------------------------------------------------------------------------
# 4. Missing values
# ---------------------------------------------------------------------------
header("3. MISSING VALUES PER COLUMN")
for col, n in df.isnull().sum().items():
    out(f"{col:<20} {n:,}")

# ---------------------------------------------------------------------------
# 5. Descriptive statistics for numeric columns
# ---------------------------------------------------------------------------
header("4. DESCRIPTIVE STATISTICS (NUMERIC COLUMNS)")
out(df.describe().round(2).to_string())

# ---------------------------------------------------------------------------
# 6. txn_type value counts and percentages
# ---------------------------------------------------------------------------
header("5. TRANSACTION TYPE COUNTS")
counts = df["txn_type"].value_counts()
pcts = df["txn_type"].value_counts(normalize=True) * 100
type_table = pd.DataFrame({"count": counts, "percent": pcts.round(2)})
out(type_table.to_string())
out(f"Unique txn_type values: {df['txn_type'].nunique()}")

# ---------------------------------------------------------------------------
# 7. Unique clients, advisors, securities
# ---------------------------------------------------------------------------
header("6. UNIQUE CLIENTS, ADVISORS, AND SECURITIES")
for label, keyword in [("Clients", "client"), ("Advisors", "advisor"), ("Securities", "security")]:
    col = find_col(keyword)
    if col:
        out(f"{label:<12} ({col}): {df[col].nunique():,}")
    else:
        out(f"{label:<12} column not found")

# ---------------------------------------------------------------------------
# 8. Date range (txn_date type is NOT changed)
# ---------------------------------------------------------------------------
header("7. DATE RANGE OF txn_date")
dates = pd.to_datetime(df["txn_date"])  # temporary copy, original column untouched
out(f"Earliest txn_date: {dates.min().date()}")
out(f"Latest txn_date:   {dates.max().date()}")
out(f"(txn_date is still stored as: {df['txn_date'].dtype})")

# ---------------------------------------------------------------------------
# 9. Duplicate txn_id check
# ---------------------------------------------------------------------------
header("8. DUPLICATE txn_id CHECK")
dup_count = df["txn_id"].duplicated().sum()
out(f"Duplicate txn_id values: {dup_count:,}")

# ---------------------------------------------------------------------------
# 10. Mean, median, skewness of amount
# ---------------------------------------------------------------------------
header("9. AMOUNT: MEAN, MEDIAN, SKEWNESS")
amount_mean = df["amount"].mean()
amount_median = df["amount"].median()
amount_skew = df["amount"].skew()
out(f"Mean amount:     ${amount_mean:,.2f}")
out(f"Median amount:   ${amount_median:,.2f}")
out(f"Skewness:        {amount_skew:.2f}"
    + ("  (right-skewed)" if amount_skew > 0 else "  (left-skewed)" if amount_skew < 0 else ""))

# ---------------------------------------------------------------------------
# 11. Group by txn_type
# ---------------------------------------------------------------------------
header("10. AMOUNT BY TRANSACTION TYPE (sorted by mean, highest first)")
grouped = (
    df.groupby("txn_type")["amount"]
    .agg(count="count", mean_amount="mean", median_amount="median")
    .round(2)
    .sort_values("mean_amount", ascending=False)
)
out(grouped.to_string())

# ---------------------------------------------------------------------------
# 12. Correlation matrix and three strongest correlations
# ---------------------------------------------------------------------------
header("11. CORRELATION MATRIX (shares, price, amount)")
corr = df[["shares", "price", "amount"]].corr().round(2)
out(corr.to_string())

pairs = []
cols = list(corr.columns)
for i in range(len(cols)):
    for j in range(i + 1, len(cols)):  # j > i skips self-pairs and repeats
        pairs.append((cols[i], cols[j], corr.iloc[i, j]))
pairs.sort(key=lambda p: abs(p[2]), reverse=True)

out()
out("Three strongest correlations (excluding self-correlation):")
for rank, (a, b, r) in enumerate(pairs[:3], start=1):
    out(f"  {rank}. {a} - {b}: {r:.2f}")

# ---------------------------------------------------------------------------
# 13. shares min / max / negative count by txn_type
# ---------------------------------------------------------------------------
header("12. SHARES: MIN, MAX, AND NEGATIVE COUNT BY TRANSACTION TYPE")
shares_table = df.groupby("txn_type")["shares"].agg(
    min_shares="min",
    max_shares="max",
    negative_count=lambda s: (s < 0).sum(),
)
out(shares_table.round(2).to_string())
out(f"Total negative shares rows: {(df['shares'] < 0).sum():,}")

# ---------------------------------------------------------------------------
# 15. Charts
# ---------------------------------------------------------------------------
header("13. SAVING CHARTS")

# Chart 1: histogram of amount with mean and median lines
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(df["amount"], bins=100, color="steelblue", edgecolor="white")
ax.axvline(amount_mean, color="red", linestyle="--", linewidth=2,
           label=f"Mean = ${amount_mean:,.0f}")
ax.axvline(amount_median, color="orange", linestyle="-", linewidth=2,
           label=f"Median = ${amount_median:,.0f}")
ax.set_title("Distribution of Transaction Amount")
ax.set_xlabel("Amount ($)")
ax.set_ylabel("Number of transactions")
ax.legend()
fig.tight_layout()
fig.savefig(f"{CHART_DIR}/hist_amount.png", dpi=150)
plt.close(fig)
out(f"Saved {CHART_DIR}/hist_amount.png")

# Chart 2: horizontal box plot of amount by txn_type
order = grouped.index.tolist()
fig, ax = plt.subplots(figsize=(10, 6))
ax.boxplot([df.loc[df["txn_type"] == t, "amount"] for t in order],
           vert=False, tick_labels=order, showfliers=True,
           flierprops={"markersize": 2, "alpha": 0.3})
ax.set_title("Transaction Amount by Transaction Type")
ax.set_xlabel("Amount ($)")
ax.set_ylabel("Transaction type")
fig.tight_layout()
fig.savefig(f"{CHART_DIR}/box_amount_by_type.png", dpi=150)
plt.close(fig)
out(f"Saved {CHART_DIR}/box_amount_by_type.png")

# Chart 3: scatter of shares vs amount, colored by txn_type
# (only rows with shares, i.e. transactions tied to a security, can be plotted)
fig, ax = plt.subplots(figsize=(10, 6))
for t, group in df.dropna(subset=["shares"]).groupby("txn_type"):
    ax.scatter(group["shares"], group["amount"], s=2, alpha=0.3, label=t)
ax.set_title("Shares vs. Amount by Transaction Type")
ax.set_xlabel("Shares")
ax.set_ylabel("Amount ($)")
ax.legend(markerscale=6)
fig.tight_layout()
fig.savefig(f"{CHART_DIR}/scatter_shares_amount.png", dpi=150)
plt.close(fig)
out(f"Saved {CHART_DIR}/scatter_shares_amount.png")

# ---------------------------------------------------------------------------
# 16. Save the text profile
# ---------------------------------------------------------------------------
with open(PROFILE_PATH, "w", encoding="utf-8") as f:
    f.write("HW2 EDA PROFILE: fact_transactions.csv\n")
    f.write("\n".join(profile_lines))
    f.write("\n")

print()
print(f"Profile saved to {PROFILE_PATH}")
print("EDA complete.")
