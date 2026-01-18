"""Tests for retry utilities."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from tweethoarder.client.retry import fetch_with_retry


def test_fetch_with_retry_exists() -> None:
    """fetch_with_retry function should be importable."""
    assert callable(fetch_with_retry)


@pytest.mark.asyncio
async def test_fetch_with_retry_retries_on_429() -> None:
    """fetch_with_retry should retry on 429 rate limit with exponential backoff."""
    mock_client = MagicMock(spec=httpx.AsyncClient)

    # First call returns 429, second call succeeds
    mock_429_response = MagicMock(spec=httpx.Response)
    mock_429_response.status_code = 429

    mock_success_response = MagicMock(spec=httpx.Response)
    mock_success_response.status_code = 200
    mock_success_response.raise_for_status = MagicMock()

    mock_client.get = AsyncMock(side_effect=[mock_429_response, mock_success_response])

    result = await fetch_with_retry(
        mock_client, "https://example.com", max_retries=5, base_delay=0.01
    )

    assert result == mock_success_response
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_with_retry_refreshes_query_id_on_404() -> None:
    """fetch_with_retry should refresh query ID on 404 and retry with new URL."""
    mock_client = MagicMock(spec=httpx.AsyncClient)

    # First call returns 404, second call (with new query ID) succeeds
    mock_404_response = MagicMock(spec=httpx.Response)
    mock_404_response.status_code = 404

    mock_success_response = MagicMock(spec=httpx.Response)
    mock_success_response.status_code = 200
    mock_success_response.raise_for_status = MagicMock()

    mock_client.get = AsyncMock(side_effect=[mock_404_response, mock_success_response])

    # Query ID refresh callback returns new ID
    mock_refresh = AsyncMock(return_value="new_query_id")

    # URL builder rebuilds URL with new query ID
    def url_builder(query_id: str) -> str:
        return f"https://example.com/{query_id}/endpoint"

    result = await fetch_with_retry(
        mock_client,
        "https://example.com/old_query_id/endpoint",
        max_retries=5,
        base_delay=0.01,
        on_query_id_refresh=mock_refresh,
        url_builder=url_builder,
    )

    assert result == mock_success_response
    assert mock_client.get.call_count == 2
    mock_refresh.assert_called_once()
    # Second call should use the new URL
    mock_client.get.assert_called_with("https://example.com/new_query_id/endpoint")
