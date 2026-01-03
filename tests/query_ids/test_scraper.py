"""Tests for query ID scraper."""

import pytest


def test_extract_bundle_urls_from_html() -> None:
    """extract_bundle_urls should find all client bundle URLs in HTML."""
    from tweethoarder.query_ids.scraper import extract_bundle_urls

    html = """
    <html>
    <script src="https://abs.twimg.com/responsive-web/client-web/main.abc123.js"></script>
    <script src="https://abs.twimg.com/responsive-web/client-web-legacy/bundle.xyz789.js"></script>
    <script src="https://example.com/other.js"></script>
    </html>
    """

    urls = extract_bundle_urls(html)

    assert len(urls) == 2
    assert "https://abs.twimg.com/responsive-web/client-web/main.abc123.js" in urls
    assert "https://abs.twimg.com/responsive-web/client-web-legacy/bundle.xyz789.js" in urls


def test_extract_operations_finds_query_id_then_operation_name() -> None:
    """extract_operations should parse pattern: queryId, then operationName."""
    from tweethoarder.query_ids.scraper import extract_operations

    # Pattern from bird: e.exports={queryId:"...",operationName:"..."}
    bundle_js = """
    e.exports={queryId:"RV1g3b8n_SGOHwkqKYSCFw",operationName:"Bookmarks"}
    e.exports={queryId:"JR2gceKucIKcVNB_9JkhsA",operationName:"Likes"}
    """

    result = extract_operations(bundle_js, {"Bookmarks", "Likes"})

    assert result["Bookmarks"] == "RV1g3b8n_SGOHwkqKYSCFw"
    assert result["Likes"] == "JR2gceKucIKcVNB_9JkhsA"


def test_extract_operations_finds_operation_name_then_query_id() -> None:
    """extract_operations should parse pattern: operationName, then queryId."""
    from tweethoarder.query_ids.scraper import extract_operations

    # Alternate pattern: e.exports={operationName:"...",queryId:"..."}
    bundle_js = """
    e.exports={operationName:"TweetDetail",queryId:"97JF30KziU00483E_8elBA"}
    """

    result = extract_operations(bundle_js, {"TweetDetail"})

    assert result["TweetDetail"] == "97JF30KziU00483E_8elBA"


def test_extract_operations_only_returns_target_operations() -> None:
    """extract_operations should ignore operations not in targets set."""
    from tweethoarder.query_ids.scraper import extract_operations

    bundle_js = """
    e.exports={queryId:"RV1g3b8n_SGOHwkqKYSCFw",operationName:"Bookmarks"}
    e.exports={queryId:"JR2gceKucIKcVNB_9JkhsA",operationName:"Likes"}
    e.exports={queryId:"ABCD1234",operationName:"SomeOtherOperation"}
    """

    result = extract_operations(bundle_js, {"Bookmarks"})

    assert len(result) == 1
    assert "Bookmarks" in result
    assert "Likes" not in result
    assert "SomeOtherOperation" not in result


def test_extract_operations_rejects_invalid_query_ids() -> None:
    """extract_operations should skip entries with invalid query ID formats."""
    from tweethoarder.query_ids.scraper import extract_operations

    bundle_js = """
    e.exports={queryId:"valid_id-123",operationName:"ValidOp"}
    e.exports={queryId:"has spaces",operationName:"InvalidOp1"}
    e.exports={queryId:"special!chars",operationName:"InvalidOp2"}
    """

    result = extract_operations(bundle_js, {"ValidOp", "InvalidOp1", "InvalidOp2"})

    assert len(result) == 1
    assert "ValidOp" in result
    assert "InvalidOp1" not in result
    assert "InvalidOp2" not in result


@pytest.mark.asyncio
async def test_refresh_query_ids_fetches_pages_and_extracts_ids() -> None:
    """refresh_query_ids should fetch discovery pages, bundles, and extract query IDs."""
    from unittest.mock import AsyncMock

    import httpx

    from tweethoarder.query_ids.scraper import refresh_query_ids

    # Mock HTTP client that returns discovery page with bundle URLs,
    # then bundle content with query IDs
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    discovery_html = """
    <html>
    <script src="https://abs.twimg.com/responsive-web/client-web/main.abc123.js"></script>
    </html>
    """
    bundle_js = """
    e.exports={queryId:"new_bookmarks_id",operationName:"Bookmarks"}
    e.exports={queryId:"new_likes_id",operationName:"Likes"}
    """

    # Create mock responses
    discovery_response = AsyncMock()
    discovery_response.text = discovery_html
    discovery_response.raise_for_status = AsyncMock()

    bundle_response = AsyncMock()
    bundle_response.text = bundle_js
    bundle_response.raise_for_status = AsyncMock()

    mock_client.get.side_effect = [discovery_response, bundle_response]

    result = await refresh_query_ids(mock_client, targets={"Bookmarks", "Likes"})

    assert result["Bookmarks"] == "new_bookmarks_id"
    assert result["Likes"] == "new_likes_id"


@pytest.mark.asyncio
async def test_refresh_query_ids_tries_multiple_bundles() -> None:
    """refresh_query_ids should try multiple bundles until all targets found."""
    from unittest.mock import AsyncMock

    import httpx

    from tweethoarder.query_ids.scraper import refresh_query_ids

    mock_client = AsyncMock(spec=httpx.AsyncClient)

    discovery_html = """
    <html>
    <script src="https://abs.twimg.com/responsive-web/client-web/bundle1.js"></script>
    <script src="https://abs.twimg.com/responsive-web/client-web/bundle2.js"></script>
    </html>
    """
    # First bundle has only Bookmarks
    bundle1_js = 'e.exports={queryId:"bookmarks_id",operationName:"Bookmarks"}'
    # Second bundle has Likes
    bundle2_js = 'e.exports={queryId:"likes_id",operationName:"Likes"}'

    discovery_response = AsyncMock()
    discovery_response.text = discovery_html

    bundle1_response = AsyncMock()
    bundle1_response.text = bundle1_js

    bundle2_response = AsyncMock()
    bundle2_response.text = bundle2_js

    mock_client.get.side_effect = [discovery_response, bundle1_response, bundle2_response]

    result = await refresh_query_ids(mock_client, targets={"Bookmarks", "Likes"})

    assert result["Bookmarks"] == "bookmarks_id"
    assert result["Likes"] == "likes_id"


@pytest.mark.asyncio
async def test_refresh_query_ids_defaults_to_all_target_operations() -> None:
    """refresh_query_ids should target all operations from TARGET_QUERY_ID_OPERATIONS by default."""
    from unittest.mock import AsyncMock

    import httpx

    from tweethoarder.query_ids.constants import TARGET_QUERY_ID_OPERATIONS
    from tweethoarder.query_ids.scraper import refresh_query_ids

    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Bundle contains all target operations
    bundle_js = "\n".join(
        f'e.exports={{queryId:"{op}_id",operationName:"{op}"}}' for op in TARGET_QUERY_ID_OPERATIONS
    )

    discovery_html = """
    <html>
    <script src="https://abs.twimg.com/responsive-web/client-web/main.js"></script>
    </html>
    """

    discovery_response = AsyncMock()
    discovery_response.text = discovery_html

    bundle_response = AsyncMock()
    bundle_response.text = bundle_js

    mock_client.get.side_effect = [discovery_response, bundle_response]

    # Call without specifying targets - should use default
    result = await refresh_query_ids(mock_client)

    # Should find all target operations
    assert len(result) == len(TARGET_QUERY_ID_OPERATIONS)
    for op in TARGET_QUERY_ID_OPERATIONS:
        assert op in result
