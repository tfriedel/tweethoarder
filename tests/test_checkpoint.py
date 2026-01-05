"""Tests for sync checkpointing."""

import sqlite3
from pathlib import Path

from tweethoarder.storage.database import init_database


def test_save_stores_checkpoint_data(tmp_path: Path) -> None:
    """SyncCheckpoint.save should store progress data in sync_progress table."""
    from tweethoarder.storage.checkpoint import SyncCheckpoint

    db_path = tmp_path / "test.db"
    init_database(db_path)

    checkpoint = SyncCheckpoint(db_path)
    checkpoint.save(
        collection_type="likes",
        cursor="cursor123",
        last_tweet_id="tweet456",
    )

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT cursor, last_tweet_id, status FROM sync_progress WHERE collection_type = ?",
        ("likes",),
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "cursor123"
    assert row[1] == "tweet456"
    assert row[2] == "in_progress"


def test_load_returns_saved_checkpoint(tmp_path: Path) -> None:
    """SyncCheckpoint.load should return previously saved checkpoint data."""
    from tweethoarder.storage.checkpoint import SyncCheckpoint

    db_path = tmp_path / "test.db"
    init_database(db_path)

    checkpoint = SyncCheckpoint(db_path)
    checkpoint.save(
        collection_type="bookmarks",
        cursor="cursor789",
        last_tweet_id="tweet012",
    )

    result = checkpoint.load("bookmarks")

    assert result is not None
    assert result.cursor == "cursor789"
    assert result.last_tweet_id == "tweet012"


def test_load_returns_checkpoint_data_type(tmp_path: Path) -> None:
    """SyncCheckpoint.load should return a CheckpointData instance."""
    from tweethoarder.storage.checkpoint import CheckpointData, SyncCheckpoint

    db_path = tmp_path / "test.db"
    init_database(db_path)

    checkpoint = SyncCheckpoint(db_path)
    checkpoint.save(
        collection_type="tweets",
        cursor="abc",
        last_tweet_id="123",
    )

    result = checkpoint.load("tweets")

    assert isinstance(result, CheckpointData)


def test_clear_removes_checkpoint(tmp_path: Path) -> None:
    """SyncCheckpoint.clear should remove the checkpoint for a collection."""
    from tweethoarder.storage.checkpoint import SyncCheckpoint

    db_path = tmp_path / "test.db"
    init_database(db_path)

    checkpoint = SyncCheckpoint(db_path)
    checkpoint.save(
        collection_type="reposts",
        cursor="cursor999",
        last_tweet_id="tweet888",
    )

    checkpoint.clear("reposts")

    result = checkpoint.load("reposts")
    assert result is None


def test_load_returns_none_when_no_checkpoint_exists(tmp_path: Path) -> None:
    """SyncCheckpoint.load should return None when no checkpoint exists."""
    from tweethoarder.storage.checkpoint import SyncCheckpoint

    db_path = tmp_path / "test.db"
    init_database(db_path)

    checkpoint = SyncCheckpoint(db_path)

    result = checkpoint.load("nonexistent")

    assert result is None


def test_save_stores_sort_index_counter(tmp_path: Path) -> None:
    """SyncCheckpoint.save should store sort_index_counter when provided."""
    from tweethoarder.storage.checkpoint import SyncCheckpoint

    db_path = tmp_path / "test.db"
    init_database(db_path)

    checkpoint = SyncCheckpoint(db_path)
    checkpoint.save(
        collection_type="likes",
        cursor="cursor123",
        last_tweet_id="tweet456",
        sort_index_counter="8999999999999999990",
    )

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT sort_index_counter FROM sync_progress WHERE collection_type = ?",
        ("likes",),
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "8999999999999999990"


def test_load_returns_sort_index_counter(tmp_path: Path) -> None:
    """SyncCheckpoint.load should return sort_index_counter when saved."""
    from tweethoarder.storage.checkpoint import SyncCheckpoint

    db_path = tmp_path / "test.db"
    init_database(db_path)

    checkpoint = SyncCheckpoint(db_path)
    checkpoint.save(
        collection_type="likes",
        cursor="cursor123",
        last_tweet_id="tweet456",
        sort_index_counter="8999999999999999990",
    )

    result = checkpoint.load("likes")

    assert result is not None
    assert result.sort_index_counter == "8999999999999999990"
