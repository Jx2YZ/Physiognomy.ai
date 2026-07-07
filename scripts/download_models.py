"""Downloads the MediaPipe Tasks model bundles required by Physiognomy.ai.

Run directly (``python scripts/download_models.py``) or import
``ensure_models(models_dir)`` and call it from application startup;
main.py does the latter automatically before the detectors are created.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

MODEL_URLS = {
    "hand_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/latest/hand_landmarker.task"
    ),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    ),
}

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_MODELS_DIR = _REPO_ROOT / "models"


def _download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)

    def _report(block_num: int, block_size: int, total_size: int) -> None:
        if total_size <= 0:
            return
        done = min(block_num * block_size, total_size)
        pct = done * 100 // total_size
        bar_len = 30
        filled = bar_len * pct // 100
        bar = "#" * filled + "-" * (bar_len - filled)
        print(f"\r  [{bar}] {pct:3d}%  {dest.name}", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, tmp, reporthook=_report)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
    print()
    tmp.replace(dest)


def ensure_models(models_dir: Path | None = None) -> None:
    """Download any missing .task model bundles into models_dir."""
    models_dir = Path(models_dir) if models_dir else _DEFAULT_MODELS_DIR
    missing = {
        name: url
        for name, url in MODEL_URLS.items()
        if not (models_dir / name).exists()
    }
    if not missing:
        return

    print(f"Physiognomy.ai: downloading {len(missing)} model file(s) into {models_dir} ...")
    for name, url in missing.items():
        dest = models_dir / name
        print(f"Fetching {name} from {url}")
        try:
            _download(url, dest)
        except Exception as exc:  # noqa: BLE001 - surface a clear startup error
            raise RuntimeError(
                f"Failed to download required model '{name}' from {url}.\n"
                f"Check your internet connection, or manually download the file and "
                f"place it at: {dest}\nOriginal error: {exc}"
            ) from exc
    print("Physiognomy.ai: model download complete.")


if __name__ == "__main__":
    ensure_models(_DEFAULT_MODELS_DIR)
    sys.exit(0)
