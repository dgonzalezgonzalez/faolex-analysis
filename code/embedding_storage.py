#!/usr/bin/env python3
"""
Embedding Storage Module
Manages JSON Lines storage for embeddings with manifest tracking.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class EmbeddingStorage:
    """Store and retrieve embeddings in JSON Lines format with manifest."""

    def __init__(
        self,
        embeddings_dir: Path = Path("data/embeddings"),
        manifest_file: str = "manifest.json"
    ):
        """
        Args:
            embeddings_dir: Directory for embeddings storage
            manifest_file: Manifest filename within embeddings_dir
        """
        self.embeddings_dir = Path(embeddings_dir)
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.embeddings_dir / manifest_file
        self.embeddings_file = self.embeddings_dir / "embeddings.jsonl"

        # Initialize or load manifest
        self.manifest = self._load_or_init_manifest()

        # Track embedding index
        self.embedding_index = self._get_next_index()

    def _load_or_init_manifest(self) -> Dict[str, Any]:
        """Load existing manifest or create new one."""
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        else:
            manifest = {
                "version": "1.0",
                "created": datetime.utcnow().isoformat(),
                "records": {},
                "total_embeddings": 0
            }
            self._save_manifest(manifest)
            return manifest

    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        """Save manifest to disk."""
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

    def _get_next_index(self) -> int:
        """Get the next embedding index (line number in JSONL)."""
        if self.embeddings_file.exists():
            with open(self.embeddings_file, 'r') as f:
                return sum(1 for _ in f)
        return 0

    def get_record_status(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get status for a specific record."""
        return self.manifest["records"].get(record_id)

    def update_record(
        self,
        record_id: str,
        status: str,
        text_source: str = None,
        text_length: int = None,
        embedding_dim: int = None,
        embedding_index: int = None,
        metadata: Dict[str, Any] = None,
        error: str = None
    ) -> None:
        """
        Update or add record entry in manifest.

        Args:
            record_id: Policy record ID
            status: 'completed', 'failed', 'pending'
            text_source: 'txt' or 'pdf'
            text_length: Length of extracted text
            embedding_dim: Dimension of embedding vector
            embedding_index: Line number in embeddings.jsonl
            metadata: Additional metadata (title, language, country, etc.)
            error: Error message if failed
        """
        record = {
            "status": status,
            "last_updated": datetime.utcnow().isoformat(),
            "text_source": text_source,
            "text_length": text_length,
            "embedding_dim": embedding_dim,
            "embedding_index": embedding_index,
            "metadata": metadata or {},
            "error": error
        }

        self.manifest["records"][record_id] = record
        self._save_manifest(self.manifest)

    def append_embedding(self, record_id: str, text: str, embedding: List[float], metadata: Dict[str, Any] = None) -> int:
        """
        Append embedding to JSON Lines file.

        Args:
            record_id: Policy record ID
            text: The text that was embedded
            embedding: Embedding vector
            metadata: Additional metadata

        Returns:
            Index (line number) where embedding was written
        """
        embedding_obj = {
            "record_id": record_id,
            "text": text[:5000],  # Store truncated text for reference
            "embedding": embedding,
            "metadata": metadata or {}
        }

        with open(self.embeddings_file, 'a') as f:
            json.dump(embedding_obj, f)
            f.write('\n')

        return self.embedding_index

    def finalize_embedding(self, record_id: str, text_length: int, embedding_dim: int, metadata: Dict[str, Any] = None) -> int:
        """
        Record that embedding was successfully stored.

        Args:
            record_id: Policy record ID
            text_length: Length of the text
            embedding_dim: Dimension of embedding
            metadata: Additional metadata

        Returns:
            Index where embedding was stored
        """
        current_index = self.embedding_index
        self.embedding_index += 1

        self.update_record(
            record_id=record_id,
            status="completed",
            text_source=metadata.get("text_source") if metadata else None,
            text_length=text_length,
            embedding_dim=embedding_dim,
            embedding_index=current_index,
            metadata=metadata
        )

        self.manifest["total_embeddings"] += 1
        self._save_manifest(self.manifest)

        return current_index

    def mark_failed(self, record_id: str, error: str, metadata: Dict[str, Any] = None) -> None:
        """Mark a record as failed."""
        self.update_record(
            record_id=record_id,
            status="failed",
            error=error,
            metadata=metadata
        )

    def get_pending_records(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of pending/failed record IDs that need processing.

        Args:
            limit: Maximum number to return (None for all)

        Returns:
            List of record IDs
        """
        pending = []
        for record_id, record in self.manifest["records"].items():
            if record["status"] in ("pending", "failed"):
                pending.append(record_id)

        if limit:
            return pending[:limit]
        return pending

    def get_statistics(self) -> Dict[str, Any]:
        """Get embedding statistics."""
        total = len(self.manifest["records"])
        completed = sum(1 for r in self.manifest["records"].values() if r["status"] == "completed")
        failed = sum(1 for r in self.manifest["records"].values() if r["status"] == "failed")
        pending = sum(1 for r in self.manifest["records"].values() if r["status"] == "pending")

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "embeddings_file_size_mb": self.embeddings_file.stat().st_size / (1024*1024) if self.embeddings_file.exists() else 0
        }

    def get_all_embeddings(self) -> List[Dict[str, Any]]:
        """
        Retrieve all completed embeddings with their vectors and metadata.

        Returns:
            List of dicts with keys: record_id, embedding, metadata (from manifest)
        """
        embeddings = []

        if not self.embeddings_file.exists():
            logger.warning("Embeddings file does not exist")
            return embeddings

        # Read all lines from embeddings.jsonl
        with open(self.embeddings_file, 'r') as f:
            for line_num, line in enumerate(f):
                try:
                    data = json.loads(line.strip())
                    record_id = data.get('record_id')

                    # Verify this record is completed in manifest
                    manifest_record = self.manifest["records"].get(record_id)
                    if manifest_record and manifest_record.get("status") == "completed":
                        embeddings.append({
                            'record_id': record_id,
                            'embedding': data.get('embedding', []),
                            'metadata': data.get('metadata', {})
                        })
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line {line_num}: {e}")
                    continue

        logger.info(f"Retrieved {len(embeddings)} completed embeddings")
        return embeddings
