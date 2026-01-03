"""CSV export functionality for TweetHoarder."""

import csv
import io
from typing import Any

CSV_COLUMNS = ["id", "text", "author_username", "author_display_name", "created_at"]


def export_tweets_to_csv(tweets: list[dict[str, Any]]) -> str:
    """Export tweets to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS)
    for tweet in tweets:
        writer.writerow([tweet.get(col, "") for col in CSV_COLUMNS])
    return output.getvalue()
