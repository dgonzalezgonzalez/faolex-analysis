#!/usr/bin/env python3
"""
Generate strategy_similarities_with_dates.csv by merging:
- strategy_similarities.csv (scores)
- policy_categories.csv (category)
- FAOLEX_Food.csv (date_original)
"""

import pandas as pd
from pathlib import Path

def main():
    # Load data
    sim_df = pd.read_csv('data/strategy_similarities.csv')
    sim_df = sim_df.rename(columns={'record_id': 'Record Id'})

    cat_df = pd.read_csv('data/policy_categories.csv')

    original_df = pd.read_csv('data/FAOLEX_Food.csv', encoding='utf-8-sig')
    first_col = original_df.columns[0]
    if first_col != 'Record Id':
        original_df = original_df.rename(columns={first_col: 'Record Id'})
    original_df.columns = original_df.columns.str.strip()
    # Keep only needed columns
    original_df = original_df[['Record Id', 'Date of original text']].rename(columns={'Date of original text': 'date_original'})

    # Merge
    merged = sim_df.merge(cat_df, on='Record Id', how='inner')
    merged = merged.merge(original_df, on='Record Id', how='inner')

    # Reorder columns to match expected order
    col_order = ['Record Id', 'date_original', 'Category', 'strategy_sus', 'strategy_fs', 'strategy_nut']
    merged = merged[col_order]

    # Save
    output_path = Path('data/strategy_similarities_with_dates.csv')
    merged.to_csv(output_path, index=False)
    print(f"✅ Saved {len(merged)} rows to {output_path}")

if __name__ == '__main__':
    main()
