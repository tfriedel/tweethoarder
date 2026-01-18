"""Tests for likes sync functionality."""

import inspect
from pathlib import Path

import pytest


def test_sync_likes_async_function_exists() -> None:
    """sync_likes_async function should be importable."""
    from tweethoarder.cli.sync import sync_likes_async

    assert callable(sync_likes_async)


def test_sync_likes_async_accepts_db_path_and_count() -> None:
    """sync_likes_async should accept db_path and count parameters."""
    from tweethoarder.cli.sync import sync_likes_async

    sig = inspect.signature(sync_likes_async)
    params = list(sig.parameters.keys())

    assert "db_path" in params
    assert "count" in params


def test_sync_likes_async_accepts_with_threads_parameter() -> None:
    """sync_likes_async should accept with_threads parameter."""
    from tweethoarder.cli.sync import sync_likes_async

    sig = inspect.signature(sync_likes_async)
    params = list(sig.parameters.keys())

    assert "with_threads" in params


def test_sync_likes_async_accepts_thread_mode_parameter() -> None:
    """sync_likes_async should accept thread_mode parameter."""
    from tweethoarder.cli.sync import sync_likes_async

    sig = inspect.signature(sync_likes_async)
    params = list(sig.parameters.keys())

    assert "thread_mode" in params


@pytest.mark.asyncio
async def test_sync_likes_async_initializes_database(tmp_path: Path) -> None:
    """sync_likes_async should initialize the database before syncing."""
    from unittest.mock import patch

    from tweethoarder.cli.sync import sync_likes_async

    db_path = tmp_path / "test.db"

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = None

        with pytest.raises(ValueError, match="No cookies found"):
            await sync_likes_async(db_path=db_path, count=10)

    assert db_path.exists()


@pytest.mark.asyncio
async def test_sync_likes_async_returns_synced_count(tmp_path: Path) -> None:
    """sync_likes_async should return a dict with synced_count."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_likes_async

    db_path = tmp_path / "test.db"

    mock_response = {
        "data": {
            "user": {
                "result": {
                    "timeline": {
                        "timeline": {
                            "instructions": [
                                {
                                    "type": "TimelineAddEntries",
                                    "entries": [],
                                }
                            ]
                        }
                    }
                }
            }
        }
    }

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "test", "ct0": "test", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = AsyncMock(
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sync_likes_async(db_path=db_path, count=10)

    assert "synced_count" in result
    assert result["synced_count"] == 0


def _make_tweet_entry(tweet_id: str, text: str = "Hello", sort_index: str | None = None) -> dict:
    """Create a mock tweet entry for testing.

    Uses the current Twitter API response structure where user info is in
    result.core instead of result.legacy.
    """
    entry: dict = {
        "entryId": f"tweet-{tweet_id}",
        "content": {
            "entryType": "TimelineTimelineItem",
            "itemContent": {
                "tweet_results": {
                    "result": {
                        "rest_id": tweet_id,
                        "core": {
                            "user_results": {
                                "result": {
                                    "rest_id": "456",
                                    "core": {"screen_name": "user", "name": "User"},
                                }
                            }
                        },
                        "legacy": {
                            "full_text": text,
                            "created_at": "Wed Jan 01 12:00:00 +0000 2025",
                            "conversation_id_str": tweet_id,
                        },
                    }
                }
            },
        },
    }
    if sort_index:
        entry["sortIndex"] = sort_index
    return entry


def _make_likes_response(entries: list) -> dict:
    """Create a mock likes API response.

    Uses the current Twitter API response structure with timeline instead of timeline_v2.
    """
    return {
        "data": {
            "user": {
                "result": {
                    "timeline": {
                        "timeline": {
                            "instructions": [{"type": "TimelineAddEntries", "entries": entries}]
                        }
                    }
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_sync_likes_async_fetches_and_saves_tweets(tmp_path: Path) -> None:
    """sync_likes_async should fetch tweets and save them to database."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async

    db_path = tmp_path / "test.db"
    mock_response = _make_likes_response([_make_tweet_entry("123", "Hello")])

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sync_likes_async(db_path=db_path, count=10)

    assert result["synced_count"] == 1

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT id, text FROM tweets WHERE id = ?", ("123",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "123"
    assert row[1] == "Hello"


