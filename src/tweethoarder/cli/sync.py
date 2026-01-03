"""Sync commands for TweetHoarder CLI."""

from pathlib import Path
from typing import Any

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
from tweethoarder.query_ids.scraper import refresh_query_ids
from tweethoarder.query_ids.store import QueryIdStore, get_query_id_with_fallback
from tweethoarder.storage.checkpoint import SyncCheckpoint
from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

app = typer.Typer(
    name="sync",
    help="Sync Twitter/X data to local storage.",
)


async def sync_likes_async(db_path: Path, count: int | float) -> dict[str, Any]:
    """Sync liked tweets from Twitter to local database.

    Fetches the user's liked tweets from the Twitter API and saves them
    to the local SQLite database. Uses pagination to fetch multiple pages
    until the requested count is reached or all likes are synced.

    Args:
        db_path: Path to the SQLite database file.
        count: Maximum number of likes to sync. Use float('inf') for all.

    Returns:
        Dictionary with 'synced_count' key containing the number of
        tweets successfully synced.

    Raises:
        ValueError: If no cookies are found or user ID cannot be determined.
    """
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
    headers = client.get_base_headers()

    # Load checkpoint for resume capability
    checkpoint = SyncCheckpoint(db_path)
    saved_checkpoint = checkpoint.load("like")
    cursor: str | None = saved_checkpoint.cursor if saved_checkpoint else None
    last_tweet_id: str | None = None

    async with httpx.AsyncClient(headers=headers) as http_client:

        async def refresh_and_get_likes_id() -> str:
            """Refresh query IDs and return the new Likes ID."""
            new_ids: dict[str, str] = await refresh_query_ids(http_client, targets={"Likes"})
            store.save(new_ids)
            return new_ids["Likes"]

        while synced_count < count:
            response = await fetch_likes_page(
                http_client,
                query_id,
                user_id,
                cursor,
                on_query_id_refresh=refresh_and_get_likes_id,
            )
            tweets, cursor = parse_likes_response(response)

            if not tweets:
                break

            for raw_tweet in tweets:
                if synced_count >= count:
                    break
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data is None:
                    continue
                save_tweet(db_path, tweet_data)
                add_to_collection(db_path, tweet_data["id"], "like")
                last_tweet_id = tweet_data["id"]
                synced_count += 1

            # Save checkpoint after each page for resume capability
            if cursor and last_tweet_id:
                checkpoint.save("like", cursor=cursor, last_tweet_id=last_tweet_id)

            if not cursor:
                break

    # Clear checkpoint on successful completion
    checkpoint.clear("like")
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


async def sync_bookmarks_async(db_path: Path, count: float) -> dict[str, int]:
    """Sync bookmarks asynchronously."""
    from tweethoarder.client.timelines import (
        extract_tweet_data,
        fetch_bookmarks_page,
        parse_bookmarks_response,
    )
    from tweethoarder.query_ids.store import QueryIdStore
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    init_database(db_path)
    cookies = resolve_cookies()
    if not cookies:
        raise ValueError("No cookies found")

    client = TwitterClient(cookies)
    cache_path = get_config_dir() / "query-ids-cache.json"
    store = QueryIdStore(cache_path)
    query_id = store.get("Bookmarks")
    headers = client.get_base_headers()
    synced_count = 0

    async with httpx.AsyncClient(headers=headers) as http_client:
        response = await fetch_bookmarks_page(http_client, query_id)
        tweets, _ = parse_bookmarks_response(response)
        for raw_tweet in tweets:
            tweet_data = extract_tweet_data(raw_tweet)
            if tweet_data:
                save_tweet(db_path, tweet_data)
                add_to_collection(db_path, tweet_data["id"], "bookmark")
                synced_count += 1

    return {"synced_count": synced_count}


@app.command()
def bookmarks(
    count: int = typer.Option(100, "--count", "-c", help="Number of bookmarks to sync."),
    all_bookmarks: bool = typer.Option(False, "--all", help="Sync all bookmarks (ignore count)."),
) -> None:
    """Sync bookmarked tweets to local storage."""
    import asyncio

    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_bookmarks else count
    result = asyncio.run(sync_bookmarks_async(db_path, effective_count))
    typer.echo(f"Synced {result['synced_count']} bookmarks.")


@app.command()
def tweets() -> None:
    """Sync user's own tweets to local storage."""


@app.command()
def reposts() -> None:
    """Sync user's reposts (retweets) to local storage."""
