"""Sync commands for TweetHoarder CLI."""

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import typer
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from tweethoarder.auth.cookies import resolve_cookies
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
from tweethoarder.storage.database import (
    add_to_collection,
    init_database,
    save_tweet,
    tweet_in_collection,
)
from tweethoarder.sync.sort_index import SortIndexGenerator

# Adaptive delay settings for thread fetches
# Start with minimal delay and increase on rate limit errors
THREAD_FETCH_INITIAL_DELAY = 0.2  # Start fast
THREAD_FETCH_MAX_DELAY = 60.0  # Cap the delay at 60s
THREAD_FETCH_DELAY_MULTIPLIER = 2.0  # Double delay on 429
THREAD_FETCH_SUCCESS_STREAK_RESET = 5  # Reset delay after N consecutive successes
THREAD_FETCH_RATE_LIMIT_COOLDOWN = 300.0  # 5 min cooldown after consecutive 429s
THREAD_FETCH_CONSECUTIVE_429_THRESHOLD = 3  # Trigger cooldown after this many 429s


def create_sync_progress() -> Progress:
    """Create a progress bar for sync operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TextColumn("ETA:"),
        TimeRemainingColumn(),
        transient=False,
    )


def needs_thread_fetch(tweet_data: dict[str, Any]) -> bool:
    """Check if tweet is part of a thread (self-reply only).

    Only returns True when the author is replying to themselves, which indicates
    a thread/tweetstorm. Replies to other users are not fetched since the thread
    filter would discard the actual thread content anyway.
    """
    reply_to_user = tweet_data.get("in_reply_to_user_id")
    if not reply_to_user:
        return False
    # Only fetch if author is replying to themselves (thread continuation)
    return bool(reply_to_user == tweet_data.get("author_id"))


async def fetch_threads_with_adaptive_delay(
    db_path: Path,
    tweet_ids: list[str],
    thread_mode: str,
    progress: Progress | None = None,
) -> dict[str, int]:
    """Fetch threads with adaptive rate limiting.

    Starts with minimal delay and increases on rate limit errors.
    On consecutive 429s, triggers a longer cooldown period.
    Retries rate-limited requests after waiting.
    """
    from tweethoarder.cli.thread import fetch_thread_async

    current_delay = THREAD_FETCH_INITIAL_DELAY
    success_streak = 0
    consecutive_429s = 0
    fetched_count = 0
    failed_count = 0

    thread_task = progress.add_task("Fetching threads", total=len(tweet_ids)) if progress else None

    i = 0
    while i < len(tweet_ids):
        tweet_id = tweet_ids[i]
        try:
            await fetch_thread_async(db_path=db_path, tweet_id=tweet_id, mode=thread_mode)
            fetched_count += 1
            success_streak += 1
            consecutive_429s = 0

            # Reset delay after consecutive successes
            if success_streak >= THREAD_FETCH_SUCCESS_STREAK_RESET:
                current_delay = THREAD_FETCH_INITIAL_DELAY
                success_streak = 0

            if progress and thread_task is not None:
                progress.update(thread_task, completed=i + 1)
            i += 1

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                consecutive_429s += 1
                success_streak = 0

                if consecutive_429s >= THREAD_FETCH_CONSECUTIVE_429_THRESHOLD:
                    # Too many 429s - enter cooldown
                    typer.echo(
                        f"\nHit rate limit {consecutive_429s}x, "
                        f"cooling down for {THREAD_FETCH_RATE_LIMIT_COOLDOWN / 60:.0f} min..."
                    )
                    await asyncio.sleep(THREAD_FETCH_RATE_LIMIT_COOLDOWN)
                    current_delay = THREAD_FETCH_INITIAL_DELAY
                    consecutive_429s = 0
                    # Retry same tweet (don't increment i)
                    continue

                # Increase delay and retry
                current_delay = min(
                    current_delay * THREAD_FETCH_DELAY_MULTIPLIER, THREAD_FETCH_MAX_DELAY
                )
                typer.echo(f"Rate limited, waiting {current_delay}s...")
                await asyncio.sleep(current_delay)
                # Retry same tweet (don't increment i)
                continue
            else:
                # Other HTTP error - skip this tweet
                typer.echo(f"HTTP error {e.response.status_code} for {tweet_id}, skipping")
                failed_count += 1
                if progress and thread_task is not None:
                    progress.update(thread_task, completed=i + 1)
                i += 1

        except Exception as e:
            # Other errors - log and continue
            typer.echo(f"Failed to fetch thread for {tweet_id}: {e}")
            failed_count += 1
            success_streak = 0
            if progress and thread_task is not None:
                progress.update(thread_task, completed=i + 1)
            i += 1

        # Add delay before next request (except for last one)
        if i < len(tweet_ids):
            await asyncio.sleep(current_delay)

    return {"fetched_count": fetched_count, "failed_count": failed_count}


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
    progress: Progress | None = None,
    full: bool = False,
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
        progress: Optional Rich progress bar for displaying sync progress.
        full: If True, force complete resync ignoring existing tweets.

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
    # Deduplicate thread fetches by conversation_id to avoid redundant API calls
    threads_by_conv_id: dict[str, str] = {}  # conversation_id -> tweet_id

    # Initialize sort index generator (uses checkpoint or derives from existing data)
    sort_gen = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "like", db_path)

    # Set up progress tracking
    total = int(count) if count != float("inf") else None
    sync_task = progress.add_task("Syncing likes", total=total) if progress else None

    hit_duplicate = False

    async with httpx.AsyncClient(headers=headers) as http_client:

        async def refresh_and_get_likes_id() -> str:
            """Refresh query IDs and return the new Likes ID."""
            new_ids: dict[str, str] = await refresh_query_ids(http_client, targets={"Likes"})
            store.save(new_ids)
            return new_ids["Likes"]

        while synced_count < count and not hit_duplicate:
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
                sort_index = sort_gen.next()
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data is None:
                    continue
                # Check for duplicate if not doing full sync
                if not full and tweet_in_collection(db_path, tweet_data["id"], "like"):
                    hit_duplicate = True
                    break
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
                if needs_thread_fetch(tweet_data):
                    conv_id = tweet_data.get("conversation_id") or tweet_data["id"]
                    if conv_id not in threads_by_conv_id:
                        threads_by_conv_id[conv_id] = tweet_data["id"]
                synced_count += 1
                if progress and sync_task is not None:
                    progress.update(sync_task, completed=synced_count)

            # Save checkpoint after each page for resume capability
            if cursor and last_tweet_id:
                checkpoint.save(
                    "like",
                    cursor=cursor,
                    last_tweet_id=last_tweet_id,
                    sort_index_counter=sort_gen.current,
                )

            if not cursor:
                break

    # Clear checkpoint on successful completion
    checkpoint.clear("like")

    # Fetch threads only for tweets that are part of a conversation
    tweets_needing_threads = list(threads_by_conv_id.values())
    if with_threads and tweets_needing_threads:
        await fetch_threads_with_adaptive_delay(
            db_path, tweets_needing_threads, thread_mode, progress
        )

    return {"synced_count": synced_count}


@app.command()
def likes(
    count: int = typer.Option(100, "--count", "-c", help="Number of likes to sync."),
    all_likes: bool = typer.Option(False, "--all", help="Sync all likes (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(
        True, "--store-raw/--no-store-raw", help="Store raw API response JSON."
    ),
    full: bool = typer.Option(
        False, "--full", help="Force complete resync, ignoring existing tweets."
    ),
) -> None:
    """Sync liked tweets to local storage."""
    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_likes else count

    with create_sync_progress() as progress:
        result = asyncio.run(
            sync_likes_async(
                db_path,
                effective_count,
                with_threads=with_threads,
                thread_mode=thread_mode,
                store_raw=store_raw,
                progress=progress,
                full=full,
            )
        )
    typer.echo(f"Synced {result['synced_count']} likes.")


async def sync_bookmarks_async(
    db_path: Path,
    count: float,
    with_threads: bool = False,
    thread_mode: str = "thread",
    store_raw: bool = False,
    progress: Progress | None = None,
    full: bool = False,
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
    # Deduplicate thread fetches by conversation_id to avoid redundant API calls
    threads_by_conv_id: dict[str, str] = {}  # conversation_id -> tweet_id

    # Initialize sort index generator (uses checkpoint or derives from existing data)
    sort_gen = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "bookmark", db_path)

    # Set up progress tracking
    total = int(count) if count != float("inf") else None
    sync_task = progress.add_task("Syncing bookmarks", total=total) if progress else None

    hit_duplicate = False

    async with httpx.AsyncClient(headers=headers) as http_client:

        async def refresh_and_get_bookmarks_id() -> str:
            """Refresh query IDs and return the new Bookmarks ID."""
            new_ids: dict[str, str] = await refresh_query_ids(http_client, targets={"Bookmarks"})
            store.save(new_ids)
            return new_ids["Bookmarks"]

        while synced_count < count and not hit_duplicate:
            response = await fetch_bookmarks_page(
                http_client,
                query_id,
                cursor,
                on_query_id_refresh=refresh_and_get_bookmarks_id,
            )
            entries, cursor = parse_bookmarks_response(response)

            if not entries:
                break

            for entry in entries:
                if synced_count >= count:
                    break
                raw_tweet = entry["tweet"]
                sort_index = sort_gen.next()
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data:
                    # Check for duplicate if not doing full sync
                    if not full and tweet_in_collection(db_path, tweet_data["id"], "bookmark"):
                        hit_duplicate = True
                        break
                    if store_raw:
                        tweet_data["raw_json"] = json.dumps(raw_tweet)
                    save_tweet(db_path, tweet_data)
                    # Also save the quoted tweet if present
                    quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                    if quoted_tweet_data:
                        save_tweet(db_path, quoted_tweet_data)
                    add_to_collection(db_path, tweet_data["id"], "bookmark", sort_index=sort_index)
                    last_tweet_id = tweet_data["id"]
                    synced_tweet_ids.append(tweet_data["id"])
                    if needs_thread_fetch(tweet_data):
                        conv_id = tweet_data.get("conversation_id") or tweet_data["id"]
                        if conv_id not in threads_by_conv_id:
                            threads_by_conv_id[conv_id] = tweet_data["id"]
                    synced_count += 1
                    if progress and sync_task is not None:
                        progress.update(sync_task, completed=synced_count)

            # Save checkpoint after each page for resume capability
            if cursor and last_tweet_id:
                checkpoint.save(
                    "bookmark",
                    cursor=cursor,
                    last_tweet_id=last_tweet_id,
                    sort_index_counter=sort_gen.current,
                )

            if not cursor:
                break

    # Clear checkpoint on successful completion
    checkpoint.clear("bookmark")

    # Fetch threads only for tweets that are part of a conversation
    tweets_needing_threads = list(threads_by_conv_id.values())
    if with_threads and tweets_needing_threads:
        await fetch_threads_with_adaptive_delay(
            db_path, tweets_needing_threads, thread_mode, progress
        )

    return {"synced_count": synced_count}


@app.command()
def bookmarks(
    count: int = typer.Option(100, "--count", "-c", help="Number of bookmarks to sync."),
    all_bookmarks: bool = typer.Option(False, "--all", help="Sync all bookmarks (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(
        True, "--store-raw/--no-store-raw", help="Store raw API response JSON."
    ),
    full: bool = typer.Option(
        False, "--full", help="Force complete resync, ignoring existing tweets."
    ),
) -> None:
    """Sync bookmarked tweets to local storage."""
    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_bookmarks else count

    with create_sync_progress() as progress:
        result = asyncio.run(
            sync_bookmarks_async(
                db_path,
                effective_count,
                with_threads=with_threads,
                thread_mode=thread_mode,
                store_raw=store_raw,
                progress=progress,
                full=full,
            )
        )
    typer.echo(f"Synced {result['synced_count']} bookmarks.")


async def sync_tweets_async(
    db_path: Path,
    count: float,
    with_threads: bool = False,
    thread_mode: str = "thread",
    store_raw: bool = False,
    progress: Progress | None = None,
    full: bool = False,
) -> dict[str, int]:
    """Sync user's tweets asynchronously.

    Note: This function syncs only original tweets, not replies.
    Replies should be synced using sync_replies_async() instead.
    """
    from tweethoarder.client.timelines import (
        extract_quoted_tweet,
        fetch_user_tweets_page,
        is_reply,
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
    synced_tweet_ids: list[str] = []

    # Load checkpoint for resume capability
    checkpoint = SyncCheckpoint(db_path)
    saved_checkpoint = checkpoint.load("tweet")
    cursor: str | None = saved_checkpoint.cursor if saved_checkpoint else None
    last_tweet_id: str | None = None

    # Initialize sort index generator (uses checkpoint or derives from existing data)
    sort_gen = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "tweet", db_path)

    # Set up progress tracking
    total = int(count) if count != float("inf") else None
    sync_task = progress.add_task("Syncing tweets", total=total) if progress else None

    hit_duplicate = False

    async with httpx.AsyncClient(headers=headers) as http_client:
        while synced_count < count and not hit_duplicate:
            response = await fetch_user_tweets_page(
                http_client,
                query_id,
                user_id,
                cursor,
            )
            entries, cursor = parse_user_tweets_response(response)

            if not entries:
                break

            for entry in entries:
                if synced_count >= count:
                    break
                raw_tweet = entry["tweet"]
                # Skip replies - they should be synced using sync_replies_async
                if is_reply(raw_tweet):
                    continue
                sort_index = sort_gen.next()
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data:
                    # Check for duplicate if not doing full sync
                    if not full and tweet_in_collection(db_path, tweet_data["id"], "tweet"):
                        hit_duplicate = True
                        break
                    if store_raw:
                        tweet_data["raw_json"] = json.dumps(raw_tweet)
                    save_tweet(db_path, tweet_data)
                    # Also save the quoted tweet if present
                    quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                    if quoted_tweet_data:
                        save_tweet(db_path, quoted_tweet_data)
                    add_to_collection(db_path, tweet_data["id"], "tweet", sort_index=sort_index)
                    last_tweet_id = tweet_data["id"]
                    synced_tweet_ids.append(tweet_data["id"])
                    synced_count += 1
                    if progress and sync_task is not None:
                        progress.update(sync_task, completed=synced_count)

            # Save checkpoint after each page for resume capability
            if cursor and last_tweet_id:
                checkpoint.save(
                    "tweet",
                    cursor=cursor,
                    last_tweet_id=last_tweet_id,
                    sort_index_counter=sort_gen.current,
                )

            if not cursor:
                break

    # Clear checkpoint on successful completion
    checkpoint.clear("tweet")

    # Fetch threads for all synced tweets if enabled
    if with_threads and synced_tweet_ids:
        await fetch_threads_with_adaptive_delay(db_path, synced_tweet_ids, thread_mode, progress)

    return {"synced_count": synced_count}


@app.command()
def tweets(
    count: int = typer.Option(100, "--count", "-c", help="Number of tweets to sync."),
    all_tweets: bool = typer.Option(False, "--all", help="Sync all tweets (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(
        True, "--store-raw/--no-store-raw", help="Store raw API response JSON."
    ),
    full: bool = typer.Option(
        False, "--full", help="Force complete resync, ignoring existing tweets."
    ),
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
            full=full,
        )
    )
    typer.echo(f"Synced {result['synced_count']} tweets.")


async def sync_reposts_async(
    db_path: Path,
    count: float,
    with_threads: bool = False,
    thread_mode: str = "thread",
    store_raw: bool = False,
    progress: Progress | None = None,
    full: bool = False,
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
    synced_tweet_ids: list[str] = []

    # Load checkpoint for resume capability
    checkpoint = SyncCheckpoint(db_path)
    saved_checkpoint = checkpoint.load("repost")
    cursor: str | None = saved_checkpoint.cursor if saved_checkpoint else None
    last_tweet_id: str | None = None

    # Initialize sort index generator (uses checkpoint or derives from existing data)
    sort_gen = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "repost", db_path)

    # Set up progress tracking
    total = int(count) if count != float("inf") else None
    sync_task = progress.add_task("Syncing reposts", total=total) if progress else None

    hit_duplicate = False

    async with httpx.AsyncClient(headers=headers) as http_client:
        while synced_count < count and not hit_duplicate:
            response = await fetch_user_tweets_page(
                http_client,
                query_id,
                user_id,
                cursor,
            )
            entries, cursor = parse_user_tweets_response(response)

            if not entries:
                break

            for entry in entries:
                if synced_count >= count:
                    break
                raw_tweet = entry["tweet"]
                if not is_repost(raw_tweet):
                    continue
                sort_index = sort_gen.next()
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data:
                    # Check for duplicate if not doing full sync
                    if not full and tweet_in_collection(db_path, tweet_data["id"], "repost"):
                        hit_duplicate = True
                        break
                    if store_raw:
                        tweet_data["raw_json"] = json.dumps(raw_tweet)
                    save_tweet(db_path, tweet_data)
                    # Also save the quoted tweet if present
                    quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                    if quoted_tweet_data:
                        save_tweet(db_path, quoted_tweet_data)
                    add_to_collection(db_path, tweet_data["id"], "repost", sort_index=sort_index)
                    last_tweet_id = tweet_data["id"]
                    synced_tweet_ids.append(tweet_data["id"])
                    synced_count += 1
                    if progress and sync_task is not None:
                        progress.update(sync_task, completed=synced_count)

            # Save checkpoint after each page for resume capability
            if cursor and last_tweet_id:
                checkpoint.save(
                    "repost",
                    cursor=cursor,
                    last_tweet_id=last_tweet_id,
                    sort_index_counter=sort_gen.current,
                )

            if not cursor:
                break

    # Clear checkpoint on successful completion
    checkpoint.clear("repost")

    # Fetch threads for all synced tweets if enabled
    if with_threads and synced_tweet_ids:
        await fetch_threads_with_adaptive_delay(db_path, synced_tweet_ids, thread_mode, progress)

    return {"synced_count": synced_count}


@app.command()
def reposts(
    count: int = typer.Option(100, "--count", "-c", help="Number of reposts to sync."),
    all_reposts: bool = typer.Option(False, "--all", help="Sync all reposts (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(
        True, "--store-raw/--no-store-raw", help="Store raw API response JSON."
    ),
    full: bool = typer.Option(
        False, "--full", help="Force complete resync, ignoring existing tweets."
    ),
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
            full=full,
        )
    )
    typer.echo(f"Synced {result['synced_count']} reposts.")


async def sync_replies_async(
    db_path: Path,
    count: float,
    with_threads: bool = False,
    thread_mode: str = "thread",
    store_raw: bool = False,
    progress: Progress | None = None,
    full: bool = False,
) -> dict[str, int]:
    """Sync user's replies asynchronously.

    Fetches tweets that are replies to other users' tweets and saves them
    to the local database with collection type 'reply'. Also fetches and saves
    the immediate parent tweet for each reply.
    """
    from tweethoarder.client.timelines import (
        extract_quoted_tweet,
        fetch_tweet_detail_page,
        fetch_user_tweets_page,
        is_reply,
        parse_user_tweets_response,
    )
    from tweethoarder.storage.database import tweet_exists

    init_database(db_path)

    cookies = resolve_cookies()
    if not cookies:
        raise ValueError("No cookies found")

    client = TwitterClient(cookies)
    cache_path = get_config_dir() / "query-ids-cache.json"
    store = QueryIdStore(cache_path)
    query_id = get_query_id_with_fallback(store, "UserTweets")
    tweet_detail_query_id = get_query_id_with_fallback(store, "TweetDetail")

    user_id = cookies.get("twid", "").replace("u%3D", "")
    if not user_id:
        raise ValueError("Could not determine user ID from cookies")

    synced_count = 0
    headers = client.get_base_headers()
    synced_tweet_ids: list[str] = []
    parent_tweet_ids: set[str] = set()

    # Load checkpoint for resume capability
    checkpoint = SyncCheckpoint(db_path)
    saved_checkpoint = checkpoint.load("reply")
    cursor: str | None = saved_checkpoint.cursor if saved_checkpoint else None
    last_tweet_id: str | None = None

    # Initialize sort index generator (uses checkpoint or derives from existing data)
    sort_gen = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "reply", db_path)

    # Set up progress tracking
    total = int(count) if count != float("inf") else None
    sync_task = progress.add_task("Syncing replies", total=total) if progress else None

    hit_duplicate = False

    async with httpx.AsyncClient(headers=headers) as http_client:
        while synced_count < count and not hit_duplicate:
            response = await fetch_user_tweets_page(
                http_client,
                query_id,
                user_id,
                cursor,
            )
            entries, cursor = parse_user_tweets_response(response)

            if not entries:
                break

            for entry in entries:
                if synced_count >= count:
                    break
                raw_tweet = entry["tweet"]
                # Only sync replies
                if not is_reply(raw_tweet):
                    continue
                sort_index = sort_gen.next()
                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data:
                    # Check for duplicate if not doing full sync
                    if not full and tweet_in_collection(db_path, tweet_data["id"], "reply"):
                        hit_duplicate = True
                        break
                    if store_raw:
                        tweet_data["raw_json"] = json.dumps(raw_tweet)
                    save_tweet(db_path, tweet_data)
                    # Also save the quoted tweet if present
                    quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                    if quoted_tweet_data:
                        save_tweet(db_path, quoted_tweet_data)
                    add_to_collection(db_path, tweet_data["id"], "reply", sort_index=sort_index)
                    last_tweet_id = tweet_data["id"]
                    synced_tweet_ids.append(tweet_data["id"])
                    # Collect parent tweet ID for later fetching
                    parent_id = tweet_data.get("in_reply_to_tweet_id")
                    if parent_id:
                        parent_tweet_ids.add(parent_id)
                    synced_count += 1
                    if progress and sync_task is not None:
                        progress.update(sync_task, completed=synced_count)

            # Save checkpoint after each page for resume capability
            if cursor and last_tweet_id:
                checkpoint.save(
                    "reply",
                    cursor=cursor,
                    last_tweet_id=last_tweet_id,
                    sort_index_counter=sort_gen.current,
                )

            if not cursor:
                break

        # Fetch parent tweets that aren't already in the database
        for parent_id in parent_tweet_ids:
            if tweet_exists(db_path, parent_id):
                continue
            try:
                parent_response = await fetch_tweet_detail_page(
                    http_client, tweet_detail_query_id, parent_id
                )
                # Extract parent tweet from TweetDetail response
                parent_result = parent_response.get("data", {}).get("tweetResult", {}).get("result")
                if parent_result:
                    parent_data = extract_tweet_data(parent_result)
                    if parent_data:
                        save_tweet(db_path, parent_data)
                # Add delay to avoid rate limiting
                await asyncio.sleep(THREAD_FETCH_INITIAL_DELAY)
            except httpx.HTTPStatusError:
                # Parent tweet may be deleted or unavailable
                pass

    # Clear checkpoint on successful completion
    checkpoint.clear("reply")

    # Fetch threads for all synced tweets if enabled
    if with_threads and synced_tweet_ids:
        await fetch_threads_with_adaptive_delay(db_path, synced_tweet_ids, thread_mode, progress)

    return {"synced_count": synced_count}


@app.command()
def replies(
    count: int = typer.Option(100, "--count", "-c", help="Number of replies to sync."),
    all_replies: bool = typer.Option(False, "--all", help="Sync all replies (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(
        True, "--store-raw/--no-store-raw", help="Store raw API response JSON."
    ),
    full: bool = typer.Option(
        False, "--full", help="Force complete resync, ignoring existing tweets."
    ),
) -> None:
    """Sync user's replies to local storage."""
    import asyncio

    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_replies else count
    result = asyncio.run(
        sync_replies_async(
            db_path,
            effective_count,
            with_threads=with_threads,
            thread_mode=thread_mode,
            store_raw=store_raw,
            full=full,
        )
    )
    typer.echo(f"Synced {result['synced_count']} replies.")


