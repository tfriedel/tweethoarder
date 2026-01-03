"""Config commands for TweetHoarder CLI."""

import typer

from tweethoarder.config import get_config_dir

app = typer.Typer(
    name="config",
    help="Manage TweetHoarder configuration.",
)


@app.command()
def show() -> None:
    """Show current configuration."""
    config_dir = get_config_dir()
    typer.echo(f"config_dir: {config_dir}")


@app.command()
def set(
    key: str = typer.Argument(..., help="Configuration key to set."),
    value: str = typer.Argument(..., help="Value to set."),
) -> None:
    """Set a configuration value."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"
    config_file.write_text(f"{key} = {value}\n")
