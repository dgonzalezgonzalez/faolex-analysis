#!/usr/bin/env python3
"""
Text Chunker Module
Splits text into overlapping chunks for embedding.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

class TextChunker:
    """Split text into overlapping chunks to handle long documents."""

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
        Split text into overlapping chunks.

        Prefers breaking at sentence boundaries when possible.

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
            # Calculate end position
            end = min(start + self.chunk_size, text_len)

            # If not at the end, try to break at a sentence boundary
            if end < text_len:
                # Look for sentence boundary within the last 200 chars of the chunk
                search_start = max(start, end - 200)
                segment = text[search_start:end]

                # Sentence boundary patterns: period, exclamation, question mark followed by space or newline
                match = re.search(r'[.!?]\s+', segment)
                if match:
                    # Adjust end to after the sentence boundary
                    boundary_pos = search_start + match.start() + 1
                    if boundary_pos - start >= self.min_chunk_size:
                        end = boundary_pos

            chunk = text[start:end].strip()
            if chunk and len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)

            # Move start forward, accounting for overlap
            start = end - self.overlap if end < text_len else text_len

            # Ensure progress
            if start >= text_len:
                break

        logger.debug(f"Chunked text into {len(chunks)} chunks (original: {text_len} chars)")
        return chunks
