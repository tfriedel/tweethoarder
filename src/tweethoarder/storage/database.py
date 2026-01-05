"""Database management for TweetHoarder."""

import sqlite3
from pathlib import Path
from typing import Any

TWEETS_SCHEMA = """
CREATE TABLE IF NOT EXISTS tweets (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_username TEXT NOT NULL,
    author_display_name TEXT,
    author_avatar_url TEXT,
    created_at TEXT NOT NULL,
    conversation_id TEXT,
    in_reply_to_tweet_id TEXT,
    in_reply_to_user_id TEXT,
    quoted_tweet_id TEXT,
    is_retweet BOOLEAN DEFAULT FALSE,
    retweeted_tweet_id TEXT,
    reply_count INTEGER DEFAULT 0,
    retweet_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    quote_count INTEGER DEFAULT 0,
    media_json TEXT,
    urls_json TEXT,
    hashtags_json TEXT,
    mentions_json TEXT,
    raw_json TEXT,
    first_seen_at TEXT NOT NULL,
    last_updated_at TEXT NOT NULL,
    FOREIGN KEY (quoted_tweet_id) REFERENCES tweets(id),
    FOREIGN KEY (retweeted_tweet_id) REFERENCES tweets(id)
)
"""

COLLECTIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS collections (
    tweet_id TEXT NOT NULL,
    collection_type TEXT NOT NULL,
    bookmark_folder_id TEXT,
    bookmark_folder_name TEXT,
    thread_id TEXT,
    sort_index TEXT,
    added_at TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    PRIMARY KEY (tweet_id, collection_type),
    FOREIGN KEY (tweet_id) REFERENCES tweets(id),
    FOREIGN KEY (thread_id) REFERENCES threads(id)
)
"""

SYNC_PROGRESS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_progress (
    collection_type TEXT PRIMARY KEY,
    cursor TEXT,
    last_tweet_id TEXT,
    total_synced INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    status TEXT DEFAULT 'pending'
)
"""

THREAD_CONTEXT_SCHEMA = """
CREATE TABLE IF NOT EXISTS thread_context (
    child_tweet_id TEXT NOT NULL,
    parent_tweet_id TEXT NOT NULL,
    depth INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (child_tweet_id, parent_tweet_id),
    FOREIGN KEY (child_tweet_id) REFERENCES tweets(id),
    FOREIGN KEY (parent_tweet_id) REFERENCES tweets(id)
)
"""

METADATA_SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""

THREADS_SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    root_tweet_id TEXT NOT NULL,
    focal_tweet_id TEXT,
    author_id TEXT NOT NULL,
    thread_type TEXT NOT NULL,
    tweet_count INTEGER NOT NULL,
    is_complete BOOLEAN DEFAULT FALSE,
    fetched_at TEXT NOT NULL,
    FOREIGN KEY (root_tweet_id) REFERENCES tweets(id),
    FOREIGN KEY (focal_tweet_id) REFERENCES tweets(id)
)
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_tweets_author ON tweets(author_id)",
    "CREATE INDEX IF NOT EXISTS idx_tweets_conversation ON tweets(conversation_id)",
    "CREATE INDEX IF NOT EXISTS idx_tweets_created_at ON tweets(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_collections_type ON collections(collection_type)",
    "CREATE INDEX IF NOT EXISTS idx_collections_added ON collections(added_at)",
    "CREATE INDEX IF NOT EXISTS idx_threads_conversation ON threads(conversation_id)",
    "CREATE INDEX IF NOT EXISTS idx_threads_focal ON threads(focal_tweet_id)",
]


def get_db_path() -> Path:
    """Get the default database path."""
    from tweethoarder.config import get_data_dir

    data_dir: Path = get_data_dir()
    return data_dir / "tweethoarder.db"


