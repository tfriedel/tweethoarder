"""TweetHoarder CLI main entry point."""

import typer

from tweethoarder.cli import export, sync
from tweethoarder.cli import stats as stats_module
from tweethoarder.config import get_config_dir
from tweethoarder.query_ids.scraper import refresh_query_ids

app = typer.Typer(
    name="tweethoarder",
    help="Archive your Twitter/X data (likes, bookmarks, tweets, reposts) locally.",
)

app.add_typer(sync.app, name="sync")
app.add_typer(export.app, name="export")


@app.command()
def stats() -> None:
    """Show statistics about synced data."""
    stats_module.show_stats()


@app.command(name="refresh-ids")
def refresh_ids_command() -> None:
    """Refresh Twitter GraphQL query IDs."""
    import asyncio

    import httpx

    from tweethoarder.query_ids.store import QueryIdStore

    async def run() -> dict[str, str]:
        async with httpx.AsyncClient() as client:
            result: dict[str, str] = await refresh_query_ids(client)
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
