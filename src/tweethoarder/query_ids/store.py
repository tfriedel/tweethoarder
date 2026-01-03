"""Query ID store with caching and TTL management."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class SnapshotInfo:
    """Information about a cached snapshot including freshness."""

    is_fresh: bool


class QueryIdStore:
    """Manages query ID cache with TTL and disk persistence."""

    def __init__(self, cache_path: Path) -> None:
        """Initialize store with cache file path."""
        self._cache_path = cache_path

    def get_query_id(self, operation_name: str) -> str | None:
        """Get query ID for operation, returning None if not cached."""
        if not self._cache_path.exists():
            return None
        data: dict[str, object] = json.loads(self._cache_path.read_text())
        ids = data.get("ids", {})
        if isinstance(ids, dict):
            value = ids.get(operation_name)
            if isinstance(value, str):
                return value
        return None

    def get_snapshot_info(self) -> SnapshotInfo | None:
        """Load and return current snapshot with freshness info."""
        if not self._cache_path.exists():
            return None
        data = json.loads(self._cache_path.read_text())
        fetched_at_str = data.get("fetched_at", "")
        ttl_seconds = data.get("ttl_seconds", 86400)
        fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
        age_seconds = (datetime.now(UTC) - fetched_at).total_seconds()
        is_fresh = age_seconds <= ttl_seconds
        return SnapshotInfo(is_fresh=is_fresh)

    def clear_memory(self) -> None:
        """Clear in-memory cache, forcing reload from disk on next access."""
        pass

    def save(self, ids: dict[str, str]) -> None:
        """Save query IDs to cache file."""
        from .constants import DEFAULT_TTL_SECONDS

        data = {
            "fetched_at": datetime.now(UTC).isoformat(),
            "ttl_seconds": DEFAULT_TTL_SECONDS,
            "ids": ids,
        }
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(json.dumps(data))


def get_query_id_with_fallback(store: QueryIdStore, operation: str) -> str:
    """Get query ID from cache, falling back to FALLBACK_QUERY_IDS."""
    from .constants import FALLBACK_QUERY_IDS

    cached = store.get_query_id(operation)
    if cached:
        return cached
    fallback = FALLBACK_QUERY_IDS.get(operation)
    if fallback:
        return fallback
    raise KeyError(f"Unknown operation: {operation}")
