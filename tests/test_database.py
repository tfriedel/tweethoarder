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


def test_save_tweet_inserts_into_database(tmp_path: Path) -> None:
    """save_tweet should insert tweet data into the tweets table."""
    from tweethoarder.storage.database import init_database, save_tweet

    db_path = tmp_path / "test.db"
    init_database(db_path)

    tweet_data = {
        "id": "123456789",
        "text": "Hello, world!",
        "author_id": "987654321",
        "author_username": "testuser",
        "author_display_name": "Test User",
        "created_at": "2025-01-01T12:00:00Z",
        "conversation_id": "123456789",
        "reply_count": 5,
        "retweet_count": 10,
        "like_count": 20,
        "quote_count": 2,
    }

    save_tweet(db_path, tweet_data)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT id, text FROM tweets WHERE id = ?", ("123456789",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "123456789"
    assert row[1] == "Hello, world!"


def test_add_to_collection_inserts_into_collections(tmp_path: Path) -> None:
    """add_to_collection should add tweet to specified collection."""
    from tweethoarder.storage.database import (
        add_to_collection,
        init_database,
        save_tweet,
    )

    db_path = tmp_path / "test.db"
    init_database(db_path)

    tweet_data = {
        "id": "123456789",
        "text": "Hello!",
        "author_id": "987654321",
        "author_username": "testuser",
        "created_at": "2025-01-01T12:00:00Z",
    }
    save_tweet(db_path, tweet_data)
    add_to_collection(db_path, "123456789", "like")

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT tweet_id, collection_type FROM collections WHERE tweet_id = ?",
        ("123456789",),
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "123456789"
    assert row[1] == "like"


def test_add_to_collection_stores_sort_index(tmp_path: Path) -> None:
    """add_to_collection should store sort_index when provided."""
    from tweethoarder.storage.database import (
        add_to_collection,
        init_database,
        save_tweet,
    )

    db_path = tmp_path / "test.db"
    init_database(db_path)

    tweet_data = {
        "id": "123456789",
        "text": "Hello!",
        "author_id": "987654321",
        "author_username": "testuser",
        "created_at": "2025-01-01T12:00:00Z",
    }
    save_tweet(db_path, tweet_data)
    add_to_collection(db_path, "123456789", "like", sort_index="2007662285526401024")

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT sort_index FROM collections WHERE tweet_id = ?",
        ("123456789",),
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "2007662285526401024"


def test_save_tweet_preserves_first_seen_at_on_update(tmp_path: Path) -> None:
    """save_tweet should preserve first_seen_at when updating existing tweet."""
    import time

    from tweethoarder.storage.database import init_database, save_tweet

    db_path = tmp_path / "test.db"
    init_database(db_path)

    tweet_data = {
        "id": "123456789",
        "text": "Hello!",
        "author_id": "987654321",
        "author_username": "testuser",
        "created_at": "2025-01-01T12:00:00Z",
        "like_count": 10,
    }
    save_tweet(db_path, tweet_data)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT first_seen_at FROM tweets WHERE id = ?", ("123456789",))
    original_first_seen = cursor.fetchone()[0]
    conn.close()

    time.sleep(0.01)

    tweet_data["like_count"] = 20
    save_tweet(db_path, tweet_data)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT first_seen_at, like_count FROM tweets WHERE id = ?", ("123456789",)
    )
    row = cursor.fetchone()
    conn.close()

    assert row[0] == original_first_seen
    assert row[1] == 20


def test_save_tweet_uses_single_upsert_operation(tmp_path: Path) -> None:
    """save_tweet should use a single UPSERT for efficiency."""
    from tweethoarder.storage.database import init_database, save_tweet

    db_path = tmp_path / "test.db"
    init_database(db_path)

    tweet_data = {
        "id": "123456789",
        "text": "Hello!",
        "author_id": "987654321",
        "author_username": "testuser",
        "created_at": "2025-01-01T12:00:00Z",
    }

    save_tweet(db_path, tweet_data)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT first_seen_at, last_updated_at FROM tweets WHERE id = ?", ("123456789",)
    )
    first_save = cursor.fetchone()
    conn.close()

    assert first_save[0] == first_save[1]


def test_get_all_tweets_returns_all_tweets(tmp_path: Path) -> None:
    """get_all_tweets should return all tweets regardless of collection."""
    from tweethoarder.storage.database import (
        add_to_collection,
        get_all_tweets,
        init_database,
        save_tweet,
    )

    db_path = tmp_path / "test.db"
    init_database(db_path)

    save_tweet(
        db_path,
        {
            "id": "1",
            "text": "Tweet 1",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "2",
            "text": "Tweet 2",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-02T12:00:00Z",
        },
    )
    add_to_collection(db_path, "1", "like")
    add_to_collection(db_path, "2", "bookmark")

    tweets = get_all_tweets(db_path)

    assert len(tweets) == 2


