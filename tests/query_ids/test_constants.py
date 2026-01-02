"""Tests for query ID constants."""


def test_twitter_api_base_is_graphql_endpoint() -> None:
    """TWITTER_API_BASE should point to the GraphQL API endpoint."""
    from tweethoarder.query_ids.constants import TWITTER_API_BASE

    assert TWITTER_API_BASE == "https://x.com/i/api/graphql"


def test_fallback_query_ids_contains_required_operations() -> None:
    """FALLBACK_QUERY_IDS should contain IDs for all required operations."""
    from tweethoarder.query_ids.constants import FALLBACK_QUERY_IDS

    required_operations = ["Bookmarks", "Likes", "TweetDetail"]
    for op in required_operations:
        assert op in FALLBACK_QUERY_IDS
        assert isinstance(FALLBACK_QUERY_IDS[op], str)
        assert len(FALLBACK_QUERY_IDS[op]) > 0


def test_target_query_id_operations_matches_fallback_keys() -> None:
    """TARGET_QUERY_ID_OPERATIONS should list all operations from FALLBACK_QUERY_IDS."""
    from tweethoarder.query_ids.constants import (
        FALLBACK_QUERY_IDS,
        TARGET_QUERY_ID_OPERATIONS,
    )

    assert set(TARGET_QUERY_ID_OPERATIONS) == set(FALLBACK_QUERY_IDS.keys())


def test_default_ttl_is_24_hours() -> None:
    """DEFAULT_TTL_SECONDS should be 24 hours."""
    from tweethoarder.query_ids.constants import DEFAULT_TTL_SECONDS

    assert DEFAULT_TTL_SECONDS == 24 * 60 * 60


def test_discovery_pages_contains_x_dot_com_urls() -> None:
    """DISCOVERY_PAGES should contain x.com URLs for bundle discovery."""
    from tweethoarder.query_ids.constants import DISCOVERY_PAGES

    assert len(DISCOVERY_PAGES) >= 1
    for url in DISCOVERY_PAGES:
        assert url.startswith("https://x.com/")


def test_bundle_url_pattern_matches_twimg_js_files() -> None:
    """BUNDLE_URL_PATTERN should match Twitter client bundle URLs."""
    import re

    from tweethoarder.query_ids.constants import BUNDLE_URL_PATTERN

    valid_urls = [
        "https://abs.twimg.com/responsive-web/client-web/main.abc123.js",
        "https://abs.twimg.com/responsive-web/client-web-legacy/bundle.xyz.js",
    ]
    for url in valid_urls:
        assert re.match(BUNDLE_URL_PATTERN, url), f"Should match: {url}"

    invalid_urls = [
        "https://example.com/script.js",
        "https://abs.twimg.com/other/file.js",
    ]
    for url in invalid_urls:
        assert not re.match(BUNDLE_URL_PATTERN, url), f"Should not match: {url}"


def test_query_id_pattern_validates_alphanumeric_with_dashes() -> None:
    """QUERY_ID_PATTERN should match valid query ID formats."""
    import re

    from tweethoarder.query_ids.constants import QUERY_ID_PATTERN

    valid_ids = ["RV1g3b8n_SGOHwkqKYSCFw", "abc123", "ABC-xyz_123"]
    for qid in valid_ids:
        assert re.match(QUERY_ID_PATTERN, qid), f"Should match: {qid}"

    invalid_ids = ["has spaces", "special!char", ""]
    for qid in invalid_ids:
        assert not re.match(QUERY_ID_PATTERN, qid), f"Should not match: {qid}"
