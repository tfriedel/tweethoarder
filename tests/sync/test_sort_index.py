"""Tests for sort index generation."""

from pathlib import Path


def test_generator_starts_at_initial_value() -> None:
    """SortIndexGenerator should start at the initial value by default."""
    from tweethoarder.sync.sort_index import INITIAL_SORT_INDEX, SortIndexGenerator

    gen = SortIndexGenerator()

    assert gen.current == INITIAL_SORT_INDEX


def test_generator_decrements_on_each_call() -> None:
    """SortIndexGenerator.next() should decrement and return values."""
    from tweethoarder.sync.sort_index import SortIndexGenerator

    gen = SortIndexGenerator("1000")

    first = gen.next()
    second = gen.next()
    third = gen.next()

    assert first == "1000"
    assert second == "999"
    assert third == "998"
    assert gen.current == "997"


def test_from_checkpoint_uses_saved_counter(tmp_path: Path) -> None:
    """from_checkpoint_or_db should use counter from saved checkpoint."""
    from tweethoarder.storage.checkpoint import SyncCheckpoint
    from tweethoarder.storage.database import init_database
    from tweethoarder.sync.sort_index import SortIndexGenerator

    db_path = tmp_path / "test.db"
    init_database(db_path)

    checkpoint = SyncCheckpoint(db_path)
    checkpoint.save(
        collection_type="like",
        cursor="cursor123",
        last_tweet_id="tweet456",
        sort_index_counter="5000",
    )

    gen = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "like", db_path)

    assert gen.current == "5000"


def test_from_checkpoint_derives_from_existing_data(tmp_path: Path) -> None:
    """from_checkpoint_or_db should derive counter from existing min(sort_index) - 1."""
    from tweethoarder.storage.checkpoint import SyncCheckpoint
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet
    from tweethoarder.sync.sort_index import SortIndexGenerator

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Add some tweets to collection with sort_index values
    for i, sort_index in enumerate(["3000", "1000", "2000"], start=1):
        save_tweet(
            db_path,
            {
                "id": str(i),
                "text": f"Tweet {i}",
                "author_id": "100",
                "author_username": "user",
                "created_at": f"2025-01-0{i}T12:00:00Z",
            },
        )
        add_to_collection(db_path, str(i), "like", sort_index=sort_index)

    checkpoint = SyncCheckpoint(db_path)
    # No checkpoint saved - should derive from min(sort_index) - 1 = 999

    gen = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "like", db_path)

    assert gen.current == "999"


def test_from_checkpoint_uses_initial_for_empty_db(tmp_path: Path) -> None:
    """from_checkpoint_or_db should use INITIAL_SORT_INDEX for empty database."""
    from tweethoarder.storage.checkpoint import SyncCheckpoint
    from tweethoarder.storage.database import init_database
    from tweethoarder.sync.sort_index import INITIAL_SORT_INDEX, SortIndexGenerator

    db_path = tmp_path / "test.db"
    init_database(db_path)

    checkpoint = SyncCheckpoint(db_path)
    # No checkpoint, no data - should use initial value

    gen = SortIndexGenerator.from_checkpoint_or_db(checkpoint, "like", db_path)

    assert gen.current == INITIAL_SORT_INDEX
