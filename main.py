"""Ramayan Video Generator - Entry Point.

Loads configuration, initializes all pipeline components, and starts
the daily scheduler.

Validates: Requirements 1.1, 10.1
"""

import logging
import sys

from dotenv import load_dotenv

load_dotenv()  # Load .env before anything reads env vars

from src.audio_engine import AudioEngine
from src.animation_engine import AnimationEngine
from src.config_loader import Config, ConfigError, load_config
from src.distribution_manager import DistributionManager
from src.gemini_llm_client import GeminiLLMClient
from src.narration_engine import NarrationEngine
from src.notifications import create_notification_sender
from src.orchestrator import VideoGeneratorOrchestrator
from src.scheduler import PipelineScheduler
from src.script_engine import ScriptEngine
from src.flux_image_generator import FluxImageGenerator
# from src.sd_image_generator import SDXLImageGenerator  # Commented out — using FLUX instead
from src.story_manager import StoryManager
from src.video_compositor import VideoCompositor


def setup_logging() -> None:
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_components(config: Config) -> VideoGeneratorOrchestrator:
    """Initialize all pipeline components and return the orchestrator.

    Args:
        config: The loaded and validated pipeline configuration.

    Returns:
        A fully wired VideoGeneratorOrchestrator.
    """
    # Story Manager
    story_manager = StoryManager(db_path="ramayan_db")

    # Script Engine (using Gemini)
    gemini_client = GeminiLLMClient()
    script_engine = ScriptEngine(
        llm_client=gemini_client,
        model="gemini-2.5-flash",
        temperature=0.7,
    )

    # Animation Engine (using FLUX.1-schnell — 256 token prompts, runs on MPS)
    image_generator = FluxImageGenerator(num_inference_steps=4)
    # # SDXL fallback (77 token limit, runs on CPU):
    # image_generator = SDXLImageGenerator(num_inference_steps=15)
    animation_engine = AnimationEngine(
        config=config.animation,
        image_generator=image_generator,
    )

    # Narration Engine
    narration_engine = NarrationEngine(config=config.narration)

    # Audio Engine
    audio_engine = AudioEngine(config=config.audio)

    # Video Compositor
    video_compositor = VideoCompositor(
        output_config=config.output,
        animation_config=config.animation,
    )

    # Distribution Manager
    distribution_manager = DistributionManager(
        storage_config=config.storage,
        distribution_config=config.distribution,
    )

    # Notification Sender
    notification_sender = create_notification_sender(config.notifications)

    # Orchestrator
    orchestrator = VideoGeneratorOrchestrator(
        config=config,
        story_manager=story_manager,
        script_engine=script_engine,
        animation_engine=animation_engine,
        narration_engine=narration_engine,
        audio_engine=audio_engine,
        video_compositor=video_compositor,
        distribution_manager=distribution_manager,
        notification_sender=notification_sender,
        output_dir="output",
    )

    return orchestrator


def main() -> None:
    """Initialize and start the Ramayan Video Generator pipeline."""
    setup_logging()
    logger = logging.getLogger(__name__)

    config_path = "config.yaml"
    logger.info("Loading configuration from %s", config_path)

    try:
        config = load_config(config_path)
    except ConfigError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)

    logger.info(
        "Configuration loaded. Schedule time: %s, Retry attempts: %d",
        config.pipeline.schedule_time,
        config.pipeline.retry_attempts,
    )

    orchestrator = build_components(config)

    scheduler = PipelineScheduler(
        pipeline_config=config.pipeline,
        orchestrator=orchestrator,
    )

    logger.info("Starting Ramayan Video Generator scheduler...")
    scheduler.start()


if __name__ == "__main__":
    main()
