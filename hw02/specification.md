# HW2 Specification: EDA Script for fact_transactions.csv

## Goal
Write ONE Python script (hw02/hw02_eda.py) that runs an exploratory data analysis on Wildcat Capital's transaction data in a single run. Use pandas and matplotlib. All file paths should be relative to the repository root, since I will run it with `python hw02/hw02_eda.py`.

## What the script should do, in order

1. Put a comment block at the very top with the script name, the dataset (fact_transactions.csv), the author (Lucas Farach), and the date it was generated.
2. Load `data/raw/fact_transactions.csv` into a pandas DataFrame.
3. Print the shape of the data (rows × columns).
4. Print a warning if the shape is not (298772, 9).
5. Print every column name and its data type.
6. Print the number of missing values in every column.
7. Print descriptive statistics (count, mean, std, min, 25th percentile, median, 75th percentile, max) for all numeric columns.
8. Print the value counts and percentages for `txn_type`, sorted from most to least common.
9. Print how many unique clients, advisors, and securities are in the file.
10. Print the earliest and latest `txn_date`. Do not change the data type of the `txn_date` column itself.
11. Check for duplicate `txn_id` values and print how many there are.
12. Print the mean, median, and skewness of the `amount` column.
13. Group the data by `txn_type` and print the count, mean amount, and median amount for each type, rounded to 2 decimals and sorted by mean amount from highest to lowest.
14. Calculate the correlation matrix for `shares`, `price`, and `amount`, rounded to 2 decimals. Print it, then print the three strongest correlations between different variables (don't count a variable with itself).
15. For the `shares` column, print the minimum, the maximum, and the count of negative values, broken out by `txn_type`.
16. Create and save three charts in `hw02/charts/` (create the folder if it doesn't exist):
    - `hist_amount.png`: a histogram of `amount` with labeled vertical lines at the mean and the median
    - `box_amount_by_type.png`: a horizontal box plot of `amount` for each `txn_type`
    - `scatter_shares_amount.png`: a scatter plot with `shares` on the x-axis and `amount` on the y-axis, colored by `txn_type`
    Charts should be saved to files, not shown in a pop-up window.
17. Save a plain-text summary of everything from steps 3–15 to `hw02/hw02_profile.txt`.

## Other requirements
- Print a clear header before each section so the terminal output is easy to read.
- Everything must be in one script that runs start to finish without errors.