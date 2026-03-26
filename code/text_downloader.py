#!/usr/bin/env python3
"""
Text Downloader Module
Downloads and caches text/PDF files from FAOLEX URLs.
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Optional, Tuple
import requests
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextDownloader:
    """Download and cache text files from URLs."""

    def __init__(self, cache_dir: Path = Path("data/text_cache"), delay: float = 1.0):
        """
        Args:
            cache_dir: Directory to store downloaded files
            delay: Delay between downloads (seconds) to be respectful
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; FAOLEX-Analysis/1.0)'
        })

    def _get_cache_path(self, record_id: str, url: str) -> Path:
        """Generate cache filename from record ID and URL."""
        # Create a unique filename using record_id and URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        # Determine extension from URL
        ext = '.txt' if url.lower().strip().endswith('.txt') else '.pdf'
        return self.cache_dir / f"{record_id}{ext}"

    def download(self, record_id: str, text_url: str, force: bool = False) -> Tuple[Path, bool]:
        """
        Download a text file if not already cached.

        Args:
            record_id: Policy record ID
            text_url: URL to download from
            force: Force re-download even if cached

        Returns:
            (path_to_cached_file, was_downloaded)
        """
        if not text_url or pd.isna(text_url):
            raise ValueError(f"No text URL provided for {record_id}")

        # Handle semicolon-separated URLs (take first valid one)
        urls = [u.strip() for u in str(text_url).split(';') if u.strip()]
        if not urls:
            raise ValueError(f"No valid URLs for {record_id}")

        # Try each URL until one succeeds
        last_error = None
        for url in urls:
            cache_path = self._get_cache_path(record_id, url)

            if cache_path.exists() and not force:
                logger.debug(f"Cache hit for {record_id}: {cache_path}")
                return cache_path, False

            try:
                logger.info(f"Downloading {record_id} from {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Save to cache
                cache_path.write_bytes(response.content)
                logger.info(f"Saved to {cache_path}")

                # Respect rate limiting
                time.sleep(self.delay)
                return cache_path, True

            except Exception as e:
                logger.warning(f"Failed to download from {url}: {e}")
                last_error = e
                continue

        raise RuntimeError(f"All download attempts failed for {record_id}: {last_error}")

    def get_file_path(self, record_id: str, text_url: str) -> Path:
        """Get cache path without downloading."""
        urls = [u.strip() for u in str(text_url).split(';') if u.strip()]
        if not urls:
            raise ValueError(f"No valid URLs for {record_id}")
        return self._get_cache_path(record_id, urls[0])

# Import pandas here since it's used in the method
import pandas as pd
