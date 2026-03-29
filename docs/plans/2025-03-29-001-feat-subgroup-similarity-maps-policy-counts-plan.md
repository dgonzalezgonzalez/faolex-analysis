---
title: feat: generate subgroup similarity maps and policy count visualizations
type: feat
status: active
date: 2026-03-29
---

# feat: Generate Subgroup Similarity Maps and Policy Count Visualizations

## Overview

This plan outlines the creation of new output visualizations for the FAOLEX analysis project:

1. **Subgroup similarity maps**: Static world maps (PDF/PNG) showing average cosine similarity for demand-side and supply-side policy subgroups for each of the three strategy dimensions (SUS, FS, NUT) — 6 maps total.
2. **Policy count visualizations**: A set of figures replacing similarity metrics with raw policy counts, including:
   - Time-trend graph showing number of policies per year (all, demand, supply) with expanded time window to the earliest valid policy.
   - Static world maps showing policy counts by country (total, demand-side, supply-side) — 3 maps.

All visualizations will follow the style and conventions of existing outputs and will be added to the `output/` directory. Documentation in `CLAUDE.md` and `README.md` will be updated accordingly.

## Problem Frame

The current analysis produces visualizations of **average cosine similarity** for three strategy dimensions, both as time trends and static world maps. These visualizations include all policies aggregated by year/country, and the trend graphs also break down by demand/supply categories.

Two gaps are identified:

- The existing static maps (`strategy_*_map.*`) show averages for **all policies only**. There is no geographic breakdown for demand-side and supply-side subgroups.
- The analysis so far focuses on similarity scores. There is no visualization of **raw policy counts** — the volume of legislation over time and across countries — which provides important context about the dataset itself and policy activity patterns.

The user requests:
1. New static maps for demand- and supply-side subgroups (similarity scores, 6 maps).
2. A complementary set of visualizations based on policy counts instead of similarities (trend graph + country maps). These will be fewer in number because counts do not vary by the three strategy dimensions.

This enhances the project's analytical deliverables and provides both depth (subgroup patterns) and breadth (count-based context).

## Requirements Trace

- **R1**: Create 6 new static world maps (PDF + PNG) showing average similarity by country for:
  - `strategy_sus` for demand-side policies only
  - `strategy_sus` for supply-side policies only
  - `strategy_fs` for demand-side policies only
  - `strategy_fs` for supply-side policies only
  - `strategy_nut` for demand-side policies only
  - `strategy_nut` for supply-side policies only
- **R2**: Create a time-trend graph of **policy counts** (not similarity) with:
  - Lines for All policies, Demand-side, and Supply-side
  - Expanded time window from earliest valid policy year to 2025 (no artificial 1992 cutoff)
  - Output as PDF and PNG in `output/`
- **R3**: Create 3 static world maps (PDF + PNG) showing **total policy counts** by country:
  - All policies (total count)
  - Demand-side policies only
  - Supply-side policies only
- **R4**: Follow existing visual style conventions (color scales, dimensions, labeling) for consistency.
- **R5**: All new scripts must read from existing `data/analysis_dataset.csv` and avoid re-computing embeddings or similarities.
- **R6**: Filter out malformed dates (same logic as existing scripts: last 4 characters must be digits).
- **R7**: Update `CLAUDE.md` to document the new outputs and any new code files.
- **R8**: Update `README.md` to inform users about the new visualizations, how to generate them, and file inventory.

## Scope Boundaries

- **Excluded**: Interactive HTML map modifications. The existing animated map already covers similarity time-series for all policies; producing a count-based animation is out of scope.
- **Excluded**: Visualizations for the `unclear` category. Only demand-side and supply-side subgroups are required.
- **Excluded**: Modifying existing visualization scripts in-place. New dedicated scripts will be created to preserve existing functionality.
- **Excluded**: Policy count breakdown by strategy dimension (not applicable).
- **Excluded**: Additional statistical tests or modeling beyond descriptive visualizations.

## Context & Research

### Relevant Code and Patterns