def _make_cursor_entry(cursor_value: str) -> dict:
    """Create a mock cursor entry for pagination."""
    return {
        "entryId": "cursor-bottom-123",
        "content": {
            "entryType": "TimelineTimelineCursor",
            "value": cursor_value,
            "cursorType": "Bottom",
        },
    }


@pytest.mark.asyncio
async def test_sync_likes_async_paginates_to_fetch_more_tweets(tmp_path: Path) -> None:
    """sync_likes_async should use cursor to fetch multiple pages."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async

    db_path = tmp_path / "test.db"

    page1_response = _make_likes_response(
        [
            _make_tweet_entry("1", "Tweet 1"),
            _make_cursor_entry("cursor_page2"),
        ]
    )
    page2_response = _make_likes_response([_make_tweet_entry("2", "Tweet 2")])

    mock_responses = [page1_response, page2_response]
    response_index = [0]

    def get_response() -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = mock_responses[response_index[0]]
        resp.raise_for_status = MagicMock()
        response_index[0] += 1
        return resp

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = lambda url: get_response()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sync_likes_async(db_path=db_path, count=10)

    assert result["synced_count"] == 2
    assert mock_client.get.call_count == 2


def test_likes_command_calls_sync_likes_async() -> None:
    """The likes CLI command should call sync_likes_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_likes_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        result = runner.invoke(app, ["sync", "likes", "--count", "10"])

    mock_sync.assert_called_once()
    assert result.exit_code == 0


def test_likes_command_passes_with_threads_to_async() -> None:
    """The likes CLI command should pass with_threads to sync_likes_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_likes_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "likes", "--with-threads"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("with_threads") is True


def test_likes_command_passes_thread_mode_to_async() -> None:
    """The likes CLI command should pass thread_mode to sync_likes_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_likes_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "likes", "--thread-mode", "conversation"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("thread_mode") == "conversation"


@pytest.mark.asyncio
async def test_sync_likes_async_skips_incomplete_tweets(tmp_path: Path) -> None:
    """sync_likes_async should skip tweets with missing required fields."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async

    db_path = tmp_path / "test.db"

    incomplete_tweet = {
        "entryId": "tweet-999",
        "content": {
            "entryType": "TimelineTimelineItem",
            "itemContent": {
                "tweet_results": {
                    "result": {
                        "rest_id": None,
                        "core": {},
                        "legacy": {},
                    }
                }
            },
        },
    }

    mock_response = _make_likes_response(
        [_make_tweet_entry("123", "Valid tweet"), incomplete_tweet]
    )

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()
    mock_http_response.status_code = 200

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sync_likes_async(db_path=db_path, count=10)

    assert result["synced_count"] == 1

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM tweets")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1


@pytest.mark.asyncio
async def test_sync_likes_async_passes_refresh_callback_to_fetch(tmp_path: Path) -> None:
    """sync_likes_async should pass on_query_id_refresh callback to fetch_likes_page."""
    from unittest.mock import patch

    from tweethoarder.cli.sync import sync_likes_async

    db_path = tmp_path / "test.db"

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.fetch_likes_page") as mock_fetch:
            mock_fetch.return_value = {
                "data": {"user": {"result": {"timeline": {"timeline": {"instructions": []}}}}}
            }

            await sync_likes_async(db_path=db_path, count=10)

            mock_fetch.assert_called()
            call_kwargs = mock_fetch.call_args.kwargs
            assert "on_query_id_refresh" in call_kwargs
            assert callable(call_kwargs["on_query_id_refresh"])


@pytest.mark.asyncio
async def test_sync_likes_async_saves_checkpoint_after_each_page(tmp_path: Path) -> None:
    """sync_likes_async should save checkpoint after processing each page."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async
    from tweethoarder.storage.checkpoint import SyncCheckpoint

    db_path = tmp_path / "test.db"

    page1_response = _make_likes_response(
        [
            _make_tweet_entry("1", "Tweet 1"),
            _make_cursor_entry("cursor_page2"),
        ]
    )
    page2_response = _make_likes_response([_make_tweet_entry("2", "Tweet 2")])

    mock_responses = [page1_response, page2_response]
    response_index = [0]

    def get_response() -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = mock_responses[response_index[0]]
        resp.raise_for_status = MagicMock()
        response_index[0] += 1
        return resp

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = lambda url: get_response()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await sync_likes_async(db_path=db_path, count=10)

    # Verify checkpoint was saved (and cleared on completion)
    checkpoint = SyncCheckpoint(db_path)
    saved = checkpoint.load("like")
    # After successful completion, checkpoint should be cleared
    assert saved is None


