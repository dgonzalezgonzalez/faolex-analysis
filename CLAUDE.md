# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a data analysis project focused on the FAOLEX (Food and Agriculture Organization of the United Nations Legislative database) food legislation dataset. The repository contains:

- **Data**: `data/FAOLEX_Food.csv` - Raw dataset (40,256+ records)
- **Code**: `code/` - Analysis scripts: policy classification, abstract-based embedding generation, similarity analysis, visualization
- **Data products**: `data/policy_categories.csv`, `data/embeddings/`, `data/analysis_dataset.dta`, `data/strategy_similarities.csv`, `data/temp/`
- **Output**: `output/` - Final results: LaTeX tables, static maps, trend graphs, interactive HTML map

## Directory Conventions

**Important**: Keep the repository organized by following these conventions:

- `output/` - Final results only (PDFs, PNGs, HTML, LaTeX files). **No CSV files, no log files**.
- `data/temp/` - Intermediate/temporary files (CSV exports, time-series data, log files, .dta files used for processing).
- `data/` - Raw data and derived datasets that are part of the analysis pipeline (CSV/DTA files that are inputs to scripts).
- `code/` - All Python, R, and Stata scripts.
- Logs from any script execution should go to `data/temp/`, not `output/`.

When creating new outputs:
1. Final visualizations/reports → `output/`
2. Intermediate data files (CSV, temp DTA) → `data/temp/`
3. Log files → `data/temp/`

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

### 2. Abstract-Based Embedding Pipeline (Standard)

The standard pipeline generates embeddings directly from the `Abstract` field in `FAOLEX_Food.csv`, avoiding external downloads and ensuring high-quality text input.

**Components**:
- `code/abstract_embedder.py` - Main script: loads abstracts, translates non-English, generates embeddings
- `code/text_translator.py` - Language detection and translation (Google Translate, cached)
- `code/embedding_client.py` - Ollama API wrapper with batch processing and normalization
- `code/embedding_storage.py` - JSON Lines storage + manifest with metadata

**Advantages**:
- No external downloads (text is already in the CSV)
- No text extraction or corruption issues
- Smart chunking handles long abstracts:
  - Translation: abstracts >4500 chars split into chunks (respects Google Translate limits)
  - Embedding: long texts chunked and averaged (respects model context limits)
  - All policies embed successfully regardless of abstract length
- Faster processing and cleaner embeddings
- Translation applied only to non-English abstracts (cached for reuse)
- Fully resumable with checkpointing via manifest

**Supported models**:
- `all-minilm` (default): 384-dimensional vectors, fast inference
- `nomic-embed-text`: 768-dimensional vectors, larger context

**Usage**:
```bash
# Test with 10 policies
python3 code/abstract_embedder.py --limit 10

# Process all policies with abstracts
python3 code/abstract_embedder.py

# Force re-processing
python3 code/abstract_embedder.py --force --limit 10

# Use different model
python3 code/abstract_embedder.py --model nomic-embed-text
```

**Note**: The full-text pipeline (`code/generate_embeddings.py`) is deprecated but retained for reference. It downloads, extracts, and chunks full policy texts, which may contain garbage or corrupted content.

**Test Results** (50 policies, abstract-based with chunking):
- ✅ 50/50 completed, 0 failures (including very long abstracts >5000 chars)
- Chunking: Long abstracts automatically split for translation and/or embedding
- Processing time: ~1-2 sec/policy depending on translation needs
- Embedding dimension: 384 (all-minilm) or 768 (nomic)

### 3. Strategy Similarity Analysis

The `code/compute_similarities.py` script computes cosine similarity between policy embeddings and predefined strategy query embeddings.

**Strategy Queries**:
- `strategy_sus`: "action embedded in broader environmentally sustainable strategies"
- `strategy_fs`: "action embedded in a broader food systems strategy or framework"
- `strategy_nut`: "action embedded in a national nutrition or public health nutrition strategy"

**Output**: `data/strategy_similarities.csv` with columns: `record_id`, `strategy_sus`, `strategy_fs`, `strategy_nut`

**Usage**:
```bash
python3 code/compute_similarities.py
```

### 4. Interactive Time-Series World Map

The `code/generate_interactive_map.py` script creates an animated HTML world map from the time series data.

**Features**:
- Three choropleth maps (one for each strategy dimension)
- Animated time slider (1965-1994) with play/pause controls
- Interactive hover tooltips showing country, year, and similarity scores
- Responsive design with Plotly (uses CDN, no local dependencies)

**Output**: `output/interactive_strategy_map.html` (single file with all three strategies)

**Usage**:
```bash
python3 code/generate_interactive_map.py
# Optional: --input path/to/time_series.csv  --output path/to/output.html
```

**Note**: The time series CSV (`data/temp/world_map_time_series.csv`) is the intermediate data used to generate the HTML. After generating the interactive map, the CSV can be removed.

### 5. Visualization & Analysis (Python, R)

The project includes additional analysis outputs:

**Python**:
- Descriptive LaTeX tables: `code/generate_descriptive_tables.py` → `output/descriptive_statistics.tex`
- Time-trend graphs: `code/generate_trends.py` → `output/strategy_*_trends.pdf/png`
- Interactive animated world map: `code/generate_interactive_map.py` → `output/interactive_strategy_map.html`
- Timeseries data generation: `code/generate_timeseries.py` → `data/temp/world_map_time_series.csv` (intermediate)

