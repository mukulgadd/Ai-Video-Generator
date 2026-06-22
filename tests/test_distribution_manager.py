"""Tests for the Distribution Manager.

Includes property-based tests (Hypothesis) and unit tests for cloud storage
upload, standardized file naming, platform publishing, thumbnail upload,
retry logic with exponential backoff, and distribution logging.

Uses mock implementations to test distribution logic without requiring
real cloud services.
"""

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from src.config_loader import DistributionConfig, PlatformConfig, StorageConfig
from src.distribution_manager import (
    BACKOFF_MULTIPLIER,
    FILENAME_PATTERN,
    INITIAL_BACKOFF_SECONDS,
    MAX_RETRY_ATTEMPTS,
    DistributionError,
    DistributionLogEntry,
    DistributionManager,
    DistributionResult,
    MockPlatformPublisher,
    MockStorageUploader,
    PlatformMetadata,
    generate_filename,
    generate_platform_metadata,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_storage_config(
    provider: str = "s3",
    bucket: str = "ramayan-videos",
    path_prefix: str = "episodes/",
) -> StorageConfig:
    """Create a StorageConfig for testing."""
    return StorageConfig(
        provider=provider,
        bucket=bucket,
        path_prefix=path_prefix,
    )


def _make_distribution_config(
    youtube_enabled: bool = False,
    instagram_enabled: bool = False,
) -> DistributionConfig:
    """Create a DistributionConfig for testing."""
    return DistributionConfig(
        youtube=PlatformConfig(
            enabled=youtube_enabled,
            credentials_path="./credentials/youtube.json",
        ),
        instagram=PlatformConfig(
            enabled=instagram_enabled,
            credentials_path="./credentials/instagram.json",
        ),
    )


def _make_manager(
    storage_uploader: Optional[Any] = None,
    platform_publishers: Optional[List[Any]] = None,
    max_retries: int = MAX_RETRY_ATTEMPTS,
    initial_backoff: float = 0.0,
    backoff_multiplier: float = BACKOFF_MULTIPLIER,
    sleep_fn: Optional[Any] = None,
) -> DistributionManager:
    """Create a DistributionManager for testing."""
    return DistributionManager(
        storage_config=_make_storage_config(),
        distribution_config=_make_distribution_config(),
        storage_uploader=storage_uploader or MockStorageUploader(),
        platform_publishers=platform_publishers or [],
        max_retries=max_retries,
        initial_backoff=initial_backoff,
        backoff_multiplier=backoff_multiplier,
        sleep_fn=sleep_fn or (lambda x: None),
    )


def _create_mock_video(tmp_path, name: str = "video.mp4") -> str:
    """Create a placeholder video file for testing."""
    video_path = os.path.join(str(tmp_path), name)
    with open(video_path, "w") as f:
        f.write("mock_video_data")
    return video_path


def _create_mock_thumbnail(tmp_path, name: str = "thumb.png") -> str:
    """Create a placeholder thumbnail file for testing."""
    thumb_path = os.path.join(str(tmp_path), name)
    with open(thumb_path, "w") as f:
        f.write("mock_thumbnail_data")
    return thumb_path


# ---------------------------------------------------------------------------
# Task 9.1: Cloud Storage Upload Tests
# ---------------------------------------------------------------------------


class TestCloudStorageUpload:
    """Tests for uploading video files to cloud storage."""

    def test_upload_to_storage_success(self, tmp_path):
        """Successful upload returns a URL."""
        uploader = MockStorageUploader()
        manager = _make_manager(storage_uploader=uploader)
        video_path = _create_mock_video(tmp_path)

        url = manager.upload_to_storage(
            local_path=video_path,
            remote_filename="test_video.mp4",
        )

        assert url is not None
        assert "ramayan-videos" in url
        assert "episodes/test_video.mp4" in url
        assert len(uploader.upload_calls) == 1

    def test_upload_uses_configured_bucket(self, tmp_path):
        """Upload uses the configured bucket name."""
        uploader = MockStorageUploader()
        manager = DistributionManager(
            storage_config=_make_storage_config(bucket="my-custom-bucket"),
            distribution_config=_make_distribution_config(),
            storage_uploader=uploader,
            sleep_fn=lambda x: None,
        )
        video_path = _create_mock_video(tmp_path)

        url = manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
        )

        assert url is not None
        assert "my-custom-bucket" in url

    def test_upload_uses_path_prefix(self, tmp_path):
        """Upload prepends the configured path prefix."""
        uploader = MockStorageUploader()
        manager = DistributionManager(
            storage_config=_make_storage_config(path_prefix="custom/path/"),
            distribution_config=_make_distribution_config(),
            storage_uploader=uploader,
            sleep_fn=lambda x: None,
        )
        video_path = _create_mock_video(tmp_path)

        manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
        )

        assert uploader.upload_calls[0]["remote_key"] == "custom/path/video.mp4"


