"""Distribution Manager for the Ramayan Video Generator.

Stores and publishes finished videos to cloud storage and optional
social media platforms. Implements standardized file naming, thumbnail
upload, retry logic with exponential backoff, and distribution logging.

Uses Protocol-based design for storage and platform uploaders to enable
dependency injection and testability without requiring real cloud services.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from src.config_loader import DistributionConfig, StorageConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRY_ATTEMPTS = 3
INITIAL_BACKOFF_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0

# Filename pattern: ramayan_e{NNNN}_{kanda_name}_{YYYYMMDD}.mp4
FILENAME_PATTERN = re.compile(
    r"^ramayan_e\d{4}_[a-z]+(?:_[a-z]+)*_\d{8}\.mp4$"
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class DistributionError(Exception):
    """Raised when the DistributionManager encounters an error."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class DistributionLogEntry:
    """A single distribution event log entry."""

    platform: str
    status: str  # "success" or "failed"
    url: Optional[str]
    timestamp: str  # ISO 8601 format
    episode_number: int = 0
    kanda_name: str = ""
    error_message: Optional[str] = None


@dataclass
class DistributionResult:
    """Result of distributing a video to all configured targets."""

    episode_number: int
    kanda_name: str
    filename: str
    storage_url: Optional[str] = None
    platform_urls: Dict[str, str] = field(default_factory=dict)
    thumbnail_url: Optional[str] = None
    log_entries: List[DistributionLogEntry] = field(default_factory=list)
    all_successful: bool = False


@dataclass
class PlatformMetadata:
    """Auto-generated metadata for platform publishing."""

    title: str
    description: str
    tags: List[str]


# ---------------------------------------------------------------------------
# StorageUploader Protocol
# ---------------------------------------------------------------------------


class StorageUploader(Protocol):
    """Protocol for cloud storage upload operations (e.g., S3/GCS).

    Concrete implementations handle the actual file upload to cloud storage.
    A mock implementation is provided for testing.
    """

    def upload_file(
        self,
        local_path: str,
        bucket: str,
        remote_key: str,
    ) -> str:
        """Upload a file to cloud storage.

        Args:
            local_path: Path to the local file.
            bucket: Storage bucket name.
            remote_key: Remote object key / path.

        Returns:
            URL of the uploaded file.

        Raises:
            DistributionError: If the upload fails.
        """
        ...


# ---------------------------------------------------------------------------
# PlatformPublisher Protocol
# ---------------------------------------------------------------------------


class PlatformPublisher(Protocol):
    """Protocol for social media / video platform publishing.

    Concrete implementations handle uploading to YouTube, Instagram, etc.
    A mock implementation is provided for testing.
    """

    @property
    def platform_name(self) -> str:
        """Name of the platform (e.g., 'youtube', 'instagram')."""
        ...

    def publish(
        self,
        video_path: str,
        metadata: PlatformMetadata,
        thumbnail_path: Optional[str] = None,
    ) -> str:
        """Publish a video to the platform.

        Args:
            video_path: Path to the video file.
            metadata: Auto-generated title, description, and tags.
            thumbnail_path: Optional path to thumbnail image.

        Returns:
            URL of the published video.

        Raises:
            DistributionError: If publishing fails.
        """
        ...


# ---------------------------------------------------------------------------
# Mock Implementations (for testing)
# ---------------------------------------------------------------------------


class MockStorageUploader:
    """Mock storage uploader that simulates S3/GCS uploads.

    Records upload calls and returns predictable URLs for testing.
    Can be configured to fail for testing retry logic.
    """

    def __init__(self, fail_count: int = 0):
        """Initialize mock uploader.

        Args:
            fail_count: Number of times to fail before succeeding.
                Set to 0 for immediate success.
        """
        self._fail_count = fail_count
        self._attempt = 0
        self.upload_calls: List[Dict[str, str]] = []

    def upload_file(
        self,
        local_path: str,
        bucket: str,
        remote_key: str,
    ) -> str:
        """Simulate a file upload."""
        self._attempt += 1
        if self._attempt <= self._fail_count:
            raise DistributionError(
                f"Mock upload failure (attempt {self._attempt})"
            )

        self.upload_calls.append({
            "local_path": local_path,
            "bucket": bucket,
            "remote_key": remote_key,
        })
        return f"https://{bucket}.s3.amazonaws.com/{remote_key}"


