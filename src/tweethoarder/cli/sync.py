"""Sync commands for TweetHoarder CLI."""

import json
from pathlib import Path
from typing import Any

import httpx
import typer

from tweethoarder.auth.cookies import resolve_cookies
from tweethoarder.cli.thread import fetch_thread_async
from tweethoarder.client.base import TwitterClient
from tweethoarder.client.timelines import (
    extract_quoted_tweet,
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


async def sync_likes_async(
    db_path: Path,
    count: int | float,
    with_threads: bool = False,
    thread_mode: str = "thread",
    store_raw: bool = False,
) -> dict[str, Any]:
    """Sync liked tweets from Twitter to local database.

    Fetches the user's liked tweets from the Twitter API and saves them
    to the local SQLite database. Uses pagination to fetch multiple pages
    until the requested count is reached or all likes are synced.

    Args:
        db_path: Path to the SQLite database file.
        count: Maximum number of likes to sync. Use float('inf') for all.
        with_threads: If True, fetch thread context for synced tweets.
        thread_mode: Mode for thread fetching ('thread' or 'conversation').
        store_raw: If True, store raw API response JSON in the database.

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
    synced_tweet_ids: list[str] = []

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
            entries, cursor = parse_likes_response(response)

            if not entries:
                break

            for entry in entries:
                if synced_count >= count:
                    break
                raw_tweet = entry["tweet"]
                sort_index = entry.get("sort_index")
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data is None:
                    continue
                if store_raw:
                    tweet_data["raw_json"] = json.dumps(raw_tweet)
                save_tweet(db_path, tweet_data)
                # Also save the quoted tweet if present
                quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                if quoted_tweet_data:
                    save_tweet(db_path, quoted_tweet_data)
                add_to_collection(db_path, tweet_data["id"], "like", sort_index=sort_index)
                last_tweet_id = tweet_data["id"]
                synced_tweet_ids.append(tweet_data["id"])
                synced_count += 1

            # Save checkpoint after each page for resume capability
            if cursor and last_tweet_id:
                checkpoint.save("like", cursor=cursor, last_tweet_id=last_tweet_id)

            if not cursor:
                break

    # Clear checkpoint on successful completion
    checkpoint.clear("like")

    # Fetch threads for all synced tweets if enabled
    if with_threads:
        for tweet_id in synced_tweet_ids:
            await fetch_thread_async(db_path=db_path, tweet_id=tweet_id, mode=thread_mode)

    return {"synced_count": synced_count}


@app.command()
def likes(
    count: int = typer.Option(100, "--count", "-c", help="Number of likes to sync."),
    all_likes: bool = typer.Option(False, "--all", help="Sync all likes (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(False, "--store-raw", help="Store raw API response JSON."),
) -> None:
    """Sync liked tweets to local storage."""
    import asyncio

    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_likes else count
    result = asyncio.run(
        sync_likes_async(
            db_path,
            effective_count,
            with_threads=with_threads,
            thread_mode=thread_mode,
            store_raw=store_raw,
        )
    )
    typer.echo(f"Synced {result['synced_count']} likes.")


async def sync_bookmarks_async(
    db_path: Path,
    count: float,
    with_threads: bool = False,
    thread_mode: str = "thread",
    store_raw: bool = False,
) -> dict[str, int]:
    """Sync bookmarks asynchronously."""
    from tweethoarder.client.timelines import (
        extract_quoted_tweet,
        extract_tweet_data,
        fetch_bookmarks_page,
        parse_bookmarks_response,
    )
    from tweethoarder.query_ids.store import QueryIdStore, get_query_id_with_fallback
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    init_database(db_path)
    cookies = resolve_cookies()
    if not cookies:
        raise ValueError("No cookies found")

    client = TwitterClient(cookies)
    cache_path = get_config_dir() / "query-ids-cache.json"
    store = QueryIdStore(cache_path)
    query_id = get_query_id_with_fallback(store, "Bookmarks")
    headers = client.get_base_headers()
    synced_count = 0

    # Load checkpoint for resume capability
    checkpoint = SyncCheckpoint(db_path)
    saved_checkpoint = checkpoint.load("bookmark")
    cursor: str | None = saved_checkpoint.cursor if saved_checkpoint else None
    last_tweet_id: str | None = None
    synced_tweet_ids: list[str] = []

    async with httpx.AsyncClient(headers=headers) as http_client:

        async def refresh_and_get_bookmarks_id() -> str:
            """Refresh query IDs and return the new Bookmarks ID."""
            new_ids: dict[str, str] = await refresh_query_ids(http_client, targets={"Bookmarks"})
            store.save(new_ids)
            return new_ids["Bookmarks"]

        while synced_count < count:
            response = await fetch_bookmarks_page(
                http_client,
                query_id,
                cursor,
                on_query_id_refresh=refresh_and_get_bookmarks_id,
            )
            tweets, cursor = parse_bookmarks_response(response)

            if not tweets:
                break

            for raw_tweet in tweets:
                if synced_count >= count:
                    break
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data:
                    if store_raw:
                        tweet_data["raw_json"] = json.dumps(raw_tweet)
                    save_tweet(db_path, tweet_data)
                    # Also save the quoted tweet if present
                    quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                    if quoted_tweet_data:
                        save_tweet(db_path, quoted_tweet_data)
                    add_to_collection(db_path, tweet_data["id"], "bookmark")
                    last_tweet_id = tweet_data["id"]
                    synced_tweet_ids.append(tweet_data["id"])
                    synced_count += 1

            # Save checkpoint after each page for resume capability
            if cursor and last_tweet_id:
                checkpoint.save("bookmark", cursor=cursor, last_tweet_id=last_tweet_id)

            if not cursor:
                break

    # Clear checkpoint on successful completion
    checkpoint.clear("bookmark")

    # Fetch threads for all synced tweets if enabled
    if with_threads:
        for tweet_id in synced_tweet_ids:
            await fetch_thread_async(db_path=db_path, tweet_id=tweet_id, mode=thread_mode)

    return {"synced_count": synced_count}


@app.command()
def bookmarks(
    count: int = typer.Option(100, "--count", "-c", help="Number of bookmarks to sync."),
    all_bookmarks: bool = typer.Option(False, "--all", help="Sync all bookmarks (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(False, "--store-raw", help="Store raw API response JSON."),
) -> None:
    """Sync bookmarked tweets to local storage."""
    import asyncio

    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_bookmarks else count
    result = asyncio.run(
        sync_bookmarks_async(
            db_path,
            effective_count,
            with_threads=with_threads,
            thread_mode=thread_mode,
            store_raw=store_raw,
        )
    )
    typer.echo(f"Synced {result['synced_count']} bookmarks.")


async def sync_tweets_async(
    db_path: Path,
    count: float,
    with_threads: bool = False,
    thread_mode: str = "thread",
    store_raw: bool = False,
) -> dict[str, int]:
    """Sync user's tweets asynchronously."""
    from tweethoarder.client.timelines import (
        extract_quoted_tweet,
        fetch_user_tweets_page,
        parse_user_tweets_response,
    )

    init_database(db_path)

    cookies = resolve_cookies()
    if not cookies:
        raise ValueError("No cookies found")

    client = TwitterClient(cookies)
    cache_path = get_config_dir() / "query-ids-cache.json"
    store = QueryIdStore(cache_path)
    query_id = get_query_id_with_fallback(store, "UserTweets")

    user_id = cookies.get("twid", "").replace("u%3D", "")
    if not user_id:
        raise ValueError("Could not determine user ID from cookies")

    synced_count = 0
    headers = client.get_base_headers()
    cursor: str | None = None
    synced_tweet_ids: list[str] = []

    async with httpx.AsyncClient(headers=headers) as http_client:
        while synced_count < count:
            response = await fetch_user_tweets_page(
                http_client,
                query_id,
                user_id,
                cursor,
            )
            tweets, cursor = parse_user_tweets_response(response)

            if not tweets:
                break

            for raw_tweet in tweets:
                if synced_count >= count:
                    break
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data:
                    if store_raw:
                        tweet_data["raw_json"] = json.dumps(raw_tweet)
                    save_tweet(db_path, tweet_data)
                    # Also save the quoted tweet if present
                    quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                    if quoted_tweet_data:
                        save_tweet(db_path, quoted_tweet_data)
                    add_to_collection(db_path, tweet_data["id"], "tweet")
                    synced_tweet_ids.append(tweet_data["id"])
                    synced_count += 1

            if not cursor:
                break

    # Fetch threads for all synced tweets if enabled
    if with_threads:
        for tweet_id in synced_tweet_ids:
            await fetch_thread_async(db_path=db_path, tweet_id=tweet_id, mode=thread_mode)

    return {"synced_count": synced_count}


@app.command()
def tweets(
    count: int = typer.Option(100, "--count", "-c", help="Number of tweets to sync."),
    all_tweets: bool = typer.Option(False, "--all", help="Sync all tweets (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(False, "--store-raw", help="Store raw API response JSON."),
) -> None:
    """Sync user's own tweets to local storage."""
    import asyncio

    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_tweets else count
    result = asyncio.run(
        sync_tweets_async(
            db_path,
            effective_count,
            with_threads=with_threads,
            thread_mode=thread_mode,
            store_raw=store_raw,
        )
    )
    typer.echo(f"Synced {result['synced_count']} tweets.")


async def sync_reposts_async(
    db_path: Path,
    count: float,
    with_threads: bool = False,
    thread_mode: str = "thread",
    store_raw: bool = False,
) -> dict[str, int]:
    """Sync user's reposts asynchronously."""
    from tweethoarder.client.timelines import (
        extract_quoted_tweet,
        fetch_user_tweets_page,
        is_repost,
        parse_user_tweets_response,
    )

    init_database(db_path)

    cookies = resolve_cookies()
    if not cookies:
        raise ValueError("No cookies found")

    client = TwitterClient(cookies)
    cache_path = get_config_dir() / "query-ids-cache.json"
    store = QueryIdStore(cache_path)
    query_id = get_query_id_with_fallback(store, "UserTweets")

    user_id = cookies.get("twid", "").replace("u%3D", "")
    if not user_id:
        raise ValueError("Could not determine user ID from cookies")

    synced_count = 0
    headers = client.get_base_headers()
    cursor: str | None = None
    synced_tweet_ids: list[str] = []

    async with httpx.AsyncClient(headers=headers) as http_client:
        while synced_count < count:
            response = await fetch_user_tweets_page(
                http_client,
                query_id,
                user_id,
                cursor,
            )
            tweets, cursor = parse_user_tweets_response(response)

            if not tweets:
                break

            for raw_tweet in tweets:
                if synced_count >= count:
                    break
                if not is_repost(raw_tweet):
                    continue
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data:
                    if store_raw:
                        tweet_data["raw_json"] = json.dumps(raw_tweet)
                    save_tweet(db_path, tweet_data)
                    # Also save the quoted tweet if present
                    quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                    if quoted_tweet_data:
                        save_tweet(db_path, quoted_tweet_data)
                    add_to_collection(db_path, tweet_data["id"], "repost")
                    synced_tweet_ids.append(tweet_data["id"])
                    synced_count += 1

            if not cursor:
                break

    # Fetch threads for all synced tweets if enabled
    if with_threads:
        for tweet_id in synced_tweet_ids:
            await fetch_thread_async(db_path=db_path, tweet_id=tweet_id, mode=thread_mode)

    return {"synced_count": synced_count}


@app.command()
def reposts(
    count: int = typer.Option(100, "--count", "-c", help="Number of reposts to sync."),
    all_reposts: bool = typer.Option(False, "--all", help="Sync all reposts (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(False, "--store-raw", help="Store raw API response JSON."),
) -> None:
    """Sync user's reposts (retweets) to local storage."""
    import asyncio

    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_reposts else count
    result = asyncio.run(
        sync_reposts_async(
            db_path,
            effective_count,
            with_threads=with_threads,
            thread_mode=thread_mode,
            store_raw=store_raw,
        )
    )
    typer.echo(f"Synced {result['synced_count']} reposts.")
