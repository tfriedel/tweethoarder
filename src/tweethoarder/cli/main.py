"""TweetHoarder CLI main entry point."""

import typer

from tweethoarder.cli import export, sync
from tweethoarder.cli import stats as stats_module

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
def refresh_ids() -> None:
    """Refresh Twitter GraphQL query IDs."""


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
