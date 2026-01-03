"""Twitter timelines client for likes and bookmarks."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from tweethoarder.client.features import build_likes_features
from tweethoarder.query_ids.constants import TWITTER_API_BASE

if TYPE_CHECKING:
    import httpx

TWITTER_DATE_FORMAT = "%a %b %d %H:%M:%S %z %Y"


def build_likes_url(query_id: str, user_id: str, cursor: str | None = None) -> str:
    """Build URL for fetching likes from Twitter GraphQL API.

    Args:
        query_id: The GraphQL query ID for the Likes endpoint.
        user_id: The Twitter user ID whose likes to fetch.
        cursor: Optional pagination cursor for fetching subsequent pages.

    Returns:
        The complete URL for the GraphQL request.
    """
    variables: dict[str, str | int] = {"userId": user_id, "count": 20}
    if cursor:
        variables["cursor"] = cursor
    features = build_likes_features()
    params = urlencode(
        {
            "variables": json.dumps(variables),
            "features": json.dumps(features),
        }
    )
    return f"{TWITTER_API_BASE}/{query_id}/Likes?{params}"


async def fetch_likes_page(
    client: "httpx.AsyncClient",
    query_id: str,
    user_id: str,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Fetch a page of likes from the Twitter API.

    Args:
        client: The httpx async client with authentication headers.
        query_id: The GraphQL query ID for the Likes endpoint.
        user_id: The Twitter user ID whose likes to fetch.
        cursor: Optional pagination cursor for fetching subsequent pages.

    Returns:
        The parsed JSON response from the API.

    Raises:
        httpx.HTTPStatusError: If the API request fails.
    """
    url = build_likes_url(query_id, user_id, cursor)
    response = await client.get(url)
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result


def parse_likes_response(
    response: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    """Parse likes API response and extract tweets and next cursor.

    Args:
        response: The raw JSON response from the Twitter API.

    Returns:
        A tuple of (tweets, cursor) where tweets is a list of raw tweet
        dictionaries and cursor is the pagination cursor for the next page,
        or None if there are no more pages.
    """
    tweets: list[dict[str, Any]] = []
    cursor: str | None = None

    timeline = (
        response.get("data", {})
        .get("user", {})
        .get("result", {})
        .get("timeline_v2", {})
        .get("timeline", {})
    )

    for instruction in timeline.get("instructions", []):
        if instruction.get("type") != "TimelineAddEntries":
            continue
        for entry in instruction.get("entries", []):
            entry_id = entry.get("entryId", "")
            content = entry.get("content", {})

            if entry_id.startswith("tweet-"):
                item_content = content.get("itemContent", {})
                tweet_result = item_content.get("tweet_results", {}).get("result")
                if tweet_result:
                    tweets.append(tweet_result)
            elif entry_id.startswith("cursor-bottom-"):
                cursor = content.get("value")

    return tweets, cursor


def _convert_twitter_date_to_iso8601(twitter_date: str | None) -> str | None:
    """Convert Twitter date format to ISO 8601.

    Args:
        twitter_date: Date string in Twitter format (e.g., "Wed Jan 01 12:00:00 +0000 2025").

    Returns:
        ISO 8601 formatted date string, or None if input is None.
    """
    if not twitter_date:
        return None
    parsed = datetime.strptime(twitter_date, TWITTER_DATE_FORMAT)
    return parsed.isoformat()


def extract_tweet_data(raw_tweet: dict[str, Any]) -> dict[str, Any]:
    """Extract and convert raw tweet data to database format.

    Args:
        raw_tweet: Raw tweet dictionary from the Twitter API response.

    Returns:
        Dictionary with normalized tweet data ready for database storage,
        including id, text, author info, timestamps, and engagement counts.
    """
    legacy = raw_tweet.get("legacy", {})
    user_result = raw_tweet.get("core", {}).get("user_results", {}).get("result", {})
    user_legacy = user_result.get("legacy", {})

    return {
        "id": raw_tweet.get("rest_id"),
        "text": legacy.get("full_text"),
        "author_id": user_result.get("rest_id"),
        "author_username": user_legacy.get("screen_name"),
        "author_display_name": user_legacy.get("name"),
        "created_at": _convert_twitter_date_to_iso8601(legacy.get("created_at")),
        "conversation_id": legacy.get("conversation_id_str"),
        "reply_count": legacy.get("reply_count", 0),
        "retweet_count": legacy.get("retweet_count", 0),
        "like_count": legacy.get("favorite_count", 0),
        "quote_count": legacy.get("quote_count", 0),
    }
