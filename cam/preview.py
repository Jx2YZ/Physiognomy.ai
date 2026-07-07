"""Tk preview window: mirrored feed with hand skeleton / face-mesh overlay,
live atomic-state labels, last-fired trigger, idle countdown, FPS, and the
q/p/c hotkeys (spec §12)."""
from __future__ import annotations

from typing import Callable

import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk

from cam.engine import EngineDebugInfo
from cam.states import HAND_CONNECTIONS, FrameState

_TEXT_COLOR = (255, 255, 255)
_HAND_LINE_COLOR = (0, 220, 0)
_HAND_POINT_COLOR = (0, 200, 255)
_FACE_POINT_COLOR = (255, 180, 0)
_MOUTH_COLOR = (0, 0, 255)


def _draw_overlays(frame: np.ndarray, frame_state: FrameState, debug: EngineDebugInfo, fps: float) -> None:
    for hand in frame_state.hands:
        pts = hand.landmarks_px
        for a, b in HAND_CONNECTIONS:
            pa = (int(pts[a][0]), int(pts[a][1]))
            pb = (int(pts[b][0]), int(pts[b][1]))
            cv2.line(frame, pa, pb, _HAND_LINE_COLOR, 2)
        for p in pts:
            cv2.circle(frame, (int(p[0]), int(p[1])), 3, _HAND_POINT_COLOR, -1)
        label_pos = (int(hand.wrist_px[0]) - 20, int(hand.wrist_px[1]) + 28)
        cv2.putText(
            frame,
            f"{hand.handedness}: {hand.shape}",
            label_pos,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )

    if frame_state.face:
        face = frame_state.face
        for p in face.landmarks_px:
            cv2.circle(frame, (int(p[0]), int(p[1])), 1, _FACE_POINT_COLOR, -1)
        mc = face.mouth_centre_px
        cv2.circle(frame, (int(mc[0]), int(mc[1])), 3, _MOUTH_COLOR, -1)

    lines: list[str] = []
    if frame_state.face:
        face = frame_state.face
        lines.append(f"IOD: {face.iod:.0f}px")
        lines.append(f"tongueOut: {face.tongue_out:.2f}  jawOpen: {face.jaw_open:.2f}")
        lines.append(f"eyeSquint: {face.eye_squint:.2f}  smile: {face.mouth_smile:.2f}")
        lines.append(f"lowerDown: {face.mouth_lower_down:.2f}")
    else:
        lines.append("face: not detected")

    lines.append(f"last trigger: {debug.last_fired or '-'}")
    remaining = max(0.0, debug.idle_seconds - debug.idle_elapsed)
    lines.append(f"idle in: {remaining:.1f}s" if remaining > 0 else "idle: ready")
    lines.append(f"FPS: {fps:.1f}")

    y = 20
    for line in lines:
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, _TEXT_COLOR, 1, cv2.LINE_AA)
        y += 20


class PreviewWindow:
    def __init__(
        self,
        root: tk.Tk,
        width: int,
        height: int,
        on_quit: Callable[[], None],
        on_clear_all: Callable[[], None],
    ):
        self.root = root
        self.width = width
        self.height = height
        self.visible = True
        self._tk_image: ImageTk.PhotoImage | None = None

        root.title("Physiognomy.ai")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=width, height=height, bg="black", highlightthickness=0)
        self.canvas.pack()
        self._image_item = self.canvas.create_image(0, 0, anchor="nw")
        self._hidden_text_item: int | None = None

        root.bind("<KeyPress-q>", lambda _e: on_quit())
        root.bind("<KeyPress-p>", lambda _e: self.toggle_visible())
        root.bind("<KeyPress-c>", lambda _e: on_clear_all())
        root.protocol("WM_DELETE_WINDOW", on_quit)

        root.focus_set()
        root.after(100, root.focus_force)

    def toggle_visible(self) -> None:
        self.visible = not self.visible
        if not self.visible:
            self.canvas.itemconfig(self._image_item, image="")
            self._hidden_text_item = self.canvas.create_text(
                self.width // 2,
                self.height // 2,
                text="Preview hidden ('p' to show)\ndetection still running",
                fill="white",
                justify="center",
            )
        elif self._hidden_text_item is not None:
            self.canvas.delete(self._hidden_text_item)
            self._hidden_text_item = None

    def render(self, frame_bgr: np.ndarray, frame_state: FrameState, debug: EngineDebugInfo, fps: float) -> None:
        if not self.visible:
            return
        frame = frame_bgr.copy()
        _draw_overlays(frame, frame_state, debug, fps)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        self._tk_image = ImageTk.PhotoImage(img)
        self.canvas.itemconfig(self._image_item, image=self._tk_image)
