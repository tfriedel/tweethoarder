"""Sync checkpointing for resumable syncs."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckpointData:
    """Data from a saved checkpoint."""

    cursor: str
    last_tweet_id: str


class SyncCheckpoint:
    """Save and restore sync progress for resume capability."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def save(
        self,
        collection_type: str,
        cursor: str,
        last_tweet_id: str,
    ) -> None:
        """Save current sync position."""
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO sync_progress
                (collection_type, cursor, last_tweet_id, status)
            VALUES (?, ?, ?, 'in_progress')
            """,
            (collection_type, cursor, last_tweet_id),
        )
        conn.commit()
        conn.close()

    def load(self, collection_type: str) -> CheckpointData | None:
        """Load checkpoint for resuming interrupted sync."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT cursor, last_tweet_id FROM sync_progress WHERE collection_type = ?",
            (collection_type,),
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return CheckpointData(cursor=row[0], last_tweet_id=row[1])

    def clear(self, collection_type: str) -> None:
        """Clear checkpoint after successful completion."""
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "DELETE FROM sync_progress WHERE collection_type = ?",
            (collection_type,),
        )
        conn.commit()
        conn.close()
