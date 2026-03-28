#!/usr/bin/env python3
"""
Build the complete analysis_dataset from the embedding manifest and FAOLEX metadata.
This is called after abstract_embedder.py to create the final analysis dataset.
"""

import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm

def main():
    # Load embedding manifest
    manifest_path = Path('data/embeddings/manifest.json')
    with open(manifest_path) as f:
        manifest = json.load(f)
    print(f"Loaded manifest with {len(manifest['records'])} records")

    # Load policy categories
    categories_df = pd.read_csv('data/policy_categories.csv')
    categories_df = categories_df.rename(columns={'Record Id': 'record_id'})
    print(f"Loaded {len(categories_df)} policy categories")

    # Load FAOLEX metadata (Title, Country, Language, Date)
    faolex_df = pd.read_csv('data/FAOLEX_Food.csv', encoding='utf-8-sig')
    # Clean BOM
    first_col = faolex_df.columns[0]
    if first_col != 'Record Id':
        faolex_df = faolex_df.rename(columns={first_col: 'Record Id'})
    faolex_df.columns = faolex_df.columns.str.strip()
    # Keep key columns
    faolex_df = faolex_df[['Record Id', 'Title', 'Country/Territory', 'Date of original text', 'Language of document']]
    faolex_df = faolex_df.rename(columns={
        'Record Id': 'record_id',
        'Country/Territory': 'country',
        'Date of original text': 'date_original',
        'Language of document': 'Language_of_document',
        'Title': 'Title'
    })
    print(f"Loaded {len(faolex_df)} FAOLEX records")

    # Build analysis records (without strategy scores initially)
    analysis_records = []
    for rec_id, record in tqdm(manifest['records'].items(), desc="Building analysis dataset"):
        if record['status'] != 'completed':
            continue

        meta = record['metadata']
        # Get category from categories_df
        cat_row = categories_df[categories_df['record_id'] == rec_id]
        category = cat_row.iloc[0]['Category'] if len(cat_row) > 0 else 'unknown'

        # Get FAOLEX metadata
        fao_row = faolex_df[faolex_df['record_id'] == rec_id]
        title = fao_row.iloc[0]['Title'] if len(fao_row) > 0 else ''
        country = fao_row.iloc[0]['country'] if len(fao_row) > 0 else ''
        date_orig = fao_row.iloc[0]['date_original'] if len(fao_row) > 0 else ''
        language = fao_row.iloc[0]['Language_of_document'] if len(fao_row) > 0 else meta.get('original_language', '')

        analysis_records.append({
            'record_id': rec_id,
            'Category': category,
            'Title': title,
            'country': country,
            'date_original': date_orig,
            'Type_of_text': 'Abstract',  # Marker that this is abstract-based
            'Language_of_document': language
        })

    analysis_df = pd.DataFrame(analysis_records)
    print(f"\nCreated analysis dataset with {len(analysis_df)} policies (without strategy scores)")

    # Merge strategy similarity scores if available
    sim_path = Path('data/strategy_similarities.csv')
    if sim_path.exists():
        print(f"Loading strategy similarities from {sim_path}")
        sim_df = pd.read_csv(sim_path)
        # Both DataFrames have 'record_id' column; merge on it
        analysis_df = analysis_df.merge(sim_df, on='record_id', how='left')
        print(f"Merged similarity scores. Missing counts:")
        for col in ['strategy_sus', 'strategy_fs', 'strategy_nut']:
            if col in analysis_df.columns:
                missing = analysis_df[col].isnull().sum()
                print(f"  {col}: {missing} missing")
    else:
        print(f"Warning: {sim_path} not found. Strategy scores will be NaN.")
        # Add NaN columns to maintain schema
        analysis_df['strategy_sus'] = float('nan')
        analysis_df['strategy_fs'] = float('nan')
        analysis_df['strategy_nut'] = float('nan')

    # Reorder columns to have strategy columns near the end (after Category, before Country?)
    # Standard order: Record Id, strategy_*, Category, Title, country, date_original, Type_of_text, Language_of_document
    # But the manifest doesn't have Record Id as a separate column? Wait we built from manifest dict keys.
    # Currently analysis_df has columns: record_id (from manifest key), Category, Title, country, date_original, Type_of_text, Language_of_document, and maybe strategy_* after merge
    # Let's standardize: record_id -> Record Id, and order
    analysis_df = analysis_df.rename(columns={'record_id': 'Record Id'})
    # Desired column order
    base_cols = ['Record Id', 'Category', 'Title', 'country', 'date_original', 'Type_of_text', 'Language_of_document']
    strategy_cols = [col for col in analysis_df.columns if col.startswith('strategy_')]
    # Put strategy cols right after Category? Or keep at end. For consistency with earlier output, put at end.
    ordered_cols = ['Record Id'] + strategy_cols + [c for c in base_cols if c != 'Record Id']
    analysis_df = analysis_df[ordered_cols]

    # Save as CSV (primary format)
    analysis_csv = Path('data/analysis_dataset.csv')
    analysis_df.to_csv(analysis_csv, index=False)
    print(f"Saved CSV: {analysis_csv}")

    print("\n✅ Analysis dataset built. Ready for visualization.")
    print(f"   Total policies: {len(analysis_df)}")
    print(f"   Categories:\n{analysis_df['Category'].value_counts().to_string()}")
    if all(col in analysis_df.columns for col in strategy_cols):
        print(f"   Strategy scores summary:")
        print(analysis_df[strategy_cols].describe().round(4).to_string())


if __name__ == "__main__":
    main()
