#!/usr/bin/env python3
"""
Generate descriptive statistics from the analysis dataset.
Creates LaTeX tables for the research report.
"""

import argparse
import logging
from pathlib import Path
import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_dataset(path: Path) -> pd.DataFrame:
    """Load the analysis dataset."""
    df = pd.read_csv(path)
    logger.info(f"Loaded dataset with {len(df)} rows and {len(df.columns)} columns")
    return df

def generate_summary_tables(df: pd.DataFrame, output_dir: Path):
    """Generate LaTeX summary tables."""

    # Table 1: Sample Overview
    n_total = len(df)
    n_demand = (df['Category'] == 'demand_side').sum()
    n_supply = (df['Category'] == 'supply_side').sum()
    n_unclear = (df['Category'] == 'unclear').sum()
    n_countries = df['country'].nunique()
    n_languages = df['Language of document'].nunique()

    # Date range
    df['year'] = pd.to_datetime(df['date_original'], format='%d-%m-%Y', errors='coerce').dt.year
    year_min = int(df['year'].min())
    year_max = int(df['year'].max())

    overview_table = f"""
\\begin{{table}}[htbp]
\\centering
\\caption{{Sample Overview (n={n_total})}}
\\label{{tab:sample_overview}}
\\begin{{tabular}}{{lcccc}}
\\toprule
 & Count & \\\\
\\midrule
Total Policies & {n_total} & \\\\
\\quad Demand-side & {n_demand} & \\\\
\\quad Supply-side & {n_supply} & \\\\
\\quad Unclear & {n_unclear} & \\\\
\\midrule
Countries & {n_countries} & \\\\
Languages & {n_languages} & \\\\
Date Range & {year_min}--{year_max} & \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""

    # Table 2: Strategy Similarity Scores by Category
    categories = ['demand_side', 'supply_side', 'unclear']
    strategies = ['strategy_sus', 'strategy_fs', 'strategy_nut']
    strategy_names = {
        'strategy_sus': 'Environmentally Sustainable Strategies',
        'strategy_fs': 'Food Systems Strategy',
        'strategy_nut': 'Nutrition Strategy'
    }

    rows = []
    for cat in categories:
        subset = df[df['Category'] == cat]
        for strat in strategies:
            scores = subset[strat].dropna()
            if len(scores) > 0:
                mean_val = scores.mean()
                std_val = scores.std()
                min_val = scores.min()
                max_val = scores.max()
                median_val = scores.median()
                rows.append({
                    'Category': cat.replace('_', ' ').title(),
                    'Strategy': strategy_names[strat].replace('&', '\\&'),
                    'N': len(scores),
                    'Mean': mean_val,
                    'Std': std_val,
                    'Min': min_val,
                    'Max': max_val,
                    'Median': median_val
                })

    stats_df = pd.DataFrame(rows)

    # Pivot for multirow formatting
    latex_rows = []
    latex_rows.append("\\begin{table}[htbp]")
    latex_rows.append("\\centering")
    latex_rows.append("\\caption{Strategy Similarity Scores by Policy Category}")
    latex_rows.append("\\label{tab:strategy_stats_by_category}")
    latex_rows.append("\\begin{tabular}{l l c c c c c}")
    latex_rows.append("\\toprule")
    latex_rows.append("Category & Strategy & N & Mean & Std & Min & Max & Median \\\\")
    latex_rows.append("\\midrule")

    current_category = None
    for _, row in stats_df.iterrows():
        cat = row['Category']
        strat = row['Strategy'][:40] + ('...' if len(row['Strategy']) > 40 else '')
        if cat != current_category:
            latex_rows.append(f"\\multirow{{3}}{{*}}{{{cat}}} & {strat} & {row['N']} & {row['Mean']:.4f} & {row['Std']:.4f} & {row['Min']:.4f} & {row['Max']:.4f} & {row['Median']:.4f} \\\\")
            current_category = cat
        else:
            latex_rows.append(f" & {strat} & {row['N']} & {row['Mean']:.4f} & {row['Std']:.4f} & {row['Min']:.4f} & {row['Max']:.4f} & {row['Median']:.4f} \\\\")

    latex_rows.append("\\bottomrule")
    latex_rows.append("\\end{tabular}")
    latex_rows.append("\\end{table}")

    strategy_table = "\n".join(latex_rows)

    # Table 3: Top and Bottom Policies for Each Strategy
    top_bottom_tables = []
    for strat in strategies:
        strat_name = strategy_names[strat].replace('&', '\\&')
        top5 = df.nlargest(5, strat)[['record_id', 'country', 'Category', strat]]
        bottom5 = df.nsmallest(5, strat)[['record_id', 'country', 'Category', strat]]

        top_bottom_tables.append(f"""
\\subsubsection{{{strat_name}}}
\\begin{{table}}[htbp]
\\centering
\\begin{{tabular}}{{l l l c}}
\\toprule
 & Country & Category & Similarity \\\\
\\midrule
\\multicolumn{{4}}{{c}}{{\\textbf{{Top 5}}}} \\\\
""")
        for idx, row in top5.iterrows():
            top_bottom_tables.append(f"{row['record_id']} & {row['country']} & {row['Category'].replace('_', ' ').title()} & {row[strat]:.4f} \\\\")
        top_bottom_tables.append("\\midrule")
        top_bottom_tables.append("\\multicolumn{4}{c}{\\textbf{Bottom 5}} \\\\")
        for idx, row in bottom5.iterrows():
            top_bottom_tables.append(f"{row['record_id']} & {row['country']} & {row['Category'].replace('_', ' ').title()} & {row[strat]:.4f} \\\\")
        top_bottom_tables.append("\\bottomrule")
        top_bottom_tables.append("\\end{tabular}")
        top_bottom_tables.append("\\caption{Top and bottom policies for " + strat_name + "}")
        top_bottom_tables.append("\\label{tab:top_bottom_" + strat.replace('strategy_', '') + "}")
        top_bottom_tables.append("\\end{table}")

    top_bottom_table = "\n".join(top_bottom_tables)

    # Save all tables to a single LaTeX file
    output_file = output_dir / "descriptive_statistics.tex"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("% LaTeX tables generated automatically\n\n")
        f.write(overview_table)
        f.write("\n\n")
        f.write(strategy_table)
        f.write("\n\n")
        f.write(top_bottom_table)

    logger.info(f"Saved LaTeX tables to {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Generate descriptive statistics LaTeX tables")
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('data/analysis_dataset.csv'),
        help='Input analysis dataset CSV'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('output'),
        help='Output directory for LaTeX files'
    )

    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading dataset from {args.input}")
    df = load_dataset(args.input)

    logger.info("Generating LaTeX tables...")
    output_file = generate_summary_tables(df, args.output_dir)

    logger.info(f"✅ All tables generated: {output_file}")

if __name__ == "__main__":
    main()