# ---------------------------------------------------------------------------
# Task 9.2: Standardized File Naming Tests
# ---------------------------------------------------------------------------


class TestFileNaming:
    """Tests for standardized file naming convention."""

    def test_basic_filename(self):
        """Basic filename generation matches expected pattern."""
        date = datetime(2024, 3, 15, tzinfo=timezone.utc)
        filename = generate_filename(1, "Bala Kanda", date)
        assert filename == "ramayan_e0001_bala_kanda_20240315.mp4"

    def test_episode_number_padding(self):
        """Episode number is zero-padded to 4 digits."""
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert generate_filename(1, "Bala Kanda", date).startswith("ramayan_e0001_")
        assert generate_filename(42, "Bala Kanda", date).startswith("ramayan_e0042_")
        assert generate_filename(999, "Bala Kanda", date).startswith("ramayan_e0999_")
        assert generate_filename(9999, "Bala Kanda", date).startswith("ramayan_e9999_")

    def test_kanda_name_lowercase_underscores(self):
        """Kanda name is lowercased with spaces replaced by underscores."""
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        filename = generate_filename(1, "Ayodhya Kanda", date)
        assert "_ayodhya_kanda_" in filename

    def test_all_kanda_names(self):
        """All seven Kanda names produce valid filenames."""
        date = datetime(2024, 6, 15, tzinfo=timezone.utc)
        kandas = [
            "Bala Kanda", "Ayodhya Kanda", "Aranya Kanda",
            "Kishkindha Kanda", "Sundara Kanda", "Yuddha Kanda",
            "Uttara Kanda",
        ]
        for kanda in kandas:
            filename = generate_filename(1, kanda, date)
            assert FILENAME_PATTERN.match(filename), (
                f"Filename '{filename}' does not match pattern"
            )

    def test_date_format(self):
        """Date is formatted as YYYYMMDD."""
        date = datetime(2025, 12, 31, tzinfo=timezone.utc)
        filename = generate_filename(1, "Bala Kanda", date)
        assert filename.endswith("_20251231.mp4")


# ---------------------------------------------------------------------------
# Task 9.3: Platform Publishing Tests
# ---------------------------------------------------------------------------


class TestPlatformPublishing:
    """Tests for optional platform publishing."""

    def test_publish_to_youtube(self, tmp_path):
        """Publishing to YouTube returns a URL."""
        publisher = MockPlatformPublisher(name="youtube")
        manager = _make_manager(platform_publishers=[publisher])
        video_path = _create_mock_video(tmp_path)

        metadata = generate_platform_metadata(
            episode_number=1,
            title="The Birth of Rama",
            kanda_name="Bala Kanda",
        )

        urls = manager.publish_to_platforms(
            video_path=video_path,
            metadata=metadata,
        )

        assert "youtube" in urls
        assert "youtube.com" in urls["youtube"]

    def test_publish_to_multiple_platforms(self, tmp_path):
        """Publishing to multiple platforms returns URLs for each."""
        yt = MockPlatformPublisher(name="youtube")
        ig = MockPlatformPublisher(name="instagram")
        manager = _make_manager(platform_publishers=[yt, ig])
        video_path = _create_mock_video(tmp_path)

        metadata = generate_platform_metadata(
            episode_number=1,
            title="The Birth of Rama",
            kanda_name="Bala Kanda",
        )

        urls = manager.publish_to_platforms(
            video_path=video_path,
            metadata=metadata,
        )

        assert "youtube" in urls
        assert "instagram" in urls

    def test_auto_generated_metadata(self):
        """Platform metadata is auto-generated with title, description, tags."""
        metadata = generate_platform_metadata(
            episode_number=5,
            title="The Exile",
            kanda_name="Ayodhya Kanda",
            narration_summary="Rama leaves for the forest.",
        )

        assert "Ramayan Episode 5" in metadata.title
        assert "The Exile" in metadata.title
        assert "Ayodhya Kanda" in metadata.title
        assert "Ayodhya Kanda" in metadata.description
        assert "Rama leaves for the forest." in metadata.description
        assert "Ramayan" in metadata.tags
        assert "Hindu Mythology" in metadata.tags
        assert "Ayodhya Kanda" in metadata.tags

    def test_no_publishers_returns_empty(self, tmp_path):
        """No platform publishers returns empty dict."""
        manager = _make_manager(platform_publishers=[])
        video_path = _create_mock_video(tmp_path)

        metadata = generate_platform_metadata(
            episode_number=1,
            title="Test",
            kanda_name="Bala Kanda",
        )

        urls = manager.publish_to_platforms(
            video_path=video_path,
            metadata=metadata,
        )

        assert urls == {}


