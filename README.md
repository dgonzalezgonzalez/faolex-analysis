# FAOLEX Food Legislation Analysis

Analysis of the FAOLEX (Food and Agriculture Organization of the United Nations Legislative database) food legislation dataset.

## Project Overview

This project analyzes global food legislation data from FAOLEX, containing over 40,000 records of food-related policies, regulations, and laws from countries worldwide.

## Current Status

✅ **Completed**:
- Loaded and cleaned the FAOLEX Food dataset (40,256 records)
- Implemented rule-based classification to categorize policies as **demand-side** or **supply-side**
- Generated `data/policy_categories.csv` with classification results
- Set up Python virtual environment with pandas, numpy, Ollama, etc.
- **Abstract-based embedding pipeline**: embeddings generated directly from the `Abstract` field in the CSV
- Automatic translation of non-English abstracts (Google Translate, cached)
- Smart chunking for long abstracts: translation (>4500 chars) and embedding (>2000 chars) with averaging
- Simplified pipeline: no external downloads, no text extraction
- Cosine similarity analysis comparing policy embeddings to strategy query embeddings
- Time-trend visualizations (Python/matplotlib) showing similarity evolution by policy type
- Static world maps (R) and interactive animated HTML map (Python/Plotly)
- LaTeX descriptive statistics tables

**Classification Results**:
- Supply-side policies: 27,049 (67.2%)
- Demand-side policies: 8,369 (20.8%)
- Unclear/ambiguous: 4,837 (12.0%)

**Abstract-Based Embedding Pipeline**:
- Model: `all-minilm` (default, 384-dimensional) or `nomic-embed-text` (768-dimensional)
- Translation: Non-English abstracts translated via Google Translate (cached in `data/translation_cache.json`)
- **Chunking for long texts**:
  - Translation: abstracts >4500 chars split into chunks (2000 char target, 200 overlap) to respect API limits
  - Embedding: texts >2000 chars (for all-minilm) or >5000 chars (for nomic) chunked and averaged
- Embeddings normalized to unit length for correct cosine similarity
- Storage: `data/embeddings/embeddings.jsonl` + `manifest.json` with full metadata
- Resumable: interrupted runs continue where they left off via manifest tracking

**Processing Speed**:
- English abstracts: ~0.3 seconds/policy
- Non-English abstracts (with translation): ~1.0-1.5 seconds/policy (first translation cached thereafter)
- For the full dataset (~40K policies): estimated 12-20 hours depending on translation mix
- **Note**: With smart chunking, all policies embed successfully regardless of abstract length (previously long abstracts failed)

**Key Code Files**:
- `code/abstract_embedder.py` - Generate embeddings from abstracts (primary script)
- `code/compute_similarities.py` - Calculate cosine similarities for strategy queries
- `code/build_analysis_dataset.py` - Merge embeddings with metadata for analysis
- `code/generate_descriptive_tables.py` - Generate LaTeX tables
- `code/generate_trends.py` - Generate time-trend graphs
- `code/generate_interactive_map.py` - Generate animated HTML world map
- `code/world_similarity_map.R` - Generate static world maps

**Interactive Time-Series World Map**:
- Generated with Plotly (HTML, self-contained with CDN dependency)
- Shows three strategy dimensions simultaneously
- Animated by year with play/pause controls
- Hover tooltips display country, year, and exact similarity scores
- Output: `output/interactive_strategy_map.html`

**Strategy Similarity Analysis**:
Three query strings measure alignment with strategic dimensions:
- `strategy_sus`: "action embedded in broader environmentally sustainable strategies"
- `strategy_fs`: "action embedded in a broader food systems strategy or framework"
- `strategy_nut`: "action embedded in a national nutrition or public health nutrition strategy"

Output: `data/strategy_similarities.csv` with cosine similarity scores for each policy.
Visualizations: `output/strategy_*_trends.pdf/png` showing time trends for all, demand-side, and supply-side policies.

## Repository Structure

