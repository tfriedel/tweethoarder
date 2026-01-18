"""Tests for the sync CLI commands."""

from pathlib import Path

import pytest
from conftest import strip_ansi
from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_sync_likes_command_exists() -> None:
    """The sync likes command should be available."""
    result = runner.invoke(app, ["sync", "likes", "--help"])
    assert result.exit_code == 0
    assert "likes" in result.output.lower()


def test_sync_bookmarks_command_exists() -> None:
    """The sync bookmarks command should be available."""
    result = runner.invoke(app, ["sync", "bookmarks", "--help"])
    assert result.exit_code == 0
    assert "bookmarks" in result.output.lower()


def test_sync_tweets_command_exists() -> None:
    """The sync tweets command should be available."""
    result = runner.invoke(app, ["sync", "tweets", "--help"])
    assert result.exit_code == 0
    assert "tweets" in result.output.lower()


def test_sync_reposts_command_exists() -> None:
    """The sync reposts command should be available."""
    result = runner.invoke(app, ["sync", "reposts", "--help"])
    assert result.exit_code == 0
    assert "reposts" in result.output.lower()


def test_sync_likes_accepts_count_option() -> None:
    """The sync likes command should accept a --count option."""
    result = runner.invoke(app, ["sync", "likes", "--help"])
    assert result.exit_code == 0
    assert "--count" in strip_ansi(result.output)


def test_sync_likes_accepts_all_flag() -> None:
    """The sync likes command should accept an --all flag for unlimited sync."""
    result = runner.invoke(app, ["sync", "likes", "--help"])
    assert result.exit_code == 0
    assert "--all" in strip_ansi(result.output)


def test_sync_bookmarks_accepts_count_option() -> None:
    """The sync bookmarks command should accept a --count option."""
    result = runner.invoke(app, ["sync", "bookmarks", "--help"])
    assert result.exit_code == 0
    assert "--count" in strip_ansi(result.output)


def test_sync_bookmarks_accepts_all_flag() -> None:
    """The sync bookmarks command should accept an --all flag for unlimited sync."""
    result = runner.invoke(app, ["sync", "bookmarks", "--help"])
    assert result.exit_code == 0
    assert "--all" in strip_ansi(result.output)


def test_sync_likes_accepts_with_threads_flag() -> None:
    """The sync likes command should accept a --with-threads flag."""
    result = runner.invoke(app, ["sync", "likes", "--help"])
    assert result.exit_code == 0
    assert "--with-threads" in strip_ansi(result.output)


def test_sync_likes_accepts_thread_mode_option() -> None:
    """The sync likes command should accept a --thread-mode option."""
    result = runner.invoke(app, ["sync", "likes", "--help"])
    assert result.exit_code == 0
    assert "--thread-mode" in strip_ansi(result.output)


def test_sync_bookmarks_accepts_with_threads_flag() -> None:
    """The sync bookmarks command should accept a --with-threads flag."""
    result = runner.invoke(app, ["sync", "bookmarks", "--help"])
    assert result.exit_code == 0
    assert "--with-threads" in strip_ansi(result.output)


def test_sync_bookmarks_accepts_thread_mode_option() -> None:
    """The sync bookmarks command should accept a --thread-mode option."""
    result = runner.invoke(app, ["sync", "bookmarks", "--help"])
    assert result.exit_code == 0
    assert "--thread-mode" in strip_ansi(result.output)


def test_sync_tweets_accepts_with_threads_flag() -> None:
    """The sync tweets command should accept a --with-threads flag."""
    result = runner.invoke(app, ["sync", "tweets", "--help"])
    assert result.exit_code == 0
    assert "--with-threads" in strip_ansi(result.output)


def test_sync_tweets_accepts_thread_mode_option() -> None:
    """The sync tweets command should accept a --thread-mode option."""
    result = runner.invoke(app, ["sync", "tweets", "--help"])
    assert result.exit_code == 0
    assert "--thread-mode" in strip_ansi(result.output)


def test_sync_reposts_accepts_with_threads_flag() -> None:
    """The sync reposts command should accept a --with-threads flag."""
    result = runner.invoke(app, ["sync", "reposts", "--help"])
    assert result.exit_code == 0
    assert "--with-threads" in strip_ansi(result.output)


def test_sync_reposts_accepts_thread_mode_option() -> None:
    """The sync reposts command should accept a --thread-mode option."""
    result = runner.invoke(app, ["sync", "reposts", "--help"])
    assert result.exit_code == 0
    assert "--thread-mode" in strip_ansi(result.output)


def test_sync_posts_async_accepts_full_parameter() -> None:
    """sync_posts_async should accept full parameter for forcing complete resync."""
    import inspect

    from tweethoarder.cli.sync import sync_posts_async

    sig = inspect.signature(sync_posts_async)
    params = list(sig.parameters.keys())

    assert "full" in params


def _make_post_entry(tweet_id: str, text: str = "Hello") -> dict:
    """Create a mock post entry for testing."""
    return {
        "entryId": f"tweet-{tweet_id}",
        "content": {
            "itemContent": {
                "tweet_results": {
                    "result": {
                        "rest_id": tweet_id,
                        "legacy": {
                            "full_text": text,
                            "created_at": "Wed Jan 01 12:00:00 +0000 2025",
                            "conversation_id_str": tweet_id,
                            "reply_count": 0,
                            "retweet_count": 0,
                            "favorite_count": 0,
                            "quote_count": 0,
                        },
                        "core": {
                            "user_results": {
                                "result": {
                                    "rest_id": "456",
                                    "core": {
                                        "screen_name": "testuser",
                                        "name": "Test User",
                                    },
                                }
                            }
                        },
                    }
                }
            },
        },
    }


def _make_posts_response(entries: list) -> dict:
    """Create a mock user tweets API response."""
    return {
        "data": {
            "user": {
                "result": {
                    "timeline_v2": {
                        "timeline": {
                            "instructions": [{"type": "TimelineAddEntries", "entries": entries}]
                        }
                    }
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_sync_posts_async_stops_on_duplicate(tmp_path: Path) -> None:
    """sync_posts_async should stop when encountering an existing tweet in the collection."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_posts_async
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Pre-populate with an existing tweet in the tweet collection
    save_tweet(
        db_path,
        {
            "id": "existing",
            "text": "Already synced",
            "author_id": "456",
            "author_username": "user",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    add_to_collection(db_path, "existing", "tweet")

    # API returns: new_tweet, then existing_tweet
    mock_response = _make_posts_response(
        [
            _make_post_entry("new_tweet", "New tweet"),
            _make_post_entry("existing", "Already synced"),
        ]
    )

    with (
        patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies,
        patch("tweethoarder.cli.sync.TwitterClient") as mock_client_class,
        patch("tweethoarder.cli.sync.get_config_dir") as mock_config_dir,
        patch("tweethoarder.cli.sync.get_query_id_with_fallback") as mock_get_query_id,
        patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_async_client,
    ):
        mock_cookies.return_value = {"twid": "u%3D789"}
        mock_client_class.return_value.get_base_headers.return_value = {}
        mock_config_dir.return_value = tmp_path
        mock_get_query_id.return_value = "ABC123"

        mock_http = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_http_response
        mock_async_client.return_value.__aenter__.return_value = mock_http

        result = await sync_posts_async(db_path, count=100)

    # Should only sync the new tweet, stop when hitting existing
    assert result["tweets_count"] == 1
    assert result["reposts_count"] == 0
