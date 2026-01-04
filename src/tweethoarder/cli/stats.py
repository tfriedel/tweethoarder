"""Stats CLI command for TweetHoarder."""

import sqlite3
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from tweethoarder.config import get_data_dir

console = Console()


def get_database_path() -> Path:
    """Get the path to the database file."""
    data_dir: Path = get_data_dir()
    return data_dir / "tweethoarder.db"


def get_total_tweet_count(db_path: Path) -> int:
    """Get the total number of tweets in the database."""
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM tweets")
        count: int = cursor.fetchone()[0]
    return count


def get_collection_counts(db_path: Path) -> dict[str, int]:
    """Get counts for each collection type."""
    if not db_path.exists():
        return {}
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT collection_type, COUNT(*) FROM collections GROUP BY collection_type"
        )
        counts = {row[0]: row[1] for row in cursor.fetchall()}
    return counts


def get_last_sync_times(db_path: Path) -> dict[str, str | None]:
    """Get last sync completion time for each collection type."""
    if not db_path.exists():
        return {}
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT collection_type, completed_at FROM sync_progress WHERE status = 'completed'"
        )
        times = {row[0]: row[1] for row in cursor.fetchall()}
    return times


def format_sync_time(timestamp: str | None) -> str:
    """Format a sync timestamp for display."""
    if not timestamp:
        return "never"
    return timestamp[:10]


def get_database_size(db_path: Path) -> str:
    """Get the database file size in human readable format."""
    if not db_path.exists():
        return "0 B"
    size_bytes = db_path.stat().st_size
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def show_stats() -> None:
    """Display statistics about synced data."""
    db_path = get_database_path()
    total_tweets = get_total_tweet_count(db_path)
    collection_counts = get_collection_counts(db_path)
    sync_times = get_last_sync_times(db_path)
    db_size = get_database_size(db_path)

    likes_time = format_sync_time(sync_times.get("likes"))
    bookmarks_time = format_sync_time(sync_times.get("bookmarks"))
    tweets_time = format_sync_time(sync_times.get("tweets"))
    reposts_time = format_sync_time(sync_times.get("reposts"))

    lines = [
        f"Likes: {collection_counts.get('like', 0):,} (last: {likes_time})",
        f"Bookmarks: {collection_counts.get('bookmark', 0):,} (last: {bookmarks_time})",
    ]

    # Add bookmark folder breakdown
    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT bookmark_folder_name, COUNT(*) FROM collections "
                "WHERE collection_type = 'bookmark' AND bookmark_folder_name IS NOT NULL "
                "GROUP BY bookmark_folder_name"
            )
            for folder, count in cursor.fetchall():
                lines.append(f"  - {folder}: {count}")

    lines.extend(
        [
            f"Tweets: {collection_counts.get('tweet', 0):,} (last: {tweets_time})",
            f"Reposts: {collection_counts.get('repost', 0):,} (last: {reposts_time})",
            f"Total Tweets: {total_tweets:,}",
            f"Database: {db_size}",
        ]
    )

    console.print(Panel("\n".join(lines), title="TweetHoarder Stats"))
