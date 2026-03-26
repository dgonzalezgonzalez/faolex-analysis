#!/usr/bin/env python3
"""
FAOLEX Policy Classification Script
Categorizes each policy as 'demand_side' or 'supply_side' based on abstract and keywords.
"""

import pandas as pd
import re
from pathlib import Path
from typing import Dict, Tuple

def normalize_text(text: str) -> str:
    """Normalize text to lowercase and remove extra whitespace."""
    if pd.isna(text):
        return ""
    return str(text).lower().strip()

def clean_column_names(columns):
    """Clean column names by removing BOM and stripping whitespace."""
    return [col.encode('utf-8').decode('utf-8-sig').strip() for col in columns]

# Comprehensive keyword lists for classification based on food policy literature
SUPPLY_SIDE_KEYWORDS = {
    # Production & sourcing
    'production', 'producer', 'producers', 'farm', 'farms', 'farmer', 'farmers',
    'fishing', 'fishery', 'fisheries', 'aquaculture', 'harvest', 'cultivation',
    'crop', 'livestock', 'agriculture', 'grow', 'growing',
    # Processing & manufacturing
    'processing', 'processor', 'processors', 'manufactur', 'factory', 'factories',
    'industrial', 'industry', 'plant', 'plants', 'facility', 'facilities',
    'packaging', 'packer', 'packers', 'transformation',
    # Distribution & logistics
    'transport', 'transportation', 'shipment', 'shipping', 'distribution',
    'logistics', 'supply chain', 'warehouse', 'storage', 'cold storage',
    'wholesale', 'wholesaler', 'importer', 'exporter', 'export', 'import',
    # Quality & standards (from producer/processor perspective)
    'quality control', 'quality assurance', 'inspection', 'inspect', 'audit',
    'certification', 'certify', 'standard', 'standards', 'technical standard',
    'hygiene', 'sanitary', 'safety', 'haccp', 'traceability',
    'licen[cs]e', 'licensing', 'authorization', 'permit',
    # Institutional/governance focused on supply
    'competent authority', 'regulatory authority', 'inspection service',
    'control agency', 'food authority',
    # Fish-specific supply
    'fish product', 'fishery product', 'processing plant', 'vessel', 'boats',
    'landing', 'port', 'quota', 'catch'
}

DEMAND_SIDE_KEYWORDS = {
    # Consumers & consumption
    'consumer', 'consumers', 'consumption', 'final consumer', 'end user',
    'public', 'population', 'household', 'households',
    # Labeling & information
    'label', 'labeling', 'labelling', 'nutrition label', 'nutrition information',
    'ingredient list', 'allergen', 'date marking', 'shelf life', 'best before',
    'use by', 'country of origin', 'place of origin', 'traceability',
    # Advertising & promotion
    'advertising', 'advertisement', 'marketing', 'promotion', 'nutrition claim',
    'health claim', 'misleading', 'false advertising',
    # Nutrition & health
    'nutrition', 'nutritional', 'dietary', 'diet', 'healthy', 'salt', 'sugar',
    'fat', 'calorie', 'nutrient', 'vitamin', 'mineral', 'balanced diet',
    'food-based dietary', 'guideline', 'recommendation',
    'fortification', 'enrichment',
    # Pricing & access
    'price', 'pricing', 'affordable', 'subsidy', 'food aid', 'food assistance',
    'food security', 'access to food', 'food distribution',
    'safety net', 'social protection',
    # Consumer protection
    'consumer protection', 'consumer right', 'food fraud', 'mislabel',
    'withdrawal', 'recall', 'consumer complaint', 'consumer education',
    # Retail & food service (consumer-facing)
    'retail', 'retailer', 'supermarket', 'grocery', 'restaurant', 'catering',
    'canteen', 'food service', 'vending machine',
    # Special populations
    'infant', 'baby', 'child', 'children', 'school', 'elderly', 'pregnant',
    'breastfeeding', 'maternal', 'special dietary', 'medical nutrition'
}

# Additional contextual patterns to help disambiguate
SUPPLY_CONTEXT_PATTERNS = [
    r' establishment[s]? ', r' business ', r' operator[s]? ', r' undertaking[s]? ',
    r' import food', r' export food', r' produce food', r' manufacture food',
    r' condition[s]? for .* (?:production|processing|storage|transport)',
    r' technical specification',
]

