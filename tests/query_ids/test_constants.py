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
