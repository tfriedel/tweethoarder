"""Tests for Twitter client base class."""

import pytest


def test_twitter_client_requires_auth_token() -> None:
    """TwitterClient should raise error if auth_token is missing."""
    from tweethoarder.client.base import TwitterClient

    with pytest.raises(ValueError, match="auth_token"):
        TwitterClient(cookies={"ct0": "test_ct0"})


def test_twitter_client_requires_ct0() -> None:
    """TwitterClient should raise error if ct0 is missing."""
    from tweethoarder.client.base import TwitterClient

    with pytest.raises(ValueError, match="ct0"):
        TwitterClient(cookies={"auth_token": "test_auth"})


def test_twitter_client_creates_with_valid_cookies() -> None:
    """TwitterClient should create successfully with valid cookies."""
    from tweethoarder.client.base import TwitterClient

    client = TwitterClient(cookies={"auth_token": "test_auth", "ct0": "test_ct0"})

    assert isinstance(client, TwitterClient)


def test_get_base_headers_includes_csrf_token() -> None:
    """get_base_headers should include x-csrf-token from ct0 cookie."""
    from tweethoarder.client.base import TwitterClient

    client = TwitterClient(cookies={"auth_token": "test_auth", "ct0": "my_csrf_token"})
    headers = client.get_base_headers()

    assert headers["x-csrf-token"] == "my_csrf_token"


def test_get_base_headers_includes_cookie_header() -> None:
    """get_base_headers should include cookie header with auth cookies."""
    from tweethoarder.client.base import TwitterClient

    client = TwitterClient(cookies={"auth_token": "my_auth", "ct0": "my_ct0"})
    headers = client.get_base_headers()

    assert "auth_token=my_auth" in headers["cookie"]
    assert "ct0=my_ct0" in headers["cookie"]


def test_get_base_headers_includes_bearer_token() -> None:
    """get_base_headers should include static Bearer authorization token."""
    from tweethoarder.client.base import BEARER_TOKEN, TwitterClient

    client = TwitterClient(cookies={"auth_token": "test_auth", "ct0": "test_ct0"})
    headers = client.get_base_headers()

    assert headers["authorization"] == BEARER_TOKEN


def test_get_json_headers_includes_content_type() -> None:
    """get_json_headers should include JSON content-type."""
    from tweethoarder.client.base import TwitterClient

    client = TwitterClient(cookies={"auth_token": "test_auth", "ct0": "test_ct0"})
    headers = client.get_json_headers()

    assert headers["content-type"] == "application/json"
    # Should also include base headers
    assert "authorization" in headers
