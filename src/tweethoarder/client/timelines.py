"""Twitter timelines client for likes and bookmarks."""

import json
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from tweethoarder.client.features import build_likes_features
from tweethoarder.query_ids.constants import TWITTER_API_BASE

if TYPE_CHECKING:
    import httpx


def build_likes_url(query_id: str, user_id: str, cursor: str | None = None) -> str:
    """Build URL for fetching likes."""
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
) -> dict:
    """Fetch a page of likes from the Twitter API."""
    url = build_likes_url(query_id, user_id, cursor)
    response = await client.get(url)
    response.raise_for_status()
    result: dict = response.json()
    return result


def parse_likes_response(response: dict) -> tuple[list[dict], str | None]:
    """Parse likes API response and extract tweets and next cursor."""
    tweets: list[dict] = []
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


def extract_tweet_data(raw_tweet: dict) -> dict:
    """Extract and convert raw tweet data to database format."""
    legacy = raw_tweet.get("legacy", {})
    user_result = raw_tweet.get("core", {}).get("user_results", {}).get("result", {})
    user_legacy = user_result.get("legacy", {})

    return {
        "id": raw_tweet.get("rest_id"),
        "text": legacy.get("full_text"),
        "author_id": user_result.get("rest_id"),
        "author_username": user_legacy.get("screen_name"),
        "author_display_name": user_legacy.get("name"),
        "created_at": legacy.get("created_at"),
        "conversation_id": legacy.get("conversation_id_str"),
        "reply_count": legacy.get("reply_count", 0),
        "retweet_count": legacy.get("retweet_count", 0),
        "like_count": legacy.get("favorite_count", 0),
        "quote_count": legacy.get("quote_count", 0),
    }
