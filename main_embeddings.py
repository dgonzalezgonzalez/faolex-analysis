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
import os
import sys
from pathlib import Path

# ========================================================================
# CRITICAL: Change working directory to project root
# This ensures all relative paths in imported modules work correctly
# regardless of where the user runs the script from.
# ========================================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)
# Add project root to Python path for imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# Add 'code' directory to Python path for module imports
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"Project root: {PROJECT_ROOT}")
logger.info(f"Working directory set to: {Path.cwd()}")
logger.info(f"Code directory: {CODE_DIR}")

def check_prerequisites() -> bool:
    """Check that required files exist."""
    data_dir = PROJECT_ROOT / 'data'
    required = [data_dir / 'FAOLEX_Food.csv']

    missing = [p for p in required if not p.exists()]
    if missing:
        logger.error(f"Missing required files: {missing}")
        logger.error(f"Please ensure the data directory exists at: {data_dir}")
        return False

    logger.info("✅ All prerequisites found")
    return True

def run_classification(force: bool = False) -> bool:
    """Run policy classification by directly calling the module."""
    try:
        import classify_policies
        output_path = PROJECT_ROOT / 'data' / 'policy_categories.csv'

        # If not forcing and output exists, skip
        if not force and output_path.exists():
            logger.info(f"⏭️  Skipping classification - output already exists: {output_path}")
            return True

        logger.info(">>> Running policy classification...")
        # Call the process_csv function directly
        classify_policies.process_csv(
            input_path=str(PROJECT_ROOT / 'data' / 'FAOLEX_Food.csv'),
            output_path=str(output_path)
        )
        logger.info("✅ Policy classification completed")
        return True
    except Exception as e:
        logger.error(f"❌ Policy classification failed: {e}", exc_info=True)
        return False

def run_embeddings(limit: int = None, model: str = 'all-minilm', force: bool = False, batch_size: int = 10) -> bool:
    """Generate embeddings by directly calling the module's main with modified sys.argv."""
    try:
        import generate_embeddings

        # Build argument list
        argv = ['generate_embeddings.py']
        if limit:
            argv.extend(['--limit', str(limit)])
        if model:
            argv.extend(['--model', model])
        if force:
            argv.append('--force')
        argv.extend(['--batch-size', str(batch_size)])

        # Temporarily replace sys.argv
        old_argv = sys.argv
        sys.argv = argv

        try:
            # Call the main function directly
            generate_embeddings.main()
            logger.info("✅ Embedding generation completed")
            return True
        finally:
            # Restore sys.argv
            sys.argv = old_argv
    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {e}", exc_info=True)
        return False

def run_similarities(model: str = 'all-minilm', force: bool = False) -> bool:
    """Compute strategy similarities by directly calling the module's main with modified sys.argv."""
    try:
        import compute_similarities

        # Build argument list
        argv = ['compute_similarities.py', '--model', model]
        if force:
            argv.append('--force')

        # Temporarily replace sys.argv
        old_argv = sys.argv
        sys.argv = argv

        try:
            # Call the main function directly
            compute_similarities.main()
            logger.info("✅ Similarity computation completed")
            return True
        finally:
            # Restore sys.argv
            sys.argv = old_argv
    except Exception as e:
        logger.error(f"❌ Similarity computation failed: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Embeddings-only pipeline: classify, embed, compute similarities (no subprocess calls)"
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
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for chunk embedding (default: 10)'
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("EMBEDDINGS-ONLY PIPELINE (Direct Imports - No Subprocess)")
    logger.info("=" * 70)
    logger.info(f"Model: {args.model}")
    logger.info(f"Limit: {args.limit or 'ALL'}")
    logger.info(f"Force: {args.force}")
    logger.info(f"Batch size: {args.batch_size}")

    # Check prerequisites
    if not check_prerequisites():
        return 1

    # =====================
    # STEP 1: Classification
    # =====================
    if not args.skip_classification:
        if not run_classification(force=args.force):
            return 1
    else:
        logger.info("⏭️  Skipping classification (using existing policy_categories.csv)")

    # =====================
    # STEP 2: Embeddings
    # =====================
    if not args.skip_embeddings:
        if not run_embeddings(
            limit=args.limit,
            model=args.model,
            force=args.force,
            batch_size=args.batch_size
        ):
            return 1
    else:
        logger.info("⏭️  Skipping embeddings (using existing data/embeddings/)")

    # =====================
    # STEP 3: Similarities
    # =====================
    if not args.skip_similarities:
        if not run_similarities(
            model=args.model,
            force=args.force
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
    logger.info("  1. Copy the data/ folder back to this machine for analysis")
    logger.info("  2. Or run: python3 main.py (for full analysis with visualizations)")
    logger.info("=" * 70)

    return 0

if __name__ == "__main__":
    sys.exit(main())
