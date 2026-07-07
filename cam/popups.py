"""Popup manager: spawns borderless always-on-top Tk windows for triggered
memes, animates GIFs at native frame durations, cycles a 3x2 screen-slot
grid, caps concurrent popups, and implements clear-all (spec §11)."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

from cam.config import PopupsConfig
from cam.engine import TriggerEvent

GRID_COLS = 3
GRID_ROWS = 2


class PopupWindow:
    def __init__(
        self,
        root: tk.Tk,
        meme_path: Path,
        display_seconds: float,
        slot_center: tuple[int, int],
        popups_config: PopupsConfig,
        on_close,
    ):
        self._on_close = on_close
        self._closed = False
        self._after_ids: list[str] = []

        is_gif = meme_path.suffix.lower() == ".gif"
        source = Image.open(meme_path)
        frames: list[Image.Image] = []
        durations: list[int] = []
        n_frames = getattr(source, "n_frames", 1)
        for i in range(n_frames):
            source.seek(i)
            frames.append(source.convert("RGBA"))
            durations.append(max(20, source.info.get("duration", 100)))

        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        short_side = min(screen_w, screen_h)
        max_dim = short_side * popups_config.max_screen_fraction
        min_dim = short_side * popups_config.min_screen_fraction

        w0, h0 = frames[0].size
        longest = max(w0, h0)
        if longest > max_dim:
            scale = max_dim / longest
        elif longest < min_dim:
            scale = min_dim / longest
        else:
            scale = 1.0

        new_size = (max(1, round(w0 * scale)), max(1, round(h0 * scale)))
        # LANCZOS reads better for the static photos; nearest-neighbour is
        # fine (and cheaper) for the small pixel-art-ish GIFs (spec §10).
        resample = Image.NEAREST if is_gif else Image.LANCZOS
        self._photo_frames = [
            ImageTk.PhotoImage(f.resize(new_size, resample)) for f in frames
        ]
        self._durations = durations

        # Borderless, always-on-top, and deliberately never given keyboard
        # focus (no focus_set/grab_set calls anywhere here) so the preview
        # window keeps hotkey input (spec §11).
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        cx, cy = slot_center
        x, y = int(cx - new_size[0] / 2), int(cy - new_size[1] / 2)
        self.top.geometry(f"{new_size[0]}x{new_size[1]}+{x}+{y}")

        self.label = tk.Label(self.top, image=self._photo_frames[0], bd=0)
        self.label.pack()

        self._frame_idx = 0
        if len(self._photo_frames) > 1:
            self._after_ids.append(self.top.after(self._durations[0], self._animate))

        close_ms = int(display_seconds * 1000)
        self._after_ids.append(self.top.after(close_ms, self.close))
        self.top.protocol("WM_DELETE_WINDOW", self.close)

    def _animate(self) -> None:
        if self._closed:
            return
        self._frame_idx = (self._frame_idx + 1) % len(self._photo_frames)
        self.label.configure(image=self._photo_frames[self._frame_idx])
        delay = self._durations[self._frame_idx]
        self._after_ids.append(self.top.after(delay, self._animate))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for after_id in self._after_ids:
            try:
                self.top.after_cancel(after_id)
            except tk.TclError:
                pass
        try:
            self.top.destroy()
        except tk.TclError:
            pass
        if self._on_close:
            self._on_close(self)


class PopupManager:
    def __init__(self, root: tk.Tk, popups_config: PopupsConfig):
        self.root = root
        self.config = popups_config
        self._popups: list[PopupWindow] = []
        self._spawn_count = 0

    def spawn(self, event: TriggerEvent) -> None:
        if event.clears_all:
            self.clear_all()

        while len(self._popups) >= self.config.max_popups:
            oldest = self._popups.pop(0)
            oldest.close()

        slot = self._spawn_count % (GRID_COLS * GRID_ROWS)
        self._spawn_count += 1
        slot_center = self._slot_position(slot)

        popup = PopupWindow(
            self.root,
            event.meme_path,
            event.display_seconds,
            slot_center,
            self.config,
            on_close=self._on_popup_closed,
        )
        self._popups.append(popup)

    def clear_all(self) -> None:
        for popup in list(self._popups):
            popup.close()
        self._popups.clear()

    def _on_popup_closed(self, popup: PopupWindow) -> None:
        if popup in self._popups:
            self._popups.remove(popup)

    def _slot_position(self, slot: int) -> tuple[int, int]:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        cell_w = screen_w / GRID_COLS
        cell_h = screen_h / GRID_ROWS
        col = slot % GRID_COLS
        row = (slot // GRID_COLS) % GRID_ROWS
        cx = cell_w * col + cell_w / 2
        cy = cell_h * row + cell_h / 2
        return int(cx), int(cy)
