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


@pytest.mark.asyncio
async def test_sync_likes_async_fetches_and_saves_tweets(tmp_path: Path) -> None:
    """sync_likes_async should fetch tweets and save them to database."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

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
                                    "entries": [
                                        {
                                            "entryId": "tweet-123",
                                            "content": {
                                                "entryType": "TimelineTimelineItem",
                                                "itemContent": {
                                                    "tweet_results": {
                                                        "result": {
                                                            "rest_id": "123",
                                                            "core": {
                                                                "user_results": {
                                                                    "result": {
                                                                        "rest_id": "456",
                                                                        "legacy": {
                                                                            "screen_name": "user",
                                                                            "name": "User",
                                                                        },
                                                                    }
                                                                }
                                                            },
                                                            "legacy": {
                                                                "full_text": "Hello",
                                                                "created_at": "Wed Jan 01 12:00:00",
                                                                "conversation_id_str": "123",
                                                            },
                                                        }
                                                    }
                                                },
                                            },
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                }
            }
        }
    }

    mock_http_response = MagicMock()
    mock_http_response.json.return_value = mock_response
    mock_http_response.raise_for_status = MagicMock()

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "test", "ct0": "test", "twid": "u%3D12345"}
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
