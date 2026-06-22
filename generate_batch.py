"""Nightly batch video generator.

Generates multiple episodes sequentially, with per-episode error handling
so one failure doesn't kill the whole batch.

Usage:
    python generate_batch.py              # Generate 3 episodes (default)
    python generate_batch.py --count 5    # Generate 5 episodes
    python generate_batch.py --dry-run    # Show what would be generated without doing it

Designed to be run overnight via cron/launchd when system is free.
Logs to: logs/batch_YYYYMMDD_HHMMSS.log
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Project root
PROJECT_DIR = Path(__file__).parent

# Ensure logs directory exists
LOGS_DIR = PROJECT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logging() -> logging.Logger:
    """Set up file + console logging for the batch run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"batch_{timestamp}.log"

    logger = logging.getLogger("batch")
    logger.setLevel(logging.INFO)

    # File handler — full detail
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Console handler — concise
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    ))

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(f"Batch log: {log_file}")
    return logger


def generate_single_episode(episode_index: int, logger: logging.Logger) -> dict:
    """Run generate_episode.py as a subprocess.
    
    Returns a dict with status, duration, output info, and any error.
    """
    start = time.time()
    result = {
        "index": episode_index,
        "status": "unknown",
        "duration_seconds": 0,
        "output": "",
        "error": "",
    }

    try:
        # Use the same Python interpreter (from the venv)
        python = sys.executable

        proc = subprocess.run(
            [python, "generate_episode.py"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=3600,  # 60 min max per episode (FLUX on MPS can take 40-50 min)
        )

        elapsed = time.time() - start
        result["duration_seconds"] = elapsed

        if proc.returncode == 0:
            result["status"] = "success"
            result["output"] = proc.stdout[-2000:]  # Last 2000 chars
            logger.info(f"  Episode {episode_index} completed in {elapsed:.0f}s")
        else:
            result["status"] = "failed"
            result["error"] = proc.stderr[-2000:] if proc.stderr else proc.stdout[-2000:]
            logger.error(f"  Episode {episode_index} FAILED (exit {proc.returncode}, {elapsed:.0f}s)")
            logger.error(f"  Error: {result['error'][-500:]}")

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        result["duration_seconds"] = elapsed
        result["status"] = "timeout"
        result["error"] = "Episode generation exceeded 60 minute timeout"
        logger.error(f"  Episode {episode_index} TIMED OUT after {elapsed:.0f}s")

    except Exception as e:
        elapsed = time.time() - start
        result["duration_seconds"] = elapsed
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"  Episode {episode_index} ERROR: {e}")

    return result


def print_summary(results: list, total_time: float, logger: logging.Logger):
    """Print a nice summary of the batch run."""
    succeeded = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]

    logger.info("")
    logger.info("=" * 60)
    logger.info("BATCH SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Total episodes attempted: {len(results)}")
    logger.info(f"  Succeeded: {len(succeeded)}")
    logger.info(f"  Failed: {len(failed)}")
    logger.info(f"  Total time: {timedelta(seconds=int(total_time))}")

    if succeeded:
        avg_time = sum(r["duration_seconds"] for r in succeeded) / len(succeeded)
        logger.info(f"  Avg time per episode: {timedelta(seconds=int(avg_time))}")

    if failed:
        logger.info("")
        logger.info("  FAILURES:")
        for r in failed:
            logger.info(f"    Episode {r['index']}: {r['status']} — {r['error'][:100]}")

    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Generate multiple Ramayan episodes overnight")
    parser.add_argument(
        "--count", type=int, default=3,
        help="Number of episodes to generate (default: 3)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without generating"
    )
    parser.add_argument(
        "--delay", type=int, default=30,
        help="Seconds to wait between episodes for GPU cooldown (default: 30)"
    )
    parser.add_argument(
        "--stop-on-fail", action="store_true",
        help="Stop the batch if any episode fails"
    )
    args = parser.parse_args()

    logger = setup_logging()

    logger.info(f"Nightly batch: generating {args.count} episodes")
    logger.info(f"  Delay between episodes: {args.delay}s")
    logger.info(f"  Stop on failure: {args.stop_on_fail}")
    logger.info(f"  Python: {sys.executable}")
    logger.info("")

    if args.dry_run:
        logger.info("[DRY RUN] Would generate %d episodes sequentially.", args.count)
        logger.info("[DRY RUN] Each episode takes ~15-25 min on MPS (FLUX + TTS + FFmpeg).")
        logger.info("[DRY RUN] Estimated total time: %d-%d minutes.", args.count * 15, args.count * 25)
        return

    results = []
    batch_start = time.time()

    for i in range(1, args.count + 1):
        logger.info(f"[{i}/{args.count}] Starting episode generation...")
        result = generate_single_episode(i, logger)
        results.append(result)

        # Stop early if requested and this one failed
        if args.stop_on_fail and result["status"] != "success":
            logger.warning(f"Stopping batch early due to failure (--stop-on-fail)")
            break

        # Cooldown between episodes (skip after last)
        if i < args.count and result["status"] == "success":
            logger.info(f"  Cooling down {args.delay}s before next episode...")
            time.sleep(args.delay)

    total_time = time.time() - batch_start
    print_summary(results, total_time, logger)

    # Exit with error code if any failed
    if any(r["status"] != "success" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
