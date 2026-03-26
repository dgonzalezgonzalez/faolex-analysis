# FAOLEX Food Legislation Analysis

Analysis of the FAOLEX (Food and Agriculture Organization of the United Nations Legislative database) food legislation dataset.

## Project Overview

This project analyzes global food legislation data from FAOLEX, containing over 40,000 records of food-related policies, regulations, and laws from countries worldwide.

## Current Status

✅ **Completed**:
- Loaded and cleaned the FAOLEX Food dataset (40,256 records)
- Implemented rule-based classification to categorize policies as **demand-side** or **supply-side**
- Generated `data/policy_categories.csv` with classification results
- Set up Python virtual environment with pandas
- Built vector embedding pipeline to generate embeddings using Ollama's `nomic-embed-text` model

**Classification Results**:
- Supply-side policies: 27,049 (67.2%)
- Demand-side policies: 8,369 (20.8%)
- Unclear/ambiguous: 4,837 (12.0%)

**Enhanced Embedding Pipeline Test** (10 policies):
- ✅ All 10 policies successfully processed
- 🌐 Translation: Non-English texts automatically translated to English using Google Translate (cached)
- 🔪 Chunking: Long texts split into overlapping chunks (2000 chars, 200 overlap) and embeddings averaged
- 📦 Storage: `data/embeddings/embeddings.jsonl` (179 KB) + `manifest.json` with full metadata
- ⏱️  Average processing time: ~21 sec/policy (6.5 chunks each)
- The pipeline is ready for full dataset scaling (potentially optimize with batching for 40K policies)

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
│   ├── policy_categories.csv     # Policy classifications
│   ├── embeddings/
│   │   ├── embeddings.jsonl      # Vector embeddings (JSON Lines)
│   │   └── manifest.json         # Processing manifest
│   └── text_cache/               # Cached downloaded text files (not committed)
├── code/
│   ├── classify_policies.py      # Policy classification
│   ├── text_downloader.py        # Download and cache text files
│   ├── text_extractor.py         # Extract text from TXT/PDF
│   ├── embedding_client.py       # Ollama embedding client
│   ├── embedding_storage.py      # Embeddings storage & manifest
│   └── generate_embeddings.py    # Main embedding pipeline
└── output/                        # Future analysis outputs
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
```

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