DEMAND_CONTEXT_PATTERNS = [
    r' consumer[s]? (?:to|must|should|be) ',
    r' (?:provide|give|supply) information ',
    r' point of sale', r' final consumer',
    r' nutritional information',
]

def classify_policy(abstract: str, title: str = "", keywords: str = "", primary_subjects: str = "") -> str:
    """
    Classify a policy as demand_side, supply_side, or unclear.

    Args:
        abstract: Policy abstract text
        title: Policy title
        keywords: Semicolon-separated keywords
        primary_subjects: Primary subject classification

    Returns:
        'demand_side', 'supply_side', or 'unclear'
    """
    text = normalize_text(f"{abstract} {title} {keywords} {primary_subjects}")

    if not text or len(text) < 10:
        return "unclear"

    # Count keyword matches
    supply_score = 0
    demand_score = 0

    # Check keyword presence
    for keyword in SUPPLY_SIDE_KEYWORDS:
        if re.search(rf'\b{keyword}\b', text):
            supply_score += 1

    for keyword in DEMAND_SIDE_KEYWORDS:
        if re.search(rf'\b{keyword}\b', text):
            demand_score += 1

    # Check contextual patterns
    for pattern in SUPPLY_CONTEXT_PATTERNS:
        if re.search(pattern, text):
            supply_score += 2  # Weight patterns higher

    for pattern in DEMAND_CONTEXT_PATTERNS:
        if re.search(pattern, text):
            demand_score += 2

    # Decision logic
    if supply_score > 0 and demand_score == 0:
        return "supply_side"
    elif demand_score > 0 and supply_score == 0:
        return "demand_side"
    elif supply_score > demand_score:
        return "supply_side"
    elif demand_score > supply_score:
        return "demand_side"
    else:
        return "unclear"

def process_csv(input_path: str, output_path: str, chunk_size: int = 10000):
    """
    Process the FAOLEX CSV in chunks and output classification results.

    Args:
        input_path: Path to input CSV
        output_path: Path to output CSV
        chunk_size: Number of rows to process at a time
    """
    print(f"Processing {input_path}...")

    # Read CSV - note encoding with BOM
    reader = pd.read_csv(
        input_path,
        encoding='utf-8-sig',
        chunksize=chunk_size,
        low_memory=False
    )

    first_chunk = True
    total_processed = 0
    category_counts = {'demand_side': 0, 'supply_side': 0, 'unclear': 0}

    for chunk in reader:
        # Clean column names: remove BOM and strip whitespace (only on first chunk)
        if first_chunk:
            # The BOM is causing issues; explicitly rename first column
            chunk = chunk.rename(columns={chunk.columns[0]: 'Record Id'})
            # Clean any remaining whitespace
            chunk.columns = chunk.columns.str.strip()
            cleaned_columns = chunk.columns.tolist()
            print(f"Column names: {cleaned_columns}")
        else:
            chunk.columns = cleaned_columns

        # Classify each policy
        chunk['Category'] = chunk.apply(
            lambda row: classify_policy(
                abstract=row.get('Abstract', ''),
                title=row.get('Title', ''),
                keywords=row.get('Keywords', ''),
                primary_subjects=row.get('Primary subjects', '')
            ),
            axis=1
        )

        # Update counts
        for cat in chunk['Category']:
            category_counts[cat] += 1

        # Write to output CSV (only Record Id and Category)
        output_cols = ['Record Id', 'Category']
        chunk[output_cols].to_csv(
            output_path,
            mode='w' if first_chunk else 'a',
            header=first_chunk,
            index=False
        )

        total_processed += len(chunk)
        print(f"  Processed {total_processed} records... "
              f"(Demand: {category_counts['demand_side']}, "
              f"Supply: {category_counts['supply_side']}, "
              f"Unclear: {category_counts['unclear']})")

        first_chunk = False

    print(f"\nClassification complete!")
    print(f"Total processed: {total_processed}")
    print(f"Demand-side: {category_counts['demand_side']}")
    print(f"Supply-side: {category_counts['supply_side']}")
    print(f"Unclear/ambiguous: {category_counts['unclear']}")
    print(f"Output saved to: {output_path}")

if __name__ == "__main__":
    # Use absolute paths based on script location
    project_root = Path(__file__).parent.parent
    input_file = project_root / "data" / "FAOLEX_Food.csv"
    output_file = project_root / "data" / "policy_categories.csv"

    process_csv(str(input_file), str(output_file))
