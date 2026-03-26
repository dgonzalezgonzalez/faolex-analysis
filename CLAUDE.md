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

### 2. Vector Embedding Pipeline (Optimized)

A modular system to download policy texts, translate to English, chunk, and generate vector embeddings using Ollama's `all-minilm` model (default) or `nomic-embed-text`.

**Components**:
- `code/text_downloader.py` - Downloads and caches `.txt` or `.pdf` files from FAOLEX URLs
- `code/text_extractor.py` - Extracts text with validation (up to 100k chars)
- `code/text_translator.py` - Detects language and translates non-English to English (Google Translate, cached)
- `code/text_chunker.py` - Splits long texts into overlapping chunks (adaptive: 300/30 for all-minilm, 2000/200 for nomic)
- `code/embedding_client.py` - Ollama API wrapper; batch embedding + normalization
- `code/embedding_storage.py` - JSON Lines storage + manifest with detailed metadata
- `code/generate_embeddings.py` - Main orchestrator with resume capability

**Key Improvements**:
- **Adaptive chunk sizing**: Prevents context overflow for smaller models
- **Normalization**: Final averaged embeddings are unit-normalized for correct cosine similarity
- **Batch processing**: Configurable batch size for efficiency
- **Translation logic**: Uses CSV language field + fallback detection

**Test Results** (10 policies):
- ✅ 10/10 completed, 0 failures
- Chunks per policy: 1–199 (depending on text length)
- Processing time: ~8 sec/policy (all-minilm)
- Embedding dimension: 384 (all-minilm) or 768 (nomic)

**Usage**:
```bash
# Test with 10 policies
python3 code/generate_embeddings.py --limit 10

# Check status
python3 code/generate_embeddings.py --status

# Full dataset (may take many hours)
python3 code/generate_embeddings.py

# Force re-processing
python3 code/generate_embeddings.py --force --limit 10

# Use different model
python3 code/generate_embeddings.py --model nomic-embed-text
```

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

**Note**: The time series CSV (`output/world_map_time_series.csv`) is the intermediate data used to generate the HTML. After generating the interactive map, the CSV can be removed.

### 5. Visualization & Analysis (Stata, R, Python)

The project includes additional analysis outputs:

**Stata**:
- Time-trend line graphs: `code/strategy_similarity_trends.do` → `output/strategy_*_trends.pdf/png`
- Descriptive LaTeX tables: `code/descriptive_tables.do` → `output/descriptive_statistics.tex`

**R**:
- Static world maps by country: `code/world_similarity_map_enhanced.R` → `output/strategy_*_map.pdf/png`

**Python**:
- Full orchestration: `main.py` (runs everything end-to-end, now includes interactive map)

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
# Ensure embeddings exist first (run generate_embeddings.py)
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
- **Strategy similarity analysis**: Comparing policy embeddings to three strategic query dimensions
- **Stata time-trend visualizations**: Line graphs showing similarity evolution by policy category
- **R world maps**: Geographic visualization of similarity scores (static PDFs)
- **Interactive HTML world map**: Animated time-series map with Play/Pause slider for all three strategies
- **LaTeX descriptive tables**: Automated report tables
- **Master orchestrator**: Single entry point for full pipeline (now generates interactive map)

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
- Use relative paths from the project root
- The repository includes README.md for project overview and usage
- Use `main.py` as the canonical entry point for end-to-end execution

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
