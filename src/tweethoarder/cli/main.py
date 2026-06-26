"""TweetHoarder CLI main entry point."""

import typer

from tweethoarder.cli import config, export, sync
from tweethoarder.cli import stats as stats_module
from tweethoarder.cli.thread import fetch_thread_async
from tweethoarder.config import get_config_dir
from tweethoarder.query_ids.scraper import refresh_query_ids

app = typer.Typer(
    name="tweethoarder",
    help="Archive your Twitter/X data (likes, bookmarks, tweets, reposts) locally.",
)

app.add_typer(sync.app, name="sync")
app.add_typer(export.app, name="export")
app.add_typer(config.app, name="config")


@app.command()
def stats() -> None:
    """Show statistics about synced data."""
    stats_module.show_stats()


@app.command()
def thread(
    tweet_id: str = typer.Argument(..., help="Tweet ID to fetch thread context for."),
    mode: str = typer.Option(
        "thread", "--mode", "-m", help="Mode: thread (author only) or conversation (all)."
    ),
    limit: int = typer.Option(200, "--limit", "-l", help="Maximum tweets to fetch."),
    depth: int = typer.Option(5, "--depth", "-d", help="Maximum depth of thread to fetch."),
) -> None:
    """Fetch thread context for a tweet."""
    import asyncio

    from tweethoarder.storage.database import get_db_path

    typer.echo(f"Fetching {mode} for tweet {tweet_id}...")
    db_path = get_db_path()
    result = asyncio.run(fetch_thread_async(db_path, tweet_id, mode, limit))
    typer.echo(f"Saved {result['tweet_count']} tweets.")


@app.command()
def user(
    screen_name: str = typer.Argument(..., help="Twitter screen name (without @)."),
    raw: bool = typer.Option(False, "--raw", "-r", help="Print raw JSON response."),
) -> None:
    """Fetch a user profile by screen name."""
    import asyncio
    import json
    from typing import Any

    import httpx

    from tweethoarder.auth.cookies import resolve_cookies
    from tweethoarder.client.base import TwitterClient
    from tweethoarder.client.timelines import fetch_user_by_screen_name
    from tweethoarder.query_ids.store import QueryIdStore, get_query_id_with_fallback

    async def run() -> dict[str, Any]:
        cookies = resolve_cookies()
        tc = TwitterClient(cookies)
        store = QueryIdStore(get_config_dir() / "query-ids-cache.json")
        query_id = get_query_id_with_fallback(store, "UserByScreenName")
        async with httpx.AsyncClient(headers=tc.get_base_headers(), timeout=30) as client:
            data: dict[str, Any] = await fetch_user_by_screen_name(client, query_id, screen_name)
            return data

    result = asyncio.run(run())
    if raw:
        typer.echo(json.dumps(result, indent=2))
    else:
        user_result = result.get("data", {}).get("user", {}).get("result", {})
        if not user_result:
            typer.echo("User not found.")
            raise typer.Exit(1)
        core = user_result.get("core", {})
        legacy = user_result.get("legacy", {})
        typer.echo(f"@{core.get('screen_name', 'unknown')}")
        typer.echo(f"  Name: {core.get('name', '?')}")
        typer.echo(f"  ID: {user_result.get('rest_id', '?')}")
        typer.echo(f"  Followers: {legacy.get('followers_count', '?')}")
        typer.echo(f"  Following: {legacy.get('friends_count', '?')}")
        typer.echo(f"  Tweets: {legacy.get('statuses_count', '?')}")
        typer.echo(f"  Created: {core.get('created_at', '?')}")
        desc = legacy.get("description", "")
        if desc:
            typer.echo(f"  Bio: {desc[:100]}")


@app.command(name="refresh-ids")
def refresh_ids_command() -> None:
    """Refresh Twitter GraphQL query IDs."""
    import asyncio

    import httpx

    from tweethoarder.query_ids.store import QueryIdStore

    async def run() -> dict[str, str]:
        from tweethoarder.auth.cookies import resolve_cookies
        cookies = resolve_cookies()
        async with httpx.AsyncClient() as client:
            result: dict[str, str] = await refresh_query_ids(client, cookies=cookies)
            return result

    ids = asyncio.run(run())
    cache_path = get_config_dir() / "query-ids-cache.json"
    store = QueryIdStore(cache_path)
    store.save(ids)
    typer.echo(f"Refreshed {len(ids)} query IDs.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    """TweetHoarder - Archive your Twitter/X data locally."""
    if version:
        typer.echo("tweethoarder version 0.1.0")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