def init_database(db_path: Path) -> None:
    """Initialize the SQLite database."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(TWEETS_SCHEMA)
        conn.execute(COLLECTIONS_SCHEMA)
        conn.execute(SYNC_PROGRESS_SCHEMA)
        conn.execute(THREAD_CONTEXT_SCHEMA)
        conn.execute(METADATA_SCHEMA)
        conn.execute(THREADS_SCHEMA)
        for index_sql in INDEXES:
            conn.execute(index_sql)
        conn.commit()


def save_tweet(db_path: Path, tweet_data: dict[str, Any]) -> None:
    """Save a tweet to the database.

    Inserts a new tweet or updates an existing one while preserving
    the original first_seen_at timestamp. Uses a single UPSERT operation
    for efficiency.

    Args:
        db_path: Path to the SQLite database file.
        tweet_data: Dictionary containing tweet data with keys:
            id, text, author_id, author_username, created_at (required),
            and optional keys like author_display_name, conversation_id,
            reply_count, retweet_count, like_count, quote_count.
    """
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO tweets (
                id, text, author_id, author_username, author_display_name,
                author_avatar_url, created_at, conversation_id, quoted_tweet_id,
                in_reply_to_tweet_id, in_reply_to_user_id,
                is_retweet, retweeted_tweet_id,
                reply_count, retweet_count, like_count, quote_count,
                urls_json, media_json, raw_json, first_seen_at, last_updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                text = excluded.text,
                author_id = excluded.author_id,
                author_username = excluded.author_username,
                author_display_name = excluded.author_display_name,
                author_avatar_url = excluded.author_avatar_url,
                created_at = excluded.created_at,
                conversation_id = excluded.conversation_id,
                quoted_tweet_id = COALESCE(
                    excluded.quoted_tweet_id, tweets.quoted_tweet_id
                ),
                in_reply_to_tweet_id = COALESCE(
                    excluded.in_reply_to_tweet_id, tweets.in_reply_to_tweet_id
                ),
                in_reply_to_user_id = COALESCE(
                    excluded.in_reply_to_user_id, tweets.in_reply_to_user_id
                ),
                is_retweet = excluded.is_retweet,
                retweeted_tweet_id = COALESCE(
                    excluded.retweeted_tweet_id, tweets.retweeted_tweet_id
                ),
                reply_count = excluded.reply_count,
                retweet_count = excluded.retweet_count,
                like_count = excluded.like_count,
                quote_count = excluded.quote_count,
                urls_json = COALESCE(excluded.urls_json, tweets.urls_json),
                media_json = COALESCE(excluded.media_json, tweets.media_json),
                raw_json = COALESCE(excluded.raw_json, tweets.raw_json),
                last_updated_at = excluded.last_updated_at
            """,
            (
                tweet_data["id"],
                tweet_data["text"],
                tweet_data["author_id"],
                tweet_data["author_username"],
                tweet_data.get("author_display_name"),
                tweet_data.get("author_avatar_url"),
                tweet_data["created_at"],
                tweet_data.get("conversation_id"),
                tweet_data.get("quoted_tweet_id"),
                tweet_data.get("in_reply_to_tweet_id"),
                tweet_data.get("in_reply_to_user_id"),
                tweet_data.get("is_retweet", False),
                tweet_data.get("retweeted_tweet_id"),
                tweet_data.get("reply_count", 0),
                tweet_data.get("retweet_count", 0),
                tweet_data.get("like_count", 0),
                tweet_data.get("quote_count", 0),
                tweet_data.get("urls_json"),
                tweet_data.get("media_json"),
                tweet_data.get("raw_json"),
                now,
                now,
            ),
        )

        conn.commit()


def add_to_collection(
    db_path: Path,
    tweet_id: str,
    collection_type: str,
    sort_index: str | None = None,
) -> None:
    """Add a tweet to a collection.

    Records that a tweet belongs to a specific collection (like, bookmark, etc.).
    Does nothing if the tweet is already in the collection.

    Args:
        db_path: Path to the SQLite database file.
        tweet_id: The ID of the tweet to add.
        collection_type: The type of collection (e.g., "like", "bookmark").
        sort_index: Twitter's sortIndex for preserving timeline order.
    """
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO collections (
                tweet_id, collection_type, sort_index, added_at, synced_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (tweet_id, collection_type, sort_index, now, now),
        )
        conn.commit()


