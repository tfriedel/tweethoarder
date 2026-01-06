"""Tests for sync threads command functionality."""

import sqlite3
from pathlib import Path

from tweethoarder.storage.database import init_database, save_tweet


def test_sync_threads_finds_incomplete_threads_with_missing_parent(tmp_path: Path) -> None:
    """Sync threads should find threads where parent tweet is missing from DB.

    Scenario: User has tweets 1/, 8/, 9/ of a thread but is missing tweets 2-7.
    The current implementation skips this because COUNT(*) > 1, but tweet 8/
    replies to a missing tweet (7/), so we should fetch the full thread.
    """
    db_path = tmp_path / "test.db"
    init_database(db_path)

    author_id = "123456"
    conversation_id = "1000000001"  # Tweet 1/

    # Tweet 1/ - thread start
    save_tweet(
        db_path,
        {
            "id": "1000000001",
            "text": "1/ This is the start of my thread",
            "author_id": author_id,
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "conversation_id": conversation_id,
            "in_reply_to_user_id": None,
            "in_reply_to_tweet_id": None,
        },
    )

    # Tweet 8/ - replies to missing tweet 7/
    save_tweet(
        db_path,
        {
            "id": "1000000008",
            "text": "8/ Continuing the thread...",
            "author_id": author_id,
            "author_username": "testuser",
            "created_at": "2025-01-01T12:07:00Z",
            "conversation_id": conversation_id,
            "in_reply_to_user_id": author_id,  # Self-reply
            "in_reply_to_tweet_id": "1000000007",  # Tweet 7/ - NOT in DB
        },
    )

    # Tweet 9/ - replies to tweet 8/
    save_tweet(
        db_path,
        {
            "id": "1000000009",
            "text": "9/ Final thoughts...",
            "author_id": author_id,
            "author_username": "testuser",
            "created_at": "2025-01-01T12:08:00Z",
            "conversation_id": conversation_id,
            "in_reply_to_user_id": author_id,  # Self-reply
            "in_reply_to_tweet_id": "1000000008",  # Tweet 8/ - IS in DB
        },
    )

    # Query for threads needing fetch (the fixed version)
    # Should find the thread because tweet 8/ replies to a missing parent
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # This is the FIXED query that should find incomplete threads
    cursor = conn.execute("""
        SELECT DISTINCT t.conversation_id, t.id as tweet_id
        FROM tweets t
        WHERE t.in_reply_to_user_id IS NOT NULL
          AND t.in_reply_to_user_id = t.author_id
          AND t.in_reply_to_tweet_id IS NOT NULL
          AND t.in_reply_to_tweet_id NOT IN (SELECT id FROM tweets)
    """)

    rows = cursor.fetchall()
    conn.close()

    # Should find tweet 8/ because its parent (tweet 7/) is missing
    assert len(rows) == 1
    assert rows[0]["tweet_id"] == "1000000008"
    assert rows[0]["conversation_id"] == conversation_id