```
.
├── CLAUDE.md                      # Guidance for Claude Code
├── README.md                      # This file
├── .gitignore                     # Git ignore patterns
├── requirements.txt               # Python dependencies
├── venv/                          # Virtual environment (not committed)
├── data/
│   ├── FAOLEX_Food.csv           # Raw dataset (67.8 MB)
│   ├── policy_categories.csv     # Demand/supply classifications
│   ├── strategy_similarities.csv # Cosine similarity scores for strategy queries
│   ├── strategy_similarities_with_dates.csv  # Merged dataset for Stata
│   ├── analysis_dataset.csv      # Combined dataset for analysis (CSV)
│   ├── analysis_dataset.dta      # Combined dataset for analysis (Stata)
│   ├── embeddings/
│   │   ├── embeddings.jsonl      # Policy vector embeddings (JSON Lines)
│   │   └── manifest.json         # Processing manifest with metadata
│   └── temp/
│       └── world_map_time_series.csv  # Intermediate time-series data (aggregated by country-year)
├── code/
│   ├── classify_policies.py      # Policy classification
│   ├── abstract_embedder.py      # **Primary**: Generate embeddings from abstracts (with translation)
│   ├── generate_embeddings.py    # Legacy: full-text pipeline (deprecated)
│   ├── embedding_client.py       # Ollama embedding client (batch + normalization)
│   ├── embedding_storage.py      # Embeddings storage & manifest management
│   ├── compute_similarities.py   # Strategy query similarity computation
│   ├── build_analysis_dataset.py # Build analysis dataset from embeddings + metadata
│   ├── generate_descriptive_tables.py  # Generate LaTeX tables
│   ├── generate_interactive_map.py    # Generate animated HTML world map
│   ├── generate_timeseries.py    # Generate time-series data (for R script)
│   ├── world_similarity_map.R    # Generate static world maps + intermediate CSV
│   ├── generate_trends.py        # Generate time-trend graphs
│   └── strategy_similarity_trends.do  # (Legacy) Stata script for time-trend plots
└── output/                       # Generated figures and reports
    ├── descriptive_statistics.tex
    ├── strategy_sus_trends.png
    ├── strategy_sus_trends.pdf
    ├── strategy_fs_trends.png
    ├── strategy_fs_trends.pdf
    ├── strategy_nut_trends.png
    ├── strategy_nut_trends.pdf
    ├── strategy_sus_map.png
    ├── strategy_sus_map.pdf
    ├── strategy_fs_map.png
    ├── strategy_fs_map.pdf
    ├── strategy_nut_map.png
    ├── strategy_nut_map.pdf
    └── interactive_strategy_map.html  # Animated world map with slider
```

## Setup

### Python Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Python packages required** (from `requirements.txt`):
- numpy==2.4.3
- pandas==3.0.1
- python-dateutil==2.9.0.post0
- six==1.17.0
- beautifulsoup4==4.14.3
- ollama==0.6.1 (for local embedding model)
- PyPDF2==3.0.1
- requests==2.33.0
- tqdm==4.67.3
- deep-translator==1.11.4
- langdetect==1.0.9
- plotly==6.0.1

### R Dependencies

The R script requires the following packages, which can be installed from CRAN:

```R
# Install required R packages
install.packages(c("ggplot2", "sf", "rnaturalearth", "countrycode", "dplyr", "cowplot"))
```

**Note**: The `sf` package requires system dependencies for spatial data handling. On macOS, you may need to install GDAL, GEOS, and PROJ via Homebrew:

```bash
brew install gdal geos proj
```

On Ubuntu/Debian:
```bash
sudo apt-get install gdal-bin libgdal-dev libgeos-dev libproj-dev
```

On Windows, the `sf` package typically installs with precompiled binaries via `install.packages()`.

### Optional: Ollama Setup

The embedding pipeline uses Ollama for generating vector embeddings. Install Ollama separately:

