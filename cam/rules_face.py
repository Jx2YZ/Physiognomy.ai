"""Face-only triggers: tongue_out, squint_smile (spec §7)."""
from __future__ import annotations

from cam.config import Thresholds
from cam.states import FaceState


def tongue_out(face: FaceState | None, thresholds: Thresholds) -> bool:
    if face is None:
        return False
    return face.tongue_out > thresholds.tongue_out


def squint_smile(face: FaceState | None, thresholds: Thresholds) -> bool:
    if face is None:
        return False
    low, high = thresholds.smile_band
    return face.eye_squint > thresholds.eye_squint and low <= face.mouth_smile <= high
