"""Tests for Twitter timelines client (likes, bookmarks)."""

import pytest


def test_build_bookmarks_url_includes_query_id() -> None:
    """build_bookmarks_url should include the Bookmarks query ID in the path."""
    from tweethoarder.client.timelines import build_bookmarks_url

    url = build_bookmarks_url(query_id="BOOK123")

    assert "BOOK123" in url
    assert "/graphql/" in url


def test_build_bookmarks_url_includes_features() -> None:
    """build_bookmarks_url should include features query param."""
    from tweethoarder.client.timelines import build_bookmarks_url

    url = build_bookmarks_url(query_id="BOOK123")

    assert "features" in url


def test_build_bookmarks_url_includes_variables() -> None:
    """build_bookmarks_url should include variables query param."""
    from tweethoarder.client.timelines import build_bookmarks_url

    url = build_bookmarks_url(query_id="BOOK123")

    assert "variables" in url


def test_build_bookmarks_url_includes_cursor_when_provided() -> None:
    """build_bookmarks_url should include cursor for pagination when provided."""
    from tweethoarder.client.timelines import build_bookmarks_url

    url = build_bookmarks_url(query_id="BOOK123", cursor="cursor_xyz")

    assert "cursor_xyz" in url


def test_fetch_bookmarks_page_exists() -> None:
    """fetch_bookmarks_page function should be importable."""
    from tweethoarder.client.timelines import fetch_bookmarks_page

    assert callable(fetch_bookmarks_page)


def test_fetch_bookmarks_page_accepts_required_params() -> None:
    """fetch_bookmarks_page should accept client and query_id parameters."""
    import inspect

    from tweethoarder.client.timelines import fetch_bookmarks_page

    sig = inspect.signature(fetch_bookmarks_page)
    params = list(sig.parameters.keys())

    assert "client" in params
    assert "query_id" in params


@pytest.mark.asyncio
async def test_fetch_bookmarks_page_returns_dict() -> None:
    """fetch_bookmarks_page should return parsed JSON response."""
    from unittest.mock import AsyncMock, MagicMock

    from tweethoarder.client.timelines import fetch_bookmarks_page

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"bookmark_timeline_v2": {}}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = await fetch_bookmarks_page(
        client=mock_client,
        query_id="BOOK123",
    )

    assert isinstance(result, dict)
    assert "data" in result