class MockPlatformPublisher:
    """Mock platform publisher for testing."""

    def __init__(
        self,
        name: str = "youtube",
        fail_count: int = 0,
    ):
        self._name = name
        self._fail_count = fail_count
        self._attempt = 0
        self.publish_calls: List[Dict[str, Any]] = []

    @property
    def platform_name(self) -> str:
        return self._name

    def publish(
        self,
        video_path: str,
        metadata: PlatformMetadata,
        thumbnail_path: Optional[str] = None,
    ) -> str:
        """Simulate publishing a video."""
        self._attempt += 1
        if self._attempt <= self._fail_count:
            raise DistributionError(
                f"Mock publish failure on {self._name} (attempt {self._attempt})"
            )

        self.publish_calls.append({
            "video_path": video_path,
            "metadata": metadata,
            "thumbnail_path": thumbnail_path,
        })
        return f"https://www.{self._name}.com/watch?v=mock_{self._attempt}"


# ---------------------------------------------------------------------------
# Filename Generation (Task 9.2)
# ---------------------------------------------------------------------------


def generate_filename(
    episode_number: int,
    kanda_name: str,
    date: datetime,
) -> str:
    """Generate a standardized filename for an episode video.

    Format: ramayan_e{NNNN}_{kanda_name}_{YYYYMMDD}.mp4

    The kanda_name is lowercased with spaces replaced by underscores.

    Args:
        episode_number: The episode number (1-9999).
        kanda_name: The Kanda name (e.g., "Bala Kanda").
        date: The date for the filename.

    Returns:
        Standardized filename string.
    """
    sanitized_kanda = kanda_name.lower().replace(" ", "_")
    date_str = date.strftime("%Y%m%d")
    return f"ramayan_e{episode_number:04d}_{sanitized_kanda}_{date_str}.mp4"


# ---------------------------------------------------------------------------
# Platform Metadata Generation (Task 9.3)
# ---------------------------------------------------------------------------


