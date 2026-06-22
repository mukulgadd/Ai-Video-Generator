"""Run a single episode generation (manual test).

This script exercises the full pipeline once:
  Gemini (script) → SDXL (images) → Edge TTS (narration) → FFmpeg (video)

Output goes to the output/ directory.
"""

import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from src.config_loader import load_config
from main import build_components


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    logger.info("Loading config...")
    config = load_config("config.yaml")

    logger.info("Building pipeline components...")
    orchestrator = build_components(config)

    logger.info("Running pipeline for 1 episode...")
    result = orchestrator.run_pipeline()

    if result.success:
        logger.info("Episode %d generated successfully!", result.episode_number)
        logger.info("Output: %s", result.output_path)
    else:
        logger.error("Pipeline failed: %s", result.error_message)
        sys.exit(1)


if __name__ == "__main__":
    main()