def test_parse_bookmarks_response_extracts_tweets() -> None:
    """parse_bookmarks_response should extract tweet entries from API response."""
    from tweethoarder.client.timelines import parse_bookmarks_response

    response = {
        "data": {
            "bookmark_timeline_v2": {
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
                                                    "legacy": {"full_text": "Hello"},
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

    tweets, _cursor = parse_bookmarks_response(response)

    assert len(tweets) == 1
    assert tweets[0]["rest_id"] == "123"


def test_fetch_bookmarks_page_accepts_cursor_param() -> None:
    """fetch_bookmarks_page should accept optional cursor parameter."""
    import inspect

    from tweethoarder.client.timelines import fetch_bookmarks_page

    sig = inspect.signature(fetch_bookmarks_page)
    params = list(sig.parameters.keys())

    assert "cursor" in params


def test_build_likes_url_includes_query_id() -> None:
    """build_likes_url should include the Likes query ID in the path."""
    from tweethoarder.client.timelines import build_likes_url

    url = build_likes_url(query_id="ABC123", user_id="12345")

    assert "ABC123" in url
    assert "/graphql/" in url


def test_build_likes_url_includes_user_id_in_variables() -> None:
    """build_likes_url should include user_id in the variables query param."""
    from tweethoarder.client.timelines import build_likes_url

    url = build_likes_url(query_id="ABC123", user_id="12345")

    assert "userId" in url
    assert "12345" in url


def test_build_likes_url_includes_cursor_when_provided() -> None:
    """build_likes_url should include cursor for pagination when provided."""
    from tweethoarder.client.timelines import build_likes_url

    url = build_likes_url(query_id="ABC123", user_id="12345", cursor="cursor_abc")

    assert "cursor_abc" in url


def test_build_likes_url_includes_features() -> None:
    """build_likes_url should include features query param."""
    from tweethoarder.client.timelines import build_likes_url

    url = build_likes_url(query_id="ABC123", user_id="12345")

    assert "features" in url


def test_build_likes_url_includes_required_variables() -> None:
    """build_likes_url should include all required variables for the API."""
    from tweethoarder.client.timelines import build_likes_url

    url = build_likes_url(query_id="ABC123", user_id="12345")

    # These variables are required by Twitter's API (from bird reference implementation)
    assert "includePromotedContent" in url
    assert "withClientEventToken" in url
    assert "withBirdwatchNotes" in url
    assert "withVoice" in url


def test_fetch_likes_page_exists() -> None:
    """fetch_likes_page function should be importable."""
    from tweethoarder.client.timelines import fetch_likes_page

    assert callable(fetch_likes_page)


def test_fetch_likes_page_accepts_required_params() -> None:
    """fetch_likes_page should accept client, query_id, and user_id parameters."""
    import inspect

    from tweethoarder.client.timelines import fetch_likes_page

    sig = inspect.signature(fetch_likes_page)
    params = list(sig.parameters.keys())

    assert "client" in params
    assert "query_id" in params
    assert "user_id" in params


@pytest.mark.asyncio
async def test_fetch_likes_page_returns_dict() -> None:
    """fetch_likes_page should return parsed JSON response."""
    from unittest.mock import AsyncMock, MagicMock

    from tweethoarder.client.timelines import fetch_likes_page

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"user": {"result": {}}}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = await fetch_likes_page(
        client=mock_client,
        query_id="ABC123",
        user_id="12345",
    )

    assert isinstance(result, dict)
    assert "data" in result


def test_parse_likes_response_extracts_tweets() -> None:
    """parse_likes_response should extract tweet entries from API response."""
    from tweethoarder.client.timelines import parse_likes_response

    # Current Twitter API response format uses 'timeline' not 'timeline_v2'
    response = {
        "data": {
            "user": {
                "result": {
                    "timeline": {
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
                                                            "legacy": {"full_text": "Hello"},
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

    tweets, _cursor = parse_likes_response(response)

    assert len(tweets) == 1
    assert tweets[0]["rest_id"] == "123"


def test_parse_likes_response_extracts_cursor() -> None:
    """parse_likes_response should extract the next cursor for pagination."""
    from tweethoarder.client.timelines import parse_likes_response

    # Current Twitter API response format uses 'timeline' not 'timeline_v2'
    response = {
        "data": {
            "user": {
                "result": {
                    "timeline": {
                        "timeline": {
                            "instructions": [
                                {
                                    "type": "TimelineAddEntries",
                                    "entries": [
                                        {
                                            "entryId": "cursor-bottom-12345",
                                            "content": {
                                                "entryType": "TimelineTimelineCursor",
                                                "value": "next_cursor_value",
                                                "cursorType": "Bottom",
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

    _tweets, cursor = parse_likes_response(response)

    assert cursor == "next_cursor_value"


def test_extract_tweet_data_returns_db_format() -> None:
    """extract_tweet_data should convert raw tweet to database format."""
    from tweethoarder.client.timelines import extract_tweet_data

    # Current Twitter API response format has screen_name in user_result.core
    raw_tweet = {
        "rest_id": "123456789",
        "core": {
            "user_results": {
                "result": {
                    "rest_id": "987654321",
                    "core": {
                        "screen_name": "testuser",
                        "name": "Test User",
                    },
                }
            }
        },
        "legacy": {
            "full_text": "Hello, world!",
            "created_at": "Wed Jan 01 12:00:00 +0000 2025",
            "conversation_id_str": "123456789",
            "reply_count": 5,
            "retweet_count": 10,
            "favorite_count": 20,
            "quote_count": 2,
        },
    }

    result = extract_tweet_data(raw_tweet)

    assert result["id"] == "123456789"
    assert result["text"] == "Hello, world!"
    assert result["author_id"] == "987654321"
    assert result["author_username"] == "testuser"


def test_extract_tweet_data_converts_date_to_iso8601() -> None:
    """extract_tweet_data should convert Twitter date format to ISO 8601."""
    from tweethoarder.client.timelines import extract_tweet_data

    # Current Twitter API response format has screen_name in user_result.core
    raw_tweet = {
        "rest_id": "123",
        "core": {
            "user_results": {
                "result": {
                    "rest_id": "456",
                    "core": {"screen_name": "user", "name": "User"},
                }
            }
        },
        "legacy": {
            "full_text": "Hello",
            "created_at": "Wed Jan 01 12:00:00 +0000 2025",
            "conversation_id_str": "123",
        },
    }

    result = extract_tweet_data(raw_tweet)

    assert result["created_at"] == "2025-01-01T12:00:00+00:00"


@pytest.mark.asyncio
async def test_fetch_likes_page_retries_on_rate_limit() -> None:
    """fetch_likes_page should retry with backoff on 429 rate limit."""
    from unittest.mock import AsyncMock, MagicMock, patch

    import httpx

    from tweethoarder.client.timelines import fetch_likes_page

    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Rate limited", request=MagicMock(), response=rate_limit_response
    )

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {"data": {"user": {"result": {}}}}
    success_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.side_effect = [rate_limit_response, success_response]

    with patch("tweethoarder.client.timelines.asyncio.sleep", new_callable=AsyncMock):
        result = await fetch_likes_page(
            client=mock_client,
            query_id="ABC123",
            user_id="12345",
        )

    assert mock_client.get.call_count == 2
    assert "data" in result


def test_extract_tweet_data_returns_none_for_missing_required_fields() -> None:
    """extract_tweet_data should return None when required fields are missing."""
    from typing import Any

    from tweethoarder.client.timelines import extract_tweet_data

    incomplete_tweet: dict[str, Any] = {
        "rest_id": None,
        "core": {},
        "legacy": {},
    }

    result = extract_tweet_data(incomplete_tweet)

    assert result is None


@pytest.mark.asyncio
async def test_fetch_likes_page_raises_after_max_retries_exhausted() -> None:
    """fetch_likes_page should raise HTTPStatusError after all retries exhausted."""
    from unittest.mock import AsyncMock, MagicMock, patch

    import httpx

    from tweethoarder.client.timelines import fetch_likes_page

    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Rate limited", request=MagicMock(), response=rate_limit_response
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = rate_limit_response

    with (
        patch("tweethoarder.client.timelines.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await fetch_likes_page(
            client=mock_client,
            query_id="ABC123",
            user_id="12345",
            max_retries=3,
        )

    assert mock_client.get.call_count == 3


@pytest.mark.asyncio
async def test_fetch_likes_page_calls_refresh_callback_on_404() -> None:
    """fetch_likes_page should call on_query_id_refresh callback on 404."""
    from unittest.mock import AsyncMock, MagicMock

    import httpx

    from tweethoarder.client.timelines import fetch_likes_page

    not_found_response = MagicMock()
    not_found_response.status_code = 404
    not_found_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not found", request=MagicMock(), response=not_found_response
    )

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {"data": {"user": {"result": {}}}}
    success_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.side_effect = [not_found_response, success_response]

    refresh_callback = AsyncMock(return_value="NEW_QUERY_ID")

    result = await fetch_likes_page(
        client=mock_client,
        query_id="OLD_QUERY_ID",
        user_id="12345",
        on_query_id_refresh=refresh_callback,
    )

    refresh_callback.assert_called_once()
    assert mock_client.get.call_count == 2
    assert "data" in result


@pytest.mark.asyncio
async def test_fetch_likes_page_retries_after_404_refresh_on_last_attempt() -> None:
    """fetch_likes_page should retry with new query ID even if 404 happens on last attempt."""
    from unittest.mock import AsyncMock, MagicMock

    import httpx

    from tweethoarder.client.timelines import fetch_likes_page

    not_found_response = MagicMock()
    not_found_response.status_code = 404
    not_found_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not found", request=MagicMock(), response=not_found_response
    )

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {"data": {"user": {"result": {}}}}
    success_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    # Only 1 retry allowed, 404 on that attempt triggers refresh, then success
    mock_client.get.side_effect = [
        not_found_response,  # Attempt 0 (only attempt with max_retries=1)
        success_response,  # Retry with refreshed query ID should still work
    ]

    refresh_callback = AsyncMock(return_value="NEW_QUERY_ID")

    result = await fetch_likes_page(
        client=mock_client,
        query_id="OLD_QUERY_ID",
        user_id="12345",
        max_retries=1,  # Only 1 attempt allowed
        on_query_id_refresh=refresh_callback,
    )

    refresh_callback.assert_called_once()
    assert mock_client.get.call_count == 2  # 1 attempt + 1 retry after refresh
    assert "data" in result
