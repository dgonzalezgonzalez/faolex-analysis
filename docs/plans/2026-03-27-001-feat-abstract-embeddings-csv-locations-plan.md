---
title: feat: Transition to abstract-only embeddings and fix intermediate CSV locations
type: feat
status: active
date: 2026-03-27
---

# Transition to Abstract-Only Embeddings and Fix Intermediate CSV Locations

## Overview

This plan addresses two issues in the FAOLEX analysis pipeline:
1. Switch from full-text embeddings to abstract-only embeddings to avoid corrupted/low-quality text files
2. Fix misplaced intermediate CSV file (`world_map_time_series.csv`) that currently goes to `output/` instead of `data/temp/`

The pipeline will be updated to generate embeddings from the `Abstract` field in the main FAOLEX CSV, with automatic translation for non-English abstracts. The trial run should process only 10 policies to validate quality.

## Problem Frame

**Full-text embedding issues:**
- The text download pipeline (`generate_embeddings.py`) fetches `.txt` and `.pdf` files from FAOLEX URLs
- Many downloaded files contain only "simples" (placeholder text), corrupted content, or are otherwise useless
- These garbage texts produce random vector embeddings that add noise to the analysis
- The full-text pipeline is also slower and more complex (download → extract → translate → chunk → embed)

**Abstract-based solution:**
- The `Abstract` field in `FAOLEX_Food.csv` is already available, high-quality, and standardized
- Abstracts are concise (typically 1-2 paragraphs), eliminating the need for chunking
- The `abstract_embedder.py` script already implements this approach but is not yet the default
- We need to make abstract embeddings the standard and ensure all downstream steps work correctly

**Intermediate file organization:**
- The R script (`world_similarity_map.R`) writes `world_map_time_series.csv` to the `output/` directory
- According to project conventions, intermediate/temporary CSV files should reside in `data/temp/`
- The Python interactive map generator already expects the file in `data/temp/`
- This mismatch causes confusion and violates directory structure conventions

## Requirements Trace

- **R1**: Embeddings must be generated from policy abstracts only (no external text downloads)
- **R2**: Non-English abstracts must be automatically detected and translated to English before embedding
- **R3**: The pipeline must support a `--limit` flag to process only a subset (10 policies) for trial runs
- **R4**: The classification step should be skipped if `policy_categories.csv` already exists (unless `--force` is used)
- **R5**: All intermediate CSV files must be stored in `data/temp/`, not `output/`
- **R6**: The master orchestrator (`main.py`) must successfully run the complete pipeline end-to-end with the new approach
- **R7**: Documentation (README.md and CLAUDE.md) must be updated to reflect the new standard approach

## Scope Boundaries

- **In scope**:
  - Modify `main.py` to make abstract embeddings the default (or only) option
  - Fix `world_similarity_map.R` to write CSV to `data/temp/`
  - Update documentation to describe abstract-based pipeline
  - Test with 10 policies using `python main.py --limit 10`
  - Ensure `build_analysis_dataset.py` correctly merges metadata from abstract embeddings

