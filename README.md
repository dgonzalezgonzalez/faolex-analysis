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
    └── strategy_nut_trends.pdf
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
The R script (`code/world_similarity_map.R`) creates a multi-panel world map showing average cosine similarity scores by country for the three strategy dimensions.
```bash
Rscript --vanilla code/world_similarity_map.R
```
Output (PNG and PDF) saved to:
- `output/world_similarity_map.pdf`
- `output/world_similarity_map.png`

### Descriptive Statistics (Python → LaTeX)
Generate LaTeX tables with summary statistics and top/bottom policy rankings:
```bash
python3 code/generate_descriptive_tables.py
```
Output:
- `output/descriptive_statistics.tex` (includes sample overview, statistics by category, and extreme cases)

### Master Orchestrator
Run the entire pipeline end-to-end with `main.py`. This is the single entry point that coordinates all steps with proper error handling and skip flags.

```bash
# Full pipeline (all 40K+ policies)
python3 main.py

# Test run (limited sample)
python3 main.py --limit 10

# Use different embedding model
python3 main.py --model nomic-embed-text

# Skip already-completed steps
python3 main.py --skip-embeddings --skip-similarities

# Force re-run from scratch
python3 main.py --force --limit 10
```

The orchestrator:
- Checks for existing outputs to avoid redundant work
- Runs steps in correct order: classify → embed → similarities → analysis
- Provides clear logging and status updates
- Generates all outputs in `data/` and `output/`


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
