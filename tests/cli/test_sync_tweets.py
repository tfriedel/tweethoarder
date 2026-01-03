"""Tests for user tweets sync functionality."""

from pathlib import Path

import pytest


def test_sync_tweets_async_function_exists() -> None:
    """sync_tweets_async function should be importable."""
    from tweethoarder.cli.sync import sync_tweets_async

    assert callable(sync_tweets_async)


def test_build_user_tweets_url_includes_query_id() -> None:
    """build_user_tweets_url should include the query ID in the path."""
    from tweethoarder.client.timelines import build_user_tweets_url

    url = build_user_tweets_url(query_id="ABC123", user_id="12345")

    assert "ABC123" in url
    assert "/graphql/" in url


def test_build_user_tweets_url_includes_user_id() -> None:
    """build_user_tweets_url should include user_id in variables."""
    from tweethoarder.client.timelines import build_user_tweets_url

    url = build_user_tweets_url(query_id="ABC123", user_id="12345")

    assert "userId" in url
    assert "12345" in url


def test_build_user_tweets_url_includes_cursor() -> None:
    """build_user_tweets_url should include cursor when provided."""
    from tweethoarder.client.timelines import build_user_tweets_url

    url = build_user_tweets_url(query_id="ABC123", user_id="12345", cursor="cursor_xyz")

    assert "cursor_xyz" in url


def test_fetch_user_tweets_page_exists() -> None:
    """fetch_user_tweets_page function should be importable."""
    from tweethoarder.client.timelines import fetch_user_tweets_page

    assert callable(fetch_user_tweets_page)


@pytest.mark.asyncio
async def test_fetch_user_tweets_page_returns_dict() -> None:
    """fetch_user_tweets_page should return parsed JSON response."""
    from unittest.mock import AsyncMock, MagicMock

    from tweethoarder.client.timelines import fetch_user_tweets_page

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"user": {"result": {}}}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = await fetch_user_tweets_page(
        client=mock_client,
        query_id="ABC123",
        user_id="12345",
    )

    assert isinstance(result, dict)
    assert "data" in result


@pytest.mark.asyncio
async def test_fetch_user_tweets_page_calls_client_get() -> None:
    """fetch_user_tweets_page should call client.get with the URL."""
    from unittest.mock import AsyncMock, MagicMock

    from tweethoarder.client.timelines import fetch_user_tweets_page

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    await fetch_user_tweets_page(
        client=mock_client,
        query_id="ABC123",
        user_id="12345",
    )

    mock_client.get.assert_called_once()
    call_url = mock_client.get.call_args[0][0]
    assert "ABC123" in call_url
    assert "12345" in call_url


def test_parse_user_tweets_response_exists() -> None:
    """parse_user_tweets_response function should be importable."""
    from tweethoarder.client.timelines import parse_user_tweets_response

    assert callable(parse_user_tweets_response)


def test_parse_user_tweets_response_extracts_tweets() -> None:
    """parse_user_tweets_response should extract tweets from response."""
    from tweethoarder.client.timelines import parse_user_tweets_response

    response = {
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
                                                "itemContent": {
                                                    "tweet_results": {"result": {"rest_id": "123"}}
                                                }
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

    tweets, _cursor = parse_user_tweets_response(response)

    assert len(tweets) == 1
    assert tweets[0]["rest_id"] == "123"


@pytest.mark.asyncio
async def test_sync_tweets_async_syncs_tweets(tmp_path: Path) -> None:
    """sync_tweets_async should sync tweets to database."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_tweets_async

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
                                                "itemContent": {
                                                    "tweet_results": {
                                                        "result": {
                                                            "rest_id": "123",
                                                            "legacy": {
                                                                "full_text": "Hello world",
                                                                "created_at": "Wed Jan 01 12:00:00 +0000 2025",  # noqa: E501
                                                                "conversation_id_str": "123",
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
                                                                            "screen_name": "testuser",  # noqa: E501
                                                                            "name": "Test User",
                                                                        },
                                                                    }
                                                                }
                                                            },
                                                        }
                                                    }
                                                }
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

        result = await sync_tweets_async(db_path, count=10)

        assert result["synced_count"] == 1


def test_tweets_command_accepts_count_option() -> None:
    """Tweets command should accept a --count option."""
    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["tweets", "--help"])

    assert "--count" in result.output or "-c" in result.output


def test_tweets_command_accepts_all_flag() -> None:
    """Tweets command should accept an --all flag."""
    import re

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["tweets", "--help"])

    # Strip ANSI escape codes for reliable matching
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--all" in clean_output


def test_tweets_command_calls_sync_tweets_async() -> None:
    """Tweets command should call sync_tweets_async."""
    from unittest.mock import AsyncMock, patch

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_tweets_async", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        result = runner.invoke(app, ["tweets", "--count", "10"])

        mock_sync.assert_called_once()
        assert "5" in result.output
