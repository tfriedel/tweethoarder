"""Tests for query ID store."""

import json
from datetime import UTC, datetime
from pathlib import Path


def test_get_query_id_returns_none_when_no_cache(tmp_path: Path) -> None:
    """get_query_id should return None when cache file doesn't exist."""
    from tweethoarder.query_ids.store import QueryIdStore

    cache_path = tmp_path / "nonexistent" / "cache.json"
    store = QueryIdStore(cache_path=cache_path)

    result = store.get_query_id("Bookmarks")

    assert result is None


def test_get_snapshot_info_returns_none_when_no_cache(tmp_path: Path) -> None:
    """get_snapshot_info should return None when cache file doesn't exist."""
    from tweethoarder.query_ids.store import QueryIdStore

    cache_path = tmp_path / "nonexistent" / "cache.json"
    store = QueryIdStore(cache_path=cache_path)

    result = store.get_snapshot_info()

    assert result is None


def test_loads_snapshot_from_disk(tmp_path: Path) -> None:
    """Store should load valid cache file from disk."""
    from tweethoarder.query_ids.store import QueryIdStore

    cache_path = tmp_path / "cache.json"
    cache_data = {
        "fetched_at": "2026-01-02T12:00:00Z",
        "ttl_seconds": 86400,
        "ids": {"Bookmarks": "RV1g3b8n_SGOHwkqKYSCFw"},
        "discovery": {"pages": ["https://x.com/"], "bundles": ["main.js"]},
    }
    cache_path.write_text(json.dumps(cache_data))

    store = QueryIdStore(cache_path=cache_path)

    result = store.get_query_id("Bookmarks")

    assert result == "RV1g3b8n_SGOHwkqKYSCFw"


def test_snapshot_info_is_fresh_when_within_ttl(tmp_path: Path) -> None:
    """get_snapshot_info should report is_fresh=True when within TTL."""
    from tweethoarder.query_ids.store import QueryIdStore

    cache_path = tmp_path / "cache.json"
    # Use current time so it's definitely within TTL
    now = datetime.now(UTC).isoformat()
    cache_data = {
        "fetched_at": now,
        "ttl_seconds": 86400,
        "ids": {"Bookmarks": "abc123"},
        "discovery": {"pages": [], "bundles": []},
    }
    cache_path.write_text(json.dumps(cache_data))

    store = QueryIdStore(cache_path=cache_path)

    info = store.get_snapshot_info()

    assert info is not None
    assert info.is_fresh is True


def test_snapshot_info_is_stale_when_past_ttl(tmp_path: Path) -> None:
    """get_snapshot_info should report is_fresh=False when past TTL."""
    from tweethoarder.query_ids.store import QueryIdStore

    cache_path = tmp_path / "cache.json"
    # Use old timestamp (2 days ago) with 1-day TTL
    old_time = "2024-01-01T00:00:00Z"
    cache_data = {
        "fetched_at": old_time,
        "ttl_seconds": 86400,  # 1 day
        "ids": {"Bookmarks": "abc123"},
        "discovery": {"pages": [], "bundles": []},
    }
    cache_path.write_text(json.dumps(cache_data))

    store = QueryIdStore(cache_path=cache_path)

    info = store.get_snapshot_info()

    assert info is not None
    assert info.is_fresh is False


def test_clear_memory_forces_reload_from_disk(tmp_path: Path) -> None:
    """clear_memory should cause next access to reload from disk."""
    from tweethoarder.query_ids.store import QueryIdStore

    cache_path = tmp_path / "cache.json"
    ids: dict[str, str] = {"Bookmarks": "original_id"}
    cache_data = {
        "fetched_at": "2026-01-02T12:00:00Z",
        "ttl_seconds": 86400,
        "ids": ids,
        "discovery": {"pages": [], "bundles": []},
    }
    cache_path.write_text(json.dumps(cache_data))

    store = QueryIdStore(cache_path=cache_path)
    assert store.get_query_id("Bookmarks") == "original_id"

    # Update the file
    ids["Bookmarks"] = "updated_id"
    cache_path.write_text(json.dumps(cache_data))

    # Without clear_memory, should still have old value (cached)
    # With clear_memory, should pick up new value
    store.clear_memory()
    assert store.get_query_id("Bookmarks") == "updated_id"


def test_get_query_id_with_fallback_returns_cached_value(tmp_path: Path) -> None:
    """get_query_id_with_fallback should return cached ID when available."""
    from tweethoarder.query_ids.store import QueryIdStore, get_query_id_with_fallback

    cache_path = tmp_path / "cache.json"
    cache_data = {
        "fetched_at": "2026-01-02T12:00:00Z",
        "ttl_seconds": 86400,
        "ids": {"Bookmarks": "cached_query_id"},
        "discovery": {"pages": [], "bundles": []},
    }
    cache_path.write_text(json.dumps(cache_data))

    store = QueryIdStore(cache_path=cache_path)

    result = get_query_id_with_fallback(store, "Bookmarks")

    assert result == "cached_query_id"


def test_get_query_id_with_fallback_uses_fallback_when_not_cached(
    tmp_path: Path,
) -> None:
    """get_query_id_with_fallback should use FALLBACK_QUERY_IDS when not in cache."""
    from tweethoarder.query_ids.store import QueryIdStore, get_query_id_with_fallback

    cache_path = tmp_path / "nonexistent" / "cache.json"
    store = QueryIdStore(cache_path=cache_path)

    # Bookmarks is in FALLBACK_QUERY_IDS
    result = get_query_id_with_fallback(store, "Bookmarks")

    assert result == "RV1g3b8n_SGOHwkqKYSCFw"