**Existing maps** (`code/world_similarity_map.R`):
- Loads `data/analysis_dataset.csv`
- Extracts year via `substr(date_original, nchar(date_original)-3, nchar(date_original))`; keeps if `^\\d{4}$`
- Filters to year window `>=1992 & <=2025`
- Aggregates by country: `mean(strategy_* )`
- Maps country names to ISO3 using `countrycode`
- Joins with `rnaturalearth` world shapefile
- Creates three maps using `ggplot2` + `geom_sf` with unified sequential color scale (#deebf7 to #08519e, limits 0.061-0.467)
- Saves as PDF and PNG to `output/`
- Also generates a time-series CSV for the interactive map.

**Existing trends** (`code/generate_trends.py`):
- Loads `data/analysis_dataset.csv`
- Same year extraction and filtering (1992-2025)
- Defines categories = `{'All': df, 'Demand-side': df[df['Category']=='demand_side'], 'Supply-side': df[df['Category']=='supply_side']}`
- For each strategy column, plots mean similarity by year for each category (3 lines on one plot)
- Saves as PDF and PNG to `output/`

**Data schema** (`data/analysis_dataset.csv`):
- Columns: `Record Id, strategy_sus, strategy_fs, strategy_nut, Category, Title, country, date_original, Type_of_text, Language_of_document`
- `Category` values: `demand_side`, `supply_side`, `unclear`
- `date_original` in various string formats; year extraction via last 4 chars is robust.

### Institutional Learnings

- The project uses a mix of Python (for trends, LaTeX tables, interactive maps) and R (for static world maps). Both are acceptable; we will follow the existing split: Python for time trends, R for static maps.
- Output files go to `output/` with descriptive naming: `{metric}_{dimension}_trends.{pdf,png}` and `{metric}_{dimension}_map.{pdf,png}`.
- Intermediate data processing should be done within the script; no intermediate CSVs are required for these visualizations (except perhaps optional debugging). Existing scripts sometimes write logs to `data/temp/`; we may follow that for robustness but not required.
- The R map style uses `theme_minimal()` with legend at bottom, specific blue sequential palette, and squishing out-of-bounds values.
- Color scale for similarity maps is fixed across all maps (0.061-0.467) to enable comparison. This should be preserved for subgroup similarity maps.
- The Python trend graphs use `matplotlib` with linewidth=2, markers only on the "All" line.

### External References

None needed; patterns are well-established within the repo.

## Key Technical Decisions

- **Decision 1**: Implement subgroup similarity maps as a new R script (`code/generate_subgroup_similarity_maps.R`) rather than modifying `world_similarity_map.R`. This preserves existing behavior and allows independent parallel development and execution.
- **Decision 2**: Implement policy count trends as a new Python script (`code/generate_policy_counts_trends.py`) following the structure of `generate_trends.py` but with counts and expanded time window.
- **Decision 3**: Implement policy count maps as a new R script (`code/generate_policy_count_maps.R`) following the structure of `world_similarity_map.R` but using counts instead of mean similarity. The color scale will be data-driven (sequential palette, percentiles) because count ranges differ from similarity ranges.
- **Decision 4**: The subgroup similarity maps will use the same fixed color scale (0.061-0.467) as existing maps for comparability.
- **Decision 5**: For policy count maps, we will sum the number of policies per country (over the 1992-2025 window, matching existing map window) rather than averaging. This reflects total legislative activity.
- **Decision 6**: For trend graphs, we will not include the `unclear` category as a separate line, maintaining consistency with existing trends which only show All, Demand-side, and Supply-side. The "All" line includes unclear policies.
- **Decision 7**: Year filtering: For subgroup maps and count maps (which replicate existing map window), use 1992-2025 as in the original. For policy count trends, use the full valid date range (earliest to 2025) as requested.
- **Decision 8**: All scripts will be executable directly (Python shebang, Rscript) and will output to `output/` with automatic directory creation.
- **Decision 9**: No intermediate CSV exports are required, but the scripts may print summary statistics to stdout for transparency.

## Open Questions

### Resolved During Planning

- **Q**: Should the subgroup similarity maps use the same color scale as all-policies maps?
  - **Resolution**: Yes, fixed scale 0.061-0.467 preserves comparability.
- **Q**: Should policy count maps use the same year window as existing maps (1992-2025) or expanded?
  - **Resolution**: Use 1992-2025 for maps; trend graph only gets expanded window as specified.
- **Q**: Should we include the `unclear` category in count visualizations?
  - **Resolution**: No, maintain consistency with existing trend breakdown (All, Demand, Supply only). Unclear is part of "All".
- **Q**: How to aggregate count by country? Sum or average per year?
  - **Resolution**: Sum over all years (1992-2025) to reflect total volume; equivalent to count of policies from that country in that period.

### Deferred to Implementation

- Exact sequential palette color choice for count maps (will use R's `Blues` or similar to maintain aesthetic).
- Whether to add optional command-line arguments to scripts (not needed for first version; can be added later).
- Whether to include additional categories (e.g., regional organizations) – out of scope.

## High-Level Technical Design

### Data Flow Sketch

All visualization scripts follow this pattern:

```
load analysis_dataset.csv
extract year (last 4 digits) and filter valid years
filter by Category if needed (for subgroups) or keep all
aggregate:
  - For trends: groupby year and category, compute count OR mean similarity
  - For maps: groupby country (and optionally year), compute count OR mean similarity
  - map country to ISO3 for spatial join
  - join with world shapefile (rnaturalearth)
  - create plot with appropriate scale
  - save to output/ as PDF and PNG
```

### Script Responsibilities

- `generate_subgroup_similarity_maps.R`:
  - For each strategy (`strategy_sus`, `strategy_fs`, `strategy_nut`) and each category (`demand_side`, `supply_side`):
    - Filter `analysis_dataset` to that category
    - Aggregate by country: mean(similarity)
    - Join with world map
    - Plot with fixed fill scale (0.061-0.467)
    - Save as `output/strategy_{strat}_{cat}_map.pdf` and `.png`
- `generate_policy_counts_trends.py`:
  - Determine full valid year range from dataset (min to max, respecting malformed date filtering)
  - For each category (All, Demand-side, Supply-side), count policies per year
  - Plot line graph (All line with markers, others without)
  - Save as `output/policy_counts_trends.pdf` and `.png`
- `generate_policy_count_maps.R`:
  - For each category (All, Demand-side, Supply-side):
    - Aggregate by country: count number of policies (over 1992-2025)
    - Join with world map
    - Plot with sequential fill scale (e.g., Blues) with limits based on percentiles
    - Save as `output/policy_counts_{cat}_map.pdf` and `.png`

## Implementation Units

- [ ] **Unit 1: Create Python script for policy count time trends**
  - **Goal**: Generate `output/policy_counts_trends.{pdf,png}` showing number of policies per year for All, Demand-side, and Supply-side categories with expanded time window.
  - **Requirements**: R2, R6, R8
  - **Dependencies**: None (standalone)
  - **Files**:
    - Create: `code/generate_policy_counts_trends.py`
    - Output: `output/policy_counts_trends.pdf`, `output/policy_counts_trends.png`
  - **Approach**:
    - Load `data/analysis_dataset.csv` with pandas.
    - Extract year: create `year_str` as last 4 chars of `date_original`; keep rows where `year_str` matches `^\d{4}$`; convert to int.
    - Determine `min_year` and `max_year` from the cleaned data (no hardcoded 1992).
    - Define categories: `All` (all data), `Demand-side` (`Category=='demand_side'`), `Supply-side` (`Category=='supply_side'`).
    - For each category, group by `year` and count records.
    - Plot with matplotlib: three lines; label All with markers; axis labels; legend; grid.
    - Save to `output/` as PDF and PNG (300 dpi).
  - **Patterns to follow**: `code/generate_trends.py` (structure, plotting style); robust date handling from `code/generate_descriptive_tables.py`.
  - **Test scenarios**:
    - Verify that malformed dates (e.g., "????", "196?") are excluded.
    - Verify that the year axis spans from the earliest valid year to 2025.
    - Verify counts per category sum correctly to total per year (All = Demand+Supply+Unclear).
    - Check that output files exist and are non-empty.
  - **Verification**:
    - Run `python3 code/generate_policy_counts_trends.py`
    - Inspect plot: three lines, proper legend, readable labels.
    - Confirm earliest year on x-axis matches dataset (likely 1940s or earlier).
    - Files appear in `output/` with correct names.

- [ ] **Unit 2: Create R script for subgroup similarity maps**
  - **Goal**: Generate 6 static world maps (PDF+PNG) of average similarity for demand-side and supply-side subgroups for each strategy dimension.
  - **Requirements**: R1, R4, R6
  - **Dependencies**: None (standalone)
  - **Files**:
    - Create: `code/generate_subgroup_similarity_maps.R`
    - Outputs:
      - `output/strategy_sus_demand_map.pdf`, `output/strategy_sus_demand_map.png`
      - `output/strategy_sus_supply_map.pdf`, `output/strategy_sus_supply_map.png`
      - `output/strategy_fs_demand_map.pdf`, `output/strategy_fs_demand_map.png`
      - `output/strategy_fs_supply_map.pdf`, `output/strategy_fs_supply_map.png`
      - `output/strategy_nut_demand_map.pdf`, `output/strategy_nut_demand_map.png`
      - `output/strategy_nut_supply_map.pdf`, `output/strategy_nut_supply_map.png`
  - **Approach**:
    - Read `data/analysis_dataset.csv`.
    - Clean and extract year as in existing `world_similarity_map.R`; filter `year >= 1992 & year <= 2025`.
    - Define target combinations: strategies = c("strategy_sus", "strategy_fs", "strategy_nut") and categories = c("demand_side", "supply_side").
    - For each combination:
      - Filter data to `Category == category`.
      - Group by `country` and compute `mean(value)` where value is the strategy column.
      - Convert `country` to ISO3 using `countrycode`.
      - Join with world `sf` object from `rnaturalearth`.
      - Create map with `ggplot2`: `geom_sf(aes(fill = value))`; use `scale_fill_gradient` with `limits = c(0.061, 0.467)` and colors `low="#deebf7"`, `high="#08519e"`, `oob = scales::squish`.
      - Apply same theme settings as existing (legend at bottom, minimal theme, no title).
      - Save with `ggsave` to `output/` with appropriate filename; width=6, height=4 inches, dpi=300 for PNG.
    - Print progress messages.
  - **Patterns to follow**: `code/world_similarity_map.R` (exactly, but with category filter). Reuse the `make_map` function logic but incorporate category as a parameter.
  - **Test scenarios**:
    - Verify that filtered datasets contain only the specified category.
    - Check that mean similarity values are computed correctly (manually spot-check a country).
    - Ensure that countries with no policies in that category appear as NA (rendered as light gray? The existing map uses `na.value = "gray80"` implicitly? Actually in the existing R script, the default is gray for NA; we should set `na.value = "gray90"` or similar to match. The existing code does not explicitly set `na.value`; we can add `na.value = "gray90"` to maintain consistency with the original. Let's check: In the existing R script, after `left_join`, NA values will be plotted as a default color. To maintain consistency, we'll use the same `na.value` as the original if needed. We'll copy the original `make_map` function exactly but allow filtering.
    - Verify that all 6 maps are generated with correct dimensions and readable legends.
  - **Verification**:
    - Run `Rscript --vanilla code/generate_subgroup_similarity_maps.R`
    - Check that 12 files (6×2 formats) exist in `output/`.
    - Open a few to confirm they render and show a world map with gradient.
    - Confirm that the fill scale is identical to existing maps (0.061-0.467).

- [ ] **Unit 3: Create R script for policy count maps**
  - **Goal**: Generate 3 static world maps (PDF+PNG) showing total policy counts by country for All, Demand-side, and Supply-side.
  - **Requirements**: R3, R4, R6
  - **Dependencies**: None (standalone)
  - **Files**:
    - Create: `code/generate_policy_count_maps.R`
    - Outputs:
      - `output/policy_counts_total_map.pdf`, `output/policy_counts_total_map.png`
      - `output/policy_counts_demand_map.pdf`, `output/policy_counts_demand_map.png`
      - `output/policy_counts_supply_map.pdf`, `output/policy_counts_supply_map.png`
  - **Approach**:
    - Load `data/analysis_dataset.csv`.
    - Extract and filter year (`>=1992 & <=2025`) consistent with existing map window.
    - Define categories: `total` (all data), `demand` (`Category=="demand_side"`), `supply` (`Category=="supply_side"`).
    - For each category:
      - Filter data as needed.
      - Group by `country` and count number of rows (`n()`).
      - Rename count column to `count`.
      - Convert country to ISO3 using `countrycode`.
      - Join with world `sf`.
      - Determine fill scale: use a sequential palette (e.g., `scale_fill_viridis_c` or `scale_fill_gradient` with Blues). To handle outliers, compute 5th and 95th percentiles of `count` and set `limits` accordingly, with `oob = scales::squish`. Alternatively, use `scale_fill_viridis_c(option="C", direction=-1)` etc. For consistency with similarity map style (which uses a specific blue sequential palette), we'll use `scale_fill_gradient(low="#deebf7", high="#08519e")` with data-driven limits. Compute `p_low = quantile(count, 0.05, na.rm=TRUE)`, `p_high = quantile(count, 0.95, na.rm=TRUE)`. This captures the core variation.
      - Use same theme as existing maps (legend at bottom, minimal, etc.).
      - Save with `ggsave` to `output/` with filename pattern.
    - Print messages.
  - **Patterns to follow**: Existing R map script, but with count aggregation and data-driven limits.
  - **Test scenarios**:
    - Verify that total count sum equals sum of demand + supply + unclear? Actually total includes unclear, so count(total) = count(demand) + count(supply) + count(unclear). That should hold.
    - Check that the count distribution makes sense (some countries high, some low).
    - Ensure maps render without errors and color scale is meaningful (not all one color).
    - Confirm that filenames are correct.
  - **Verification**:
    - Run `Rscript --vanilla code/generate_policy_count_maps.R`
    - Confirm 6 files (3×2) in `output/`.
    - Spot-check that high-count countries (e.g., USA, EU aggregates) appear darker.

- [ ] **Unit 4: Update CLAUDE.md**
  - **Goal**: Document the new code files, their purpose, and the new output files.
  - **Requirements**: R7
  - **Dependencies**: Units 1-3 completed (to reference actual filenames)
  - **Files**: Modify: `CLAUDE.md`
  - **Approach**:
    - In the "Completed Analysis" or "Repository Structure" section, add new bullet points:
      - New code: `generate_subgroup_similarity_maps.R`, `generate_policy_counts_trends.py`, `generate_policy_count_maps.R`
      - New outputs: list the new files (trends, maps) with brief descriptions.
    - Add a subsection "Policy Count Visualizations" describing the trend and map outputs.
    - Add a subsection "Subgroup Similarity Maps" describing the 6 maps.
    - Update the "Repository Structure" tree to include new files under `code/` and `output/`.
    - Mention usage: `Rscript code/generate_subgroup_similarity_maps.R`, `python3 code/generate_policy_counts_trends.py`, `Rscript code/generate_policy_count_maps.R`.
    - Keep the rest unchanged.
  - **Patterns to follow**: The existing CLAUDE.md style (clear, concise, markdown).
  - **Test scenarios**:
    - Verify that new scripts are mentioned and described.
    - Verify that file names are accurate.
    - Check that formatting (code blocks, bullet lists) is consistent.
  - **Verification**:
    - Read the updated `CLAUDE.md` and confirm it reflects the new additions.
    - No script execution needed.

- [ ] **Unit 5: Update README.md**
  - **Goal**: Update user-facing documentation to include new visualizations and instructions.
  - **Requirements**: R8
  - **Dependencies**: Units 1-3 completed; Unit 4 may inform wording.
  - **Files**: Modify: `README.md`
  - **Approach**:
    - In "Current Status" section, add bullet points listing the new output files.
    - In "Repository Structure" tree, add new code files under `code/` and new output files under `output/`.
    - Add a new subsection "Policy Count Visualizations" describing:
      - `policy_counts_trends.{pdf,png}` — time trend of number of policies.
      - `policy_counts_{category}_map.{pdf,png}` — country maps of policy counts.
      - Mention expanded time window for trends.
    - Add a new subsection "Subgroup Similarity Maps" describing the 6 maps.
    - Add usage examples:
      - `python3 code/generate_policy_counts_trends.py`
      - `Rscript code/generate_subgroup_similarity_maps.R`
      - `Rscript code/generate_policy_count_maps.R`
    - Possibly update the "Full Dataset Results" table to indicate these outputs are now available.
    - Keep the overall tone and formatting consistent.
  - **Patterns to follow**: Existing README structure, markdown.
  - **Test scenarios**:
    - Check that the new sections are clear and accurate.
    - Verify that all new filenames are listed correctly.
    - Ensure no broken links (there are no actual links to these files).
  - **Verification**:
    - View `README.md` to confirm updates.
    - Optionally run `markdown` lint if available, but not necessary.

- [ ] **Unit 6: Test all new scripts end-to-end**
  - **Goal**: Ensure all new visualizations generate correctly and outputs are valid.
  - **Requirements**: All above
  - **Dependencies**: Units 1-5 (documentation can be tested after, but scripts must be ready)
  - **Files**: Scripts from Units 1-3; output files.
  - **Approach**:
    - Activate virtual environment (for Python). Ensure R and required packages are installed.
    - Run each script individually and capture output/logs.
    - Verify that all expected output files appear in `output/` and are non-empty (check file sizes > 0).
    - Open a sample of PDF/PNG files to confirm they render (could be done manually; for automated check, at least verify file size > typical threshold, e.g., 1KB).
    - Check that the count trend graph includes data from the earliest year in the dataset (print the min year from script output or inspect the plot axis).
    - Run `python3 code/generate_policy_counts_trends.py` and confirm it prints summary statistics or at least completes without error.
    - Run the two R scripts and confirm they complete with "✓" messages or similar.
    - If any script fails, capture error and log it for debugging.
    - Optionally, generate a manifest of all new outputs and compare to expected list.
  - **Patterns to follow**: The existing testing approach (`main.py` checks).
  - **Test scenarios**:
    - Missing data file: script should error clearly.
    - Empty dataset: script should handle gracefully (maybe produce empty plot? but data exists).
    - R package availability: script should fail with informative message if packages missing.
  - **Verification**:
    - All expected files exist.
    - Files have reasonable size (PDFs > few KB, PNGs > few hundred KB).
    - Visual inspection of a few plots shows expected patterns (world maps, trend lines).
    - No errors in stdout/stderr.

- [ ] **Unit 7: Commit and push changes (optional, user-triggered)**
  - **Goal**: Record all new code and documentation changes in git.
  - **Requirements**: User confirmation to push.
  - **Dependencies**: Unit 6 successful.
  - **Files**: All new and modified files.
  - **Approach**:
    - Run `git status` to see changes.
    - Stage new files (`code/generate_*.py`, `code/generate_*.R`) and modified files (`CLAUDE.md`, `README.md`).
    - Create a conventional commit: `feat: add subgroup similarity maps and policy count visualizations`
    - Push to origin if user confirms.
    - If user defers, note that changes are ready to commit.
  - **Patterns to follow**: Standard git workflow.
  - **Test scenarios**:
    - Verify `git diff` includes expected changes.
    - Ensure no unintended files are staged.
  - **Verification**:
    - `git log -1` shows the new commit if performed.

## System-Wide Impact

- **Interaction graph**: No callbacks; scripts are independent utilities.
- **Error propagation**: Each script will validate input data and fail fast with clear messages.
- **State lifecycle risks**: None; read-only access to existing `analysis_dataset.csv`.
- **API surface parity**: N/A.
- **Integration coverage**: The scripts can be run separately or in parallel; no interdependencies.

## Risks & Dependencies

- **Risk**: R package availability varies across machines. The R scripts require `ggplot2`, `sf`, `rnaturalearth`, `countrycode`, `dplyr`, `cowplot`. The project already documents these dependencies in README; users must have them installed. We can add a check at the start of each R script to error with a helpful message if packages are missing.
- **Risk**: The count maps' color scale limits are data-driven; if the count distribution is extremely skewed, the map may appear mostly white or mostly dark. But using 5th/95th percentiles will squish extremes, as done for similarity maps, which should ensure visible variation.
- **Risk**: The expanded time window for count trends may include very early years with extremely few policies, making the early part of the trend noisy. That's acceptable; the user explicitly requested expanded window. We will include all valid data.

## Documentation / Operational Notes

- Update `CLAUDE.md` to include a "New Outputs" section with descriptions and usage.
- Update `README.md` to include:
  - New code files in the "Repository Structure" and "Key Code Files" lists.
  - New outputs in "Full Dataset Results" and "Repository Structure".
  - New usage subsections after existing ones.
- Consider adding the new scripts to the `.gitignore`? Not needed; they are code, not outputs.
- No changes to `main.py` orchestration needed because these are optional add-on analyses.

## Sources & References

- **Origin document**: User request (see conversation)
- **Related code**:
  - `code/world_similarity_map.R`
  - `code/generate_trends.py`
  - `code/generate_descriptive_tables.py` (date handling)
- **Related PRs/issues**: N/A (new feature)