async def sync_posts_async(
    db_path: Path,
    count: float,
    with_threads: bool = False,
    thread_mode: str = "thread",
    store_raw: bool = False,
    progress: Progress | None = None,
    full: bool = False,
) -> dict[str, int]:
    """Sync user's posts (tweets and reposts) in a single API pass.

    This is more efficient than syncing tweets and reposts separately,
    as it only makes one API call for both types.
    """
    from tweethoarder.client.timelines import (
        extract_quoted_tweet,
        fetch_user_tweets_page,
        is_reply,
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

    tweets_count = 0
    reposts_count = 0
    headers = client.get_base_headers()

    # Load checkpoint for resume capability (using "posts" as combined checkpoint)
    checkpoint = SyncCheckpoint(db_path)
    saved_checkpoint = checkpoint.load("posts")
    cursor: str | None = saved_checkpoint.cursor if saved_checkpoint else None
    last_tweet_id: str | None = None

    # Initialize separate sort index generators for tweets and reposts
    # This maintains correct ordering within each collection type
    sort_gen_tweet = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "tweet", db_path)
    sort_gen_repost = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "repost", db_path)

    # Set up progress tracking
    total = int(count) if count != float("inf") else None
    sync_task = progress.add_task("Syncing posts", total=total) if progress else None

    hit_duplicate = False

    async with httpx.AsyncClient(headers=headers) as http_client:
        while (tweets_count + reposts_count) < count and not hit_duplicate:
            response = await fetch_user_tweets_page(
                http_client,
                query_id,
                user_id,
                cursor,
            )
            entries, cursor = parse_user_tweets_response(response)

            if not entries:
                break

            for entry in entries:
                if (tweets_count + reposts_count) >= count:
                    break
                raw_tweet = entry["tweet"]

                # Skip replies - they're not part of posts
                if is_reply(raw_tweet):
                    continue

                tweet_data = extract_tweet_data(raw_tweet)
                if tweet_data:
                    # Check for duplicate if not doing full sync
                    collection_to_check = "repost" if is_repost(raw_tweet) else "tweet"
                    if not full and tweet_in_collection(
                        db_path, tweet_data["id"], collection_to_check
                    ):
                        hit_duplicate = True
                        break

                    if store_raw:
                        tweet_data["raw_json"] = json.dumps(raw_tweet)
                    save_tweet(db_path, tweet_data)
                    # Also save the quoted tweet if present
                    quoted_tweet_data = extract_quoted_tweet(raw_tweet)
                    if quoted_tweet_data:
                        save_tweet(db_path, quoted_tweet_data)

                    # Classify as tweet or repost
                    if is_repost(raw_tweet):
                        sort_index = sort_gen_repost.next()
                        add_to_collection(
                            db_path, tweet_data["id"], "repost", sort_index=sort_index
                        )
                        reposts_count += 1
                    else:
                        sort_index = sort_gen_tweet.next()
                        add_to_collection(db_path, tweet_data["id"], "tweet", sort_index=sort_index)
                        tweets_count += 1

                    last_tweet_id = tweet_data["id"]

                    if progress and sync_task is not None:
                        progress.update(sync_task, completed=tweets_count + reposts_count)

            # Save checkpoint after each page for resume capability
            if cursor and last_tweet_id:
                checkpoint.save(
                    "posts",
                    cursor=cursor,
                    last_tweet_id=last_tweet_id,
                )

            if not cursor:
                break

    # Clear checkpoint on successful completion
    checkpoint.clear("posts")

    return {"tweets_count": tweets_count, "reposts_count": reposts_count}