**R**:
- Static world maps by country: `code/world_similarity_map.R` → `output/strategy_sus_map.pdf/png`, `output/strategy_fs_map.pdf/png`, `output/strategy_nut_map.pdf/png`
- Also generates intermediate timeseries CSV: `data/temp/world_map_time_series.csv`

**Full orchestration**:
- `main.py` runs the complete pipeline end-to-end (Python + R components)

See README.md for complete usage instructions.

### 3. Strategy Similarity Analysis

The `code/compute_similarities.py` script computes cosine similarity between policy embeddings and predefined strategy query embeddings. This allows ranking policies by their relevance to specific strategic dimensions.

**Strategy Queries**:
- `strategy_sus`: "action embedded in broader environmentally sustainable strategies"
- `strategy_fs`: "action embedded in a broader food systems strategy or framework"
- `strategy_nut`: "action embedded in a national nutrition or public health nutrition strategy"

**Output**: `data/strategy_similarities.csv`
- Columns: `record_id`, `strategy_sus`, `strategy_fs`, `strategy_nut`
- Similarity scores range from -1 to 1 (higher = more semantically similar)

**Usage**:
```bash
# Ensure embeddings exist first (run abstract_embedder.py)
python3 code/compute_similarities.py

# Use different embedding model (must match policy embeddings)
python3 code/compute_similarities.py --model nomic-embed-text

# Custom output path
python3 code/compute_similarities.py --output data/custom_similarities.csv
```

**Results Interpretation**:
- Scores near 1: Policy text strongly aligns with the strategy query
- Scores near 0: No meaningful alignment
- Negative scores: Semantic opposition or contradiction
- Top policies can be identified by sorting on each strategy column

**Note**: The embedding model used must match the model used to generate policy embeddings. The default `all-minilm` produces 384-dimensional vectors; `nomic-embed-text` produces 768-dimensional vectors.

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
- ollama==0.6.1
- requests==2.33.0
- PyPDF2==3.0.1
- tqdm==4.67.3
- beautifulsoup4==4.14.3
- deep-translator==1.11.4
- langdetect==1.0.9

## Running Code

To execute analysis scripts:

```bash
source venv/bin/activate
python3 code/classify_policies.py
```

### Master Pipeline

The recommended way to run the complete analysis is via `main.py`:

```bash
python3 main.py --limit 10  # Test run
python3 main.py            # Full dataset
```

See README.md for detailed usage options.

## Recent Updates

The project now includes:
- **Abstract-based embedding pipeline**: Embeddings generated directly from policy abstracts (high quality, no downloads, no chunking)
- **Automatic translation**: Non-English abstracts are translated via Google Translate (cached)
- **Strategy similarity analysis**: Comparing policy embeddings to three strategic query dimensions
- **Python time-trend visualizations**: Line graphs showing similarity evolution by policy category
- **R world maps**: Geographic visualization of similarity scores (static PDFs)
- **Interactive HTML world map**: Animated time-series map with Play/Pause slider for all three strategies
- **LaTeX descriptive tables**: Automated report tables
- **Master orchestrator**: Single entry point (`main.py`) for full pipeline (Python + R)
- **Clean intermediate file organization**: All CSV temporaries stored in `data/temp/`

---

## Full Dataset Run Summary

**Completed**: March 28, 2025

| Metric | Value |
|--------|-------|
| **Policies embedded** | 39,491 |
| **Total dataset** | 40,256 records (excluded ~750 with missing/short abstracts) |
| **Embedding runtime** | ~24 hours |
| **Machine** | macOS 24.5.0 (Darwin) on MacBook Air (Intel x86_64) |
| **Embedding model** | all-minilm (384-dimensional) |
| **Translation** | Google Translate via deep-translator (cached) |
| **Chunking** | Translation: >4500 chars; Embedding: >2000 chars for all-minilm |

**Data quality notes**:
- 7 policies had malformed dates (e.g., "????", "196?") and were excluded from time-series analysis
- All other analyses use the full 39,491 policies with valid dates

**Pipeline improvements**:
- Robust error handling for malformed dates in `generate_trends.py` and `generate_descriptive_tables.py`
- CSV-only data format (removed duplicate `.dta` file)
- Smart chunking ensures all abstracts embed successfully regardless of length

All outputs are generated and committed to the repository.

## Suggested Workflow

1. **Initial test**: `python3 main.py --limit 10` - Verify everything works on small sample
2. **Check outputs**: Inspect `data/` and `output/` directories
3. **Full run**: `python3 main.py` - Process all ~40K policies (may take significant time)
4. **Customize**: Modify strategy queries in `code/compute_similarities.py` or add new analyses

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
- Use `main.py` as the canonical entry point for end-to-end execution

## Documentation Maintenance

**Important**: Whenever you implement significant changes, add new features, or modify existing analysis pipelines, you MUST also update the README.md file to reflect these changes. This ensures the repository documentation stays current and useful for anyone reviewing or using the project.

- Keep the "Current Status" section updated with completed work
- Update the "Repository Structure" section when adding/removing files
- Add new usage examples when modifying or adding scripts
- Document any new data products in the appropriate sections
- Remove references to deprecated files or functionality

The README.md serves as the primary documentation for the repository, while CLAUDE.md provides implementation guidance. Both should be kept in sync with the project's evolution.