1. Download from [ollama.ai](https://ollama.ai)
2. Pull the embedding model(s):
   ```bash
   ollama pull all-minilm  # Default model (384-dimensional)
   # or
   ollama pull nomic-embed-text  # Alternative (768-dimensional)
   ```
3. Ensure Ollama is running before executing the embedding scripts.

## Usage

### Policy Classification
```bash
source venv/bin/activate
python3 code/classify_policies.py
```

### Vector Embeddings Generation (Abstract-Based)

The standard pipeline generates embeddings directly from the `Abstract` field in `FAOLEX_Food.csv`.

```bash
# Test with 10 policies
python3 code/abstract_embedder.py --limit 10

# Process all policies with abstracts (may take many hours)
python3 code/abstract_embedder.py

# Force re-processing (e.g., after fixing issues)
python3 code/abstract_embedder.py --force --limit 10

# Use a different embedding model
python3 code/abstract_embedder.py --model nomic-embed-text  # 768-dim, larger context
```

Non-English abstracts are automatically translated to English before embedding. Translation results are cached in `data/translation_cache.json` for reuse.

### Strategy Similarity Analysis
Compute cosine similarity between policy embeddings and predefined strategy queries:
```bash
# Must run after embeddings are generated
python3 code/compute_similarities.py

# With custom output path
python3 code/compute_similarities.py --output data/my_results.csv
```
Output: `data/strategy_similarities.csv` (or custom path) with columns:
`record_id, strategy_sus, strategy_fs, strategy_nut`

### Time-Trend Visualization (Python)
The Python script (`code/generate_trends.py`) creates line graphs showing average similarity trends over time for all policies, demand-side, and supply-side subsets.

```bash
python3 code/generate_trends.py
```

Output figures (PNG and PDF) are saved to `output/`:
- `strategy_sus_trends.*` - Environmentally sustainable strategies
- `strategy_fs_trends.*` - Food systems strategy frameworks
- `strategy_nut_trends.*` - Nutrition/public health nutrition strategies

### World Map Visualization (R)
The R script (`code/world_similarity_map.R`) creates:

1. **Three separate static maps** (one per strategy, no titles):
   - `output/strategy_sus_map.pdf` / `.png` - Sustainability
   - `output/strategy_fs_map.pdf` / `.png` - Food Systems
   - `output/strategy_nut_map.pdf` / `.png` - Nutrition

2. **Time-series data** (intermediate file for Python interactive map):
   - `data/temp/world_map_time_series.csv` - Country-year averaged scores

Run:
```bash
Rscript --vanilla code/world_similarity_map.R
```

### Interactive Animated World Map (Python)
Create an interactive HTML map with time-series animation:

```bash
# Generate the interactive map from time series data (reads from data/temp/ by default)
python3 code/generate_interactive_map.py

# Customize input/output paths
python3 code/generate_interactive_map.py --input data/custom_timeseries.csv --output output/custom_map.html
```

The resulting HTML file (`output/interactive_strategy_map.html`) includes:
- Three choropleth maps (Environmental Sustainability, Food Systems, Nutrition)
- Slider to select year (1965-1994) with Play/Pause button
- Hover tooltips showing country name, year, strategy dimension, and similarity score
- Fully self-contained (loads Plotly from CDN)

Open the HTML file in any modern web browser to interact.

### Descriptive Statistics (Python → LaTeX)
Generate LaTeX tables with summary statistics and top/bottom policy rankings:
```bash
python3 code/generate_descriptive_tables.py
```
Output:
- `output/descriptive_statistics.tex` (includes sample overview, statistics by category, and extreme cases)

### Master Orchestrator (Full Pipeline)
Run the entire analysis end-to-end with `main.py`:

```bash
# Test run with 10 policies
python3 main.py --limit 10

# Full 40K+ dataset (will take many hours/days)
python3 main.py
```

Options: `--model`, `--force`, `--skip-similarities`, `--skip-analysis`. See script for details.

This single script runs all steps:
1. Policy classification (demand/suppy/unclear) [skipped if already exists]
2. **Abstract-based embedding generation** (translation as needed, no downloads)
3. Analysis dataset construction
4. Strategy similarity computation
5. Descriptive statistics (LaTeX)
6. World maps (R) and time-trends (Python)
7. Interactive HTML map (Python)


## Next Steps

Future analysis will explore:
- Temporal trends in food legislation
- Geographic distribution of policies
- Keyword and topic analysis
- Correlations between policy types and country characteristics
- [To be determined based on research objectives]

## About the Data

The FAOLEX dataset includes legislation from countries worldwide with metadata such as:
- Country/Territory
- Language (multilingual)
- Date of original text and amendments
- Type of text (Regulation, Legislation, etc.)
- Abstracts and keywords
- Primary subjects and domains

Source: [FAOLEX - Food and Agriculture Organization of the United Nations](http://www.fao.org/faolex/en/)

## Contributing

This is a research/analysis project. For questions or suggestions, please open an issue.

---

### Co-Creation

This project was co-created with **Claude Code** using **Step 3.5 Flash** (StepFun's AI model). The interactive development environment assisted with code generation, debugging, documentation, and analysis throughout the project lifecycle.
