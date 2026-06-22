"""Tests for the StoryManager module.

Includes property-based tests using Hypothesis and edge case tests
for Kanda boundary advancement and series completion.
"""

import json
import os
import shutil
import tempfile

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.story_manager import (
    KANDA_DIR_NAMES,
    KANDA_NAMES,
    Position,
    StoryManager,
    StoryManagerError,
    StorySegment,
)


# ---------------------------------------------------------------------------
# Helpers: create a temporary ramayan_db for testing
# ---------------------------------------------------------------------------

def _create_test_db(
    base_dir: str,
    kanda_segments: dict[int, int] | None = None,
    initial_kanda: int = 1,
    initial_segment: int = 1,
    total_completed: int = 0,
    series_complete: bool = False,
) -> str:
    """Create a minimal ramayan_db structure for testing.

    Args:
        base_dir: Parent directory for the test DB.
        kanda_segments: Mapping of kanda_index -> number of segments.
            Defaults to {1: 5, 2: 5} if None.
        initial_kanda: Starting kanda index in metadata.
        initial_segment: Starting segment index in metadata.
        total_completed: Total episodes completed so far.
        series_complete: Whether the series is marked complete.

    Returns:
        Path to the created ramayan_db directory.
    """
    if kanda_segments is None:
        kanda_segments = {1: 5, 2: 5}

    db_path = os.path.join(base_dir, "ramayan_db")
    os.makedirs(db_path, exist_ok=True)

    # metadata.json
    metadata = {
        "current_kanda_index": initial_kanda,
        "current_segment_index": initial_segment,
        "total_episodes_completed": total_completed,
        "series_complete": series_complete,
    }
    with open(os.path.join(db_path, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    # episodes directory
    os.makedirs(os.path.join(db_path, "episodes"), exist_ok=True)

    # kandas
    kandas_dir = os.path.join(db_path, "kandas")
    for kanda_idx in range(1, 8):
        kanda_dir_name = KANDA_DIR_NAMES[kanda_idx - 1]
        kanda_dir = os.path.join(kandas_dir, kanda_dir_name)
        segments_dir = os.path.join(kanda_dir, "segments")
        os.makedirs(segments_dir, exist_ok=True)

        # kanda.json
        num_segments = kanda_segments.get(kanda_idx, 0)
        kanda_meta = {
            "kanda_index": kanda_idx,
            "kanda_name": KANDA_NAMES[kanda_idx - 1],
            "description": f"Test Kanda {kanda_idx}",
            "total_segments": num_segments,
        }
        with open(os.path.join(kanda_dir, "kanda.json"), "w") as f:
            json.dump(kanda_meta, f, indent=2)

        # segment files
        for seg_idx in range(1, num_segments + 1):
            segment = {
                "kanda_index": kanda_idx,
                "kanda_name": KANDA_NAMES[kanda_idx - 1],
                "chapter": seg_idx,
                "segment_index": seg_idx,
                "title": f"Test Segment {kanda_idx}-{seg_idx}",
                "content": f"Content for kanda {kanda_idx}, segment {seg_idx}.",
                "characters": ["Rama", "Sita"],
                "key_events": [f"Event {seg_idx}"],
            }
            seg_path = os.path.join(segments_dir, f"{seg_idx:03d}.json")
            with open(seg_path, "w") as f:
                json.dump(segment, f, indent=2)

    return db_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Task 2.7.1 [PBT] Property test: N calls to get_next_segment() return
# N distinct segments in sequential order with correct position tracking.
# **Validates: Requirements 2.2, 2.3**
# ---------------------------------------------------------------------------

@given(n=st.integers(min_value=1, max_value=10))
@settings(max_examples=30, deadline=None)
def test_get_next_segment_sequential_progress(n):
    """Property 1: For N calls to get_next_segment(), exactly N distinct
    segments are returned in sequential order and position reflects N
    segments of progress.

    **Validates: Requirements 2.2, 2.3**
    """
    d = tempfile.mkdtemp()
    try:
        # Create a DB with enough segments across kandas
        kanda_segments = {1: 5, 2: 5, 3: 5}
        total_available = sum(kanda_segments.values())
        assume(n <= total_available)

        db_path = _create_test_db(d, kanda_segments=kanda_segments)
        manager = StoryManager(db_path=db_path)

        segments: list[StorySegment] = []
        for _ in range(n):
            seg = manager.get_next_segment()
            segments.append(seg)

        # Exactly N distinct segments
        segment_ids = [
            (s.kanda_index, s.segment_index) for s in segments
        ]
        assert len(set(segment_ids)) == n, (
            f"Expected {n} distinct segments, got {len(set(segment_ids))}"
        )

        # Sequential order: each segment comes after the previous one
        for i in range(1, len(segments)):
            prev = segments[i - 1]
            curr = segments[i]
            if prev.kanda_index == curr.kanda_index:
                assert curr.segment_index > prev.segment_index, (
                    f"Segment {i} not after segment {i-1} within same kanda"
                )
            else:
                assert curr.kanda_index > prev.kanda_index, (
                    f"Kanda did not advance: {prev.kanda_index} -> {curr.kanda_index}"
                )

        # Position reflects N segments of progress
        pos = manager.get_current_position()
        assert pos.total_episodes_completed == n
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Task 2.7.2 [PBT] Property test: save/load round-trip preserves state.
# **Validates: Requirements 2.6**
# ---------------------------------------------------------------------------

@given(
    kanda_idx=st.integers(min_value=1, max_value=7),
    segment_idx=st.integers(min_value=1, max_value=10),
    total_completed=st.integers(min_value=0, max_value=100),
    series_complete=st.booleans(),
)
@settings(max_examples=50, deadline=None)
def test_save_load_round_trip(kanda_idx, segment_idx, total_completed, series_complete):
    """Property 2: Saving state then loading produces equivalent state.
    load(save(state)) == state.

    **Validates: Requirements 2.6**
    """
    d = tempfile.mkdtemp()
    try:
        # Create a DB with segments so StoryManager can initialize
        kanda_segments = {i: 10 for i in range(1, 8)}
        db_path = _create_test_db(
            d,
            kanda_segments=kanda_segments,
            initial_kanda=kanda_idx,
            initial_segment=segment_idx,
            total_completed=total_completed,
            series_complete=series_complete,
        )

        # Load state
        manager1 = StoryManager(db_path=db_path)
        pos1 = manager1.get_current_position()

        # Save state (already saved during init load, but force a save)
        manager1._save_metadata()

        # Load again from disk
        manager2 = StoryManager(db_path=db_path)
        pos2 = manager2.get_current_position()

        # States must be equivalent
        assert pos1.current_kanda_index == pos2.current_kanda_index
        assert pos1.current_segment_index == pos2.current_segment_index
        assert pos1.total_episodes_completed == pos2.total_episodes_completed
        assert pos1.series_complete == pos2.series_complete
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Task 2.7.3 Edge case: Kanda boundary advancement
# **Validates: Requirements 2.4**
# ---------------------------------------------------------------------------

def test_kanda_boundary_advancement(tmp_dir):
    """Completing the last segment of Bala Kanda advances to the first
    segment of Ayodhya Kanda.

    **Validates: Requirements 2.4**
    """
    kanda_segments = {1: 3, 2: 3}
    db_path = _create_test_db(tmp_dir, kanda_segments=kanda_segments)
    manager = StoryManager(db_path=db_path)

    # Consume all segments of Bala Kanda
    for i in range(3):
        seg = manager.get_next_segment()
        assert seg.kanda_index == 1
        assert seg.segment_index == i + 1

    # Next segment should be from Ayodhya Kanda
    seg = manager.get_next_segment()
    assert seg.kanda_index == 2
    assert seg.kanda_name == "Ayodhya Kanda"
    assert seg.segment_index == 1

    pos = manager.get_current_position()
    assert pos.current_kanda_index == 2


# ---------------------------------------------------------------------------
# Task 2.7.4 Edge case: Series completion
# **Validates: Requirements 2.5**
# ---------------------------------------------------------------------------

def test_series_completion(tmp_dir):
    """Completing the last segment of Uttara Kanda marks the series complete.

    **Validates: Requirements 2.5**
    """
    # Create a minimal DB with only 1 segment per kanda
    kanda_segments = {i: 1 for i in range(1, 8)}
    db_path = _create_test_db(tmp_dir, kanda_segments=kanda_segments)
    manager = StoryManager(db_path=db_path)

    # Consume all 7 segments (one per kanda)
    for kanda_idx in range(1, 8):
        seg = manager.get_next_segment()
        assert seg.kanda_index == kanda_idx
        assert seg.kanda_name == KANDA_NAMES[kanda_idx - 1]

    # Series should now be complete
    assert manager.is_series_complete() is True

    pos = manager.get_current_position()
    assert pos.series_complete is True
    assert pos.total_episodes_completed == 7

    # Attempting to get another segment should raise an error
    with pytest.raises(StoryManagerError, match="complete"):
        manager.get_next_segment()
