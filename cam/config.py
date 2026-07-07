"""Loads and validates config.yaml, failing loudly with helpful errors."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# The fixed set of 10 triggers this app understands (see spec §7).
KNOWN_GESTURE_IDS = {
    "neutral",
    "tongue_out",
    "squint_smile",
    "finger_bite",
    "fist_cover_mouth",
    "lip_pull",
    "hands_up",
    "pray",
    "six_seven",
    "double_guns",
    "head_shake",
    "nerd",
    "thumbs_up",
}

_REQUIRED_SCALAR_THRESHOLDS = (
    "tongue_out",
    "eye_squint",
    "finger_bite_distance",
    "fist_mouth_distance",
    "lip_pull_distance",
    "lip_pull_lower_down",
    "pray_hands_distance",
    "pray_mouth_distance",
    "six_seven_amplitude",
    "hands_up_max_speed",
    "head_shake_amplitude",
    "head_shake_window_seconds",
)
_REQUIRED_BAND_THRESHOLDS = ("smile_band", "finger_bite_jaw")
_REQUIRED_INT_THRESHOLDS = ("six_seven_reversals", "head_shake_reversals")


class ConfigError(Exception):
    """Raised when config.yaml is missing, malformed, or references bad media.

    The message is a human-readable, newline-joined list of every problem
    found, so a user can fix everything in one pass instead of one error at
    a time.
    """


@dataclass
class CameraConfig:
    index: int = 0
    width: int = 640
    height: int = 480


@dataclass
class EngineConfig:
    hold_frames: int = 6
    cooldown_seconds: float = 4.0
    idle_seconds: float = 5.0
    motion_window_seconds: float = 1.2


@dataclass
class PopupsConfig:
    display_seconds: float = 3.5
    max_popups: int = 5
    max_screen_fraction: float = 0.40
    min_screen_fraction: float = 0.20


@dataclass
class Thresholds:
    tongue_out: float
    eye_squint: float
    smile_band: tuple[float, float]
    finger_bite_distance: float
    finger_bite_jaw: tuple[float, float]
    fist_mouth_distance: float
    lip_pull_distance: float
    lip_pull_lower_down: float
    pray_hands_distance: float
    pray_mouth_distance: float
    six_seven_amplitude: float
    six_seven_reversals: int
    hands_up_max_speed: float
    head_shake_amplitude: float
    head_shake_reversals: int
    head_shake_window_seconds: float


@dataclass
class GestureConfig:
    id: str
    meme_path: Path
    cooldown_seconds: float
    hold_frames: int
    clears_all: bool = False


@dataclass
class ComboConfig:
    parts: list[str]
    meme_path: Path


@dataclass
class AppConfig:
    camera: CameraConfig
    engine: EngineConfig
    popups: PopupsConfig
    thresholds: Thresholds
    gestures: dict[str, GestureConfig]
    combos: list[ComboConfig] = field(default_factory=list)
    root_dir: Path = Path(".")


def _err(errors: list[str], msg: str) -> None:
    errors.append(f"  - {msg}")


def _as_band(errors: list[str], raw: Any, key: str) -> tuple[float, float]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        _err(errors, f"thresholds.{key} must be a 2-element list [low, high], got: {raw!r}")
        return (0.0, 1.0)
    low, high = raw
    try:
        low, high = float(low), float(high)
    except (TypeError, ValueError):
        _err(errors, f"thresholds.{key} values must be numbers, got: {raw!r}")
        return (0.0, 1.0)
    if low >= high:
        _err(errors, f"thresholds.{key} low bound must be < high bound, got: [{low}, {high}]")
    return (low, high)


def _as_float(errors: list[str], raw: Any, key: str) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        _err(errors, f"thresholds.{key} must be a number, got: {raw!r}")
        return 0.0


def _as_int(errors: list[str], raw: Any, key: str) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        _err(errors, f"thresholds.{key} must be an integer, got: {raw!r}")
        return 0


def _is_readable_media(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        from PIL import Image

        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


def load_config(config_path: str | Path) -> AppConfig:
    config_path = Path(config_path)
    root_dir = config_path.resolve().parent
    errors: list[str] = []

    if not config_path.is_file():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"config.yaml is not valid YAML:\n  {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("config.yaml must contain a top-level mapping.")

    camera_raw = raw.get("camera", {}) or {}
    camera = CameraConfig(
        index=int(camera_raw.get("index", 0)),
        width=int(camera_raw.get("width", 640)),
        height=int(camera_raw.get("height", 480)),
    )

    engine_raw = raw.get("engine", {}) or {}
    engine = EngineConfig(
        hold_frames=int(engine_raw.get("hold_frames", 6)),
        cooldown_seconds=float(engine_raw.get("cooldown_seconds", 4.0)),
        idle_seconds=float(engine_raw.get("idle_seconds", 5.0)),
        motion_window_seconds=float(engine_raw.get("motion_window_seconds", 1.2)),
    )

    popups_raw = raw.get("popups", {}) or {}
    popups = PopupsConfig(
        display_seconds=float(popups_raw.get("display_seconds", 3.5)),
        max_popups=int(popups_raw.get("max_popups", 5)),
        max_screen_fraction=float(popups_raw.get("max_screen_fraction", 0.40)),
        min_screen_fraction=float(popups_raw.get("min_screen_fraction", 0.20)),
    )

    thresholds_raw = raw.get("thresholds", {}) or {}
    for key in (*_REQUIRED_SCALAR_THRESHOLDS, *_REQUIRED_BAND_THRESHOLDS, *_REQUIRED_INT_THRESHOLDS):
        if key not in thresholds_raw:
            _err(errors, f"thresholds.{key} is missing")

    thresholds = Thresholds(
        tongue_out=_as_float(errors, thresholds_raw.get("tongue_out", 0.5), "tongue_out"),
        eye_squint=_as_float(errors, thresholds_raw.get("eye_squint", 0.5), "eye_squint"),
        smile_band=_as_band(errors, thresholds_raw.get("smile_band", [0.10, 0.45]), "smile_band"),
        finger_bite_distance=_as_float(
            errors, thresholds_raw.get("finger_bite_distance", 0.30), "finger_bite_distance"
        ),
        finger_bite_jaw=_as_band(
            errors, thresholds_raw.get("finger_bite_jaw", [0.15, 0.60]), "finger_bite_jaw"
        ),
        fist_mouth_distance=_as_float(
            errors, thresholds_raw.get("fist_mouth_distance", 0.40), "fist_mouth_distance"
        ),
        lip_pull_distance=_as_float(
            errors, thresholds_raw.get("lip_pull_distance", 0.30), "lip_pull_distance"
        ),
        lip_pull_lower_down=_as_float(
            errors, thresholds_raw.get("lip_pull_lower_down", 0.30), "lip_pull_lower_down"
        ),
        pray_hands_distance=_as_float(
            errors, thresholds_raw.get("pray_hands_distance", 0.50), "pray_hands_distance"
        ),
        pray_mouth_distance=_as_float(
            errors, thresholds_raw.get("pray_mouth_distance", 0.50), "pray_mouth_distance"
        ),
        six_seven_amplitude=_as_float(
            errors, thresholds_raw.get("six_seven_amplitude", 0.60), "six_seven_amplitude"
        ),
        six_seven_reversals=_as_int(
            errors, thresholds_raw.get("six_seven_reversals", 2), "six_seven_reversals"
        ),
        hands_up_max_speed=_as_float(
            errors, thresholds_raw.get("hands_up_max_speed", 0.15), "hands_up_max_speed"
        ),
        head_shake_amplitude=_as_float(
            errors, thresholds_raw.get("head_shake_amplitude", 0.30), "head_shake_amplitude"
        ),
        head_shake_reversals=_as_int(
            errors, thresholds_raw.get("head_shake_reversals", 4), "head_shake_reversals"
        ),
        head_shake_window_seconds=_as_float(
            errors, thresholds_raw.get("head_shake_window_seconds", 2.5), "head_shake_window_seconds"
        ),
    )

    gestures_raw = raw.get("gestures", {}) or {}
    if not gestures_raw:
        _err(errors, "gestures: section is empty; map at least one trigger to a meme")

    gestures: dict[str, GestureConfig] = {}
    clears_all_ids: list[str] = []
    for gesture_id, gesture_body in gestures_raw.items():
        if gesture_id not in KNOWN_GESTURE_IDS:
            _err(
                errors,
                f"gestures.{gesture_id} is not a recognized trigger id. "
                f"Known ids: {sorted(KNOWN_GESTURE_IDS)}",
            )
            continue
        if not isinstance(gesture_body, dict) or "meme" not in gesture_body:
            _err(errors, f"gestures.{gesture_id} must have a 'meme' path")
            continue

        meme_path = (root_dir / gesture_body["meme"]).resolve()
        if not meme_path.is_file():
            _err(errors, f"gestures.{gesture_id}.meme file not found: {meme_path}")
        elif not _is_readable_media(meme_path):
            _err(errors, f"gestures.{gesture_id}.meme is not a readable image/GIF: {meme_path}")

        clears_all = bool(gesture_body.get("clears_all", False))
        if clears_all:
            clears_all_ids.append(gesture_id)

        gestures[gesture_id] = GestureConfig(
            id=gesture_id,
            meme_path=meme_path,
            cooldown_seconds=float(gesture_body.get("cooldown_seconds", engine.cooldown_seconds)),
            hold_frames=int(gesture_body.get("hold_frames", engine.hold_frames)),
            clears_all=clears_all,
        )

    # Gestures absent from config.yaml are simply disabled (the engine skips
    # them), so a partial gestures: mapping is valid.

    if len(clears_all_ids) > 1:
        _err(errors, f"only one gesture may set clears_all: true, found: {clears_all_ids}")

    combos_raw = raw.get("combos", []) or []
    combos: list[ComboConfig] = []
    for i, combo_body in enumerate(combos_raw):
        if not isinstance(combo_body, dict) or "parts" not in combo_body or "meme" not in combo_body:
            _err(errors, f"combos[{i}] must have 'parts' (list) and 'meme' (path)")
            continue
        combo_meme_path = (root_dir / combo_body["meme"]).resolve()
        if not combo_meme_path.is_file():
            _err(errors, f"combos[{i}].meme file not found: {combo_meme_path}")
        combos.append(ComboConfig(parts=list(combo_body["parts"]), meme_path=combo_meme_path))

    if errors:
        header = "Physiognomy.ai config.yaml has problems that need fixing:\n"
        raise ConfigError(header + "\n".join(errors))

    return AppConfig(
        camera=camera,
        engine=engine,
        popups=popups,
        thresholds=thresholds,
        gestures=gestures,
        combos=combos,
        root_dir=root_dir,
    )
