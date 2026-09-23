# Cross-validation Prompt B:
# "Write Python to count the total rows in fact_transactions.csv, then subtract the
#  count of rows where txn_type is Sell, Deposit, Withdrawal, Dividend, or Advisory Fee."
import pandas as pd

df = pd.read_csv("data/raw/fact_transactions.csv")

total_rows = len(df)
other_types = ["Sell", "Deposit", "Withdrawal", "Dividend", "Advisory Fee"]
other_count = df["txn_type"].isin(other_types).sum()

buy_count = total_rows - other_count
print(f"Total rows:            {total_rows:,}")
print(f"Non-Buy rows:          {other_count:,}")
print(f"Prompt B - Buy count (total minus others): {buy_count:,}")
