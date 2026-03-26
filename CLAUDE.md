# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a data analysis project focused on the FAOLEX (Food and Agriculture Organization of the United Nations Legislative database) food legislation dataset. The repository contains:

- **Data**: `data/FAOLEX_Food.csv` - Raw dataset (40,256 records)
- **Code**: `code/` - Analysis scripts: policy classification, text downloading, embedding generation
- **Data products**: `data/policy_categories.csv`, `data/embeddings/`, `data/text_cache/`
- **Output**: `output/` - Future analysis results, visualizations, and reports

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

### 1. Policy Classification

A rule-based classification script (`code/classify_policies.py`) to categorize each policy as **demand-side** or **supply-side** based on the Abstract, Title, Keywords, and Primary subjects fields.

**Classification Logic**:
- **Supply-side**: Production, processing, distribution, quality standards, licensing, inspection, etc.
- **Demand-side**: Consumers, labeling, nutrition, advertising, food prices, consumer protection, retail.

**Output**: `data/policy_categories.csv`
- 40,255 policies classified: 67.2% supply-side, 20.8% demand-side, 12.0% unclear

### 2. Vector Embedding Pipeline (In Progress)

A modular system to download policy texts, extract clean content, and generate vector embeddings using Ollama's `nomic-embed-text` model.

**Components**:
- `code/text_downloader.py` - Downloads and caches `.txt` or `.pdf` files from FAOLEX URLs
- `code/text_extractor.py` - Extracts text with validation and truncation
- `code/embedding_client.py` - Interface with Ollama embedding API (768-dimensional vectors)
- `code/embedding_storage.py` - Stores embeddings in JSON Lines format with manifest tracking
- `code/generate_embeddings.py` - Main orchestrator with resume capability

**Storage**:
- `data/text_cache/` - Raw downloaded files (cached, not committed)
- `data/embeddings/embeddings.jsonl` - Embeddings and metadata
- `data/embeddings/manifest.json` - Processing status for each Record ID

**Test Results** (10 policies):
- 5 successful embeddings generated
- 5 failed due to embedding model context length limits (need improved text chunking/truncation strategy)

**Usage**:
```bash
# Test with 10 policies
python3 code/generate_embeddings.py --limit 10

# Check processing status
python3 code/generate_embeddings.py --status

# Force re-run on failures
python3 code/generate_embeddings.py --force --limit 10
```

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

- Keep raw data immutable; derived datasets (embeddings, classifications) are stored alongside in `data/`
- Document analysis scripts with clear comments explaining methodology
- Use relative paths: `../data/FAOLEX_Food.csv` from the `code/` directory
- The repository already includes README.md for documentation
- **Note**: The original recommendation to use `output/` for transformed data was superseded by user request to keep derived data in `data/` (e.g., `data/policy_categories.csv`, `data/embeddings/`)
