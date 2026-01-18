"""Tests for feed sync functionality."""

import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest


def test_sync_feed_async_function_exists() -> None:
    """sync_feed_async function should be importable."""
    from tweethoarder.cli.sync import sync_feed_async

    assert callable(sync_feed_async)


def test_sync_feed_async_accepts_db_path_and_hours() -> None:
    """sync_feed_async should accept db_path and hours parameters."""
    from tweethoarder.cli.sync import sync_feed_async

    sig = inspect.signature(sync_feed_async)
    params = list(sig.parameters.keys())

    assert "db_path" in params
    assert "hours" in params


@pytest.mark.asyncio
async def test_sync_feed_async_initializes_database(tmp_path: Path) -> None:
    """sync_feed_async should initialize the database before syncing."""
    from unittest.mock import patch

    from tweethoarder.cli.sync import sync_feed_async

    db_path = tmp_path / "test.db"

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = None

        with pytest.raises(ValueError, match="No cookies found"):
            await sync_feed_async(db_path=db_path, hours=24)

    assert db_path.exists()


@pytest.mark.asyncio
async def test_sync_feed_async_returns_synced_count(tmp_path: Path) -> None:
    """sync_feed_async should return a dict with synced_count."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_feed_async

    db_path = tmp_path / "test.db"

    mock_response = {
        "data": {
            "home": {
                "home_timeline_urt": {
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
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = AsyncMock(
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sync_feed_async(db_path=db_path, hours=24)

    assert isinstance(result, dict)
    assert "synced_count" in result


@pytest.mark.asyncio
async def test_sync_feed_async_syncs_tweets_within_time_window(tmp_path: Path) -> None:
    """sync_feed_async should sync tweets within the time window."""
    from datetime import datetime
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_feed_async

    db_path = tmp_path / "test.db"

    # Create a mock tweet from 1 hour ago (within 24h window)
    recent_time = datetime.now(UTC).strftime("%a %b %d %H:%M:%S %z %Y")
    mock_response = {
        "data": {
            "home": {
                "home_timeline_urt": {
                    "instructions": [
                        {
                            "type": "TimelineAddEntries",
                            "entries": [
                                {
                                    "entryId": "tweet-123",
                                    "sortIndex": "1234567890",
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
                                                                "core": {
                                                                    "screen_name": "testuser",
                                                                    "name": "Test User",
                                                                },
                                                            }
                                                        }
                                                    },
                                                    "legacy": {
                                                        "full_text": "Hello world",
                                                        "created_at": recent_time,
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

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "test", "ct0": "test"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = AsyncMock(
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sync_feed_async(db_path=db_path, hours=24)

    assert result["synced_count"] == 1


def test_feed_command_exists() -> None:
    """Feed CLI command should be importable from sync module."""
    from tweethoarder.cli.sync import feed

    assert callable(feed)


def test_feed_command_registered_with_app() -> None:
    """Feed command should be registered with the sync app."""
    from tweethoarder.cli.sync import app

    command_names = [cmd.callback.__name__ for cmd in app.registered_commands]
    assert "feed" in command_names


def test_feed_command_accepts_hours_option() -> None:
    """Feed command should accept --hours option."""
    from tweethoarder.cli.sync import feed

    sig = inspect.signature(feed)
    params = list(sig.parameters.keys())

    assert "hours" in params


def test_feed_command_calls_sync_feed_async() -> None:
    """Feed command should call sync_feed_async with correct parameters."""
    from unittest.mock import AsyncMock, patch

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_feed_async", new_callable=AsyncMock) as mock:
        mock.return_value = {"synced_count": 5}
        result = runner.invoke(app, ["feed", "--hours", "48"])

    assert result.exit_code == 0
    mock.assert_called_once()
    call_kwargs = mock.call_args.kwargs
    assert call_kwargs["hours"] == 48


@pytest.mark.asyncio
async def test_sync_feed_async_passes_refresh_callback(tmp_path: Path) -> None:
    """Sync_feed_async should pass on_query_id_refresh callback to fetch function."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_feed_async

    db_path = tmp_path / "test.db"

    mock_response = {
        "data": {
            "home": {
                "home_timeline_urt": {
                    "instructions": [{"type": "TimelineAddEntries", "entries": []}]
                }
            }
        }
    }

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "test", "ct0": "test"}
        with patch(
            "tweethoarder.client.timelines.fetch_home_timeline_page", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_response

            await sync_feed_async(db_path=db_path, hours=24)

            # Verify on_query_id_refresh was passed
            call_kwargs = mock_fetch.call_args.kwargs
            assert "on_query_id_refresh" in call_kwargs
            assert callable(call_kwargs["on_query_id_refresh"])


@pytest.mark.asyncio
async def test_sync_feed_async_saves_sort_index(tmp_path: Path) -> None:
    """sync_feed_async should save sort_index for correct ordering."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_feed_async
    from tweethoarder.storage.database import get_tweets_by_collection

    db_path = tmp_path / "test.db"

    recent_time = datetime.now(UTC).strftime("%a %b %d %H:%M:%S %z %Y")
    mock_response = {
        "data": {
            "home": {
                "home_timeline_urt": {
                    "instructions": [
                        {
                            "type": "TimelineAddEntries",
                            "entries": [
                                {
                                    "entryId": "tweet-111",
                                    "sortIndex": "1000",
                                    "content": {
                                        "entryType": "TimelineTimelineItem",
                                        "itemContent": {
                                            "tweet_results": {
                                                "result": {
                                                    "rest_id": "111",
                                                    "core": {
                                                        "user_results": {
                                                            "result": {
                                                                "rest_id": "456",
                                                                "core": {
                                                                    "screen_name": "user1",
                                                                    "name": "User One",
                                                                },
                                                            }
                                                        }
                                                    },
                                                    "legacy": {
                                                        "full_text": "First tweet",
                                                        "created_at": recent_time,
                                                        "conversation_id_str": "111",
                                                    },
                                                }
                                            }
                                        },
                                    },
                                },
                                {
                                    "entryId": "tweet-222",
                                    "sortIndex": "2000",
                                    "content": {
                                        "entryType": "TimelineTimelineItem",
                                        "itemContent": {
                                            "tweet_results": {
                                                "result": {
                                                    "rest_id": "222",
                                                    "core": {
                                                        "user_results": {
                                                            "result": {
                                                                "rest_id": "789",
                                                                "core": {
                                                                    "screen_name": "user2",
                                                                    "name": "User Two",
                                                                },
                                                            }
                                                        }
                                                    },
                                                    "legacy": {
                                                        "full_text": "Second tweet",
                                                        "created_at": recent_time,
                                                        "conversation_id_str": "222",
                                                    },
                                                }
                                            }
                                        },
                                    },
                                },
                            ],
                        }
                    ]
                }
            }
        }
    }

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "test", "ct0": "test"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = AsyncMock(
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await sync_feed_async(db_path=db_path, hours=24)

    # Get tweets - should be ordered by sort_index DESC (2000 first, 1000 second)
    tweets = get_tweets_by_collection(db_path, "feed")
    assert len(tweets) == 2
    assert tweets[0]["id"] == "222"  # Higher sort_index = newer = first
    assert tweets[1]["id"] == "111"  # Lower sort_index = older = second

    # Verify sort_index is actually saved in the database
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT tweet_id, sort_index FROM collections WHERE collection_type = 'feed'"
        )
        rows = {row["tweet_id"]: row["sort_index"] for row in cursor.fetchall()}

    assert rows["111"] == "1000"
    assert rows["222"] == "2000"


def test_sync_feed_async_accepts_full_parameter() -> None:
    """sync_feed_async should accept full parameter for forcing complete resync."""
    from tweethoarder.cli.sync import sync_feed_async

    sig = inspect.signature(sync_feed_async)
    params = list(sig.parameters.keys())

    assert "full" in params


def _make_feed_entry(tweet_id: str, text: str = "Hello") -> dict:
    """Create a mock feed entry for testing."""
    recent_time = datetime.now(UTC).strftime("%a %b %d %H:%M:%S %z %Y")
    return {
        "entryId": f"tweet-{tweet_id}",
        "sortIndex": tweet_id,
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
                                    "core": {
                                        "screen_name": "testuser",
                                        "name": "Test User",
                                    },
                                }
                            }
                        },
                        "legacy": {
                            "full_text": text,
                            "created_at": recent_time,
                            "conversation_id_str": tweet_id,
                        },
                    }
                }
            },
        },
    }


def _make_feed_response(entries: list) -> dict:
    """Create a mock home timeline API response."""
    return {
        "data": {
            "home": {
                "home_timeline_urt": {
                    "instructions": [{"type": "TimelineAddEntries", "entries": entries}]
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_sync_feed_async_stops_on_duplicate(tmp_path: Path) -> None:
    """sync_feed_async should stop when encountering an existing tweet in the collection."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_feed_async
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Pre-populate with an existing tweet in the feed collection
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
    add_to_collection(db_path, "existing", "feed")

    # API returns: new_tweet, then existing_tweet
    mock_response = _make_feed_response(
        [
            _make_feed_entry("new_tweet", "New tweet"),
            _make_feed_entry("existing", "Already synced"),
        ]
    )

    with patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies:
        mock_cookies.return_value = {"auth_token": "test", "ct0": "test"}
        with patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = AsyncMock(
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await sync_feed_async(db_path, hours=24)

    # Should only sync the new tweet, stop when hitting existing
    assert result["synced_count"] == 1


def test_feed_command_accepts_full_flag() -> None:
    """Feed CLI command should accept --full flag."""
    import re

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["feed", "--help"])

    # Strip ANSI escape codes for reliable matching
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--full" in clean_output
