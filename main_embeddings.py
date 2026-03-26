#!/usr/bin/env python3
"""
Embeddings-Only Pipeline: Generate policy classifications, embeddings, and similarity scores.

This script runs only the computationally intensive steps:
1. Policy classification (demand/supply)
2. Embedding generation (full dataset)
3. Cosine similarity computation for strategy queries

It is designed to be run on a powerful computer to generate the core data products:
- data/policy_categories.csv
- data/embeddings/ (full embeddings)
- data/strategy_similarities.csv

After completion, you can copy the data/ folder back to run analysis scripts.

Usage:
    python3 main_embeddings.py [options]

Examples:
    # Full dataset (all policies)
    python3 main_embeddings.py

    # Test with 100 policies first
    python3 main_embeddings.py --limit 100

    # Use nomic-embed-text model (larger, slower)
    python3 main_embeddings.py --model nomic-embed-text

    # Force re-run from scratch
    python3 main_embeddings.py --force
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_step(script: str, description: str, args_list: list = None) -> bool:
    """Run a Python script as subprocess."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Step: {description}")
    logger.info(f"{'='*60}")

    cmd = [sys.executable, script]
    if args_list:
        cmd.extend(args_list)

    logger.info(f"Running: {' '.join(cmd)}")

    try:
        # Stream output live
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Print stdout/stderr as they come
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)

        if result.returncode != 0:
            logger.error(f"❌ {description} FAILED with exit code {result.returncode}")
            return False
        else:
            logger.info(f"✅ {description} COMPLETED")
            return True

    except Exception as e:
        logger.error(f"❌ {description} FAILED with exception: {e}")
        return False

def check_prerequisites() -> bool:
    """Check that required files exist."""
    data_dir = Path('data')
    required = [data_dir / 'FAOLEX_Food.csv']

    missing = [p for p in required if not p.exists()]
    if missing:
        logger.error(f"Missing required files: {missing}")
        return False

    logger.info("✅ All prerequisites found")
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Embeddings-only pipeline: classify, embed, compute similarities"
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of policies (for testing). Default: process all.'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='all-minilm',
        choices=['nomic-embed-text', 'all-minilm'],
        help='Embedding model (default: all-minilm)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-running all steps, overwriting existing outputs'
    )
    parser.add_argument(
        '--skip-classification',
        action='store_true',
        help='Skip policy classification (use existing policy_categories.csv)'
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

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("EMBEDDINGS-ONLY PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Model: {args.model}")
    logger.info(f"Limit: {args.limit or 'ALL'}")
    logger.info(f"Force: {args.force}")

    # Check prerequisites
    if not check_prerequisites():
        return 1

    # =====================
    # STEP 1: Classification
    # =====================
    if not args.skip_classification:
        if not run_step(
            'code/classify_policies.py',
            'Policy Classification (demand/supply)'
        ):
            return 1
    else:
        logger.info("⏭️  Skipping classification (using existing policy_categories.csv)")

    # =====================
    # STEP 2: Embeddings
    # =====================
    if not args.skip_embeddings:
        embed_args = []
        if args.limit:
            embed_args.extend(['--limit', str(args.limit)])
        if args.model:
            embed_args.extend(['--model', args.model])
        if args.force:
            embed_args.append('--force')

        if not run_step(
            'code/generate_embeddings.py',
            f'Embedding Generation ({args.model})',
            embed_args
        ):
            return 1
    else:
        logger.info("⏭️  Skipping embeddings (using existing data/embeddings/)")

    # =====================
    # STEP 3: Similarities
    # =====================
    if not args.skip_similarities:
        sim_args = ['--model', args.model]
        if args.force:
            sim_args.append('--force')

        if not run_step(
            'code/compute_similarities.py',
            'Strategy Similarity Computation',
            sim_args
        ):
            return 1
    else:
        logger.info("⏭️  Skipping similarities (using existing strategy_similarities.csv)")

    # =====================
    # FINAL SUMMARY
    # =====================
    logger.info("\n" + "=" * 70)
    logger.info("✅ EMBEDDINGS PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("=" * 70)
    logger.info("\nGenerated outputs:")
    logger.info("  • data/policy_categories.csv")
    logger.info("  • data/embeddings/embeddings.jsonl")
    logger.info("  • data/embeddings/manifest.json")
    logger.info("  • data/strategy_similarities.csv")
    logger.info("\nYou can now:")
    logger.info("  1. Copy the data/ folder to another machine")
    logger.info("  2. Run analysis scripts: code/compute_similarities.py, Stata do-files, R scripts")
    logger.info("  3. Or run: python3 main.py (for full analysis with visualizations)")
    logger.info("=" * 70)

    return 0

if __name__ == "__main__":
    sys.exit(main())
