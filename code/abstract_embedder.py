#!/usr/bin/env python3
"""
Generate embeddings directly from the Abstract field in FAOLEX_Food.csv.
This replaces the full-text download/extract/translate pipeline with a simpler,
higher-quality approach that avoids corrupted PDFs and translation issues.

Handles long abstracts by:
- Chunking before translation (>4500 chars) to respect Google Translate limits
- Chunking before embedding (if needed for model context) and averaging chunk embeddings
"""

import argparse
import logging
from pathlib import Path
from typing import List, Tuple
import pandas as pd
from tqdm import tqdm
import numpy as np
import re

from text_translator import TextTranslator
from embedding_client import EmbeddingClient
from embedding_storage import EmbeddingStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextChunker:
    """Split text into overlapping chunks for translation or embedding."""

    def __init__(
        self,
        chunk_size: int = 2000,  # characters per chunk
        overlap: int = 200,      # overlap between chunks
        min_chunk_size: int = 100
    ):
        """
        Args:
            chunk_size: Target size for each chunk (in characters)
            overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum acceptable chunk size
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks. Prefers breaking at sentence boundaries.

        Args:
            text: Input text to chunk

        Returns:
            List of text chunks
        """
        if not text or len(text) <= self.chunk_size:
            return [text] if text else []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)

            # If not at the end, try to break at a sentence boundary
            if end < text_len:
                search_start = max(start, end - 200)
                segment = text[search_start:end]
                match = re.search(r'[.!?]\s+', segment)
                if match:
                    boundary_pos = search_start + match.start() + 1
                    if boundary_pos - start >= self.min_chunk_size:
                        end = boundary_pos

            chunk = text[start:end].strip()
            if chunk and len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)

            start = end - self.overlap if end < text_len else text_len
            if start >= text_len:
                break

        logger.debug(f"Chunked text into {len(chunks)} chunks (original: {text_len} chars)")
        return chunks


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


# ============================
# CHUNKING HELPERS
# ============================

def chunk_for_translation(text: str, max_chunk_size: int = 4500, overlap: int = 200) -> List[str]:
    """
    Split text into chunks for translation, respecting Google Translate's 5000 char limit.
    Uses conservative 4500 char limit with overlap to maintain context.
    """
    chunker = TextChunker(chunk_size=max_chunk_size, overlap=overlap)
    return chunker.chunk_text(text)


def chunk_for_embedding(text: str, model: str) -> List[str]:
    """
    Split text into chunks appropriate for the embedding model's context limit.
    Uses adaptive chunk sizes: all-minilm (300/30), nomic (2000/200).
    """
    if model == 'all-minilm':
        chunk_size, overlap = 300, 30
    elif model == 'nomic-embed-text':
        chunk_size, overlap = 2000, 200
    else:
        chunk_size, overlap = 2000, 200  # default

    chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
    chunks = chunker.chunk_text(text)
    # Filter out very short chunks (< 50 chars) which add noise
    return [c for c in chunks if len(c) >= 50]


def translate_chunks(chunks: List[str], translator: TextTranslator, src_lang: str = None) -> str:
    """
    Translate multiple text chunks and concatenate them.
    Returns the full translated text.
    """
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        translated = translator.translate(chunk, force=True, source_lang=src_lang)
        if translated is None or translated == chunk:
            logger.warning(f"Translation may have failed for chunk {i}, using original")
            translated_chunks.append(chunk)
        else:
            translated_chunks.append(translated)
    return ' '.join(translated_chunks)


def embed_and_average(chunks: List[str], embed_client: EmbeddingClient) -> np.ndarray:
    """
    Generate embeddings for each chunk and return the average (normalized) embedding.
    Chunks are normalized before averaging to produce a unit vector.
    """
    if not chunks:
        raise ValueError("No chunks to embed")

    embeddings = []
    for chunk in chunks:
        emb = embed_client.generate_embedding(chunk)
        if emb is None:
            raise ValueError(f"Failed to generate embedding for chunk")
        embeddings.append(np.array(emb))

    # Average embeddings and re-normalize to unit length
    avg_embedding = np.mean(embeddings, axis=0)
    norm = np.linalg.norm(avg_embedding)
    if norm > 0:
        avg_embedding = avg_embedding / norm

    return avg_embedding.tolist()


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
        abstract_text = str(abstract)

        # ======================
        # TRANSLATION (with chunking if needed)
        # ======================
        if needs_translation:
            src_lang_code = language_to_iso_code(language)

            # Check if abstract is too long for single translation (>4500 chars)
            if len(abstract_text) > 4500:
                logger.info(f"Abstract {record_id} is long ({len(abstract_text)} chars), chunking for translation")
                chunks = chunk_for_translation(abstract_text)
                logger.debug(f"Translated in {len(chunks)} chunks")
                text_to_embed = translate_chunks(chunks, translator, src_lang_code)
                was_translated = True
            else:
                translated = translator.translate(abstract_text, force=True, source_lang=src_lang_code)
                if translated is None or translated == abstract_text:
                    logger.warning(f"Translation may have failed for {record_id}, using original")
                    text_to_embed = abstract_text
                    was_translated = False
                else:
                    text_to_embed = translated
                    was_translated = True
        else:
            text_to_embed = abstract_text
            was_translated = False

        # ======================
        # EMBEDDING (with chunking if needed)
        # ======================
        model = embed_client.model
        # Check if text is too long for model context (approx 2000 chars for all-minilm safety)
        max_safe_length = 2000 if model == 'all-minilm' else 5000

        if len(text_to_embed) > max_safe_length:
            logger.info(f"Text for {record_id} is long ({len(text_to_embed)} chars), chunking for embedding")
            chunks = chunk_for_embedding(text_to_embed, model)
            logger.debug(f"Embedded in {len(chunks)} chunks")
            embedding = embed_and_average(chunks, embed_client)
        else:
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
