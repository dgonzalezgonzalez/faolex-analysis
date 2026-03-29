#!/usr/bin/env python3
"""
Generate policy counts trends by year and category.
Shows the number of policies enacted each year for All, Demand-side, and Supply-side categories.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def main():
    # Load analysis dataset (CSV format)
    df_original = pd.read_csv('data/analysis_dataset.csv')
    original_count = len(df_original)
    print(f"Loaded {original_count} policies")

    # Extract year - handle malformed dates (e.g., '????', '196?', NaN)
    # Only keep rows where the last 4 characters are digits
    df_original['year_str'] = df_original['date_original'].astype(str).str[-4:]
    valid_year_mask = df_original['year_str'].str.isdigit()
    df = df_original[valid_year_mask].copy()
    df['year'] = df['year_str'].astype(int)
    df = df.drop(columns=['year_str'])

    # Additional filter: exclude obviously invalid years (e.g., year=0 from '0000' placeholders)
    # and keep reasonable bounds (e.g., >= 1 and <= 2025)
    valid_range_mask = (df['year'] > 0) & (df['year'] <= 2025)
    df = df[valid_range_mask].copy()

    dropped_total = original_count - len(df)
    year_min = int(df['year'].min())
    year_max = int(df['year'].max())
    print(f"Using {len(df)} policies with valid dates in full range {year_min}--{year_max}")
    print(f"(Dropped {dropped_total} policies with malformed dates or invalid years)")

    # Define categories
    categories = {
        'All': df,
        'Demand-side': df[df['Category'] == 'demand_side'],
        'Supply-side': df[df['Category'] == 'supply_side']
    }

    output_dir = Path('output')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepare data: count by year for each category
    plt.figure(figsize=(12, 6))

    for label, subset in categories.items():
        agg = subset.groupby('year').size().reset_index(name='count')
        plt.plot(agg['year'], agg['count'],
                 label=label,
                 linewidth=2,
                 marker='o' if label == 'All' else None,
                 markersize=4)

    plt.xlabel('Year', fontsize=12)
    plt.ylabel('Number of Policies', fontsize=12)
    plt.legend(title='Policy Category', loc='best')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save as PDF and PNG
    base_name = 'policy_counts_trends'
    plt.savefig(output_dir / f'{base_name}.pdf', bbox_inches='tight')
    plt.savefig(output_dir / f'{base_name}.png', dpi=300, bbox_inches='tight')
    print(f'Created: {base_name}.pdf and {base_name}.png')
    plt.close()

    print('\n✅ Policy counts trends saved to output/')

if __name__ == "__main__":
    main()
