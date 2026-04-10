# Repository Guidelines

## Project Structure & Module Organization
Core pipeline code lives in `code/`. Python scripts handle classification, embeddings, similarity scoring, tables, trends, interactive maps, and the unified dashboard (`generate_dashboard.py`, `dashboard_builder.py`). R scripts generate static map outputs. `main.py` is the canonical end-to-end entrypoint. Keep raw and derived datasets in `data/`, embeddings in `data/embeddings/`, and intermediate CSV/log files in `data/temp/`. Reserve `output/` for final deliverables only: PDF, PNG, HTML, and LaTeX.

## Build, Test, and Development Commands
Create the local environment first:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the full pipeline with `python3 main.py`. Use `python3 main.py --limit 10` for a short validation run, or `python3 main.py --force` to rebuild outputs. Common step-level commands:

```bash
python3 code/classify_policies.py
python3 code/abstract_embedder.py --limit 10
python3 code/compute_similarities.py
python3 code/generate_trends.py
python3 code/generate_dashboard.py
Rscript --vanilla code/world_similarity_map.R
```

Ollama must be installed and running for embedding commands. When working from individual scripts, keep paths repo-relative and preserve the existing data flow into `data/`, `data/temp/`, and `output/`.

## Coding Style & Naming Conventions
Follow existing Python style: 4-space indentation, `snake_case` for functions/files/variables, and small CLI-oriented scripts with a `main()` entrypoint where appropriate. Use `utf-8-sig` when reading the FAOLEX CSV because the dataset includes a BOM. Prefer clear pandas transformations over dense one-liners, and handle date parsing defensively because source dates are inconsistent. For R scripts, keep filenames descriptive and aligned with generated outputs, such as `generate_policy_count_maps.R`.

## Testing Guidelines
Python dashboard coverage now lives in `tests/` and runs with `venv/bin/python -m unittest discover -s tests`. Validate analysis changes by running the smallest relevant pipeline step and checking the artifact it generates. Start with `python3 main.py --limit 10` for smoke testing, then inspect updated files in `data/`, `data/temp/`, or `output/` as appropriate. When changing map logic, rerun the affected `Rscript` command and verify both PDF and PNG outputs are produced.

## Commit & Pull Request Guidelines
Recent history uses short, imperative subjects, often with a scope prefix, for example `feat(analysis): add subgroup similarity maps and policy count visualizations`. Keep commits focused and describe the user-visible pipeline change. PRs should include: purpose, affected scripts or data products, exact validation commands run, and representative output paths. Add screenshots only when interactive HTML or visual outputs change materially. If you change the pipeline, outputs, or repository layout, update `README.md` in the same PR.
