#!/usr/bin/env python3
"""
Compute cosine similarity between policy embeddings and strategy query embeddings.
Generates a CSV with policy IDs and similarity scores for each strategy dimension.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List
import pandas as pd
import numpy as np
from tqdm import tqdm

from embedding_client import EmbeddingClient
from embedding_storage import EmbeddingStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define strategy queries
STRATEGY_QUERIES = {
    'strategy_sus': 'action embedded in broader environmentally sustainable strategies',
    'strategy_fs': 'action embedded in a broader food systems strategy or framework',
    'strategy_nut': 'action embedded in a national nutrition or public health nutrition strategy'
}

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

def main():
    parser = argparse.ArgumentParser(description="Compute cosine similarities between policy embeddings and strategy queries")
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('data/strategy_similarities.csv'),
        help='Output CSV file path'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='all-minilm',
        choices=['nomic-embed-text', 'all-minilm'],
        help='Embedding model to use for queries (must match policy embeddings)'
    )

    args = parser.parse_args()

    # Initialize components
    embed_client = EmbeddingClient(model=args.model)
    storage = EmbeddingStorage()

    logger.info(f"Using embedding model: {args.model}")
    logger.info(f"Embedding dimension: {embed_client.get_embedding_dimension()}")

    # 1. Load policy embeddings from storage
    policies = storage.get_all_embeddings()
    logger.info(f"Loaded {len(policies)} policy embeddings")

    if len(policies) == 0:
        logger.error("No embeddings found. Run generate_embeddings.py first.")
        return

    # 2. Generate embeddings for strategy queries
    logger.info("Generating embeddings for strategy queries...")
    query_embeddings = {}
    for key, query_text in STRATEGY_QUERIES.items():
        embedding = embed_client.generate_embedding(query_text)
        if embedding is None:
            logger.error(f"Failed to generate embedding for query: {key}")
            return
        query_embeddings[key] = embedding
        logger.info(f"  ✓ {key}: embedding generated (dim={len(embedding)})")

    # 3. Compute cosine similarities for each policy
    logger.info("Computing cosine similarities...")
    results = []

    for policy in tqdm(policies, desc="Computing similarities"):
        record_id = policy['record_id']
        policy_embedding = policy['embedding']

        # Compute similarity with each query
        similarities = {}
        for query_key, query_embedding in query_embeddings.items():
            sim = cosine_similarity(policy_embedding, query_embedding)
            similarities[query_key] = sim

        # Build result row
        row = {'record_id': record_id}
        row.update(similarities)
        results.append(row)

    # 4. Create DataFrame and save to CSV
    df = pd.DataFrame(results)
    df = df[['record_id', 'strategy_sus', 'strategy_fs', 'strategy_nut']]

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    logger.info(f"✓ Saved similarity scores to {args.output}")
    logger.info(f"Total policies: {len(df)}")
    logger.info("\nTop similarities:")
    print(df.to_string(index=False))

    # Print summary statistics
    print("\nSummary statistics:")
    print(df.describe().round(4))

if __name__ == "__main__":
    main()