# ---------------------------------------------------------------------------
# Task 9.4: Thumbnail Upload Tests
# ---------------------------------------------------------------------------


class TestThumbnailUpload:
    """Tests for thumbnail upload alongside video."""

    def test_thumbnail_upload_success(self, tmp_path):
        """Thumbnail is uploaded with _thumb suffix."""
        uploader = MockStorageUploader()
        manager = _make_manager(storage_uploader=uploader)
        thumb_path = _create_mock_thumbnail(tmp_path)

        url = manager.upload_thumbnail(
            thumbnail_path=thumb_path,
            remote_filename="ramayan_e0001_bala_kanda_20240315.mp4",
        )

        assert url is not None
        assert len(uploader.upload_calls) == 1
        remote_key = uploader.upload_calls[0]["remote_key"]
        assert "thumb" in remote_key
        assert remote_key.endswith(".png")

    def test_thumbnail_in_distribute_flow(self, tmp_path):
        """Thumbnail is uploaded during full distribute flow."""
        uploader = MockStorageUploader()
        manager = _make_manager(storage_uploader=uploader)
        video_path = _create_mock_video(tmp_path)
        thumb_path = _create_mock_thumbnail(tmp_path)

        result = manager.distribute(
            video_path=video_path,
            episode_number=1,
            kanda_name="Bala Kanda",
            title="The Birth of Rama",
            thumbnail_path=thumb_path,
            date=datetime(2024, 3, 15, tzinfo=timezone.utc),
        )

        assert result.thumbnail_url is not None
        # Two uploads: video + thumbnail
        assert len(uploader.upload_calls) == 2


