#!/usr/bin/env python3
"""
Generate descriptive statistics LaTeX tables from analysis dataset.
This replaces the complex Stata do-file with simpler Python code.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def latex_escape(text):
    """Escape special LaTeX characters."""
    if pd.isna(text):
        return ""
    text = str(text)
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\~{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '"': r'\textquotedbl{}'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def main():
    # Load the analysis dataset
    df = pd.read_stata('data/analysis_dataset.dta')
    print(f"Loaded {len(df)} policies")

    # Prepare LaTeX-escaped title and country
    df['title_latex'] = df['Title'].apply(latex_escape)
    df['country_latex'] = df['country'].apply(latex_escape)

    # Extract year from date
    df['year'] = df['date_original'].str[-4:].astype(float)
    df['year'] = df['year'].astype(int)

    output_file = Path('output/descriptive_statistics.tex')

    # =====================================================
    # TABLE 1: SAMPLE OVERVIEW
    # =====================================================
    n_total = len(df)
    n_demand = len(df[df['Category'] == 'demand_side'])
    n_supply = len(df[df['Category'] == 'supply_side'])
    n_unclear = len(df[df['Category'] == 'unclear'])
    n_countries = df['country'].nunique()
    n_languages = df['Language_of_document'].nunique()
    year_min = int(df['year'].min())
    year_max = int(df['year'].max())

    latex = []
    latex.append("% LaTeX tables generated automatically\n")
    latex.append(r"\begin{table}[htbp]")
    latex.append(r"\centering")
    latex.append(rf"\caption{{Sample Overview (n={n_total})}}")
    latex.append(r"\label{tab:sample_overview}")
    latex.append(r"\begin{tabular}{lcccc}")
    latex.append(r"\toprule")
    latex.append(r" & Count & \\")
    latex.append(r"\midrule")
    latex.append(f"Total Policies & {n_total} & \\\\")
    latex.append(rf"\quad Demand-side & {n_demand} & \\")
    latex.append(rf"\quad Supply-side & {n_supply} & \\")
    latex.append(rf"\quad Unclear & {n_unclear} & \\")
    latex.append(r"\midrule")
    latex.append(rf"Countries & {n_countries} & \\")
    latex.append(rf"Languages & {n_languages} & \\")
    latex.append(rf"Date Range & {year_min}--{year_max} & \\")
    latex.append(r"\bottomrule")
    latex.append(r"\end{tabular}")
    latex.append(r"\end{table}")
    latex.append("")
    latex.append("")

    # =====================================================
    # TABLE 2: STRATEGY SIMILARITY BY CATEGORY
    # =====================================================
    latex.append(r"\begin{table}[htbp]")
    latex.append(r"\centering")
    latex.append(r"\caption{Strategy Similarity Scores by Policy Category}")
    latex.append(r"\label{tab:strategy_stats_by_category}")
    latex.append(r"\begin{tabular}{l l c c c c c}")
    latex.append(r"\toprule")
    latex.append(r"Category & Strategy & N & Mean & Std & Min & Max & Median \\")
    latex.append(r"\midrule")

    categories = [
        ('demand_side', 'Demand-side'),
        ('supply_side', 'Supply-side'),
        ('unclear', 'Unclear')
    ]

    strategies = [
        ('strategy_sus', 'Environmentally Sustainable Strategies'),
        ('strategy_fs', 'Food Systems Strategy'),
        ('strategy_nut', 'Nutrition Strategy')
    ]

    for cat_key, cat_label in categories:
        for strat_key, strat_label in strategies:
            subset = df[df['Category'] == cat_key]
            n_cat = len(subset)
            if n_cat > 0:
                mean_val = subset[strat_key].mean()
                std_val = subset[strat_key].std()
                min_val = subset[strat_key].min()
                max_val = subset[strat_key].max()
                median_val = subset[strat_key].median()

                # Format numbers
                mean_str = f"{mean_val:.4f}"
                std_str = f"{std_val:.4f}" if not np.isnan(std_val) else "."
                min_str = f"{min_val:.4f}"
                max_str = f"{max_val:.4f}"
                median_str = f"{median_val:.4f}"

                if strat_key == 'strategy_sus':
                    latex.append(f"{cat_label} & {strat_label} & {n_cat} & {mean_str} & {std_str} & {min_str} & {max_str} & {median_str} \\\\")
                else:
                    latex.append(f" & {strat_label} & {n_cat} & {mean_str} & {std_str} & {min_str} & {max_str} & {median_str} \\\\")

    latex.append(r"\bottomrule")
    latex.append(r"\end{tabular}")
    latex.append(r"\end{table}")
    latex.append("")
    latex.append("")

    # =====================================================
    # TABLE 3: TOP AND BOTTOM POLICIES FOR EACH STRATEGY
    # =====================================================
    for strat_key, strat_label in strategies:
        suffix = strat_key.split('_')[1]  # sus, fs, nut

        latex.append(rf"\subsubsection{{{strat_label}}}")
        latex.append(r"\begin{table}[htbp]")
        latex.append(r"\centering")
        latex.append(r"\begin{tabular}{l l l c}")
        latex.append(r"\toprule")
        latex.append(r" & Country & Category & Similarity \\")
        latex.append(r"\midrule")

        # Top 5
        latex.append(r"\multicolumn{4}{c}{\textbf{Top 5}} \\")
        top5 = df.nlargest(5, strat_key)
        for _, row in top5.iterrows():
            rec = row['title_latex']
            ctry = row['country_latex']
            cat = row['Category'].replace('_', ' ').title()
            sim = f"{row[strat_key]:.4f}"
            latex.append(f"{rec} & {ctry} & {cat} & {sim} \\\\")

        # Bottom 5
        latex.append(r"\midrule")
        latex.append(r"\multicolumn{4}{c}{\textbf{Bottom 5}} \\")
        bottom5 = df.nsmallest(5, strat_key)
        for _, row in bottom5.iterrows():
            rec = row['title_latex']
            ctry = row['country_latex']
            cat = row['Category'].replace('_', ' ').title()
            sim = f"{row[strat_key]:.4f}"
            latex.append(f"{rec} & {ctry} & {cat} & {sim} \\\\")

        latex.append(r"\bottomrule")
        latex.append(r"\end{tabular}")
        latex.append(rf"\caption{{Top and bottom policies for {strat_label}}}")
        latex.append(rf"\label{{tab:top_bottom_{suffix}}}")
        latex.append(r"\end{table}")
        latex.append("")

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(latex))

    print(f"✓ LaTeX tables saved to {output_file}")
    print(f"  Total policies: {n_total}")
    print(f"  Demand-side: {n_demand}, Supply-side: {n_supply}, Unclear: {n_unclear}")

if __name__ == "__main__":
    main()
