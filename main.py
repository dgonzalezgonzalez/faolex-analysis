#!/usr/bin/env python3
"""
Master orchestrator for the FAOLEX analysis pipeline.

This script runs the complete analysis from raw data to final outputs:
1. Policy classification (demand/supply)
2. Embedding generation with translation and chunking
3. Cosine similarity computation for strategy queries
4. Descriptive statistics and visualizations

Usage:
    python3 main.py [options]

Examples:
    # Run full pipeline on all policies
    python3 main.py

    # Test run with 10 policies
    python3 main.py --limit 10

    # Use nomic-embed-text model instead of all-minilm
    python3 main.py --model nomic-embed-text

    # Skip steps that are already done
    python3 main.py --skip-embeddings --skip-similarities
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

# ========================================================================
# CRITICAL: Change working directory to project root
# This ensures all relative paths resolve correctly regardless of where
# the user runs the script from (especially important on Windows).
# ========================================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"Project root: {PROJECT_ROOT}")
logger.info(f"Working directory set to: {Path.cwd()}")

def run_command(cmd: list, description: str, cwd: Path = None) -> bool:
    """Run a subprocess command and log output."""
    logger.info(f"Running: {description}")
    logger.debug(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False  # We handle errors manually
        )

        if result.stdout:
            logger.info(result.stdout.strip())
        if result.stderr:
            logger.warning(result.stderr.strip())

        if result.returncode != 0:
            logger.error(f"❌ {description} failed with exit code {result.returncode}")
            return False
        else:
            logger.info(f"✅ {description} completed successfully")
            return True

    except Exception as e:
        logger.error(f"❌ {description} failed with exception: {e}")
        return False

def check_file_exists(path: Path, description: str) -> bool:
    """Check if a required file exists."""
    if path.exists():
        logger.info(f"✅ Found {description}: {path}")
        return True
    else:
        logger.warning(f"⚠️  Missing {description}: {path}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run the complete FAOLEX analysis pipeline")
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of policies to process (for testing)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='all-minilm',
        choices=['nomic-embed-text', 'all-minilm'],
        help='Embedding model to use'
    )
    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Skip text download step (use cached texts)'
    )
    parser.add_argument(
        '--skip-embeddings',
        action='store_true',
        help='Skip embedding generation (use existing embeddings)'
    )
    parser.add_argument(
        '--skip-similarities',
        action='store_true',
        help='Skip similarity computation (use existing similarities)'
    )
    parser.add_argument(
        '--skip-analysis',
        action='store_true',
        help='Skip descriptive analysis (LaTeX tables + maps)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-running steps (overwrite existing outputs)'
    )
    parser.add_argument(
        '--venv',
        type=Path,
        default=Path('venv/bin/activate'),
        help='Path to virtual environment activation script'
    )

    args = parser.parse_args()

    # Define paths
    venv_activate = args.venv
    data_dir = Path('data')
    output_dir = Path('output')

    # Ensure directories exist
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("FAOLEX Analysis Pipeline Orchestrator")
    logger.info("=" * 60)

    # ===========================
    # STEP 0: PRELIMINARY CHECKS
    # ===========================
    logger.info("\n>>> Step 0: Preliminary Checks <<<")

    # Check if we need to create classification (policy_categories.csv)
    classification_needed = args.force or not check_file_exists(
        data_dir / 'policy_categories.csv',
        'policy classification results'
    )

    # Check embeddings
    embeddings_needed = args.force or not check_file_exists(
        data_dir / 'embeddings' / 'manifest.json',
        'embeddings manifest'
    )

    # Check similarities
    similarities_needed = args.force or not check_file_exists(
        data_dir / 'strategy_similarities.csv',
        'strategy similarity scores'
    )

    # Check analysis outputs
    analysis_needed = args.force or not check_file_exists(
        output_dir / 'descriptive_statistics.tex',
        'descriptive statistics LaTeX'
    ) or not check_file_exists(
        output_dir / 'world_similarity_map.pdf',
        'world similarity map'
    )

    # ===========================
    # STEP 1: POLICY CLASSIFICATION
    # ===========================
    if classification_needed:
        logger.info("\n>>> Step 1: Policy Classification <<<")
        if run_command(
            [sys.executable, 'code/classify_policies.py'],
            description="Classify policies as demand-side/supply-side"
        ):
            logger.info("✅ Policy classification completed")
        else:
            logger.error("❌ Pipeline stopped: classification failed")
            return 1
    else:
        logger.info("\n>>> Step 1: Policy Classification [SKIPPED] (already exists) <<<")

    # ===========================
    # STEP 2: EMBEDDING GENERATION
    # ===========================
    if embeddings_needed:
        logger.info("\n>>> Step 2: Embedding Generation <<<")

        cmd = [sys.executable, 'code/generate_embeddings.py']
        if args.limit:
            cmd.extend(['--limit', str(args.limit)])
        if args.model:
            cmd.extend(['--model', args.model])
        if args.force:
            cmd.append('--force')

        if run_command(
            cmd,
            description=f"Generate embeddings (model={args.model}, limit={args.limit or 'all'})"
        ):
            logger.info("✅ Embedding generation completed")
        else:
            logger.error("❌ Pipeline stopped: embedding generation failed")
            return 1
    else:
        logger.info("\n>>> Step 2: Embedding Generation [SKIPPED] (already exists) <<<")

    # ===========================
    # STEP 3: SIMILARITY COMPUTATION
    # ===========================
    if similarities_needed:
        logger.info("\n>>> Step 3: Strategy Similarity Computation <<<")

        if run_command(
            [sys.executable, 'code/compute_similarities.py', '--model', args.model],
            description="Compute cosine similarities for strategy queries"
        ):
            logger.info("✅ Similarity computation completed")
        else:
            logger.error("❌ Pipeline stopped: similarity computation failed")
            return 1
    else:
        logger.info("\n>>> Step 3: Strategy Similarity Computation [SKIPPED] (already exists) <<<")

    # ===========================
    # STEP 4: ANALYSIS & VISUALIZATION
    # ===========================
    if analysis_needed:
        logger.info("\n>>> Step 4: Analysis & Visualization <<<")

        # 4a: Generate descriptive LaTeX tables
        if run_command(
            [sys.executable, 'code/generate_descriptive_tables.py'],
            description="Generate descriptive statistics LaTeX tables"
        ):
            logger.info("✅ Descriptive tables generated")
        else:
            logger.error("❌ Analysis: descriptive tables failed")
            # Continue anyway

        # 4b: Generate world maps (if R is available)
        logger.info("Checking for R to generate world maps...")
        r_check = subprocess.run(['which', 'Rscript'], capture_output=True)
        if r_check.returncode == 0:
            if run_command(
                ['Rscript', '--vanilla', 'code/world_similarity_map.R'],
                description="Generate world map visualizations"
            ):
                logger.info("✅ World maps generated")
            else:
                logger.error("❌ Analysis: world map generation failed")
        else:
            logger.warning("⚠️  Rscript not found, skipping world map generation")

        # 4c: Generate interactive HTML time-series map
        if run_command(
            [sys.executable, 'code/generate_interactive_map.py'],
            description="Generate interactive animated HTML world map"
        ):
            logger.info("✅ Interactive HTML map generated")
        else:
            logger.error("❌ Analysis: interactive map generation failed")
    else:
        logger.info("\n>>> Step 4: Analysis & Visualization [SKIPPED] (outputs exist) <<<")

    # ===========================
    # FINAL SUMMARY
    # ===========================
    logger.info("\n" + "=" * 60)
    logger.info("✅ PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info("\nOutputs:")
    logger.info(f"  • Policy embeddings: {data_dir / 'embeddings' / 'embeddings.jsonl'}")
    logger.info(f"  • Similarity scores: {data_dir / 'strategy_similarities.csv'}")
    logger.info(f"  • Descriptives LaTeX: {output_dir / 'descriptive_statistics.tex'}")
    logger.info(f"  • Time trends: {output_dir / 'strategy_*_trends.*'}")
    logger.info(f"  • World maps: {output_dir / 'world_similarity_map.*'}")
    logger.info(f"  • Interactive map: {output_dir / 'interactive_strategy_map.html'}")
    logger.info("\nTo view results:")
    logger.info(f"  pd {'data/strategy_similarities.csv'}")
    logger.info(f"  cat {'output/descriptive_statistics.tex'}")
    logger.info(f"  open {'output/strategy_*_trends.pdf'}")
    logger.info(f"  open {'output/interactive_strategy_map.html'} (in browser)")
    logger.info("=" * 60)

    return 0

if __name__ == "__main__":
    sys.exit(main())
