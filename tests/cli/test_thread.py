"""Tests for thread command."""

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_thread_command_exists() -> None:
    """Thread command should be available."""
    result = runner.invoke(app, ["thread", "--help"])
    assert result.exit_code == 0
    assert "tweet_id" in result.output.lower() or "TWEET_ID" in result.output


def test_thread_command_has_depth_option() -> None:
    """Thread command should have --depth option."""
    import re

    result = runner.invoke(app, ["thread", "--help"])
    assert result.exit_code == 0
    # Strip ANSI escape codes for reliable matching
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--depth" in clean_output


def test_thread_command_displays_tweet_id() -> None:
    """Thread command should display the tweet ID being fetched."""
    from unittest.mock import AsyncMock, patch

    with patch("tweethoarder.cli.main.fetch_thread_async", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"tweet_count": 0}
        result = runner.invoke(app, ["thread", "1234567890"])
        assert result.exit_code == 0
        assert "1234567890" in result.output


def test_thread_command_has_mode_option() -> None:
    """Thread command should have --mode option for thread vs conversation."""
    import re

    result = runner.invoke(app, ["thread", "--help"])
    assert result.exit_code == 0
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--mode" in clean_output


def test_thread_command_has_limit_option() -> None:
    """Thread command should have --limit option for max tweets."""
    import re

    result = runner.invoke(app, ["thread", "--help"])
    assert result.exit_code == 0
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--limit" in clean_output


def test_thread_command_displays_mode_in_output() -> None:
    """Thread command should display the mode in output."""
    from unittest.mock import AsyncMock, patch

    with patch("tweethoarder.cli.main.fetch_thread_async", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"tweet_count": 0}
        result = runner.invoke(app, ["thread", "1234567890", "--mode", "conversation"])
        assert result.exit_code == 0
        assert "conversation" in result.output.lower()


def test_thread_command_does_not_crash_on_import() -> None:
    """Thread command should not crash due to import errors."""
    from unittest.mock import AsyncMock, patch

    # Mock the async function to avoid real API calls
    with patch("tweethoarder.cli.main.fetch_thread_async", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"tweet_count": 0}
        result = runner.invoke(app, ["thread", "1234567890"])
        # Should not have import error
        assert "cannot import" not in str(result.exception or "")
        assert result.exit_code == 0
