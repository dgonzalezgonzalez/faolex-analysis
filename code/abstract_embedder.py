#!/usr/bin/env python3
"""
Generate embeddings directly from the Abstract field in FAOLEX_Food.csv.
This replaces the full-text download/extract/translate pipeline with a simpler,
higher-quality approach that avoids corrupted PDFs and translation issues.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from tqdm import tqdm

from text_translator import TextTranslator
from embedding_client import EmbeddingClient
from embedding_storage import EmbeddingStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_policy_abstracts(csv_path: Path, limit: int = None) -> pd.DataFrame:
    """
    Load policies with their abstracts from the main FAOLEX CSV.

    Returns DataFrame with columns: record_id, abstract, country, category (if available)
    """
    logger.info(f"Loading policies from {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    # BOM cleanup
    first_col = df.columns[0]
    if first_col != 'Record Id':
        df = df.rename(columns={first_col: 'Record Id'})
    df.columns = df.columns.str.strip()

    # Keep essential columns
    needed = ['Record Id', 'Abstract', 'Title', 'Country/Territory', 'Language of document']
    available = [col for col in needed if col in df.columns]
    df = df[available].copy()

    # Rename for consistency
    df = df.rename(columns={
        'Record Id': 'record_id',
        'Abstract': 'abstract',
        'Title': 'title',
        'Country/Territory': 'country',
        'Language of document': 'language'
    })

    # Drop rows with missing abstracts
    before = len(df)
    df = df.dropna(subset=['abstract'])
    after = len(df)
    logger.info(f"Kept {after} policies with abstracts (dropped {before - after} missing)")

    # Filter out very short abstracts (< 50 chars)
    df = df[df['abstract'].astype(str).str.len() >= 50]
    logger.info(f"Kept {len(df)} policies with abstracts >= 50 chars")

    if limit:
        df = df.head(limit)
        logger.info(f"Limited to {len(df)} policies for testing")

    return df


def language_to_iso_code(language: str) -> str:
    """
    Convert language name or code to ISO 639-1 code for translation API.
    Returns None if unknown (will use auto-detect).
    """
    if pd.isna(language):
        return None
    lang = str(language).strip().lower()
    mapping = {
        'english': 'en', 'en': 'en', 'eng': 'en', 'anglais': 'en', 'ingles': 'en',
        'french': 'fr', 'fr': 'fr', 'fra': 'fr', 'francais': 'fr', 'français': 'fr',
        'spanish': 'es', 'es': 'es', 'esp': 'es', 'espanol': 'es', 'español': 'es',
        'portuguese': 'pt', 'pt': 'pt', 'por': 'pt', 'portugues': 'pt', 'português': 'pt',
        'italian': 'it', 'it': 'it', 'ita': 'it', 'italiano': 'it',
        'german': 'de', 'de': 'de', 'deu': 'de', 'deutsch': 'de',
    }
    return mapping.get(lang)

def determine_if_translation_needed(language: str, abstract_text: str) -> bool:
    """
    Determine if translation is needed based on language field and text detection.
    Uses ISO code mapping to avoid substring false positives (e.g., 'french' contains 'en').
    """
    if pd.isna(language) or language == '':
        # Auto-detect
        from langdetect import detect
        try:
            lang = detect(str(abstract_text)[:500])
            return lang != 'en'
        except:
            return True  # Play safe, translate if unsure
    else:
        # Use ISO code mapping to accurately identify English
        iso_code = language_to_iso_code(language)
        if iso_code is None:
            # Unknown language string, fallback to auto-detect
            try:
                from langdetect import detect
                detected_lang = detect(str(abstract_text)[:500])
                return detected_lang != 'en'
            except:
                return True
        else:
            return iso_code != 'en'


def process_abstract_embedding(
    record_id: str,
    abstract: str,
    language: str,
    translator: TextTranslator,
    embed_client: EmbeddingClient,
    storage: EmbeddingStorage
) -> bool:
    """
    Process a single policy abstract:
    - Translate to English if needed
    - Generate embedding
    - Store
    """
    try:
        # Check if already completed
        existing = storage.get_record_status(record_id)
        if existing and existing["status"] == "completed":
            logger.debug(f"Skipping {record_id} - already completed")
            return True

        # Determine if translation needed
        needs_translation = determine_if_translation_needed(language, abstract)

        if needs_translation:
            # Use CSV language as source hint to improve translation accuracy
            src_lang_code = language_to_iso_code(language)
            translated = translator.translate(str(abstract), force=True, source_lang=src_lang_code)
            if translated is None or translated == abstract:
                logger.warning(f"Translation may have failed for {record_id}, using original")
                text_to_embed = str(abstract)
                was_translated = False
            else:
                text_to_embed = translated
                was_translated = True
        else:
            text_to_embed = str(abstract)
            was_translated = False

        # Generate embedding ( abstracts are short, no chunking needed)
        embedding = embed_client.generate_embedding(text_to_embed)
        if embedding is None:
            logger.error(f"Embedding generation failed for {record_id}")
            storage.mark_failed(record_id, error="Embedding generation failed")
            return False

        # Store embedding with metadata
        storage.append_embedding(
            record_id=record_id,
            text=text_to_embed[:5000],
            embedding=embedding,
            metadata={
                "title": "",  # Will be filled later from dataset
                "language": language,
                "original_language": language,
                "country": "",  # Will be filled later
                "category": "",  # Will be filled later
                "text_source": "abstract",
                "was_translated": was_translated,
                "original_text_length": len(str(abstract)),
                "processed_text_length": len(text_to_embed)
            }
        )

        storage.finalize_embedding(
            record_id=record_id,
            text_length=len(text_to_embed),
            embedding_dim=len(embedding),
            metadata={
                "title": "",
                "language": language,
                "original_language": language,
                "country": "",
                "category": "",
                "text_source": "abstract",
                "was_translated": was_translated,
                "original_text_length": len(str(abstract))
            }
        )

        logger.info(f"Successfully processed {record_id} (dim={len(embedding)})")
        return True

    except Exception as e:
        logger.error(f"Error processing {record_id}: {e}", exc_info=True)
        storage.mark_failed(record_id, error=str(e))
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings from policy abstracts")
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('data/FAOLEX_Food.csv'),
        help='Input CSV file with policy data'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of policies to process (for testing). Default: all with abstracts.'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='all-minilm',
        choices=['nomic-embed-text', 'all-minilm'],
        help='Embedding model to use'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-processing even if already completed'
    )

    args = parser.parse_args()

    # Initialize components
    translator = TextTranslator()
    embed_client = EmbeddingClient(model=args.model)
    storage = EmbeddingStorage()

    logger.info(f"Using embedding model: {args.model}")
    logger.info(f"Embedding dimension: {embed_client.get_embedding_dimension()}")

    # Load policies with abstracts
    policies = load_policy_abstracts(args.input, limit=args.limit)
    logger.info(f"Loaded {len(policies)} policies with abstracts")

    # Process each policy
    success_count = 0
    fail_count = 0

    for _, row in tqdm(policies.iterrows(), total=len(policies), desc="Processing abstracts"):
        record_id = row['record_id']
        abstract = row['abstract']
        language = row.get('language', '')

        success = process_abstract_embedding(
            record_id=record_id,
            abstract=abstract,
            language=language,
            translator=translator,
            embed_client=embed_client,
            storage=storage
        )

        if success:
            success_count += 1
        else:
            fail_count += 1

    # Final summary
    logger.info("Pipeline complete!")
    logger.info(f"Successfully processed: {success_count}")
    logger.info(f"Failed: {fail_count}")

    stats = storage.get_statistics()
    logger.info(f"Total records in manifest: {stats['total']}")
    logger.info(f"Completed embeddings: {stats['completed']}")
    logger.info(f"Embeddings file: {storage.embeddings_file}")

    # After embedding generation, we should also update manifest with title/country/category
    # by merging with policy_categories.csv and the original FAOLEX data
    logger.info("\nNext step: Run compute_similarities.py to calculate strategy scores.")


if __name__ == "__main__":
    main()