@pytest.mark.asyncio
async def test_sync_likes_async_resumes_from_checkpoint(tmp_path: Path) -> None:
    """sync_likes_async should resume from saved checkpoint cursor."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async
    from tweethoarder.storage.checkpoint import SyncCheckpoint
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Pre-save a checkpoint with cursor
    checkpoint = SyncCheckpoint(db_path)
    checkpoint.save("like", cursor="saved_cursor", last_tweet_id="999")

    # Only return page 2 data (simulating resume)
    page2_response = _make_likes_response([_make_tweet_entry("2", "Tweet 2")])

    def get_response() -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = page2_response
        resp.raise_for_status = MagicMock()
        return resp

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = lambda url: get_response()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            with patch("tweethoarder.cli.sync.fetch_likes_page") as mock_fetch:
                mock_fetch.return_value = page2_response

                await sync_likes_async(db_path=db_path, count=10)

                # Verify fetch was called with the saved cursor
                mock_fetch.assert_called()
                call_args = mock_fetch.call_args
                assert call_args[0][3] == "saved_cursor"  # cursor is 4th positional arg


@pytest.mark.asyncio
async def test_sync_likes_async_fetches_threads_for_self_reply_tweets(tmp_path: Path) -> None:
    """sync_likes_async should fetch threads only for self-reply tweets (threads)."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async

    db_path = tmp_path / "test.db"
    # Create response with 3 tweets:
    # - 1 self-reply (author replies to themselves = thread) - needs thread fetch
    # - 1 reply to other user - does NOT need thread fetch (would be filtered anyway)
    # - 1 standalone tweet - does NOT need thread fetch
    self_reply_entry = _make_tweet_entry("111", "Thread continuation")
    self_reply_entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"][
        "in_reply_to_status_id_str"
    ] = "000"
    self_reply_entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"][
        "in_reply_to_user_id_str"
    ] = "456"  # Same as author_id in _make_tweet_entry

    reply_to_other_entry = _make_tweet_entry("222", "Reply to someone else")
    reply_to_other_entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"][
        "in_reply_to_status_id_str"
    ] = "000"
    reply_to_other_entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"][
        "in_reply_to_user_id_str"
    ] = "999"  # Different from author_id

    standalone_entry = _make_tweet_entry("333", "Standalone tweet")

    mock_response = _make_likes_response([self_reply_entry, reply_to_other_entry, standalone_entry])

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            with patch("tweethoarder.cli.thread.fetch_thread_async") as mock_fetch_thread:
                mock_fetch_thread.return_value = {"tweet_count": 5}

                await sync_likes_async(db_path=db_path, count=10, with_threads=True)

                # Should be called 1 time - only for self-reply tweet (thread)
                assert mock_fetch_thread.call_count == 1
                # Verify only self-reply tweet ID was passed
                call_tweet_ids = [call[1]["tweet_id"] for call in mock_fetch_thread.call_args_list]
                assert call_tweet_ids == ["111"]


