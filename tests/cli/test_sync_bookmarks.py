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


def _make_bookmark_entry(tweet_id: str, text: str = "Hello") -> dict:
    """Create a mock bookmark entry for testing."""
    return {
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