@app.command()
def posts(
    count: int = typer.Option(100, "--count", "-c", help="Number of posts to sync."),
    all_posts: bool = typer.Option(False, "--all", help="Sync all posts (ignore count)."),
    with_threads: bool = typer.Option(False, "--with-threads", help="Fetch thread context."),
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    store_raw: bool = typer.Option(
        True, "--store-raw/--no-store-raw", help="Store raw API response JSON."
    ),
    full: bool = typer.Option(
        False, "--full", help="Force complete resync, ignoring existing tweets."
    ),
) -> None:
    """Sync all your posts (tweets and reposts) to local storage.

    Uses a single API pass to fetch both tweets and reposts efficiently.
    Note: Replies are not available via the Twitter API's UserTweets endpoint.
    """
    import asyncio

    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"
    effective_count = float("inf") if all_posts else count

    with create_sync_progress() as progress:
        result = asyncio.run(
            sync_posts_async(
                db_path,
                effective_count,
                with_threads=with_threads,
                thread_mode=thread_mode,
                store_raw=store_raw,
                progress=progress,
                full=full,
            )
        )

    typer.echo(f"Synced {result['tweets_count']} tweets, {result['reposts_count']} reposts.")


@app.command()
def threads(
    thread_mode: str = typer.Option(
        "thread", "--thread-mode", help="Thread mode: thread (author only) or conversation."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Fetch threads even if we might already have them."
    ),
) -> None:
    """Fetch thread context for existing tweets in the database.

    Finds self-reply tweets (threads) that may be missing context and fetches
    the full thread. By default, skips conversations where we already have
    multiple tweets (likely already fetched). Use --force to fetch all.
    """
    import asyncio
    import sqlite3

    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"

    # Find self-reply tweets (threads) that need fetching
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if force:
        # Fetch all self-reply tweets, deduplicated by conversation_id
        cursor = conn.execute("""
            SELECT DISTINCT conversation_id, id as tweet_id
            FROM tweets
            WHERE in_reply_to_user_id IS NOT NULL
              AND in_reply_to_user_id = author_id
              AND conversation_id IS NOT NULL
            GROUP BY conversation_id
        """)
    else:
        # Fetch threads where a self-reply's parent tweet is missing from the DB
        cursor = conn.execute("""
            SELECT DISTINCT t.conversation_id, t.id as tweet_id
            FROM tweets t
            WHERE t.in_reply_to_user_id IS NOT NULL
              AND t.in_reply_to_user_id = t.author_id
              AND t.in_reply_to_tweet_id IS NOT NULL
              AND t.in_reply_to_tweet_id NOT IN (SELECT id FROM tweets)
        """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        typer.echo("No threads need fetching.")
        return

    tweet_ids = [row["tweet_id"] for row in rows]
    typer.echo(f"Found {len(tweet_ids)} threads to fetch.")

    with create_sync_progress() as progress:
        result = asyncio.run(
            fetch_threads_with_adaptive_delay(db_path, tweet_ids, thread_mode, progress)
        )

    typer.echo(
        f"Fetched {result['fetched_count']} threads"
        + (f", {result['failed_count']} failed" if result["failed_count"] else "")
        + "."
    )


async def sync_feed_async(
    db_path: Path,
    hours: int = 24,
    count: int | float = float("inf"),
    store_raw: bool = False,
    progress: Progress | None = None,
    full: bool = False,
) -> dict[str, Any]:
    """Sync home timeline (Following feed) from Twitter to local database."""
    from tweethoarder.client.timelines import (
        fetch_home_timeline_page,
        parse_home_timeline_response,
    )

    init_database(db_path)

    cookies = resolve_cookies()
    if not cookies:
        raise ValueError("No cookies found. Please log in to Twitter in your browser.")

    client = TwitterClient(cookies=cookies)
    cache_path = get_config_dir() / "query-ids-cache.json"
    store = QueryIdStore(cache_path)
    query_id = get_query_id_with_fallback(store, "HomeLatestTimeline")

    synced_count = 0
    headers = client.get_base_headers()

    async with httpx.AsyncClient(headers=headers) as http_client:

        async def refresh_and_get_home_timeline_id() -> str:
            """Refresh query IDs and return the new HomeLatestTimeline ID."""
            new_ids: dict[str, str] = await refresh_query_ids(
                http_client, targets={"HomeLatestTimeline"}
            )
            store.save(new_ids)
            return new_ids["HomeLatestTimeline"]

        response = await fetch_home_timeline_page(
            http_client, query_id, on_query_id_refresh=refresh_and_get_home_timeline_id
        )
        entries, _ = parse_home_timeline_response(response)

        for entry in entries:
            raw_tweet = entry["tweet"]
            sort_index = entry.get("sort_index")
            tweet_data = extract_tweet_data(raw_tweet)
            if tweet_data:
                # Check for duplicate if not doing full sync
                if not full and tweet_in_collection(db_path, tweet_data["id"], "feed"):
                    break

                save_tweet(db_path, tweet_data)
                add_to_collection(db_path, tweet_data["id"], "feed", sort_index=sort_index)
                synced_count += 1

    return {"synced_count": synced_count}


@app.command()
def feed(
    hours: int = typer.Option(24, "--hours", "-h", help="Hours of feed to sync."),
    full: bool = typer.Option(
        False, "--full", help="Force complete resync, ignoring existing tweets."
    ),
) -> None:
    """Sync home timeline (Following feed) to local storage."""
    from tweethoarder.config import get_data_dir

    db_path = get_data_dir() / "tweethoarder.db"

    result = asyncio.run(sync_feed_async(db_path=db_path, hours=hours, full=full))
    typer.echo(f"Synced {result['synced_count']} feed tweets.")
