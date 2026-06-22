"""Story Manager for the Ramayan Video Generator.

Maintains the Ramayan narrative database and tracks episode progression
across the seven Kandas. Provides sequential access to story segments
and persists state via metadata.json.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


KANDA_NAMES = [
    "Bala Kanda",
    "Ayodhya Kanda",
    "Aranya Kanda",
    "Kishkindha Kanda",
    "Sundara Kanda",
    "Yuddha Kanda",
    "Uttara Kanda",
]

KANDA_DIR_NAMES = [
    "1_bala_kanda",
    "2_ayodhya_kanda",
    "3_aranya_kanda",
    "4_kishkindha_kanda",
    "5_sundara_kanda",
    "6_yuddha_kanda",
    "7_uttara_kanda",
]


@dataclass
class StorySegment:
    """A single story segment from the Ramayan narrative."""

    kanda_index: int
    kanda_name: str
    chapter: int
    segment_index: int
    title: str
    content: str
    characters: List[str]
    key_events: List[str]
    # Explainer analysis fields (optional — enriched segments have these)
    philosophical_themes: List[str] = field(default_factory=list)
    lesser_known_facts: List[str] = field(default_factory=list)
    debate_angles: List[str] = field(default_factory=list)
    modern_relevance: List[str] = field(default_factory=list)
    suggested_angles: List[str] = field(default_factory=list)


@dataclass
class Position:
    """Current position in the Ramayan narrative."""

    current_kanda_index: int
    current_segment_index: int
    total_episodes_completed: int
    series_complete: bool
    current_video_index: int = 0  # Which sub-video of the current segment (0 = first)


@dataclass
class EpisodeRecord:
    """Record of a single episode."""

    episode_number: int
    kanda: str
    segment_ids: List[str]
    status: str  # "pending", "complete", "failed"
    output_path: str
    created_at: str


class StoryManagerError(Exception):
    """Raised when the StoryManager encounters an error."""

    pass


class StoryManager:
    """Manages the Ramayan story database and episode progression.

    Provides sequential access to story segments, tracks the current
    position in the narrative, and persists state to disk.
    """

    def __init__(self, db_path: str = "ramayan_db"):
        """Initialize the StoryManager.

        Args:
            db_path: Path to the ramayan_db directory.
        """
        self.db_path = db_path
        self._metadata_path = os.path.join(db_path, "metadata.json")
        self._kandas_path = os.path.join(db_path, "kandas")
        self._episodes_path = os.path.join(db_path, "episodes")
        self._position: Optional[Position] = None
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load current position from metadata.json."""
        try:
            with open(self._metadata_path, "r") as f:
                data = json.load(f)
            self._position = Position(
                current_kanda_index=data["current_kanda_index"],
                current_segment_index=data["current_segment_index"],
                total_episodes_completed=data["total_episodes_completed"],
                series_complete=data["series_complete"],
                current_video_index=data.get("current_video_index", 0),
            )
        except FileNotFoundError:
            raise StoryManagerError(
                f"Metadata file not found: {self._metadata_path}"
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise StoryManagerError(f"Invalid metadata file: {e}")

    def _save_metadata(self) -> None:
        """Save current position to metadata.json."""
        if self._position is None:
            return
        data = asdict(self._position)
        with open(self._metadata_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def _get_kanda_dir(self, kanda_index: int) -> str:
        """Get the directory path for a given Kanda index (1-based)."""
        if kanda_index < 1 or kanda_index > 7:
            raise StoryManagerError(f"Invalid kanda index: {kanda_index}")
        return os.path.join(self._kandas_path, KANDA_DIR_NAMES[kanda_index - 1])

    def _get_segment_count(self, kanda_index: int) -> int:
        """Get the number of segments in a Kanda."""
        kanda_dir = self._get_kanda_dir(kanda_index)
        segments_dir = os.path.join(kanda_dir, "segments")
        if not os.path.isdir(segments_dir):
            return 0
        segment_files = [
            f for f in os.listdir(segments_dir)
            if f.endswith(".json")
        ]
        return len(segment_files)

    def _load_segment(self, kanda_index: int, segment_index: int) -> StorySegment:
        """Load a specific story segment from disk."""
        kanda_dir = self._get_kanda_dir(kanda_index)
        segment_path = os.path.join(
            kanda_dir, "segments", f"{segment_index:03d}.json"
        )
        try:
            with open(segment_path, "r") as f:
                data = json.load(f)
            return StorySegment(
                kanda_index=data["kanda_index"],
                kanda_name=data["kanda_name"],
                chapter=data["chapter"],
                segment_index=data["segment_index"],
                title=data["title"],
                content=data["content"],
                characters=data["characters"],
                key_events=data["key_events"],
                philosophical_themes=data.get("philosophical_themes", []),
                lesser_known_facts=data.get("lesser_known_facts", []),
                debate_angles=data.get("debate_angles", []),
                modern_relevance=data.get("modern_relevance", []),
                suggested_angles=data.get("suggested_angles", []),
            )
        except FileNotFoundError:
            raise StoryManagerError(
                f"Segment file not found: {segment_path}"
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise StoryManagerError(f"Invalid segment file: {e}")

    def get_next_segment(self) -> StorySegment:
        """Return the next story segment WITHOUT advancing the pointer.

        The pointer only advances when mark_episode_complete() is called.
        This ensures failed pipeline runs don't consume episode numbers.

        Returns:
            The next StorySegment in sequential narrative order.

        Raises:
            StoryManagerError: If the series is complete or no segments remain.
        """
        if self._position is None:
            raise StoryManagerError("StoryManager not initialized")

        if self._position.series_complete:
            raise StoryManagerError("Series is already complete")

        kanda_index = self._position.current_kanda_index
        segment_index = self._position.current_segment_index

        # Load the segment (don't advance — that happens on mark_episode_complete)
        segment = self._load_segment(kanda_index, segment_index)

        # Create episode record as "pending" (will be updated on completion)
        episode_number = self._position.total_episodes_completed + 1
        video_index = self._position.current_video_index
        episode_record = EpisodeRecord(
            episode_number=episode_number,
            kanda=KANDA_NAMES[kanda_index - 1],
            segment_ids=[f"{kanda_index}_{segment_index:03d}_v{video_index}"],
            status="pending",
            output_path="",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save_episode_record(episode_record)

        return segment

    @staticmethod
    def _get_videos_per_segment(segment: StorySegment) -> int:
        """Calculate how many videos a segment can produce.

        Each segment produces videos based on its enrichment data:
        - Each lesser_known_fact → 1 video (unknown_facts angle)
        - Each debate_angle → 1 video (debate angle)
        - Each modern_relevance → 1 video (life_lesson angle)
        - Plus 1 video for the primary suggested angle (hidden_meaning/why/etc.)

        This gives 5-8 videos per segment, totaling 175-280 across all 35 segments.
        """
        count = 1  # At least 1 video per segment (primary angle)
        count += len(segment.lesser_known_facts)  # Each fact = 1 video
        count += len(segment.debate_angles)  # Each debate = 1 video
        count += len(segment.modern_relevance)  # Each lesson = 1 video
        # Add extra suggested angles beyond the first
        if len(segment.suggested_angles) > 1:
            count += len(segment.suggested_angles) - 1
        return count

    def _save_episode_record(self, record: EpisodeRecord) -> None:
        """Save an episode record to disk."""
        os.makedirs(self._episodes_path, exist_ok=True)
        episode_path = os.path.join(
            self._episodes_path,
            f"episode_{record.episode_number:03d}.json",
        )
        with open(episode_path, "w") as f:
            json.dump(asdict(record), f, indent=2)
            f.write("\n")

    def mark_episode_complete(self, episode_id: int, output_path: str) -> None:
        """Mark an episode as complete, update its record, and advance the pointer.

        This is where the position advances — ensuring failed runs don't
        consume episode numbers or advance the pointer.

        Args:
            episode_id: The episode number to mark complete.
            output_path: Path to the generated video file.

        Raises:
            StoryManagerError: If the episode record is not found.
        """
        episode_path = os.path.join(
            self._episodes_path, f"episode_{episode_id:03d}.json"
        )
        try:
            with open(episode_path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise StoryManagerError(
                f"Episode record not found: {episode_path}"
            )

        data["status"] = "complete"
        data["output_path"] = output_path

        with open(episode_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        # NOW advance the position (only on success)
        if self._position is None:
            return

        kanda_index = self._position.current_kanda_index
        segment_index = self._position.current_segment_index
        video_index = self._position.current_video_index

        # Load segment to get video count
        segment = self._load_segment(kanda_index, segment_index)
        videos_per_segment = self._get_videos_per_segment(segment)

        # Advance position
        if video_index + 1 >= videos_per_segment:
            # All sub-videos for this segment are done, advance to next segment
            self._position.current_video_index = 0
            segment_count = self._get_segment_count(kanda_index)
            if segment_index >= segment_count:
                if kanda_index >= 7:
                    self._position.series_complete = True
                    self._position.current_segment_index = segment_index
                else:
                    self._position.current_kanda_index = kanda_index + 1
                    self._position.current_segment_index = 1
            else:
                self._position.current_segment_index = segment_index + 1
        else:
            # More sub-videos to produce from this segment
            self._position.current_video_index = video_index + 1

        self._position.total_episodes_completed = episode_id
        self._save_metadata()

    def get_current_position(self) -> Position:
        """Return the current position in the Ramayan narrative.

        Returns:
            A Position object with current Kanda, segment, and progress info.
        """
        if self._position is None:
            raise StoryManagerError("StoryManager not initialized")
        return Position(
            current_kanda_index=self._position.current_kanda_index,
            current_segment_index=self._position.current_segment_index,
            total_episodes_completed=self._position.total_episodes_completed,
            series_complete=self._position.series_complete,
        )

    def is_series_complete(self) -> bool:
        """Check if all segments have been processed.

        Returns:
            True if the entire Ramayan series is complete.
        """
        if self._position is None:
            raise StoryManagerError("StoryManager not initialized")
        return self._position.series_complete
