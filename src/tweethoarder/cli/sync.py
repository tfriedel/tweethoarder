"""Sync commands for TweetHoarder CLI."""

from pathlib import Path

import httpx
import typer

from tweethoarder.auth.cookies import resolve_cookies
from tweethoarder.client.base import TwitterClient
from tweethoarder.client.timelines import (
    extract_tweet_data,
    fetch_likes_page,
    parse_likes_response,
)
from tweethoarder.config import get_config_dir
from tweethoarder.query_ids.store import QueryIdStore, get_query_id_with_fallback
from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

app = typer.Typer(
    name="sync",
    help="Sync Twitter/X data to local storage.",
)


async def sync_likes_async(db_path: Path, count: int | float) -> dict:
    """Async implementation of likes sync."""
    init_database(db_path)

    cookies = resolve_cookies()
    if not cookies:
        raise ValueError("No cookies found. Please log in to Twitter in your browser.")

    client = TwitterClient(cookies=cookies)
    cache_path = get_config_dir() / "query-ids-cache.json"
    store = QueryIdStore(cache_path)
    query_id = get_query_id_with_fallback(store, "Likes")

    user_id = cookies.get("twid", "").replace("u%3D", "")
    if not user_id:
        raise ValueError("Could not determine user ID from cookies")

    synced_count = 0

    async with httpx.AsyncClient() as http_client:
        http_client.headers.update(client.get_base_headers())
        response = await fetch_likes_page(http_client, query_id, user_id)
        tweets, _cursor = parse_likes_response(response)

        for raw_tweet in tweets:
            if synced_count >= count:
                break
            tweet_data = extract_tweet_data(raw_tweet)
            save_tweet(db_path, tweet_data)
            add_to_collection(db_path, tweet_data["id"], "like")
            synced_count += 1

    return {"synced_count": synced_count}


@app.command()
def likes(
    count: int = typer.Option(100, "--count", "-c", help="Number of likes to sync."),
    all_likes: bool = typer.Option(False, "--all", help="Sync all likes (ignore count)."),
) -> None:
    """Sync liked tweets to local storage."""
    import asyncio

    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_likes else count
    result = asyncio.run(sync_likes_async(db_path, effective_count))
    typer.echo(f"Synced {result['synced_count']} likes.")


@app.command()
def bookmarks() -> None:
    """Sync bookmarked tweets to local storage."""


@app.command()
def tweets() -> None:
    """Sync user's own tweets to local storage."""


@app.command()
def reposts() -> None:
    """Sync user's reposts (retweets) to local storage."""
