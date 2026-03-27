#!/usr/bin/env python3
"""
Generate time series data for interactive world map from policy similarities.
Aggregates similarity scores by country and year.
"""

import pandas as pd
import countrycode
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
    original_df['year'] = pd.to_datetime(original_df['Date of original text'], errors='coerce').dt.year

    year_country_lookup = original_df[['Record Id', 'year', 'Country/Territory']].dropna(subset=['year'])
    year_country_lookup = year_country_lookup.rename(columns={'Country/Territory': 'country_raw'})

    # Merge
    df = sim_df.merge(cat_df, on='Record Id', how='inner')
    df = df.merge(year_country_lookup, on='Record Id', how='left')
    df = df.dropna(subset=['year'])
    df['year'] = df['year'].astype(int)

    print(f"Total rows with country (before split): {len(df)}")

    # Split multi-country entries
    df['country_list'] = df['country_raw'].str.split(';')
    df = df.explode('country_list')
    df['country'] = df['country_list'].str.strip()
    df = df.drop(columns=['country_raw', 'country_list'])
    # Drop rows with missing country
    df = df.dropna(subset=['country'])
    # Reset index to avoid misalignment when adding iso3
    df = df.reset_index(drop=True)

    print(f"After splitting multi-country entries: {len(df)} rows")

    # Map to ISO3
    df['iso3'] = countrycode.countrycode(df['country'], origin='country.name', destination='iso3c')
    missing_iso3 = df[df['iso3'].isna()]['country'].unique()
    if len(missing_iso3) > 0:
        print(f"Warning: Could not map to ISO3: {missing_iso3}")
        df = df.dropna(subset=['iso3'])

    print(f"Final rows with ISO3: {len(df)}")

    # Aggregate by country-year
    agg = df.groupby(['country', 'year', 'iso3'])[['strategy_sus', 'strategy_fs', 'strategy_nut']].mean().reset_index()
    agg = agg.sort_values(['country', 'year'])

    # Rename columns to match expected names (sus, fs, nut)
    agg = agg.rename(columns={
        'strategy_sus': 'sus',
        'strategy_fs': 'fs',
        'strategy_nut': 'nut'
    })

    print(f"Aggregated to {len(agg)} country-year observations")
    print(f"Years: {agg.year.min()}-{agg.year.max()}")
    print(f"Countries: {agg.country.nunique()}")

    # Save to temp folder
    output_path = Path('data/temp/world_map_time_series.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(output_path, index=False)
    print(f"\n✅ Saved to {output_path}")

if __name__ == '__main__':
    main()
