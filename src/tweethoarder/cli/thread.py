"""Thread fetching functionality for TweetHoarder CLI."""

import asyncio
from pathlib import Path
from typing import Any

import httpx

from tweethoarder.auth.cookies import resolve_cookies
from tweethoarder.client.base import TwitterClient
from tweethoarder.config import get_config_dir
from tweethoarder.query_ids.store import get_query_id_with_fallback


async def fetch_tweet_detail_with_retry(
    http_client: httpx.AsyncClient,
    query_id: str,
    tweet_id: str,
    max_retries: int = 5,
    base_delay: float = 2.0,
) -> dict[str, Any]:
    """Fetch tweet detail with retry on rate limit."""
    from tweethoarder.client.timelines import fetch_tweet_detail_page

    for attempt in range(max_retries):
        try:
            result: dict[str, Any] = await fetch_tweet_detail_page(http_client, query_id, tweet_id)
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                await asyncio.sleep(delay)
                continue
            raise
    raise RuntimeError("Unreachable: retry loop should always return or raise")


async def fetch_thread_async(
    db_path: Path,
    tweet_id: str,
    mode: str = "thread",
    limit: int = 200,
) -> dict[str, int]:
    """Fetch thread for a tweet."""
    from tweethoarder.client.timelines import (
        extract_quoted_tweet,
        extract_tweet_data,
        filter_tweets_by_mode,
        get_focal_tweet_author_id,
        parse_tweet_detail_response,
    )
    from tweethoarder.query_ids.store import QueryIdStore
    from tweethoarder.storage.database import save_tweet

    cookies = resolve_cookies()
    client = TwitterClient(cookies=cookies)
    cache_path = get_config_dir() / "query-ids-cache.json"
    store = QueryIdStore(cache_path)
    query_id = get_query_id_with_fallback(store, "TweetDetail")

    headers = client.get_base_headers()
    tweet_count = 0

    async with httpx.AsyncClient(headers=headers) as http_client:
        response = await fetch_tweet_detail_with_retry(http_client, query_id, tweet_id)
        tweets = parse_tweet_detail_response(response)
        author_id = get_focal_tweet_author_id(response, tweet_id)
        tweets = filter_tweets_by_mode(tweets, mode, author_id)

        for raw_tweet in tweets:
            tweet_data = extract_tweet_data(raw_tweet)
            if tweet_data:
                save_tweet(db_path, tweet_data)
                # Also save the quoted tweet if present
                quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                if quoted_tweet_data:
                    save_tweet(db_path, quoted_tweet_data)
                tweet_count += 1

    return {"tweet_count": tweet_count}
