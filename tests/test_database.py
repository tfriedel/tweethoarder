"""Tests for database management."""

import sqlite3
from pathlib import Path


def _table_exists(db_path: Path, table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def test_init_database_creates_file(tmp_path: Path) -> None:
    """Database initialization should create the SQLite file."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)
    assert db_path.exists()


def test_init_database_creates_tweets_table(tmp_path: Path) -> None:
    """Database should have a tweets table with required columns."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    assert _table_exists(db_path, "tweets")


def test_init_database_creates_collections_table(tmp_path: Path) -> None:
    """Database should have a collections table for tracking likes, bookmarks, etc."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    assert _table_exists(db_path, "collections")


def test_init_database_creates_sync_progress_table(tmp_path: Path) -> None:
    """Database should have a sync_progress table for checkpointing."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    assert _table_exists(db_path, "sync_progress")


def test_init_database_creates_thread_context_table(tmp_path: Path) -> None:
    """Database should have a thread_context table for storing parent tweets."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    assert _table_exists(db_path, "thread_context")


def test_init_database_creates_metadata_table(tmp_path: Path) -> None:
    """Database should have a metadata table for key-value storage."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    assert _table_exists(db_path, "metadata")


def test_init_database_creates_indexes(tmp_path: Path) -> None:
    """Database should have indexes for common queries."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    )
    indexes = {row[0] for row in cursor.fetchall()}
    conn.close()

    expected_indexes = {
        "idx_tweets_author",
        "idx_tweets_conversation",
        "idx_tweets_created_at",
        "idx_collections_type",
        "idx_collections_added",
    }
    assert expected_indexes.issubset(indexes)
