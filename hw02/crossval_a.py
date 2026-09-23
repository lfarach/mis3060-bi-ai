# Cross-validation Prompt A:
# "Write Python to count rows in fact_transactions.csv where txn_type equals exactly 'Buy'."
import pandas as pd

df = pd.read_csv("data/raw/fact_transactions.csv")

# Keep only rows where txn_type is exactly "Buy", then count them
buy_count = (df["txn_type"] == "Buy").sum()
print(f"Prompt A - Buy count (direct filter): {buy_count:,}")