def get_tweets_by_collection(db_path: Path, collection_type: str) -> list[dict[str, Any]]:
    """Get all tweets in a collection.

    Args:
        db_path: Path to the SQLite database file.
        collection_type: The type of collection (e.g., "like", "bookmark").

    Returns:
        List of tweet dictionaries ordered by sort_index (Twitter's timeline order),
        falling back to added_at for entries without sort_index.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT t.* FROM tweets t
            JOIN collections c ON t.id = c.tweet_id
            WHERE c.collection_type = ?
            ORDER BY c.sort_index IS NULL ASC, c.sort_index DESC, c.added_at DESC
            """,
            (collection_type,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_all_tweets(db_path: Path) -> list[dict[str, Any]]:
    """Get all tweets in the database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        List of tweet dictionaries ordered by creation date (most recent first).
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT * FROM tweets
            ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def get_tweets_by_bookmark_folder(db_path: Path, folder_name: str) -> list[dict[str, Any]]:
    """Get bookmarked tweets filtered by folder name.

    Args:
        db_path: Path to the SQLite database file.
        folder_name: The bookmark folder name to filter by.

    Returns:
        List of tweet dictionaries ordered by when they were added (most recent first).
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT t.* FROM tweets t
            JOIN collections c ON t.id = c.tweet_id
            WHERE c.collection_type = 'bookmark' AND c.bookmark_folder_name = ?
            ORDER BY c.added_at DESC
            """,
            (folder_name,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_tweets_by_conversation_id(db_path: Path, conversation_id: str) -> list[dict[str, Any]]:
    """Get all tweets in a conversation."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT * FROM tweets
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_tweets_by_ids(db_path: Path, tweet_ids: list[str]) -> list[dict[str, Any]]:
    """Get tweets by their IDs.

    Args:
        db_path: Path to the SQLite database file.
        tweet_ids: List of tweet IDs to fetch.

    Returns:
        List of tweet dictionaries for tweets that exist in the database.
    """
    if not tweet_ids:
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" * len(tweet_ids))
        cursor = conn.execute(
            f"""
            SELECT * FROM tweets
            WHERE id IN ({placeholders})
            """,
            tweet_ids,
        )
        return [dict(row) for row in cursor.fetchall()]


def tweet_exists(db_path: Path, tweet_id: str) -> bool:
    """Check if a tweet exists in the database.

    Args:
        db_path: Path to the SQLite database file.
        tweet_id: The tweet ID to check.

    Returns:
        True if the tweet exists, False otherwise.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT 1 FROM tweets WHERE id = ?",
            (tweet_id,),
        )
        return cursor.fetchone() is not None


def get_tweets_by_collections(db_path: Path, collection_types: list[str]) -> list[dict[str, Any]]:
    """Get all tweets in multiple collections.

    Args:
        db_path: Path to the SQLite database file.
        collection_types: List of collection types (e.g., ["tweet", "reply", "repost"]).

    Returns:
        List of tweet dictionaries ordered by created_at (most recent first).
        Note: We use created_at for combined collections because sort_index values
        from different sync operations aren't comparable chronologically.
    """
    if not collection_types:
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" * len(collection_types))
        cursor = conn.execute(
            f"""
            SELECT t.* FROM tweets t
            JOIN collections c ON t.id = c.tweet_id
            WHERE c.collection_type IN ({placeholders})
            ORDER BY t.created_at DESC
            """,
            collection_types,
        )
        return [dict(row) for row in cursor.fetchall()]


def get_parent_tweet(db_path: Path, reply_tweet_id: str) -> dict[str, Any] | None:
    """Get the parent tweet for a reply.

    Args:
        db_path: Path to the SQLite database file.
        reply_tweet_id: The ID of the reply tweet.

    Returns:
        The parent tweet as a dictionary, or None if not found.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        # First get the in_reply_to_tweet_id from the reply
        cursor = conn.execute(
            "SELECT in_reply_to_tweet_id FROM tweets WHERE id = ?",
            (reply_tweet_id,),
        )
        row = cursor.fetchone()
        if not row or not row["in_reply_to_tweet_id"]:
            return None
        # Then get the parent tweet
        parent_id = row["in_reply_to_tweet_id"]
        cursor = conn.execute(
            "SELECT * FROM tweets WHERE id = ?",
            (parent_id,),
        )
        parent_row = cursor.fetchone()
        return dict(parent_row) if parent_row else None
