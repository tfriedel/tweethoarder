"""Tests for bookmarks sync functionality."""

import inspect
from pathlib import Path

import pytest


def test_sync_bookmarks_async_function_exists() -> None:
    """sync_bookmarks_async function should be importable."""
    from tweethoarder.cli.sync import sync_bookmarks_async

    assert callable(sync_bookmarks_async)


def test_sync_bookmarks_async_accepts_db_path_and_count() -> None:
    """sync_bookmarks_async should accept db_path and count parameters."""
    from tweethoarder.cli.sync import sync_bookmarks_async

    sig = inspect.signature(sync_bookmarks_async)
    params = list(sig.parameters.keys())

    assert "db_path" in params
    assert "count" in params


def test_sync_bookmarks_async_accepts_with_threads_parameter() -> None:
    """sync_bookmarks_async should accept with_threads parameter."""
    from tweethoarder.cli.sync import sync_bookmarks_async

    sig = inspect.signature(sync_bookmarks_async)
    params = list(sig.parameters.keys())

    assert "with_threads" in params


@pytest.mark.asyncio
async def test_sync_bookmarks_async_uses_fallback_when_cache_empty(tmp_path: Path) -> None:
    """sync_bookmarks_async should use fallback query ID when cache is empty."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async
    from tweethoarder.query_ids.constants import FALLBACK_QUERY_IDS

    db_path = tmp_path / "test.db"
    mock_response = _make_bookmarks_response([_make_bookmark_entry("123", "Hello")])

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Use empty cache directory - forces fallback
            await sync_bookmarks_async(db_path=db_path, count=10)

            # Verify the API was called with the fallback query ID
            call_url = mock_client.get.call_args[0][0]
            assert FALLBACK_QUERY_IDS["Bookmarks"] in call_url


def test_sync_bookmarks_async_accepts_thread_mode_parameter() -> None:
    """sync_bookmarks_async should accept thread_mode parameter."""
    from tweethoarder.cli.sync import sync_bookmarks_async

    sig = inspect.signature(sync_bookmarks_async)
    params = list(sig.parameters.keys())

    assert "thread_mode" in params


@pytest.mark.asyncio
async def test_sync_bookmarks_async_returns_synced_count(tmp_path: Path) -> None:
    """sync_bookmarks_async should return a dict with synced_count."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async

    db_path = tmp_path / "test.db"

    mock_response = {
        "data": {
            "bookmark_timeline_v2": {
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

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "test", "ct0": "test"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "BOOK123"
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = AsyncMock(
                    json=lambda: mock_response,
                    raise_for_status=lambda: None,
                )
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                result = await sync_bookmarks_async(db_path=db_path, count=10)

    assert "synced_count" in result
    assert result["synced_count"] == 0


def _make_bookmark_entry(tweet_id: str, text: str = "Hello", sort_index: str | None = None) -> dict:
    """Create a mock bookmark entry for testing."""
    entry = {
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


def _make_bookmarks_response(entries: list) -> dict:
    """Create a mock bookmarks API response."""
    return {
        "data": {
            "bookmark_timeline_v2": {
                "timeline": {"instructions": [{"type": "TimelineAddEntries", "entries": entries}]}
            }
        }
    }


@pytest.mark.asyncio
async def test_sync_bookmarks_async_fetches_and_saves_tweets(tmp_path: Path) -> None:
    """sync_bookmarks_async should fetch tweets and save them to database."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async

    db_path = tmp_path / "test.db"
    mock_response = _make_bookmarks_response([_make_bookmark_entry("123", "Hello")])

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "BOOK123"
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_http_response
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                result = await sync_bookmarks_async(db_path=db_path, count=10)

    assert result["synced_count"] == 1

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT id, text FROM tweets WHERE id = ?", ("123",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "123"
    assert row[1] == "Hello"


def test_bookmarks_command_calls_sync_bookmarks_async() -> None:
    """The bookmarks command should call sync_bookmarks_async."""
    from unittest.mock import AsyncMock, patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_bookmarks_async", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        result = runner.invoke(app, ["sync", "bookmarks"])

    mock_sync.assert_called_once()
    assert result.exit_code == 0
    assert "5" in result.output


def test_bookmarks_command_passes_with_threads_to_async() -> None:
    """The bookmarks CLI command should pass with_threads to sync_bookmarks_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_bookmarks_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "bookmarks", "--with-threads"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("with_threads") is True


def test_bookmarks_command_passes_thread_mode_to_async() -> None:
    """The bookmarks CLI command should pass thread_mode to sync_bookmarks_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_bookmarks_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "bookmarks", "--thread-mode", "conversation"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("thread_mode") == "conversation"


@pytest.mark.asyncio
async def test_sync_bookmarks_async_paginates_with_cursor(tmp_path: Path) -> None:
    """sync_bookmarks_async should paginate through multiple pages using cursor."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async

    db_path = tmp_path / "test.db"

    # First page with cursor, second page without cursor
    first_page = _make_bookmarks_response([_make_bookmark_entry("1", "First")])
    first_page["data"]["bookmark_timeline_v2"]["timeline"]["instructions"][0]["entries"].append(
        {
            "entryId": "cursor-bottom-123",
            "content": {"value": "next_cursor"},
        }
    )
    second_page = _make_bookmarks_response([_make_bookmark_entry("2", "Second")])

    mock_http_response_1 = MagicMock()
    mock_http_response_1.json.return_value = first_page
    mock_http_response_1.raise_for_status = MagicMock()

    mock_http_response_2 = MagicMock()
    mock_http_response_2.json.return_value = second_page
    mock_http_response_2.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "BOOK123"
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.side_effect = [mock_http_response_1, mock_http_response_2]
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                result = await sync_bookmarks_async(db_path=db_path, count=10)

    assert result["synced_count"] == 2
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_sync_bookmarks_async_respects_count_limit(tmp_path: Path) -> None:
    """sync_bookmarks_async should stop syncing when count is reached."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async

    db_path = tmp_path / "test.db"

    # Page with 3 bookmarks
    page = _make_bookmarks_response(
        [
            _make_bookmark_entry("1", "First"),
            _make_bookmark_entry("2", "Second"),
            _make_bookmark_entry("3", "Third"),
        ]
    )

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = page
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "BOOK123"
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_http_response
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                result = await sync_bookmarks_async(db_path=db_path, count=2)

    assert result["synced_count"] == 2


@pytest.mark.asyncio
async def test_sync_bookmarks_async_stops_pagination_when_count_reached(tmp_path: Path) -> None:
    """sync_bookmarks_async should not fetch more pages when count is reached."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async

    db_path = tmp_path / "test.db"

    # Page with 2 bookmarks and a cursor (would normally trigger more fetches)
    page = _make_bookmarks_response(
        [
            _make_bookmark_entry("1", "First"),
            _make_bookmark_entry("2", "Second"),
        ]
    )
    page["data"]["bookmark_timeline_v2"]["timeline"]["instructions"][0]["entries"].append(
        {
            "entryId": "cursor-bottom-123",
            "content": {"value": "next_cursor"},
        }
    )

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = page
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "BOOK123"
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_http_response
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                result = await sync_bookmarks_async(db_path=db_path, count=2)

    # Should only fetch once since count was reached
    assert mock_client.get.call_count == 1
    assert result["synced_count"] == 2


@pytest.mark.asyncio
async def test_sync_bookmarks_async_clears_checkpoint_on_completion(tmp_path: Path) -> None:
    """sync_bookmarks_async should clear checkpoint on successful completion."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async
    from tweethoarder.storage.checkpoint import SyncCheckpoint

    db_path = tmp_path / "test.db"

    # Page with cursor (should trigger checkpoint save)
    page = _make_bookmarks_response([_make_bookmark_entry("1", "First")])
    page["data"]["bookmark_timeline_v2"]["timeline"]["instructions"][0]["entries"].append(
        {
            "entryId": "cursor-bottom-123",
            "content": {"value": "next_cursor"},
        }
    )
    page2 = _make_bookmarks_response([])  # Empty second page to stop

    mock_http_response_1 = MagicMock()
    mock_http_response_1.json.return_value = page
    mock_http_response_1.raise_for_status = MagicMock()

    mock_http_response_2 = MagicMock()
    mock_http_response_2.json.return_value = page2
    mock_http_response_2.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "BOOK123"
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.side_effect = [mock_http_response_1, mock_http_response_2]
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                await sync_bookmarks_async(db_path=db_path, count=100)

    # Checkpoint should be cleared on successful completion
    checkpoint = SyncCheckpoint(db_path)
    assert checkpoint.load("bookmark") is None


@pytest.mark.asyncio
async def test_sync_bookmarks_async_resumes_from_checkpoint(tmp_path: Path) -> None:
    """sync_bookmarks_async should resume from a saved checkpoint."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async
    from tweethoarder.storage.checkpoint import SyncCheckpoint
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Save a checkpoint as if previous sync was interrupted
    checkpoint = SyncCheckpoint(db_path)
    checkpoint.save("bookmark", cursor="saved_cursor", last_tweet_id="100")

    # This page should be returned when resuming with saved_cursor
    page = _make_bookmarks_response([_make_bookmark_entry("200", "Resumed")])

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = page
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "BOOK123"
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_http_response
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                result = await sync_bookmarks_async(db_path=db_path, count=100)

    # Should have synced the resumed tweet
    assert result["synced_count"] == 1

    # Check that the API was called with the saved cursor
    call_args = mock_client.get.call_args[0][0]
    assert "saved_cursor" in call_args


@pytest.mark.asyncio
async def test_sync_bookmarks_async_saves_checkpoint_after_page(tmp_path: Path) -> None:
    """sync_bookmarks_async should save checkpoint after each page with cursor."""
    from unittest.mock import AsyncMock, MagicMock, patch

    import httpx

    from tweethoarder.cli.sync import sync_bookmarks_async
    from tweethoarder.storage.checkpoint import SyncCheckpoint

    db_path = tmp_path / "test.db"

    # Page with cursor - sync will be interrupted after first page
    page = _make_bookmarks_response([_make_bookmark_entry("1", "First")])
    page["data"]["bookmark_timeline_v2"]["timeline"]["instructions"][0]["entries"].append(
        {
            "entryId": "cursor-bottom-123",
            "content": {"value": "next_cursor"},
        }
    )

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = page
    mock_http_response.raise_for_status = MagicMock()

    # Simulate error on second page (interruption)
    error_response = MagicMock()
    error_response.status_code = 500
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error", request=MagicMock(), response=error_response
    )

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "BOOK123"
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.side_effect = [mock_http_response, error_response]
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                try:
                    await sync_bookmarks_async(db_path=db_path, count=100)
                except httpx.HTTPStatusError:
                    pass  # Expected - sync was interrupted

    # Checkpoint should be saved with the cursor from first page
    checkpoint = SyncCheckpoint(db_path)
    saved = checkpoint.load("bookmark")
    assert saved is not None
    assert saved.cursor == "next_cursor"
    assert saved.last_tweet_id == "1"


@pytest.mark.asyncio
async def test_sync_bookmarks_async_refreshes_query_id_on_404(tmp_path: Path) -> None:
    """sync_bookmarks_async should refresh query ID on 404 and retry."""
    from unittest.mock import AsyncMock, MagicMock, patch

    import httpx

    from tweethoarder.cli.sync import sync_bookmarks_async

    db_path = tmp_path / "test.db"

    # First call returns 404, second returns success
    not_found_response = MagicMock()
    not_found_response.status_code = 404
    not_found_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not found", request=MagicMock(), response=not_found_response
    )

    page = _make_bookmarks_response([_make_bookmark_entry("1", "After refresh")])
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = page
    success_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "OLD_QUERY_ID"
            mock_store.save = MagicMock()
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.refresh_query_ids") as mock_refresh:
                mock_refresh.return_value = {"Bookmarks": "NEW_QUERY_ID"}
                with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                    mock_client = AsyncMock()
                    mock_client.get.side_effect = [not_found_response, success_response]
                    mock_client_cls.return_value.__aenter__.return_value = mock_client

                    result = await sync_bookmarks_async(db_path=db_path, count=10)

    assert result["synced_count"] == 1
    mock_refresh.assert_called_once()
    mock_store.save.assert_called_once()


def test_sync_bookmarks_async_accepts_store_raw_parameter() -> None:
    """sync_bookmarks_async should accept store_raw parameter."""
    from tweethoarder.cli.sync import sync_bookmarks_async

    sig = inspect.signature(sync_bookmarks_async)
    params = list(sig.parameters.keys())

    assert "store_raw" in params


def test_bookmarks_command_passes_store_raw_to_async() -> None:
    """The bookmarks CLI command should pass store_raw to sync_bookmarks_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_bookmarks_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "bookmarks", "--store-raw"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("store_raw") is True


@pytest.mark.asyncio
async def test_sync_bookmarks_async_stores_raw_json_when_store_raw_enabled(tmp_path: Path) -> None:
    """sync_bookmarks_async should store raw_json in database when store_raw=True."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async

    db_path = tmp_path / "test.db"
    mock_response = _make_bookmarks_response([_make_bookmark_entry("123", "Hello")])

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await sync_bookmarks_async(db_path=db_path, count=10, store_raw=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT raw_json FROM tweets WHERE id = ?", ("123",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] is not None


@pytest.mark.asyncio
async def test_sync_bookmarks_async_fetches_threads_for_conversation_tweets(tmp_path: Path) -> None:
    """sync_bookmarks_async should fetch threads only for tweets that are part of conversations."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async

    db_path = tmp_path / "test.db"
    # Create response with 3 bookmarks - 2 are replies (need threads), 1 is standalone
    reply_entry_1 = _make_bookmark_entry("111", "First reply")
    reply_entry_1["content"]["itemContent"]["tweet_results"]["result"]["legacy"][
        "in_reply_to_status_id_str"
    ] = "000"
    reply_entry_2 = _make_bookmark_entry("222", "Second reply")
    reply_entry_2["content"]["itemContent"]["tweet_results"]["result"]["legacy"][
        "in_reply_to_status_id_str"
    ] = "000"
    standalone_entry = _make_bookmark_entry("333", "Standalone tweet")

    mock_response = _make_bookmarks_response([reply_entry_1, reply_entry_2, standalone_entry])

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.query_ids.store.QueryIdStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.get.return_value = "BOOK123"
            mock_store_cls.return_value = mock_store
            with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_http_response
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                with patch("tweethoarder.cli.sync.fetch_thread_async") as mock_fetch_thread:
                    mock_fetch_thread.return_value = {"tweet_count": 5}

                    await sync_bookmarks_async(db_path=db_path, count=10, with_threads=True)

                    # Should be called 2 times - only for reply tweets, not standalone
                    assert mock_fetch_thread.call_count == 2
                    # Verify only reply tweet IDs were passed
                    call_tweet_ids = [
                        call[1]["tweet_id"] for call in mock_fetch_thread.call_args_list
                    ]
                    assert set(call_tweet_ids) == {"111", "222"}


@pytest.mark.asyncio
async def test_sync_bookmarks_async_stores_sort_index(tmp_path: Path) -> None:
    """sync_bookmarks_async should store generated sort_index in collections table."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_bookmarks_async
    from tweethoarder.sync.sort_index import INITIAL_SORT_INDEX

    db_path = tmp_path / "test.db"
    mock_response = _make_bookmarks_response(
        [_make_bookmark_entry("123", "Hello", sort_index="9876543210")]
    )

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "t", "ct0": "t"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_http_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await sync_bookmarks_async(db_path=db_path, count=10)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT sort_index FROM collections WHERE tweet_id = ? AND collection_type = ?",
        ("123", "bookmark"),
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    # First bookmark gets the initial sort_index value
    assert row[0] == INITIAL_SORT_INDEX
