"""Bundle discovery and query ID extraction from Twitter client JS."""

import re

from .constants import BUNDLE_URL_PATTERN, QUERY_ID_PATTERN

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
