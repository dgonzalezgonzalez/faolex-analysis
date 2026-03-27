#!/usr/bin/env python3
"""
Generate strategy similarity time trend graphs.
Replaces the Stata do-file with Python/matplotlib.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def main():
    # Load analysis dataset
    df = pd.read_stata('data/analysis_dataset.dta')
    # Extract year
    df['year'] = df['date_original'].str[-4:].astype(int)

    # Define categories
    categories = {
        'All': df,
        'Demand-side': df[df['Category'] == 'demand_side'],
        'Supply-side': df[df['Category'] == 'supply_side']
    }

    strategies = [
        ('strategy_sus', 'Strategy SUS Cosine Similarity'),
        ('strategy_fs', 'Strategy FS Cosine Similarity'),
        ('strategy_nut', 'Strategy NUT Cosine Similarity')
    ]

    output_dir = Path('output')
    output_dir.mkdir(parents=True, exist_ok=True)

    for strat_col, ylabel in strategies:
        # Prepare data: average by year for each category
        plt.figure(figsize=(10, 6))
        for label, subset in categories.items():
            agg = subset.groupby('year')[[strat_col]].mean().reset_index()
            plt.plot(agg['year'], agg[strat_col],
                     label=label,
                     linewidth=2,
                     marker='o' if label == 'All' else None,
                     markersize=4)

        plt.xlabel('Year', fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.legend(title='Policy Category', loc='best')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # Save as PDF and PNG
        base_name = strat_col.replace('strategy_', 'strategy_')  # keep same naming pattern
        plt.savefig(output_dir / f'{base_name}_trends.pdf', bbox_inches='tight')
        plt.savefig(output_dir / f'{base_name}_trends.png', dpi=300, bbox_inches='tight')
        print(f'Created: {base_name}_trends.pdf and .png')
        plt.close()

    print('\n✅ All trend graphs saved to output/')

if __name__ == "__main__":
    main()
