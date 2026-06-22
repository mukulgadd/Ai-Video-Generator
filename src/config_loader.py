"""Configuration loader for the Ramayan Video Generator.

Reads YAML configuration, validates all fields, applies documented defaults
for missing optional keys, and raises ConfigError with specific field names
for invalid values.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


class ConfigError(Exception):
    """Raised when configuration contains invalid values.

    Attributes:
        invalid_fields: List of field names that have invalid values.
    """

    def __init__(self, message: str, invalid_fields: Optional[List[str]] = None):
        self.invalid_fields = invalid_fields or []
        super().__init__(message)


@dataclass
class PipelineConfig:
    schedule_time: str = "06:00"
    target_duration_seconds: int = 120
    retry_attempts: int = 3


@dataclass
class AnimationConfig:
    style_reference: str = "indian_traditional_art"
    resolution: List[int] = field(default_factory=lambda: [1080, 1920])
    fps: int = 24
    model: str = "stable-diffusion-xl"
    lora_path: str = "./models/indian_art_lora.safetensors"


@dataclass
class NarrationConfig:
    default_locale: str = "hi"
    narrator_voice: str = "narrator_v1"
    tts_provider: str = "coqui"
    character_voices: Dict[str, str] = field(default_factory=lambda: {
        "Rama": "voice_rama_01",
        "Sita": "voice_sita_01",
        "Hanuman": "voice_hanuman_01",
        "Ravana": "voice_ravana_01",
    })


@dataclass
class AudioConfig:
    music_library_path: str = "./assets/music/"
    sfx_library_path: str = "./assets/sfx/"
    narration_boost_db: int = 6
    crossfade_seconds: float = 0.75


@dataclass
class OutputConfig:
    format: str = "mp4"
    video_codec: str = "h264"
    audio_codec: str = "aac"


@dataclass
class StorageConfig:
    provider: str = "s3"
    bucket: str = "ramayan-videos"
    path_prefix: str = "episodes/"


@dataclass
class PlatformConfig:
    enabled: bool = False
    credentials_path: str = ""


@dataclass
class DistributionConfig:
    youtube: PlatformConfig = field(
        default_factory=lambda: PlatformConfig(
            enabled=False, credentials_path="./credentials/youtube.json"
        )
    )
    instagram: PlatformConfig = field(
        default_factory=lambda: PlatformConfig(
            enabled=False, credentials_path="./credentials/instagram.json"
        )
    )


@dataclass
class NotificationsConfig:
    provider: str = "email"
    recipients: List[str] = field(default_factory=lambda: ["admin@example.com"])


@dataclass
class Config:
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    narration: NarrationConfig = field(default_factory=NarrationConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    distribution: DistributionConfig = field(default_factory=DistributionConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)


def _validate_config(data: Dict[str, Any]) -> List[str]:
    """Validate configuration data and return list of invalid field names."""
    invalid_fields: List[str] = []

    if "pipeline" in data and data["pipeline"] is not None:
        p = data["pipeline"]
        if not isinstance(p, dict):
            invalid_fields.append("pipeline")
        else:
            if "schedule_time" in p:
                v = p["schedule_time"]
                if not isinstance(v, str):
                    invalid_fields.append("pipeline.schedule_time")
                else:
                    parts = v.split(":")
                    if (
                        len(parts) != 2
                        or not parts[0].isdigit()
                        or not parts[1].isdigit()
                        or not (0 <= int(parts[0]) <= 23)
                        or not (0 <= int(parts[1]) <= 59)
                    ):
                        invalid_fields.append("pipeline.schedule_time")
            if "target_duration_seconds" in p:
                v = p["target_duration_seconds"]
                if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                    invalid_fields.append("pipeline.target_duration_seconds")
            if "retry_attempts" in p:
                v = p["retry_attempts"]
                if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                    invalid_fields.append("pipeline.retry_attempts")

    if "animation" in data and data["animation"] is not None:
        a = data["animation"]
        if not isinstance(a, dict):
            invalid_fields.append("animation")
        else:
            if "style_reference" in a:
                if not isinstance(a["style_reference"], str):
                    invalid_fields.append("animation.style_reference")
            if "resolution" in a:
                v = a["resolution"]
                if (
                    not isinstance(v, list)
                    or len(v) != 2
                    or not all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in v)
                ):
                    invalid_fields.append("animation.resolution")
            if "fps" in a:
                v = a["fps"]
                if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                    invalid_fields.append("animation.fps")
            if "model" in a:
                if not isinstance(a["model"], str):
                    invalid_fields.append("animation.model")
            if "lora_path" in a:
                if not isinstance(a["lora_path"], str):
                    invalid_fields.append("animation.lora_path")

    if "narration" in data and data["narration"] is not None:
        n = data["narration"]
        if not isinstance(n, dict):
            invalid_fields.append("narration")
        else:
            if "default_locale" in n:
                if not isinstance(n["default_locale"], str):
                    invalid_fields.append("narration.default_locale")
            if "narrator_voice" in n:
                if not isinstance(n["narrator_voice"], str):
                    invalid_fields.append("narration.narrator_voice")
            if "tts_provider" in n:
                if not isinstance(n["tts_provider"], str):
                    invalid_fields.append("narration.tts_provider")
            if "character_voices" in n:
                v = n["character_voices"]
                if not isinstance(v, dict):
                    invalid_fields.append("narration.character_voices")
                elif not all(
                    isinstance(k, str) and isinstance(val, str)
                    for k, val in v.items()
                ):
                    invalid_fields.append("narration.character_voices")

    if "audio" in data and data["audio"] is not None:
        au = data["audio"]
        if not isinstance(au, dict):
            invalid_fields.append("audio")
        else:
            if "music_library_path" in au:
                if not isinstance(au["music_library_path"], str):
                    invalid_fields.append("audio.music_library_path")
            if "sfx_library_path" in au:
                if not isinstance(au["sfx_library_path"], str):
                    invalid_fields.append("audio.sfx_library_path")
            if "narration_boost_db" in au:
                v = au["narration_boost_db"]
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    invalid_fields.append("audio.narration_boost_db")
            if "crossfade_seconds" in au:
                v = au["crossfade_seconds"]
                if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
                    invalid_fields.append("audio.crossfade_seconds")

    if "output" in data and data["output"] is not None:
        o = data["output"]
        if not isinstance(o, dict):
            invalid_fields.append("output")
        else:
            if "format" in o:
                if not isinstance(o["format"], str):
                    invalid_fields.append("output.format")
            if "video_codec" in o:
                if not isinstance(o["video_codec"], str):
                    invalid_fields.append("output.video_codec")
            if "audio_codec" in o:
                if not isinstance(o["audio_codec"], str):
                    invalid_fields.append("output.audio_codec")

    if "storage" in data and data["storage"] is not None:
        s = data["storage"]
        if not isinstance(s, dict):
            invalid_fields.append("storage")
        else:
            if "provider" in s:
                if not isinstance(s["provider"], str):
                    invalid_fields.append("storage.provider")
            if "bucket" in s:
                if not isinstance(s["bucket"], str):
                    invalid_fields.append("storage.bucket")
            if "path_prefix" in s:
                if not isinstance(s["path_prefix"], str):
                    invalid_fields.append("storage.path_prefix")

    if "distribution" in data and data["distribution"] is not None:
        d = data["distribution"]
        if not isinstance(d, dict):
            invalid_fields.append("distribution")
        else:
            for platform in ("youtube", "instagram"):
                if platform in d:
                    pv = d[platform]
                    if not isinstance(pv, dict):
                        invalid_fields.append(f"distribution.{platform}")
                    else:
                        if "enabled" in pv:
                            if not isinstance(pv["enabled"], bool):
                                invalid_fields.append(
                                    f"distribution.{platform}.enabled"
                                )
                        if "credentials_path" in pv:
                            if not isinstance(pv["credentials_path"], str):
                                invalid_fields.append(
                                    f"distribution.{platform}.credentials_path"
                                )

    if "notifications" in data and data["notifications"] is not None:
        nt = data["notifications"]
        if not isinstance(nt, dict):
            invalid_fields.append("notifications")
        else:
            if "provider" in nt:
                if not isinstance(nt["provider"], str):
                    invalid_fields.append("notifications.provider")
            if "recipients" in nt:
                v = nt["recipients"]
                if not isinstance(v, list) or not all(
                    isinstance(r, str) for r in v
                ):
                    invalid_fields.append("notifications.recipients")

    return invalid_fields


def _build_config(data: Dict[str, Any]) -> Config:
    """Build a Config object from validated data, applying defaults for missing keys."""
    config = Config()

    if "pipeline" in data and isinstance(data["pipeline"], dict):
        p = data["pipeline"]
        config.pipeline = PipelineConfig(
            schedule_time=p.get("schedule_time", PipelineConfig.schedule_time),
            target_duration_seconds=p.get(
                "target_duration_seconds",
                PipelineConfig.target_duration_seconds,
            ),
            retry_attempts=p.get("retry_attempts", PipelineConfig.retry_attempts),
        )

    if "animation" in data and isinstance(data["animation"], dict):
        a = data["animation"]
        config.animation = AnimationConfig(
            style_reference=a.get(
                "style_reference", AnimationConfig.style_reference
            ),
            resolution=a.get("resolution", AnimationConfig().resolution),
            fps=a.get("fps", AnimationConfig.fps),
            model=a.get("model", AnimationConfig.model),
            lora_path=a.get("lora_path", AnimationConfig.lora_path),
        )

    if "narration" in data and isinstance(data["narration"], dict):
        n = data["narration"]
        config.narration = NarrationConfig(
            default_locale=n.get(
                "default_locale", NarrationConfig.default_locale
            ),
            narrator_voice=n.get(
                "narrator_voice", NarrationConfig.narrator_voice
            ),
            tts_provider=n.get("tts_provider", NarrationConfig.tts_provider),
            character_voices=n.get(
                "character_voices", NarrationConfig().character_voices
            ),
        )

    if "audio" in data and isinstance(data["audio"], dict):
        au = data["audio"]
        config.audio = AudioConfig(
            music_library_path=au.get(
                "music_library_path", AudioConfig.music_library_path
            ),
            sfx_library_path=au.get(
                "sfx_library_path", AudioConfig.sfx_library_path
            ),
            narration_boost_db=au.get(
                "narration_boost_db", AudioConfig.narration_boost_db
            ),
            crossfade_seconds=au.get(
                "crossfade_seconds", AudioConfig.crossfade_seconds
            ),
        )

    if "output" in data and isinstance(data["output"], dict):
        o = data["output"]
        config.output = OutputConfig(
            format=o.get("format", OutputConfig.format),
            video_codec=o.get("video_codec", OutputConfig.video_codec),
            audio_codec=o.get("audio_codec", OutputConfig.audio_codec),
        )

    if "storage" in data and isinstance(data["storage"], dict):
        s = data["storage"]
        config.storage = StorageConfig(
            provider=s.get("provider", StorageConfig.provider),
            bucket=s.get("bucket", StorageConfig.bucket),
            path_prefix=s.get("path_prefix", StorageConfig.path_prefix),
        )

    if "distribution" in data and isinstance(data["distribution"], dict):
        d = data["distribution"]
        yt_data = d.get("youtube", {})
        ig_data = d.get("instagram", {})
        yt_defaults = DistributionConfig().youtube
        ig_defaults = DistributionConfig().instagram
        config.distribution = DistributionConfig(
            youtube=PlatformConfig(
                enabled=yt_data.get("enabled", yt_defaults.enabled)
                if isinstance(yt_data, dict)
                else yt_defaults.enabled,
                credentials_path=yt_data.get(
                    "credentials_path", yt_defaults.credentials_path
                )
                if isinstance(yt_data, dict)
                else yt_defaults.credentials_path,
            ),
            instagram=PlatformConfig(
                enabled=ig_data.get("enabled", ig_defaults.enabled)
                if isinstance(ig_data, dict)
                else ig_defaults.enabled,
                credentials_path=ig_data.get(
                    "credentials_path", ig_defaults.credentials_path
                )
                if isinstance(ig_data, dict)
                else ig_defaults.credentials_path,
            ),
        )

    if "notifications" in data and isinstance(data["notifications"], dict):
        nt = data["notifications"]
        config.notifications = NotificationsConfig(
            provider=nt.get("provider", NotificationsConfig.provider),
            recipients=nt.get("recipients", NotificationsConfig().recipients),
        )

    return config


def load_config(path: str) -> Config:
    """Load and validate configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        A fully populated Config object with defaults applied for missing keys.

    Raises:
        ConfigError: If the file cannot be read, parsed, or contains invalid values.
    """
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(
            f"Configuration file not found: {path}",
            invalid_fields=["path"],
        )
    except yaml.YAMLError as e:
        raise ConfigError(
            f"Invalid YAML in configuration file: {e}",
            invalid_fields=["yaml"],
        )

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ConfigError(
            "Configuration file must contain a YAML mapping at the top level",
            invalid_fields=["root"],
        )

    invalid_fields = _validate_config(data)
    if invalid_fields:
        raise ConfigError(
            f"Invalid configuration fields: {', '.join(invalid_fields)}",
            invalid_fields=invalid_fields,
        )

    return _build_config(data)
