"""MediaPipe Tasks wrappers: runs HandLandmarker + FaceLandmarker (VIDEO mode)
over a frame and returns plain-data results (no mediapipe types leak out)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

Point3 = tuple[float, float, float]


@dataclass
class HandResult:
    # 21 normalized (x, y, z) landmarks, MediaPipe hand topology.
    landmarks: list[Point3]
    handedness: str  # "Left" or "Right", as reported (best-effort; not relied on by rules)


@dataclass
class FaceResult:
    # 478 normalized (x, y, z) landmarks, MediaPipe face mesh topology.
    landmarks: list[Point3]
    blendshapes: dict[str, float] = field(default_factory=dict)


@dataclass
class FrameLandmarks:
    hands: list[HandResult]
    face: FaceResult | None
    width: int
    height: int


class LandmarkDetector:
    def __init__(self, models_dir: Path):
        models_dir = Path(models_dir)
        hand_model = models_dir / "hand_landmarker.task"
        face_model = models_dir / "face_landmarker.task"
        if not hand_model.is_file() or not face_model.is_file():
            raise FileNotFoundError(
                f"MediaPipe model bundles missing in {models_dir}. "
                f"Run scripts/download_models.py or restart the app to auto-download."
            )

        hand_options = mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(hand_model)),
            num_hands=2,
            running_mode=mp_vision.RunningMode.VIDEO,
        )
        self._hand_landmarker = mp_vision.HandLandmarker.create_from_options(hand_options)

        face_options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(face_model)),
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=False,
            num_faces=1,
            running_mode=mp_vision.RunningMode.VIDEO,
        )
        self._face_landmarker = mp_vision.FaceLandmarker.create_from_options(face_options)

        self._last_timestamp_ms = -1

    def _next_timestamp_ms(self, timestamp_ms: int) -> int:
        # VIDEO mode requires strictly increasing timestamps.
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms

    def process(self, frame_bgr: np.ndarray, timestamp_ms: int) -> FrameLandmarks:
        timestamp_ms = self._next_timestamp_ms(timestamp_ms)
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        hand_result = self._hand_landmarker.detect_for_video(mp_image, timestamp_ms)
        face_result = self._face_landmarker.detect_for_video(mp_image, timestamp_ms)

        hands: list[HandResult] = []
        handedness_list = getattr(hand_result, "handedness", None) or []
        for i, hand_landmarks in enumerate(hand_result.hand_landmarks):
            label = "Unknown"
            if i < len(handedness_list) and handedness_list[i]:
                label = handedness_list[i][0].category_name
            hands.append(
                HandResult(
                    landmarks=[(lm.x, lm.y, lm.z) for lm in hand_landmarks],
                    handedness=label,
                )
            )

        face: FaceResult | None = None
        if face_result.face_landmarks:
            face_landmarks = face_result.face_landmarks[0]
            blendshapes: dict[str, float] = {}
            if face_result.face_blendshapes:
                for category in face_result.face_blendshapes[0]:
                    blendshapes[category.category_name] = category.score
            face = FaceResult(
                landmarks=[(lm.x, lm.y, lm.z) for lm in face_landmarks],
                blendshapes=blendshapes,
            )

        h, w = frame_bgr.shape[:2]
        return FrameLandmarks(hands=hands, face=face, width=w, height=h)

    def close(self) -> None:
        self._hand_landmarker.close()
        self._face_landmarker.close()
