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
- Built and optimized vector embedding pipeline using Ollama's `all-minilm` model (384-dim)
- Implemented automatic translation of non-English texts (Google Translate, cached)
- Implemented text chunking with adaptive sizing based on model context limits
- Added cosine similarity analysis comparing policy embeddings to strategy query embeddings
- Generated time-trend visualizations (Stata) showing similarity evolution by policy type

**Classification Results**:
- Supply-side policies: 27,049 (67.2%)
- Demand-side policies: 8,369 (20.8%)
- Unclear/ambiguous: 4,837 (12.0%)

**Enhanced Embedding Pipeline**:
- Model: `all-minilm` (fast, 384-dimensional) with fallback to `nomic-embed-text` (768-dim)
- Translation: Automatic detection + forced translation based on CSV language field
- Chunking: Adaptive - `all-minilm` uses 300-char chunks (30 overlap); `nomic` uses 2000-char chunks
- Normalization: Averaged chunk embeddings are explicitly normalized to unit length for correct cosine similarity
- Storage: `data/embeddings/embeddings.jsonl` + `manifest.json` with full metadata (translation, chunk counts, etc.)
- Batch embedding: Configurable batch size for efficient Ollama API usage

**Interactive Time-Series World Map**:
- Generated with Plotly (HTML, self-contained with CDN dependency)
- Shows three strategy dimensions simultaneously
- Animated by year with play/pause controls
- Hover tooltips display country, year, and exact similarity scores
- Output: `output/interactive_strategy_map.html`

**Test Results** (10 policies):
- ✅ 10/10 policies successfully embedded
- Chunks per policy: 1–199 (depending on text length)
- Processing time: ~8 sec/policy
- Embedding dimension: 384 (all-minilm)

**Strategy Similarity Analysis**:
Three query strings measure alignment with strategic dimensions:
- `strategy_sus`: "action embedded in broader environmentally sustainable strategies"
- `strategy_fs`: "action embedded in a broader food systems strategy or framework"
- `strategy_nut`: "action embedded in a national nutrition or public health nutrition strategy"

Output: `data/strategy_similarities.csv` with cosine similarity scores for each policy.
Visualizations: `output/strategy_*_trends.pdf/png` showing time trends for all, demand-side, and supply-side policies.

**Key Code Files**:
- `code/generate_embeddings.py` - Main pipeline orchestration
- `code/embedding_client.py` - Ollama API client with batch support and normalization
- `code/compute_similarities.py` - Strategy query similarity computation
- `code/strategy_similarity_trends.do` - Stata script for time-series plots

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
│   ├── embeddings/
│   │   ├── embeddings.jsonl      # Policy vector embeddings (JSON Lines)
│   │   └── manifest.json         # Processing manifest with metadata
│   └── text_cache/               # Cached downloaded text files (not committed)
├── code/
│   ├── classify_policies.py      # Policy classification
│   ├── text_downloader.py        # Download and cache text files
│   ├── text_extractor.py         # Extract text from TXT/PDF
│   ├── text_translator.py        # Language detection & translation
│   ├── text_chunker.py           # Split text into overlapping chunks
│   ├── embedding_client.py       # Ollama embedding client (batch + normalization)
│   ├── embedding_storage.py      # Embeddings storage & manifest management
│   ├── generate_embeddings.py    # Main embedding pipeline orchestrator
│   ├── compute_similarities.py   # Strategy query similarity computation
│   └── strategy_similarity_trends.do  # Stata script for time-trend plots
└── output/                       # Generated figures and reports
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
    ├── world_similarity_map.png
    ├── world_similarity_map.pdf
    └── interactive_strategy_map.html  # Animated world map with slider
```

## Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Policy Classification
```bash
source venv/bin/activate
python3 code/classify_policies.py
```

### Vector Embeddings Generation
```bash
# Test with 10 policies
python3 code/generate_embeddings.py --limit 10

# Process all policies (may take hours/days)
python3 code/generate_embeddings.py

# Resume or check status
python3 code/generate_embeddings.py --status

# Force re-processing (e.g., after fixing issues)
python3 code/generate_embeddings.py --force --limit 10

# Use a different embedding model
python3 code/generate_embeddings.py --model nomic-embed-text  # 768-dim, larger context
```

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

### Time-Trend Visualization (Stata)
The Stata do-file (`code/strategy_similarity_trends.do`) creates line graphs showing average similarity trends over time for all policies, demand-side, and supply-side subsets.
```stata
do code/strategy_similarity_trends.do
```
Output figures (PNG and PDF) are saved to `output/`:
- `strategy_sus_trends.*` - Environmentally sustainable strategies
- `strategy_fs_trends.*` - Food systems strategy frameworks
- `strategy_nut_trends.*` - Nutrition/public health nutrition strategies

### World Map Visualization (R)
The enhanced R script (`code/world_similarity_map_enhanced.R`) creates:

1. **Three separate static maps** (one per strategy, no titles):
   - `output/strategy_sus_map.pdf` / `.png` - Sustainability
   - `output/strategy_fs_map.pdf` / `.png` - Food Systems
   - `output/strategy_nut_map.pdf` / `.png` - Nutrition

2. **Combined static world map**:
   - `output/world_similarity_map.pdf` / `.png` - All three strategies in one figure

3. **Time-series data** (used by the Python interactive map generator):
   - `output/world_map_time_series.csv` - Country-year averaged scores

Run:
```bash
Rscript --vanilla code/world_similarity_map_enhanced.R
```

### Interactive Animated World Map (Python)
Create an interactive HTML map with time-series animation:

```bash
# Generate the interactive map from time series data
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
python3 main.py --limit 10   # Test run
python3 main.py              # Full 40K+ dataset
```

Options: `--model`, `--skip-*`, `--force`. See script for details.

### Embeddings-Only Pipeline (for External Compute)
For running the heavy embedding computation on a powerful external machine:

```bash
python3 main_embeddings.py --limit 100   # Test
python3 main_embeddings.py              # Full dataset
```

This runs only: classify → embed → similarities. Outputs the core data products (`data/policy_categories.csv`, `data/embeddings/`, `data/strategy_similarities.csv`). After completion, copy the `data/` folder back and run `main.py` (or individual analysis scripts) for visualizations and reports.

### Stata Time-Trends
```stata
do code/strategy_similarity_trends.do
```
Outputs: `output/strategy_*_trends.pdf/png`

### Stata Descriptive Tables
```stata
do code/descriptive_tables.do
```
Generates LaTeX tables including sample overview, strategy scores by category, and top/bottom policies: `output/descriptive_statistics.tex`


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