- **Out of scope**:
  - Removing the full-text pipeline (`generate_embeddings.py`) entirely (it may be kept for reference or specialized use cases)
  - Optimizing performance for the full 40K+ policy dataset
  - Adding new analysis or visualization types
  - Changing the embedding model or chunking strategy (abstracts don't need chunking)

## Context & Research

### Relevant Code and Patterns

- `code/abstract_embedder.py`: Already implements abstract-based embedding with translation. Needs integration into main pipeline.
- `code/main.py`: Orchestrator with `--use-abstract` flag. Will be modified to use abstract embeddings by default.
- `code/build_analysis_dataset.py`: Constructs analysis dataset from embedding manifest + FAOLEX metadata. Sets `Type_of_text: 'Abstract'` marker (line 69).
- `code/world_similarity_map.R`: Writes `world_map_time_series.csv` to `output/` (line 118). **Needs fix**.
- `code/generate_timeseries.py`: Already writes correctly to `data/temp/world_map_time_series.csv` (line 73).
- `code/generate_interactive_map.py`: Defaults to reading from `data/temp/world_map_time_series.csv` (line 183).

### Institutional Learnings

From recent commits:
- `a8018ad`: Move remaining log files from root to data/temp/
- `026c5c9`: Update file organization: move intermediate files to data/temp, clarify conventions in CLAUDE.md
- `5cf6d5e`: Update analysis to use all 1,327 policies with embeddings

The project has been progressively organizing intermediate files into `data/temp/`. The R script's CSV output is an outlier that needs correction.

### External References

(none needed - all changes are internal code organization)

## Key Technical Decisions

- **Decision 1**: `main.py` will default to using `abstract_embedder.py` instead of `generate_embeddings.py`.
  - Rationale: Abstracts are higher quality, faster to process, and avoid corrupted downloads. The full-text pipeline is no longer needed for standard analysis.
  - Implementation: Remove `--use-abstract` flag and hardcode the orchestrator to call `abstract_embedder.py`. Alternatively, keep the flag but change default to `True` and update docs. **Preferred approach**: Simplify by calling `abstract_embedder.py` directly, as the full-text pipeline is deprecated.
  - The `--skip-download` flag becomes meaningless with abstracts-only; may be removed or left ignored.

- **Decision 2**: Keep abstract embeddings in same storage format (`data/embeddings/`) as full-text embeddings.
  - Rationale: Downstream code (`compute_similarities.py`, `build_analysis_dataset.py`) reads from the same manifest/JSONL storage regardless of source. The `text_source` metadata field will distinguish them.

- **Decision 3**: Fix CSV path in R script only. Python code already uses correct path.
  - Rationale: `world_similarity_map.R` is the sole source writing the CSV to `output/`. The interactive map generator already defaults to `data/temp/`, so fixing the R script resolves the inconsistency.

## Implementation Units

- [x] **Unit 1: Update main.py to use abstract embeddings as the standard pipeline**
  - **Goal**: Remove reliance on `--use-abstract` flag and call `abstract_embedder.py` directly
  - **Requirements**: R1, R2, R3, R6, R7
  - **Dependencies**: None
  - **Files to modify**:
    - `main.py`: Remove `--use-abstract` argument (lines 116-119). In Step 2, always construct command `[sys.executable, 'code/abstract_embedder.py']` with appropriate flags (`--limit`, `--model`, `--force`). Remove logic for `else` branch that calls `generate_embeddings.py`.
  - **Approach**:
    - Simplify argument parser: delete `--use-abstract` option
    - Replace the conditional in Step 2 with a single unconditional call to `abstract_embedder.py`
    - Keep flags `--limit`, `--model`, `--force` which are already supported by `abstract_embedder.py`
    - Update help text and logging messages to reflect abstract-based approach
  - **Pattern to follow**: Maintain existing structure of run_command calls and logging
  - **Test scenarios**:
    - Run `python main.py --limit 10` and verify abstract_embedder.py is invoked
    - Check that embedding generation completes without attempting any downloads
    - Verify `data/embeddings/manifest.json` records have `"text_source": "abstract"`
  - **Verification**: main.py executes successfully through embeddings step; logs indicate abstract-based processing

- [x] **Unit 2: Fix intermediate CSV output location in R script**
  - **Goal**: Write `world_map_time_series.csv` to `data/temp/` instead of `output/`
  - **Requirements**: R5
  - **Dependencies**: None
  - **Files to modify**:
    - `code/world_similarity_map.R`: Change line 118 from `write.csv(anim_data, file.path(output_dir, "world_map_time_series.csv"), row.names = FALSE)` to `write.csv(anim_data, "data/temp/world_map_time_series.csv", row.names = FALSE)`. Also update line 120 message accordingly.
  - **Approach**:
    - Hardcode the path to `data/temp/world_map_time_series.csv` since it's an intermediate file, not a final output
    - Create `data/temp/` directory if needed (R's `dir.create` can be called with `recursive=TRUE` or Python handles it in generate_interactive_map)
  - **Pattern to follow**: Match the path used in `generate_timeseries.py` (line 73)
  - **Test scenarios**:
    - Run `Rscript code/world_similarity_map.R` (after analysis_dataset exists) and verify CSV is created in `data/temp/`
    - Confirm no CSV is written to `output/`
  - **Verification**: `data/temp/world_map_time_series.csv` exists; `output/world_map_time_series.csv` does not exist

- [x] **Unit 3: Update documentation to reflect abstract-based pipeline**
  - **Goal**: Align README.md and CLAUDE.md with the new standard
  - **Requirements**: R7
  - **Dependencies**: Unit 1 (main.py changes) should be done first
  - **Files to modify**:
    - `README.md`: Revise sections to indicate abstract embeddings are now the default. Update usage examples under "Vector Embeddings Generation" and "Master Orchestrator". Change reference to `output/world_map_time_series.csv` to `data/temp/world_map_time_series.csv` (line 176).
    - `CLAUDE.md`: Update "Completed Analysis" and "Embedding Pipeline" sections to describe abstract-based embeddings. Remove or deprecate references to full-text pipeline. Fix the note about `output/world_map_time_series.csv` (line 134). Update directory conventions if needed.
  - **Approach**:
    - Emphasize that embeddings are generated from abstracts directly
    - Mention that translation is applied for non-English abstracts
    - Update code file references: remove or archive full-text component docs (text_downloader, text_extractor, text_chunker may become unused)
    - Keep mention of `abstract_embedder.py` as the core embedding script
  - **Pattern to follow**: Keep prose accurate and concise; maintain hyperlinks where appropriate
  - **Test scenarios**:
    - Read updated docs and confirm they match the actual code behavior
    - Verify no contradictions between README and CLAUDE.md
  - **Verification**: `grep -n "generate_embeddings.py" README.md` should show it's either removed or clearly marked deprecated; references to intermediate CSV point to `data/temp/`

- [x] **Unit 4: Run trial pipeline with 10 policies to validate integration**
  - **Goal**: Execute full pipeline on small sample to confirm all components work together
  - **Requirements**: R6
  - **Dependencies**: Units 1, 2 (code changes) must be complete; classification already exists (`data/policy_categories.csv`)
  - **Files to test**: Entire pipeline (no specific file creation)
  - **Approach**:
    - Activate virtual environment: `source venv/bin/activate`
    - Run: `python main.py --limit 10`
    - Ensure Ollama is running with the required model (`all-minilm` by default)
    - Observe logs for errors; check that steps complete in order:
      1. Classification [SKIPPED if policy_categories.csv exists]
      2. Embedding Generation (abstract_embedder.py)
      3. Build Analysis Dataset
      4. Similarity Computation
      5. Analysis & Visualization (descriptive tables, world maps, trends, interactive map)
    - If any step fails, fix errors and retry
  - **Execution note**: This is a test run; if issues arise, debug and iterate within this unit before considering plan complete
  - **Pattern to follow**: Use existing logging and error handling; capture terminal output for verification
  - **Test scenarios**:
    - Successful completion with exit code 0
    - Embeddings file created: `data/embeddings/embeddings.jsonl`
    - Similarities file created: `data/strategy_similarities.csv`
    - Analysis dataset created: `data/analysis_dataset.dta` and `.csv`
    - Output files created in `output/`: descriptive_statistics.tex, strategy_*_maps, strategy_*_trends, interactive_strategy_map.html
    - Intermediate CSV: `data/temp/world_map_time_series.csv` exists; no CSV in `output/`
  - **Verification**: Pipeline returns exit code 0; all expected output files present; intermediate file locations correct

## System-Wide Impact

- **Interaction graph**: The embedding generation step in `main.py` changes to invoke `abstract_embedder.py` directly. Downstream steps remain unchanged.
- **Error propagation**: If abstract embedding fails (e.g., translation API down), the failure is at Step 2; downstream steps won't run.
- **State lifecycle risks**: The `data/embeddings/` directory may contain a mix of old full-text embeddings and new abstract embeddings. To avoid mixing, either:
  - Use `--force` to start fresh, or
  - The `abstract_embedder.py` and `EmbeddingStorage` will skip already-completed record_ids, which could be from either pipeline. Metadata field `text_source` distinguishes them, but mixed embeddings might introduce inconsistency in the analysis dataset. For a clean trial, recommend deleting or archiving old `data/embeddings/` before full run.
- **API surface parity**: The `abstract_embedder.py` command-line interface is similar to `generate_embeddings.py` (supports `--limit`, `--model`, `--force`), so main.py integration is straightforward.
- **Integration coverage**: All downstream scripts (`compute_similarities.py`, `build_analysis_dataset.py`, `generate_descriptive_tables.py`, `generate_interactive_map.py`, R script) are data-agnostic; they only read from manifest/CSV. No further changes needed.

## Risks & Dependencies

- **Risk 1**: Mixed embeddings from old full-text and new abstract pipelines could cause inconsistency if `--force` is not used.
  - Mitigation: Document that for clean results, users should either run with `--force` or delete `data/embeddings/` before running. The build_analysis_dataset step reads from manifest, so it will include whatever embeddings exist. For the trial with 10 policies, this is negligible; for full run, a clean start is recommended.

- **Risk 2**: `abstract_embedder.py` may not yet populate all metadata fields that `build_analysis_dataset.py` expects (title, country, category).
  - Mitigation: `build_analysis_dataset.py` already enriches embeddings by merging with FAOLEX metadata and policy_categories.csv (lines 24-58). The abstract embedder stores minimal metadata, but that's sufficient; enrichment happens later. Verify during Unit 4.

- **Risk 3**: Translation failures could produce poor-quality embeddings for non-English abstracts.
  - Mitigation: The abstract_embedder uses cached translation; it should mirror the translator used in full-text pipeline. Monitor logs in trial for translation warnings.

- **Dependency**: Ollama must be running with the specified model before running the pipeline. This was already a requirement; no change.

## Documentation / Operational Notes

- **README.md updates**:
  - Revise "Current Status" to highlight abstract-based embeddings
  - Under "Usage", replace reference to `code/generate_embeddings.py` with `code/abstract_embedder.py` as the primary script (or note it's called by main.py). Keep `generate_embeddings.py` documentation if we decide to keep it as deprecated.
  - Update "Repository Structure" to reflect that `text_cache/` may become unused.
  - Change `output/world_map_time_series.csv` reference to `data/temp/world_map_time_series.csv`
  - Master orchestrator section should reflect that abstract embeddings are now the standard.

- **CLAUDE.md updates**:
  - Update "Completed Analysis" to describe abstract-based embedding pipeline
  - Update "Vector Embedding Pipeline" section or replace with "Abstract Embedding Pipeline"
  - Remove or clearly deprecate the full-text component description (text_downloader, text_extractor, text_chunker usage)
  - Fix intermediate file note about world_map_time_series.csv location
  - Consider adding a note that the old pipeline is retained for backward compatibility but not recommended

- **Operational note**: After merging this plan, users should run `python main.py --limit 10` to test. For full dataset, simply `python main.py`. The `--use-abstract` flag is removed; the `--skip-download` flag is now redundant but harmless.

## Sources & References

- **Origin document**: User request via ce-plan skill (2026-03-27)
- Relevant code:
  - `main.py` (orchestrator)
  - `code/abstract_embedder.py` (new standard)
  - `code/generate_embeddings.py` (old pipeline, to be deprecated)
  - `code/world_similarity_map.R` (CSV output location fix)
  - `code/build_analysis_dataset.py` (metadata enrichment)
  - `README.md` and `CLAUDE.md` (documentation)
- Related commits:
  - `5cf6d5e`: Update analysis to use all 1,327 policies with embeddings
  - `026c5c9`: Move intermediate files to data/temp

## Implementation Outcome (2026-03-27)

- Trial run: `python main.py --limit 10` completed successfully (exit code 0)
- Classification skipped (existing `policy_categories.csv`)
- Abstract embeddings generated for 10 policies; translation applied as needed
- All downstream steps executed: analysis dataset, similarities, descriptive tables, R maps, Python trends, interactive map
- Intermediate CSV `data/temp/world_map_time_series.csv` correctly placed (not in `output/`)
- All final outputs generated in `output/`
- Pipeline now defaults to abstract-based embeddings; full-text pipeline deprecated