def generate_platform_metadata(
    episode_number: int,
    title: str,
    kanda_name: str,
    narration_summary: str = "",
) -> PlatformMetadata:
    """Generate auto-generated metadata for platform publishing.

    Args:
        episode_number: The episode number.
        title: The episode title.
        kanda_name: The Kanda name.
        narration_summary: Optional narration summary for description.

    Returns:
        PlatformMetadata with title, description, and tags.
    """
    platform_title = f"Ramayan Episode {episode_number}: {title} | {kanda_name}"

    description = (
        f"Episode {episode_number} of the Ramayan animated series - {title}.\n"
        f"From {kanda_name} of the Ramayan epic."
    )
    if narration_summary:
        description += f"\n\n{narration_summary}"

    tags = [
        "Ramayan",
        "Hindu Mythology",
        kanda_name,
        title,
        "Indian Epic",
        "Animation",
        "Mythology",
    ]

    return PlatformMetadata(
        title=platform_title,
        description=description,
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Sleep function (injectable for testing)
# ---------------------------------------------------------------------------

_sleep_fn = time.sleep


# ---------------------------------------------------------------------------
# DistributionManager (Tasks 9.1 - 9.6)
# ---------------------------------------------------------------------------


class DistributionManager:
    """Stores and publishes finished videos.

    The manager orchestrates the distribution pipeline:
    1. Generates standardized filename (Task 9.2)
    2. Uploads video to cloud storage with retry (Tasks 9.1, 9.5)
    3. Uploads thumbnail alongside video (Task 9.4)
    4. Publishes to enabled platforms with retry (Tasks 9.3, 9.5)
    5. Logs all distribution events (Task 9.6)

    All external dependencies (storage, platform publishers) are injectable
    via Protocol interfaces for testability.

    Args:
        storage_config: StorageConfig with provider, bucket, path_prefix.
        distribution_config: DistributionConfig with platform settings.
        storage_uploader: An object implementing the StorageUploader protocol.
        platform_publishers: List of PlatformPublisher implementations.
        max_retries: Maximum retry attempts for failed uploads.
        initial_backoff: Initial backoff delay in seconds.
        backoff_multiplier: Multiplier for exponential backoff.
        sleep_fn: Sleep function (injectable for testing).
    """

    def __init__(
        self,
        storage_config: StorageConfig,
        distribution_config: DistributionConfig,
        storage_uploader: Optional[Any] = None,
        platform_publishers: Optional[List[Any]] = None,
        max_retries: int = MAX_RETRY_ATTEMPTS,
        initial_backoff: float = INITIAL_BACKOFF_SECONDS,
        backoff_multiplier: float = BACKOFF_MULTIPLIER,
        sleep_fn: Any = None,
    ):
        self._storage_config = storage_config
        self._distribution_config = distribution_config
        self._storage_uploader = storage_uploader or MockStorageUploader()
        self._platform_publishers = platform_publishers or []
        self._max_retries = max_retries
        self._initial_backoff = initial_backoff
        self._backoff_multiplier = backoff_multiplier
        self._sleep_fn = sleep_fn or _sleep_fn
        self._log: List[DistributionLogEntry] = []

    @property
    def distribution_log(self) -> List[DistributionLogEntry]:
        """Return the distribution log entries."""
        return list(self._log)

    def _retry_with_backoff(
        self,
        operation: str,
        fn: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function with retry and exponential backoff.

        Args:
            operation: Description of the operation (for logging).
            fn: The callable to execute.
            *args: Positional arguments for fn.
            **kwargs: Keyword arguments for fn.

        Returns:
            The return value of fn.

        Raises:
            DistributionError: If all retry attempts fail.
        """
        last_error: Optional[Exception] = None
        backoff = self._initial_backoff

        for attempt in range(1, self._max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    "%s failed (attempt %d/%d): %s",
                    operation,
                    attempt,
                    self._max_retries,
                    e,
                )
                if attempt < self._max_retries:
                    logger.info(
                        "Retrying %s in %.1f seconds...",
                        operation,
                        backoff,
                    )
                    self._sleep_fn(backoff)
                    backoff *= self._backoff_multiplier

        raise DistributionError(
            f"{operation} failed after {self._max_retries} attempts: {last_error}"
        )

    def _log_event(
        self,
        platform: str,
        status: str,
        url: Optional[str],
        episode_number: int = 0,
        kanda_name: str = "",
        error_message: Optional[str] = None,
    ) -> DistributionLogEntry:
        """Record a distribution event in the log.

        Args:
            platform: Platform name (e.g., "s3", "youtube").
            status: Upload status ("success" or "failed").
            url: URL of the uploaded resource (if successful).
            episode_number: The episode number.
            kanda_name: The Kanda name.
            error_message: Error message (if failed).

        Returns:
            The created log entry.
        """
        entry = DistributionLogEntry(
            platform=platform,
            status=status,
            url=url,
            timestamp=datetime.now(timezone.utc).isoformat(),
            episode_number=episode_number,
            kanda_name=kanda_name,
            error_message=error_message,
        )
        self._log.append(entry)
        logger.info(
            "Distribution event: platform=%s status=%s url=%s",
            platform,
            status,
            url,
        )
        return entry

    def upload_to_storage(
        self,
        local_path: str,
        remote_filename: str,
        episode_number: int = 0,
        kanda_name: str = "",
    ) -> Optional[str]:
        """Upload a file to cloud storage with retry logic.

        Args:
            local_path: Path to the local file.
            remote_filename: The filename to use in storage.
            episode_number: Episode number for logging.
            kanda_name: Kanda name for logging.

        Returns:
            URL of the uploaded file, or None if all retries failed.
        """
        remote_key = f"{self._storage_config.path_prefix}{remote_filename}"
        provider = self._storage_config.provider

        try:
            url = self._retry_with_backoff(
                f"Storage upload ({provider})",
                self._storage_uploader.upload_file,
                local_path,
                self._storage_config.bucket,
                remote_key,
            )
            self._log_event(
                platform=provider,
                status="success",
                url=url,
                episode_number=episode_number,
                kanda_name=kanda_name,
            )
            return url
        except DistributionError as e:
            self._log_event(
                platform=provider,
                status="failed",
                url=None,
                episode_number=episode_number,
                kanda_name=kanda_name,
                error_message=str(e),
            )
            logger.error("Storage upload failed: %s", e)
            return None

    def upload_thumbnail(
        self,
        thumbnail_path: str,
        remote_filename: str,
        episode_number: int = 0,
        kanda_name: str = "",
    ) -> Optional[str]:
        """Upload a thumbnail image alongside the video.

        Args:
            thumbnail_path: Path to the thumbnail image file.
            remote_filename: Base filename (will append _thumb extension).
            episode_number: Episode number for logging.
            kanda_name: Kanda name for logging.

        Returns:
            URL of the uploaded thumbnail, or None if failed.
        """
        # Generate thumbnail filename from video filename
        base_name = os.path.splitext(remote_filename)[0]
        ext = os.path.splitext(thumbnail_path)[1] or ".png"
        thumb_filename = f"{base_name}_thumb{ext}"

        return self.upload_to_storage(
            local_path=thumbnail_path,
            remote_filename=thumb_filename,
            episode_number=episode_number,
            kanda_name=kanda_name,
        )

    def publish_to_platforms(
        self,
        video_path: str,
        metadata: PlatformMetadata,
        thumbnail_path: Optional[str] = None,
        episode_number: int = 0,
        kanda_name: str = "",
    ) -> Dict[str, str]:
        """Publish video to all enabled platforms with retry logic.

        Args:
            video_path: Path to the video file.
            metadata: Auto-generated platform metadata.
            thumbnail_path: Optional path to thumbnail image.
            episode_number: Episode number for logging.
            kanda_name: Kanda name for logging.

        Returns:
            Dict mapping platform name to published URL.
        """
        platform_urls: Dict[str, str] = {}

        for publisher in self._platform_publishers:
            platform = publisher.platform_name
            try:
                url = self._retry_with_backoff(
                    f"Platform publish ({platform})",
                    publisher.publish,
                    video_path,
                    metadata,
                    thumbnail_path,
                )
                platform_urls[platform] = url
                self._log_event(
                    platform=platform,
                    status="success",
                    url=url,
                    episode_number=episode_number,
                    kanda_name=kanda_name,
                )
            except DistributionError as e:
                self._log_event(
                    platform=platform,
                    status="failed",
                    url=None,
                    episode_number=episode_number,
                    kanda_name=kanda_name,
                    error_message=str(e),
                )
                logger.error("Platform publish to %s failed: %s", platform, e)

        return platform_urls

    def distribute(
        self,
        video_path: str,
        episode_number: int,
        kanda_name: str,
        title: str,
        thumbnail_path: Optional[str] = None,
        narration_summary: str = "",
        date: Optional[datetime] = None,
    ) -> DistributionResult:
        """Distribute a video to all configured targets.

        This is the main entry point that orchestrates the full
        distribution pipeline:
        1. Generate standardized filename
        2. Upload video to cloud storage
        3. Upload thumbnail (if provided)
        4. Publish to enabled platforms (if any)
        5. Log all events

        Args:
            video_path: Path to the rendered video file.
            episode_number: The episode number.
            kanda_name: The Kanda name.
            title: The episode title.
            thumbnail_path: Optional path to thumbnail image.
            narration_summary: Optional narration summary for descriptions.
            date: Date for filename. Defaults to current UTC date.

        Returns:
            DistributionResult with all URLs and log entries.
        """
        if date is None:
            date = datetime.now(timezone.utc)

        # Step 1: Generate filename (Task 9.2)
        filename = generate_filename(episode_number, kanda_name, date)
        logger.info(
            "Distributing episode %d (%s) as %s",
            episode_number,
            kanda_name,
            filename,
        )

        result = DistributionResult(
            episode_number=episode_number,
            kanda_name=kanda_name,
            filename=filename,
        )

        # Step 2: Upload to cloud storage (Task 9.1)
        storage_url = self.upload_to_storage(
            local_path=video_path,
            remote_filename=filename,
            episode_number=episode_number,
            kanda_name=kanda_name,
        )
        result.storage_url = storage_url

        # Step 3: Upload thumbnail (Task 9.4)
        if thumbnail_path and os.path.exists(thumbnail_path):
            thumb_url = self.upload_thumbnail(
                thumbnail_path=thumbnail_path,
                remote_filename=filename,
                episode_number=episode_number,
                kanda_name=kanda_name,
            )
            result.thumbnail_url = thumb_url

        # Step 4: Publish to platforms (Task 9.3)
        if self._platform_publishers:
            metadata = generate_platform_metadata(
                episode_number=episode_number,
                title=title,
                kanda_name=kanda_name,
                narration_summary=narration_summary,
            )
            platform_urls = self.publish_to_platforms(
                video_path=video_path,
                metadata=metadata,
                thumbnail_path=thumbnail_path,
                episode_number=episode_number,
                kanda_name=kanda_name,
            )
            result.platform_urls = platform_urls

        # Step 5: Collect log entries (Task 9.6)
        result.log_entries = self.distribution_log

        # Determine overall success
        result.all_successful = (
            result.storage_url is not None
            and all(
                entry.status == "success"
                for entry in result.log_entries
            )
        )

        logger.info(
            "Distribution complete for episode %d: storage=%s, platforms=%s, "
            "thumbnail=%s, success=%s",
            episode_number,
            result.storage_url,
            list(result.platform_urls.keys()),
            result.thumbnail_url,
            result.all_successful,
        )

        return result
