"""Sort index generation for consistent ordering across sync sessions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tweethoarder.storage.checkpoint import SyncCheckpoint

INITIAL_SORT_INDEX = "9000000000000000000"


class SortIndexGenerator:
    """Generate monotonically decreasing sort_index values for sync operations."""

    def __init__(self, initial_value: str | None = None) -> None:
        """Initialize the generator with an optional starting value.

        Args:
            initial_value: Starting value for the counter. If None, uses INITIAL_SORT_INDEX.
        """
        self._counter = int(initial_value or INITIAL_SORT_INDEX)

    def next(self) -> str:
        """Get the next sort_index value and decrement counter.

        Returns:
            The current counter value as a string, then decrements for next call.
        """
        value = str(self._counter)
        self._counter -= 1
        return value

    @property
    def current(self) -> str:
        """Get current counter value without decrementing."""
        return str(self._counter)

    @classmethod
    def from_checkpoint_or_db(
        cls,
        checkpoint: SyncCheckpoint,
        collection_type: str,
        db_path: Path,
    ) -> SortIndexGenerator:
        """Create generator from checkpoint or derive from existing data.

        Resolution priority:
        1. If checkpoint exists with counter, use it (mid-sync resume)
        2. If collection has existing data, use min(sort_index) - 1
        3. Otherwise, start fresh with INITIAL_SORT_INDEX

        Args:
            checkpoint: SyncCheckpoint instance to load from.
            collection_type: The collection type (e.g., "like", "bookmark").
            db_path: Path to the SQLite database file.

        Returns:
            A new SortIndexGenerator initialized with the appropriate value.
        """
        from tweethoarder.storage.database import get_min_sort_index

        saved = checkpoint.load(collection_type)
        if saved and saved.sort_index_counter:
            return cls(saved.sort_index_counter)

        min_index = get_min_sort_index(db_path, collection_type)
        if min_index:
            new_start = str(int(min_index) - 1)
            return cls(new_start)

        return cls()
