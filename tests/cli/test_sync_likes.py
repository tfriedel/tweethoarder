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
                    "timeline_v2": {
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


def _make_tweet_entry(tweet_id: str, text: str = "Hello") -> dict:
    """Create a mock tweet entry for testing."""
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
                                    "legacy": {"screen_name": "user", "name": "User"},
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


def _make_likes_response(entries: list) -> dict:
    """Create a mock likes API response."""
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
