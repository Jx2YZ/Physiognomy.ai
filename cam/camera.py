"""Webcam capture. Runs inside the detection worker thread, never on the
Tk main thread, and never touches cv2.imshow (see README / spec §2)."""
from __future__ import annotations

import cv2
import numpy as np


class CameraError(Exception):
    """Raised when the webcam cannot be opened."""


class Camera:
    def __init__(self, index: int = 0, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self._cap = cv2.VideoCapture(index)
        if not self._cap.isOpened():
            raise CameraError(
                f"Could not open webcam at index {index}. Is another app using it, "
                f"or does this process lack camera permission?"
            )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read(self) -> np.ndarray | None:
        """Returns a mirrored (selfie-view) BGR frame resized to width x height,
        or None if a frame could not be captured."""
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return None
        frame = cv2.flip(frame, 1)
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        return frame

    def release(self) -> None:
        self._cap.release()
