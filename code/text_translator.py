#!/usr/bin/env python3
"""
Text Translation Module
Detects language and translates non-English text to English.
"""

import logging
from typing import Optional
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator
from pathlib import Path
import hashlib
import json

# Ensure consistent detection
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

class TextTranslator:
    """Translate text to English with caching."""

    def __init__(self, cache_file: Path = Path("data/translation_cache.json")):
        """
        Args:
            cache_file: Path to translation cache JSON
        """
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.translator = GoogleTranslator(source='auto', target='en')

    def _load_cache(self) -> dict:
        """Load translation cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load translation cache: {e}")
        return {}

    def _save_cache(self):
        """Save translation cache to disk."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def _cache_key(self, text: str, source_lang: str) -> str:
        """Generate cache key for text."""
        content = f"{source_lang}:{text[:500]}"  # Use first 500 chars as key
        return hashlib.md5(content.encode()).hexdigest()

    def is_english(self, text: str) -> bool:
        """
        Detect if text is in English.

        Args:
            text: Text to detect

        Returns:
            True if English, False otherwise
        """
        if not text or len(text.strip()) < 10:
            return True  # Assume very short texts are fine

        try:
            lang = detect(text)
            return lang == 'en'
        except Exception as e:
            logger.warning(f"Language detection failed: {e}, assuming English")
            return True

    def should_translate(self, csv_language: str) -> bool:
        """
        Determine if translation is needed based on CSV language field.

        Args:
            csv_language: Language value from Language of document column

        Returns:
            True if translation needed, False if English
        """
        if not csv_language:
            # Fallback to auto-detect
            return None  # Signal to auto-detect

        # Normalize language string
        lang = str(csv_language).strip().lower()
        # Check if it's English (common variations)
        english_indicators = ['english', 'en', 'eng', 'anglais', 'ingles']
        return not any(indicator in lang for indicator in english_indicators)

    def translate(self, text: str, force: bool = False, source_lang: str = None) -> str:
        """
        Translate text to English if not already English.

        Args:
            text: Input text
            force: Force translation even if detected as English
            source_lang: Optional source language code (e.g., 'fr', 'es') to override auto-detection.
                         Useful when the CSV provides language metadata.

        Returns:
            Translated text (or original if already English)
        """
        if not text:
            return ""

        # Skip translation if already English (unless forced)
        if not force and self.is_english(text):
            logger.debug("Text already in English, skipping translation")
            return text

        # Determine source language for caching/translation
        if source_lang:
            # Use provided source language directly
            actual_source = source_lang
        else:
            try:
                actual_source = detect(text) if not force else 'unknown'
            except:
                actual_source = 'unknown'

        # Check cache (use source_lang if provided as part of key)
        cache_key = self._cache_key(text, actual_source)
        if cache_key in self.cache and not force:
            logger.debug("Translation cache hit")
            return self.cache[cache_key]

        # Translate
        try:
            logger.info(f"Translating {len(text)} chars from {actual_source} to English")
            # Choose translator based on whether we have explicit source
            if source_lang:
                # Use explicit source language
                translator = GoogleTranslator(source=source_lang, target='en')
            else:
                # Use the default auto-detect translator
                translator = self.translator

            # Deep translator has max length, so chunk if needed
            max_chunk = 5000
            if len(text) <= max_chunk:
                translated = translator.translate(text)
            else:
                # Split into chunks and translate separately
                chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
                translated_chunks = []
                for chunk in chunks:
                    if chunk.strip():
                        translated_chunks.append(translator.translate(chunk))
                translated = ' '.join(translated_chunks)

            # Cache result
            self.cache[cache_key] = translated
            self._save_cache()

            return translated
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Return original text on failure
            return text
