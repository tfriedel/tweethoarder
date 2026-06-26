"""Bundle discovery and query ID extraction from Twitter client JS."""

import re

import httpx

from .constants import BUNDLE_URL_PATTERN, DISCOVERY_PAGES, QUERY_ID_PATTERN

# Patterns from bird's runtime-query-ids.ts for parsing JS bundles
# Each tuple: (regex_pattern, query_id_group_index, operation_name_group_index)
OPERATION_PATTERNS = [
    # e.exports={queryId:"...",operationName:"..."}
    (
        r'e\.exports=\{queryId\s*:\s*["\']([^"\']+)["\']\s*,\s*operationName\s*:\s*["\']([^"\']+)["\']',
        1,
        2,
    ),
    # e.exports={operationName:"...",queryId:"..."}
    (
        r'e\.exports=\{operationName\s*:\s*["\']([^"\']+)["\']\s*,\s*queryId\s*:\s*["\']([^"\']+)["\']',
        2,
        1,
    ),
    # operationName:"..."...queryId:"..." (with up to 4000 chars between)
    (
        r'operationName\s*[:=]\s*["\']([^"\']+)["\'](.{0,4000}?)queryId\s*[:=]\s*["\']([^"\']+)["\']',
        3,
        1,
    ),
    # queryId:"..."...operationName:"..." (with up to 4000 chars between)
    (
        r'queryId\s*[:=]\s*["\']([^"\']+)["\'](.{0,4000}?)operationName\s*[:=]\s*["\']([^"\']+)["\']',
        1,
        3,
    ),
]


def extract_bundle_urls(html: str) -> list[str]:
    """Extract Twitter client bundle URLs from HTML content."""
    return re.findall(BUNDLE_URL_PATTERN, html)


def extract_operations(bundle_content: str, targets: set[str]) -> dict[str, str]:
    """Extract query IDs for target operations from JS bundle content."""
    discovered: dict[str, str] = {}
    query_id_regex = re.compile(QUERY_ID_PATTERN)

    for pattern, query_id_group, operation_group in OPERATION_PATTERNS:
        for match in re.finditer(pattern, bundle_content, re.DOTALL):
            operation_name = match.group(operation_group)
            query_id = match.group(query_id_group)

            if operation_name not in targets:
                continue
            if not query_id_regex.match(query_id):
                continue
            if operation_name in discovered:
                continue

            discovered[operation_name] = query_id

            if len(discovered) == len(targets):
                return discovered

    return discovered


_HTML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


async def refresh_query_ids(
    client: httpx.AsyncClient,
    targets: set[str] | None = None,
    discovery_pages: list[str] | None = None,
    cookies: dict[str, str] | None = None,
) -> dict[str, str]:
    """Fetch discovery pages, download bundles, and extract query IDs.

    Discovery pages return HTML (not JSON), so they need browser-like headers
    rather than the API Bearer/x-csrf-token headers that `client` carries.
    A separate httpx client is used for the HTML fetches; `client` is kept for
    any caller that wants to reuse it for subsequent API calls.
    """
    from .constants import TARGET_QUERY_ID_OPERATIONS

    if discovery_pages is None:
        discovery_pages = DISCOVERY_PAGES
    if targets is None:
        targets = set(TARGET_QUERY_ID_OPERATIONS)

    discovered: dict[str, str] = {}

    html_headers = dict(_HTML_HEADERS)
    if cookies:
        html_headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())

    async with httpx.AsyncClient(
        headers=html_headers, follow_redirects=True
    ) as html_client:
        bundle_urls: list[str] = []
        for page in discovery_pages:
            response = await html_client.get(page)
            if response.status_code == 200:
                bundle_urls = extract_bundle_urls(response.text)
                if bundle_urls:
                    break

        for bundle_url in bundle_urls:
            if len(discovered) == len(targets):
                break
            bundle_response = await html_client.get(bundle_url)
            bundle_response.raise_for_status()
            remaining_targets = targets - discovered.keys()
            new_ids = extract_operations(bundle_response.text, remaining_targets)
            discovered.update(new_ids)

    return discovered
