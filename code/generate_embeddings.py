#!/usr/bin/env python3
"""
Main Pipeline: Generate embeddings for FAOLEX policies.
Downloads text, extracts content, generates embeddings with Ollama.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List
import pandas as pd
from tqdm import tqdm

from text_downloader import TextDownloader
from text_extractor import TextExtractor
from text_translator import TextTranslator
from text_chunker import TextChunker
from embedding_client import EmbeddingClient
from embedding_storage import EmbeddingStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_policies(csv_path: Path, limit: int = None) -> pd.DataFrame:
    """
    Load policies from CSV.

    Args:
        csv_path: Path to FAOLEX_Food.csv
        limit: Limit number of records (for testing)

    Returns:
        DataFrame with policies
    """
    logger.info(f"Loading policies from {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    # BOM cleanup: explicitly rename first column to 'Record Id'
    # The BOM causes the first column name to have weird characters
    first_col = df.columns[0]
    if first_col != 'Record Id':
        df = df.rename(columns={first_col: 'Record Id'})

    # Strip whitespace from all columns
    df.columns = df.columns.str.strip()

    if limit:
        df = df.head(limit)
        logger.info(f"Limited to {len(df)} policies for testing")

    logger.info(f"Loaded {len(df)} policies")
    return df

def process_policy(
    record_id: str,
    title: str,
    text_url: str,
    language: str,
    country: str,
    category: str,
    downloader: TextDownloader,
    extractor: TextExtractor,
    translator: TextTranslator,
    chunker: TextChunker,
    embed_client: EmbeddingClient,
    storage: EmbeddingStorage,
    batch_size: int = 10,
    force_redownload: bool = False
) -> bool:
    """
    Process a single policy through the full pipeline:
    download -> extract -> translate -> chunk -> embed (average) -> store

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if already completed
        existing = storage.get_record_status(record_id)
        if existing and existing["status"] == "completed" and not force_redownload:
            logger.debug(f"Skipping {record_id} - already completed")
            return True

        # 1. Download text
        cache_path, was_downloaded = downloader.download(record_id, text_url, force=force_redownload)
        text_source = cache_path.suffix.lstrip('.')

        # 2. Extract text (use higher limit; we'll chunk later)
        text = extractor.extract_text(cache_path, max_length=100000)

        # Validate text quality
        if not extractor.validate_text(text):
            error_msg = f"Text validation failed for {record_id}"
            logger.error(error_msg)
            storage.mark_failed(record_id, error=error_msg, metadata={
                "title": title, "language": language, "country": country,
                "category": category, "text_source": text_source
            })
            return False

        # 3. Translate to English if needed
        # Use CSV language field to decide if translation is required (forced)
        needs_translation = translator.should_translate(language)
        original_language = language  # from CSV metadata

        if needs_translation is False:
            # CSV indicates it's English, but still verify and maybe translate if detection says otherwise
            if translator.is_english(text):
                translated_text = text
                was_translated = False
            else:
                # CSV says English but text is not English - force translation anyway
                logger.warning(f"{record_id}: CSV indicates English but text not English, translating...")
                translated_text = translator.translate(text, force=True)
                was_translated = True
                original_language = 'unknown (mislabeled)'
        elif needs_translation is True:
            # CSV indicates non-English, force translation
            logger.info(f"{record_id}: Forcing translation from {language}")
            translated_text = translator.translate(text, force=True)
            was_translated = True
        else:
            # CSV language is missing/empty, auto-detect
            is_english = translator.is_english(text)
            if is_english:
                translated_text = text
                was_translated = False
            else:
                translated_text = translator.translate(text)
                was_translated = True
                original_language = 'auto-detected'

        # Check if translation failed
        if translated_text == text and (needs_translation is True or (needs_translation is False and not translator.is_english(text))):
            logger.warning(f"Translation may have failed for {record_id}, using original text")

        # 4. Chunk text into manageable pieces
        chunks = chunker.chunk_text(translated_text)
        if not chunks:
            error_msg = f"No chunks produced for {record_id}"
            logger.error(error_msg)
            storage.mark_failed(record_id, error=error_msg, metadata={
                "title": title, "language": language, "country": country,
                "category": category, "text_source": text_source, "text_length": len(translated_text)
            })
            return False

        logger.info(f"Generated {len(chunks)} chunks for {record_id}")

        # 5. Generate embedding by averaging chunk embeddings (with batching)
        embedding = embed_client.generate_embedding_from_chunks(chunks, batch_size=batch_size)
        if embedding is None:
            error_msg = f"Embedding generation failed for {record_id}"
            logger.error(error_msg)
            storage.mark_failed(record_id, error=error_msg, metadata={
                "title": title, "language": language, "country": country,
                "category": category, "text_source": text_source,
                "text_length": len(translated_text), "chunk_count": len(chunks)
            })
            return False

        # 6. Store embedding
        embedding_index = storage.append_embedding(
            record_id=record_id,
            text=translated_text[:5000],  # Store truncated translated text
            embedding=embedding,
            metadata={
                "title": title,
                "language": language,
                "original_language": original_language,
                "country": country,
                "category": category,
                "text_source": text_source,
                "was_translated": was_translated,
                "chunk_count": len(chunks),
                "original_text_length": len(text),
                "processed_text_length": len(translated_text)
            }
        )

        # 7. Update manifest
        embedding_dim = len(embedding)
        storage.finalize_embedding(
            record_id=record_id,
            text_length=len(translated_text),
            embedding_dim=embedding_dim,
            metadata={
                "title": title,
                "language": language,
                "original_language": original_language,
                "country": country,
                "category": category,
                "text_source": text_source,
                "was_translated": was_translated,
                "chunk_count": len(chunks),
                "original_text_length": len(text)
            }
        )

        logger.info(f"Successfully processed {record_id} (dim={embedding_dim}, index={embedding_index}, chunks={len(chunks)})")
        return True

    except Exception as e:
        logger.error(f"Error processing {record_id}: {e}", exc_info=True)
        storage.mark_failed(record_id, error=str(e))
        return False