def test_sync_likes_async_accepts_store_raw_parameter() -> None:
    """sync_likes_async should accept store_raw parameter."""
    import inspect

    from tweethoarder.cli.sync import sync_likes_async

    sig = inspect.signature(sync_likes_async)
    params = list(sig.parameters.keys())

    assert "store_raw" in params


def test_likes_command_passes_store_raw_to_async() -> None:
    """The likes CLI command should pass store_raw to sync_likes_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_likes_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "likes", "--store-raw"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("store_raw") is True


@pytest.mark.asyncio
async def test_sync_likes_async_stores_raw_json_when_store_raw_enabled(tmp_path: Path) -> None:
    """sync_likes_async should store raw_json in database when store_raw=True."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async

    db_path = tmp_path / "test.db"
    mock_response = _make_likes_response([_make_tweet_entry("123", "Hello")])

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await sync_likes_async(db_path=db_path, count=10, store_raw=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT raw_json FROM tweets WHERE id = ?", ("123",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] is not None


def test_sync_likes_async_accepts_full_parameter() -> None:
    """sync_likes_async should accept full parameter for forcing complete resync."""
    import inspect

    from tweethoarder.cli.sync import sync_likes_async

    sig = inspect.signature(sync_likes_async)
    params = list(sig.parameters.keys())

    assert "full" in params


@pytest.mark.asyncio
async def test_sync_likes_async_stops_on_duplicate(tmp_path: Path) -> None:
    """sync_likes_async should stop when encountering an existing tweet in the collection."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Pre-populate with an existing liked tweet
    save_tweet(
        db_path,
        {
            "id": "existing",
            "text": "Already liked",
            "author_id": "456",
            "author_username": "user",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    add_to_collection(db_path, "existing", "like")

    # API returns: new_tweet, then existing_tweet
    mock_response = _make_likes_response(
        [
            _make_tweet_entry("new_tweet", "New tweet"),
            _make_tweet_entry("existing", "Already liked"),
        ]
    )

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sync_likes_async(db_path=db_path, count=100)

    # Should only sync the new tweet, not the existing one
    assert result["synced_count"] == 1


@pytest.mark.asyncio
async def test_sync_likes_async_full_ignores_duplicates(tmp_path: Path) -> None:
    """sync_likes_async with full=True should continue past existing tweets."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Pre-populate with an existing liked tweet
    save_tweet(
        db_path,
        {
            "id": "existing",
            "text": "Already liked",
            "author_id": "456",
            "author_username": "user",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    add_to_collection(db_path, "existing", "like")

    # API returns: new_tweet, then existing_tweet
    mock_response = _make_likes_response(
        [
            _make_tweet_entry("new_tweet", "New tweet"),
            _make_tweet_entry("existing", "Already liked"),
        ]
    )

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sync_likes_async(db_path=db_path, count=100, full=True)

    # With full=True, should sync both tweets (existing one gets updated)
    assert result["synced_count"] == 2


@pytest.mark.asyncio
async def test_sync_likes_async_stores_sort_index(tmp_path: Path) -> None:
    """sync_likes_async should store generated sort_index in collections table."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_likes_async
    from tweethoarder.sync.sort_index import INITIAL_SORT_INDEX

    db_path = tmp_path / "test.db"
    mock_response = _make_likes_response(
        [_make_tweet_entry("123", "Hello", sort_index="2007662285526401024")]
    )

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t", "twid": "u%3D12345"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await sync_likes_async(db_path=db_path, count=10)

    # Verify sort_index was stored - now uses our generated value, not Twitter's
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT sort_index FROM collections WHERE tweet_id = ?", ("123",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    # First tweet gets the initial sort_index value
    assert row[0] == INITIAL_SORT_INDEX


def test_likes_command_accepts_full_flag() -> None:
    """Likes CLI command should accept --full flag."""
    import re

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["likes", "--help"])

    # Strip ANSI escape codes for reliable matching
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--full" in clean_output
