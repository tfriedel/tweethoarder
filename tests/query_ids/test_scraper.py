"""Tests for query ID scraper."""


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
