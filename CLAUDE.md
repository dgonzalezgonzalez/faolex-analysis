# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a data analysis project focused on the FAOLEX (Food and Agriculture Organization of the United Nations Legislative database) food legislation dataset. The repository contains:

- **Data**: `data/FAOLEX_Food.csv` - A comprehensive dataset with 40,256 records of food-related legislation from around the world
- **Code**: `code/` - Directory for analysis scripts and notebooks (currently empty)
- **Output**: `output/` - Directory for generated analysis results, visualizations, and reports (currently empty)

## Data Structure

The CSV dataset contains 19 columns:
- **Record Id**: Unique identifier (e.g., LEX-FAOC001069)
- **Record URL**, **Document URL**, **Text URL**: Links to original sources
- **Title** (English), **Original title** (original language)
- **Date of original text**, **Last amended date**: Temporal information
- **Available website**, **Language of document**: Multilingual content (English, French, Spanish, Portuguese, Italian, German)
- **Country/Territory**, **Regional organizations**, **Territorial subdivision**: Geographic coverage
- **Type of text**: Regulation, Legislation, etc.
- **Repealed**: Y/N status
- **Abstract**: Summary of the legislation
- **Primary subjects**, **Domain**: Classification (primarily "Food and nutrition")
- **Keywords**: Tagged topics (e.g., fish products, standards, food safety and quality)

## Completed Analysis

**Policy Classification**: A rule-based classification script (`code/classify_policies.py`) has been created to categorize each policy as **demand-side** or **supply-side** based on the Abstract, Title, Keywords, and Primary subjects fields.

### Classification Logic

- **Supply-side policies**: Focus on production, processing, distribution infrastructure, quality standards for producers, farming practices, food safety from production perspective. Keywords include: production, processing, transport, storage, inspection, certification, licensing, hygiene, etc.
- **Demand-side policies**: Focus on consumers, consumption patterns, nutrition, labeling, advertising, food prices, consumer protection, and retail. Keywords include: consumer, labeling, nutrition, advertising, dietary, food aid, retail, etc.

### Output

The classification results are stored in `data/policy_categories.csv` with two columns:
- `Record Id`: Policy identifier from original dataset
- `Category`: `demand_side`, `supply_side`, or `unclear` (if ambiguous)

**Results** (40,255 policies classified):
- Demand-side: 8,369 (20.8%)
- Supply-side: 27,049 (67.2%)
- Unclear/ambiguous: 4,837 (12.0%)

To re-run the classification: `python3 code/classify_policies.py`

## Environment Setup

A Python virtual environment is included and recommended:

```bash
# Create virtual environment (if not already created)
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or: venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

Current dependencies (in `requirements.txt`):
- pandas==3.0.1
- numpy==2.4.3
- python-dateutil==2.9.0.post0
- six==1.17.0

## Running Code

To execute analysis scripts:

```bash
source venv/bin/activate
python3 code/classify_policies.py
```

## Recommended Development Approach

This project appears to be in the initial stage with only raw data. Suggested next steps for development:

1. **Create exploratory analysis scripts** in the `code/` directory to:
   - Load and clean the data (handle encoding issues, missing values)
   - Generate summary statistics (countries represented, time span, document types)
   - Analyze keyword distributions and subject classifications
   - Explore multilingual content patterns
   - Create visualizations of temporal trends

2. **Generate reports** in the `output/` directory:
   - HTML/PDF reports from analysis notebooks
   - Charts and visualizations
   - Data extracts or aggregated datasets

3. **Consider adding**:
   - Jupyter notebooks for interactive exploration
   - `.gitignore` to exclude large intermediate files and venv

## Notes for Code Generation

- The dataset has a BOM (Byte Order Mark) at the beginning; use appropriate encoding (`utf-8-sig` in Python)
- Dates are in various formats (DD-MM-YYYY, YYYY, year only) and may require parsing
- Keywords are semicolon-separated and may need tokenization
- Some fields have multiple values (Regional organizations, Keywords)
- The data is primarily focused on food and nutrition legislation but may contain other domains

## Project Conventions

- Keep raw data immutable; store any transformed data in `output/`
- Document analysis scripts with clear comments explaining methodology
- Use relative paths: `../data/FAOLEX_Food.csv` from the `code/` directory
- Consider creating a README.md to document analysis approach and findings
