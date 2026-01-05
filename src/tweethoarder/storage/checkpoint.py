"""Sync checkpointing for resumable syncs."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckpointData:
    """Data from a saved checkpoint."""

    cursor: str
    last_tweet_id: str
    sort_index_counter: str | None = None


class SyncCheckpoint:
    """Save and restore sync progress for resume capability."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def save(
        self,
        collection_type: str,
        cursor: str,
        last_tweet_id: str,
        sort_index_counter: str | None = None,
    ) -> None:
        """Save current sync position."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_progress
                    (collection_type, cursor, last_tweet_id, sort_index_counter, status)
                VALUES (?, ?, ?, ?, 'in_progress')
                """,
                (collection_type, cursor, last_tweet_id, sort_index_counter),
            )
            conn.commit()

    def load(self, collection_type: str) -> CheckpointData | None:
        """Load checkpoint for resuming interrupted sync."""
        with sqlite3.connect(self._db_path) as conn:
            result = conn.execute(
                """SELECT cursor, last_tweet_id, sort_index_counter
                FROM sync_progress WHERE collection_type = ?""",
                (collection_type,),
            )
            row = result.fetchone()

        if row is None:
            return None

        return CheckpointData(
            cursor=row[0],
            last_tweet_id=row[1],
            sort_index_counter=row[2],
        )

    def clear(self, collection_type: str) -> None:
        """Clear checkpoint after successful completion."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "DELETE FROM sync_progress WHERE collection_type = ?",
                (collection_type,),
            )
            conn.commit()