def test_get_tweets_by_collection_returns_tweets(tmp_path: Path) -> None:
    """get_tweets_by_collection should return tweets in a specific collection."""
    from tweethoarder.storage.database import (
        add_to_collection,
        get_tweets_by_collection,
        init_database,
        save_tweet,
    )

    db_path = tmp_path / "test.db"
    init_database(db_path)

    tweet_data = {
        "id": "123456789",
        "text": "Hello!",
        "author_id": "987654321",
        "author_username": "testuser",
        "created_at": "2025-01-01T12:00:00Z",
    }
    save_tweet(db_path, tweet_data)
    add_to_collection(db_path, "123456789", "like")

    tweets = get_tweets_by_collection(db_path, "like")

    assert len(tweets) == 1
    assert tweets[0]["id"] == "123456789"
    assert tweets[0]["text"] == "Hello!"


def test_get_tweets_by_collection_orders_by_sort_index(tmp_path: Path) -> None:
    """get_tweets_by_collection should order by sort_index descending."""
    import time

    from tweethoarder.storage.database import (
        add_to_collection,
        get_tweets_by_collection,
        init_database,
        save_tweet,
    )

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Create two tweets
    save_tweet(
        db_path,
        {
            "id": "1",
            "text": "First liked",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "2",
            "text": "Second liked",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-02T12:00:00Z",
        },
    )

    # Add with sort_index - tweet "1" has HIGHER sort_index (more recently liked)
    # but is added FIRST (earlier added_at), so if ordering by added_at, "2" would be first
    add_to_collection(db_path, "1", "like", sort_index="2000")
    time.sleep(0.01)  # Ensure different added_at timestamps
    add_to_collection(db_path, "2", "like", sort_index="1000")

    tweets = get_tweets_by_collection(db_path, "like")

    # Should be ordered by sort_index DESC (2000 before 1000)
    # If ordered by added_at DESC, "2" would be first (wrong)
    assert len(tweets) == 2
    assert tweets[0]["id"] == "1"  # Higher sort_index first
    assert tweets[1]["id"] == "2"


def test_init_database_creates_threads_table(tmp_path: Path) -> None:
    """Database should have a threads table for storing thread/conversation metadata."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    assert _table_exists(db_path, "threads")


def test_collections_table_has_thread_id_column(tmp_path: Path) -> None:
    """Collections table should have thread_id column for linking to threads table."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(collections)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()

    assert "thread_id" in columns


def test_init_database_creates_threads_indexes(tmp_path: Path) -> None:
    """Database should have indexes for the threads table."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    )
    indexes = {row[0] for row in cursor.fetchall()}
    conn.close()

    assert "idx_threads_conversation" in indexes
    assert "idx_threads_focal" in indexes


def test_get_db_path_exists() -> None:
    """get_db_path function should be importable."""
    from tweethoarder.storage.database import get_db_path

    assert callable(get_db_path)


def test_collections_table_has_sort_index_column(tmp_path: Path) -> None:
    """Collections table should have sort_index column for preserving Twitter order."""
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(collections)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()

    assert "sort_index" in columns


def test_get_tweets_by_bookmark_folder_filters_by_folder(tmp_path: Path) -> None:
    """get_tweets_by_bookmark_folder should filter bookmarks by folder name."""
    from tweethoarder.storage.database import (
        get_tweets_by_bookmark_folder,
        init_database,
        save_tweet,
    )

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Create tweets
    save_tweet(
        db_path,
        {
            "id": "1",
            "text": "Tweet 1",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "2",
            "text": "Tweet 2",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-02T12:00:00Z",
        },
    )

    # Add to bookmarks with different folders
    insert_sql = """
        INSERT INTO collections (
            tweet_id, collection_type, bookmark_folder_name, added_at, synced_at
        ) VALUES (?, ?, ?, ?, ?)
    """
    conn = sqlite3.connect(db_path)
    conn.execute(
        insert_sql,
        ("1", "bookmark", "Work", "2025-01-01T12:00:00Z", "2025-01-01T12:00:00Z"),
    )
    conn.execute(
        insert_sql,
        ("2", "bookmark", "Personal", "2025-01-02T12:00:00Z", "2025-01-02T12:00:00Z"),
    )
    conn.commit()
    conn.close()

    # Filter by folder
    tweets = get_tweets_by_bookmark_folder(db_path, "Work")

    assert len(tweets) == 1
    assert tweets[0]["id"] == "1"
    assert tweets[0]["text"] == "Tweet 1"
