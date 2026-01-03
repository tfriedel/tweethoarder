"""Database management for TweetHoarder."""

import sqlite3
from pathlib import Path

TWEETS_SCHEMA = """
CREATE TABLE IF NOT EXISTS tweets (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_username TEXT NOT NULL,
    author_display_name TEXT,
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
    added_at TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    PRIMARY KEY (tweet_id, collection_type),
    FOREIGN KEY (tweet_id) REFERENCES tweets(id)
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

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_tweets_author ON tweets(author_id)",
    "CREATE INDEX IF NOT EXISTS idx_tweets_conversation ON tweets(conversation_id)",
    "CREATE INDEX IF NOT EXISTS idx_tweets_created_at ON tweets(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_collections_type ON collections(collection_type)",
    "CREATE INDEX IF NOT EXISTS idx_collections_added ON collections(added_at)",
]


def init_database(db_path: Path) -> None:
    """Initialize the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.execute(TWEETS_SCHEMA)
    conn.execute(COLLECTIONS_SCHEMA)
    conn.execute(SYNC_PROGRESS_SCHEMA)
    conn.execute(THREAD_CONTEXT_SCHEMA)
    conn.execute(METADATA_SCHEMA)
    for index_sql in INDEXES:
        conn.execute(index_sql)
    conn.commit()
    conn.close()


def save_tweet(db_path: Path, tweet_data: dict) -> None:
    """Save a tweet to the database."""
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT OR REPLACE INTO tweets (
            id, text, author_id, author_username, author_display_name,
            created_at, conversation_id, reply_count, retweet_count,
            like_count, quote_count, first_seen_at, last_updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tweet_data["id"],
            tweet_data["text"],
            tweet_data["author_id"],
            tweet_data["author_username"],
            tweet_data.get("author_display_name"),
            tweet_data["created_at"],
            tweet_data.get("conversation_id"),
            tweet_data.get("reply_count", 0),
            tweet_data.get("retweet_count", 0),
            tweet_data.get("like_count", 0),
            tweet_data.get("quote_count", 0),
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()


def add_to_collection(db_path: Path, tweet_id: str, collection_type: str) -> None:
    """Add a tweet to a collection."""
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT OR IGNORE INTO collections (
            tweet_id, collection_type, added_at, synced_at
        ) VALUES (?, ?, ?, ?)
        """,
        (tweet_id, collection_type, now, now),
    )
    conn.commit()
    conn.close()
