"""Retry utilities for Twitter API calls."""

import asyncio
from collections.abc import Awaitable, Callable

import httpx


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 5,
    base_delay: float = 1.0,
    on_query_id_refresh: Callable[[], Awaitable[str]] | None = None,
    url_builder: Callable[[str], str] | None = None,
) -> httpx.Response:
    """Fetch URL with retry on 429 rate limit and optional 404 query ID refresh.

    Args:
        client: The httpx async client to use for requests.
        url: The URL to fetch.
        max_retries: Maximum number of retry attempts on rate limit.
        base_delay: Base delay in seconds for exponential backoff.
        on_query_id_refresh: Optional async callback to get new query ID on 404.
        url_builder: Optional function to rebuild URL with new query ID.

    Returns:
        The successful httpx.Response.

    Raises:
        httpx.HTTPStatusError: If the request fails after all retries.
    """
    attempt = 0
    current_url = url
    refreshed = False

    while attempt < max_retries:
        response = await client.get(current_url)

        # Handle 404 with query ID refresh (one attempt)
        if response.status_code == 404 and on_query_id_refresh and url_builder and not refreshed:
            new_query_id = await on_query_id_refresh()
            current_url = url_builder(new_query_id)
            refreshed = True
            attempt = 0  # Reset attempts after refresh
            continue

        # Handle 429 rate limit with exponential backoff
        if response.status_code == 429:
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                await asyncio.sleep(delay)
                attempt += 1
                continue
            response.raise_for_status()

        response.raise_for_status()
        return response

    raise RuntimeError("Unreachable: retry loop should always return or raise")
