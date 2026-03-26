#!/usr/bin/env python3
"""
Text Extractor Module
Extracts clean text from TXT and PDF files.
"""

from pathlib import Path
from typing import Optional
import logging
import re

logger = logging.getLogger(__name__)

class TextExtractor:
    """Extract text from various file formats."""

    @staticmethod
    def extract_text(file_path: Path, max_length: int = 50000) -> str:
        """
        Extract text from a file based on its extension.

        Args:
            file_path: Path to the file
            max_length: Maximum characters to return (truncate if longer)

        Returns:
            Cleaned text string
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()

        if ext == '.txt':
            text = TextExtractor._extract_from_txt(file_path)
        elif ext == '.pdf':
            text = TextExtractor._extract_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        # Clean and normalize text
        text = TextExtractor._clean_text(text)

        # Truncate if too long
        if len(text) > max_length:
            logger.warning(f"Text for {file_path.stem} is {len(text)} chars, truncating to {max_length}")
            text = text[:max_length]

        return text

    @staticmethod
    def _extract_from_txt(file_path: Path) -> str:
        """Extract text from a .txt file."""
        try:
            # Try UTF-8 first
            return file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Fallback to latin-1
            return file_path.read_text(encoding='latin-1')

    @staticmethod
    def _extract_from_pdf(file_path: Path) -> str:
        """Extract text from a PDF file using PyPDF2."""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(file_path))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return '\n'.join(text_parts)
        except Exception as e:
            logger.error(f"PDF extraction failed for {file_path}: {e}")
            raise

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean extracted text:
        - Remove excessive whitespace
        - Normalize line breaks
        - Remove control characters
        """
        if not text:
            return ""

        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)

        # Remove control characters except newlines and tabs
        text = ''.join(ch for ch in text if ch >= ' ' or ch in '\n\t')

        # Strip leading/trailing whitespace
        return text.strip()

    @staticmethod
    def validate_text(text: str, min_length: int = 50) -> bool:
        """
        Basic validation to ensure text is readable.
        Checks for garbled text (e.g., Farsi encoding issues).

        Args:
            text: Text to validate
            min_length: Minimum acceptable length

        Returns:
            True if text appears valid, False otherwise
        """
        if len(text) < min_length:
            return False

        # Check for excessive non-ASCII characters (might indicate encoding issues)
        non_ascii_ratio = sum(1 for c in text if ord(c) > 127) / len(text)
        if non_ascii_ratio > 0.7:
            logger.warning(f"Text has {non_ascii_ratio:.1%} non-ASCII characters - may be garbled")
            return False

        # Check for very low letter-to-symbol ratio (might be binary garbage)
        letters = sum(1 for c in text if c.isalpha())
        if letters / len(text) < 0.3:
            logger.warning(f"Text has only {letters/len(text):.1%} letters - may be corrupted")
            return False

        return True
