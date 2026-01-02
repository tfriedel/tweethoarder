"""Sync commands for TweetHoarder CLI."""

import typer

app = typer.Typer(
    name="sync",
    help="Sync Twitter/X data to local storage.",
)


@app.command()
def likes() -> None:
    """Sync liked tweets to local storage."""


@app.command()
def bookmarks() -> None:
    """Sync bookmarked tweets to local storage."""


@app.command()
def tweets() -> None:
    """Sync user's own tweets to local storage."""


@app.command()
def reposts() -> None:
    """Sync user's reposts (retweets) to local storage."""