def load_category_map() -> Dict[str, str]:
    """Load the policy categories from policy_categories.csv."""
    csv_path = Path("data/policy_categories.csv")
    if not csv_path.exists():
        logger.warning(f"Category file not found: {csv_path}")
        return {}

    df = pd.read_csv(csv_path)
    return dict(zip(df['Record Id'], df['Category']))

def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for FAOLEX policies")
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('data/FAOLEX_Food.csv'),
        help='Input CSV file'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit number of policies to process (for testing)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download and re-processing'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for chunk embedding'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='all-minilm',
        choices=['nomic-embed-text', 'all-minilm'],
        help='Embedding model to use (default: all-minilm for speed)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show current status and exit'
    )

    args = parser.parse_args()

    # Check status mode
    if args.status:
        storage = EmbeddingStorage()
        stats = storage.get_statistics()
        print("Embedding Storage Status:")
        print(f"  Total records: {stats['total']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Embeddings file size: {stats['embeddings_file_size_mb']:.2f} MB")
        return

    # Adjust batch size and chunk size for models with smaller context windows
    if args.model == 'all-minilm':
        if args.batch_size > 1:
            logger.warning(f"all-minilm has a small context window; setting batch_size to 1 to avoid exceeding limits")
            args.batch_size = 1
        # all-minilm has a smaller context window (~512 tokens). Legal text has high token density,
        # so we need to be conservative. Empirical testing shows 300 chars is safe.
        chunk_size = 300
        overlap = 30
    else:
        chunk_size = 2000
        overlap = 200

    # Load data
    policies = load_policies(args.input, limit=args.limit)
    categories = load_category_map()

    # Initialize components
    downloader = TextDownloader()
    extractor = TextExtractor()
    translator = TextTranslator()
    chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
    embed_client = EmbeddingClient(model=args.model)
    storage = EmbeddingStorage()

    logger.info(f"Starting embedding generation for {len(policies)} policies")
    logger.info(f"Using model: {args.model}")
    logger.info(f"Chunk batch size: {args.batch_size}")
    logger.info(f"Embedding dimension: {embed_client.get_embedding_dimension()}")

    # Process each policy
    success_count = 0
    fail_count = 0

    for _, row in tqdm(policies.iterrows(), total=len(policies), desc="Processing policies"):
        record_id = row['Record Id']
        title = row.get('Title', '')
        text_url = row.get('Text URL', '')
        language = row.get('Language of document', '')
        country = row.get('Country/Territory', '')
        category = categories.get(record_id, 'unknown')

        success = process_policy(
            record_id=record_id,
            title=title,
            text_url=text_url,
            language=language,
            country=country,
            category=category,
            downloader=downloader,
            extractor=extractor,
            translator=translator,
            chunker=chunker,
            embed_client=embed_client,
            storage=storage,
            batch_size=args.batch_size,
            force_redownload=args.force
        )

        if success:
            success_count += 1
        else:
            fail_count += 1

    # Final summary
    logger.info(f"Pipeline complete!")
    logger.info(f"Successfully processed: {success_count}")
    logger.info(f"Failed: {fail_count}")

    stats = storage.get_statistics()
    logger.info(f"Total records in manifest: {stats['total']}")
    logger.info(f"Completed embeddings: {stats['completed']}")
    logger.info(f"Embeddings file: {storage.embeddings_file}")

if __name__ == "__main__":
    main()
