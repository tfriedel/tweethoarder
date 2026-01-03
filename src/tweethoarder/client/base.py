"""Base Twitter client with HTTP headers and auth handling."""

BEARER_TOKEN = (
    "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)


class TwitterClient:
    """Twitter API client with cookie-based authentication."""

    def __init__(self, cookies: dict[str, str]) -> None:
        """Initialize client with cookies."""
        if "auth_token" not in cookies:
            raise ValueError("auth_token is required")
        if "ct0" not in cookies:
            raise ValueError("ct0 is required")
        self._ct0 = cookies["ct0"]
        self._auth_token = cookies["auth_token"]

    def get_base_headers(self) -> dict[str, str]:
        """Get base HTTP headers for API requests."""
        return {
            "accept": "*/*",
            "authorization": BEARER_TOKEN,
            "x-csrf-token": self._ct0,
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
            "cookie": f"auth_token={self._auth_token}; ct0={self._ct0}",
            "origin": "https://x.com",
            "referer": "https://x.com/",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        }

    def get_json_headers(self) -> dict[str, str]:
        """Get HTTP headers for JSON API requests."""
        return {
            **self.get_base_headers(),
            "content-type": "application/json",
        }