# ---------------------------------------------------------------------------
# Task 9.5: Retry Logic Tests
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Tests for retry with exponential backoff."""

    def test_retry_succeeds_after_failures(self, tmp_path):
        """Upload succeeds after initial failures within retry limit."""
        uploader = MockStorageUploader(fail_count=2)
        manager = _make_manager(
            storage_uploader=uploader,
            max_retries=3,
        )
        video_path = _create_mock_video(tmp_path)

        url = manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
        )

        assert url is not None

    def test_retry_fails_after_max_attempts(self, tmp_path):
        """Upload returns None after exhausting all retries."""
        uploader = MockStorageUploader(fail_count=5)
        manager = _make_manager(
            storage_uploader=uploader,
            max_retries=3,
        )
        video_path = _create_mock_video(tmp_path)

        url = manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
        )

        assert url is None

    def test_exponential_backoff_delays(self, tmp_path):
        """Retry uses exponential backoff with increasing delays."""
        sleep_calls: List[float] = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        uploader = MockStorageUploader(fail_count=3)
        manager = _make_manager(
            storage_uploader=uploader,
            max_retries=3,
            initial_backoff=1.0,
            backoff_multiplier=2.0,
            sleep_fn=mock_sleep,
        )
        video_path = _create_mock_video(tmp_path)

        # All 3 attempts fail, so we get 2 sleeps (between attempts)
        manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
        )

        assert len(sleep_calls) == 2
        assert sleep_calls[0] == pytest.approx(1.0)
        assert sleep_calls[1] == pytest.approx(2.0)

    def test_platform_publish_retry(self, tmp_path):
        """Platform publishing retries on failure."""
        publisher = MockPlatformPublisher(name="youtube", fail_count=1)
        manager = _make_manager(
            platform_publishers=[publisher],
            max_retries=3,
        )
        video_path = _create_mock_video(tmp_path)

        metadata = generate_platform_metadata(
            episode_number=1,
            title="Test",
            kanda_name="Bala Kanda",
        )

        urls = manager.publish_to_platforms(
            video_path=video_path,
            metadata=metadata,
        )

        assert "youtube" in urls


# ---------------------------------------------------------------------------
# Task 9.6: Distribution Logging Tests
# ---------------------------------------------------------------------------


class TestDistributionLogging:
    """Tests for distribution event logging."""

    def test_successful_upload_logged(self, tmp_path):
        """Successful upload creates a log entry with status and URL."""
        manager = _make_manager()
        video_path = _create_mock_video(tmp_path)

        manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
            episode_number=1,
            kanda_name="Bala Kanda",
        )

        log = manager.distribution_log
        assert len(log) == 1
        assert log[0].status == "success"
        assert log[0].url is not None
        assert log[0].platform == "s3"
        assert log[0].timestamp is not None

    def test_failed_upload_logged(self, tmp_path):
        """Failed upload creates a log entry with error details."""
        uploader = MockStorageUploader(fail_count=5)
        manager = _make_manager(
            storage_uploader=uploader,
            max_retries=3,
        )
        video_path = _create_mock_video(tmp_path)

        manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
            episode_number=1,
            kanda_name="Bala Kanda",
        )

        log = manager.distribution_log
        assert len(log) == 1
        assert log[0].status == "failed"
        assert log[0].url is None
        assert log[0].error_message is not None

    def test_full_distribute_logs_all_events(self, tmp_path):
        """Full distribute logs events for storage and platforms."""
        yt = MockPlatformPublisher(name="youtube")
        manager = _make_manager(platform_publishers=[yt])
        video_path = _create_mock_video(tmp_path)

        result = manager.distribute(
            video_path=video_path,
            episode_number=1,
            kanda_name="Bala Kanda",
            title="The Birth of Rama",
            date=datetime(2024, 3, 15, tzinfo=timezone.utc),
        )

        # Should have log entries for storage + youtube
        assert len(result.log_entries) >= 2
        platforms = [e.platform for e in result.log_entries]
        assert "s3" in platforms
        assert "youtube" in platforms

    def test_log_entry_has_timestamp(self, tmp_path):
        """Every log entry has a valid ISO 8601 timestamp."""
        manager = _make_manager()
        video_path = _create_mock_video(tmp_path)

        manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
        )

        log = manager.distribution_log
        assert len(log) == 1
        # Verify timestamp is valid ISO 8601
        ts = log[0].timestamp
        parsed = datetime.fromisoformat(ts)
        assert parsed is not None


# ---------------------------------------------------------------------------
# Full Distribution Flow Test
# ---------------------------------------------------------------------------


class TestFullDistributionFlow:
    """Integration tests for the full distribution pipeline."""

    def test_distribute_basic(self, tmp_path):
        """Basic distribution uploads video and returns result."""
        manager = _make_manager()
        video_path = _create_mock_video(tmp_path)

        result = manager.distribute(
            video_path=video_path,
            episode_number=1,
            kanda_name="Bala Kanda",
            title="The Birth of Rama",
            date=datetime(2024, 3, 15, tzinfo=timezone.utc),
        )

        assert result.episode_number == 1
        assert result.kanda_name == "Bala Kanda"
        assert result.filename == "ramayan_e0001_bala_kanda_20240315.mp4"
        assert result.storage_url is not None
        assert result.all_successful is True

    def test_distribute_with_platforms(self, tmp_path):
        """Distribution with platform publishers uploads to all targets."""
        yt = MockPlatformPublisher(name="youtube")
        ig = MockPlatformPublisher(name="instagram")
        manager = _make_manager(platform_publishers=[yt, ig])
        video_path = _create_mock_video(tmp_path)

        result = manager.distribute(
            video_path=video_path,
            episode_number=5,
            kanda_name="Sundara Kanda",
            title="Hanuman's Leap",
            date=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )

        assert result.storage_url is not None
        assert "youtube" in result.platform_urls
        assert "instagram" in result.platform_urls
        assert result.all_successful is True

    def test_distribute_partial_failure(self, tmp_path):
        """Partial failure marks result as not all successful."""
        yt = MockPlatformPublisher(name="youtube", fail_count=5)
        manager = _make_manager(
            platform_publishers=[yt],
            max_retries=3,
        )
        video_path = _create_mock_video(tmp_path)

        result = manager.distribute(
            video_path=video_path,
            episode_number=1,
            kanda_name="Bala Kanda",
            title="Test",
            date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        assert result.storage_url is not None
        assert "youtube" not in result.platform_urls
        assert result.all_successful is False



# ---------------------------------------------------------------------------
# Task 9.7.1 [PBT] Property 14: Distribution Naming Convention
# ---------------------------------------------------------------------------


@st.composite
def filename_params_strategy(draw):
    """Generate random episode numbers, kanda names, and dates for filename testing."""
    episode_number = draw(st.integers(min_value=1, max_value=9999))

    kanda_name = draw(
        st.sampled_from([
            "Bala Kanda",
            "Ayodhya Kanda",
            "Aranya Kanda",
            "Kishkindha Kanda",
            "Sundara Kanda",
            "Yuddha Kanda",
            "Uttara Kanda",
        ])
    )

    date = draw(
        st.dates(
            min_value=datetime(2000, 1, 1).date(),
            max_value=datetime(2099, 12, 31).date(),
        )
    )

    return {
        "episode_number": episode_number,
        "kanda_name": kanda_name,
        "date": datetime(date.year, date.month, date.day, tzinfo=timezone.utc),
    }


@given(params=filename_params_strategy())
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
def test_property_14_distribution_naming_convention(params):
    """**Validates: Requirements 9.2**

    Property 14: For any episode with a given episode number, Kanda name,
    and date, the generated filename matches the pattern
    `ramayan_e{NNNN}_{kanda_name}_{YYYYMMDD}.mp4`.

    We generate random episode numbers (1-9999), kanda names, and dates,
    then verify the filename matches the expected pattern.
    """
    filename = generate_filename(
        episode_number=params["episode_number"],
        kanda_name=params["kanda_name"],
        date=params["date"],
    )

    # Verify overall pattern match
    assert FILENAME_PATTERN.match(filename), (
        f"Filename '{filename}' does not match pattern "
        f"'ramayan_e{{NNNN}}_{{kanda_name}}_{{YYYYMMDD}}.mp4'"
    )

    # Verify episode number is zero-padded to 4 digits
    ep_str = f"e{params['episode_number']:04d}"
    assert ep_str in filename, (
        f"Expected '{ep_str}' in filename '{filename}'"
    )

    # Verify kanda name is lowercase with underscores
    expected_kanda = params["kanda_name"].lower().replace(" ", "_")
    assert expected_kanda in filename, (
        f"Expected '{expected_kanda}' in filename '{filename}'"
    )

    # Verify date format YYYYMMDD
    expected_date = params["date"].strftime("%Y%m%d")
    assert filename.endswith(f"_{expected_date}.mp4"), (
        f"Expected filename to end with '_{expected_date}.mp4', "
        f"got '{filename}'"
    )

    # Verify .mp4 extension
    assert filename.endswith(".mp4"), (
        f"Expected .mp4 extension, got '{filename}'"
    )


# ---------------------------------------------------------------------------
# Task 9.7.2 [PBT] Property 15: Distribution Log Completeness
# ---------------------------------------------------------------------------


@st.composite
def distribution_event_strategy(draw):
    """Generate random distribution events for log completeness testing."""
    episode_number = draw(st.integers(min_value=1, max_value=9999))

    kanda_name = draw(
        st.sampled_from([
            "Bala Kanda",
            "Ayodhya Kanda",
            "Aranya Kanda",
            "Kishkindha Kanda",
            "Sundara Kanda",
            "Yuddha Kanda",
            "Uttara Kanda",
        ])
    )

    title = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
        min_size=1,
        max_size=50,
    ))

    # Whether to include platform publishers
    include_youtube = draw(st.booleans())
    include_instagram = draw(st.booleans())

    # Whether uploads should fail
    storage_fail = draw(st.booleans())

    return {
        "episode_number": episode_number,
        "kanda_name": kanda_name,
        "title": title,
        "include_youtube": include_youtube,
        "include_instagram": include_instagram,
        "storage_fail": storage_fail,
    }


@given(params=distribution_event_strategy())
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
def test_property_15_distribution_log_completeness(params, tmp_path_factory):
    """**Validates: Requirements 9.6**

    Property 15: For any distribution event, the log entry contains all
    required fields: upload status, platform name, URL (if successful),
    and timestamp.

    We generate random distribution events with varying configurations
    and verify every log entry has the required fields.
    """
    tmp_path = tmp_path_factory.mktemp("pbt15")

    # Set up storage uploader (may fail)
    fail_count = 5 if params["storage_fail"] else 0
    uploader = MockStorageUploader(fail_count=fail_count)

    # Set up platform publishers
    publishers: List[Any] = []
    if params["include_youtube"]:
        publishers.append(MockPlatformPublisher(name="youtube"))
    if params["include_instagram"]:
        publishers.append(MockPlatformPublisher(name="instagram"))

    manager = DistributionManager(
        storage_config=_make_storage_config(),
        distribution_config=_make_distribution_config(),
        storage_uploader=uploader,
        platform_publishers=publishers,
        max_retries=3,
        initial_backoff=0.0,
        backoff_multiplier=2.0,
        sleep_fn=lambda x: None,
    )

    video_path = os.path.join(str(tmp_path), "video.mp4")
    with open(video_path, "w") as f:
        f.write("mock")

    result = manager.distribute(
        video_path=video_path,
        episode_number=params["episode_number"],
        kanda_name=params["kanda_name"],
        title=params["title"],
        date=datetime(2024, 6, 15, tzinfo=timezone.utc),
    )

    # Verify every log entry has required fields
    assert len(result.log_entries) > 0, "Expected at least one log entry"

    for entry in result.log_entries:
        # Required: platform name
        assert entry.platform is not None and entry.platform != "", (
            f"Log entry missing platform name: {entry}"
        )

        # Required: upload status
        assert entry.status in ("success", "failed"), (
            f"Log entry has invalid status '{entry.status}': {entry}"
        )

        # Required: URL if successful
        if entry.status == "success":
            assert entry.url is not None and entry.url != "", (
                f"Successful log entry missing URL: {entry}"
            )

        # Required: timestamp
        assert entry.timestamp is not None and entry.timestamp != "", (
            f"Log entry missing timestamp: {entry}"
        )

        # Verify timestamp is valid ISO 8601
        parsed_ts = datetime.fromisoformat(entry.timestamp)
        assert parsed_ts is not None, (
            f"Log entry has invalid timestamp '{entry.timestamp}': {entry}"
        )


# ---------------------------------------------------------------------------
# Task 9.7.3: Retry with Exponential Backoff Test
# ---------------------------------------------------------------------------


class TestRetryExponentialBackoff:
    """Test retry with exponential backoff: mock upload failures,
    verify 3 retries with increasing delays."""

    def test_three_retries_with_increasing_delays(self, tmp_path):
        """Mock upload failures trigger 3 retries with exponential backoff."""
        sleep_calls: List[float] = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        # Uploader fails all 3 attempts
        uploader = MockStorageUploader(fail_count=3)
        manager = _make_manager(
            storage_uploader=uploader,
            max_retries=3,
            initial_backoff=1.0,
            backoff_multiplier=2.0,
            sleep_fn=mock_sleep,
        )
        video_path = _create_mock_video(tmp_path)

        url = manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
        )

        # All 3 attempts failed
        assert url is None

        # 2 sleep calls between 3 attempts (no sleep after last attempt)
        assert len(sleep_calls) == 2

        # Verify exponential backoff: 1.0, 2.0
        assert sleep_calls[0] == pytest.approx(1.0)
        assert sleep_calls[1] == pytest.approx(2.0)

    def test_retry_succeeds_on_third_attempt(self, tmp_path):
        """Upload succeeds on the third attempt after two failures."""
        sleep_calls: List[float] = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        # Uploader fails first 2 attempts, succeeds on 3rd
        uploader = MockStorageUploader(fail_count=2)
        manager = _make_manager(
            storage_uploader=uploader,
            max_retries=3,
            initial_backoff=1.0,
            backoff_multiplier=2.0,
            sleep_fn=mock_sleep,
        )
        video_path = _create_mock_video(tmp_path)

        url = manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
        )

        assert url is not None

        # 2 sleep calls between attempts 1->2 and 2->3
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == pytest.approx(1.0)
        assert sleep_calls[1] == pytest.approx(2.0)

    def test_no_retry_on_immediate_success(self, tmp_path):
        """No retries or sleeps when upload succeeds immediately."""
        sleep_calls: List[float] = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        uploader = MockStorageUploader(fail_count=0)
        manager = _make_manager(
            storage_uploader=uploader,
            max_retries=3,
            initial_backoff=1.0,
            backoff_multiplier=2.0,
            sleep_fn=mock_sleep,
        )
        video_path = _create_mock_video(tmp_path)

        url = manager.upload_to_storage(
            local_path=video_path,
            remote_filename="video.mp4",
        )

        assert url is not None
        assert len(sleep_calls) == 0
