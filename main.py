"""Physiognomy.ai entry point: starts the detection worker thread, then runs the
Tk mainloop on the main thread (spec §4). All processing is local - no
frame or landmark data ever leaves this machine."""
from __future__ import annotations

import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

from cam import states
from cam.camera import Camera, CameraError
from cam.config import AppConfig, ConfigError, load_config
from cam.engine import Engine
from cam.landmarks import LandmarkDetector
from cam.popups import PopupManager
from cam.preview import PreviewWindow
from scripts.download_models import ensure_models

# When frozen (PyInstaller), config.yaml/assets/models are staged next to the
# app, and there is no console: send prints to a log file instead.
IS_FROZEN = getattr(sys, "frozen", False)
if IS_FROZEN:
    _exe = Path(sys.executable).resolve()
    # macOS .app: exe lives at Physiognomy.app/Contents/MacOS/Physiognomy;
    # the staged files sit beside the .app, so climb out of the bundle.
    if ".app" in _exe.parts and _exe.parent.name == "MacOS":
        REPO_ROOT = _exe.parents[3]
    else:  # Windows one-folder build: files sit next to the .exe
        REPO_ROOT = _exe.parent
    try:
        _log = open(REPO_ROOT / "physiognomy.log", "w", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = _log
    except OSError:
        pass  # read-only install dir: run without a log rather than not at all
else:
    REPO_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
MODELS_DIR = REPO_ROOT / "models"

POLL_INTERVAL_MS = 15
FPS_WINDOW_SECONDS = 0.5


class DetectionWorker(threading.Thread):
    """Owns the camera + both landmarkers + the engine. Everything in run()
    happens off the Tk main thread; only queue.put crosses back over."""

    def __init__(
        self,
        config: AppConfig,
        frame_queue: "queue.Queue",
        event_queue: "queue.Queue",
        stop_event: threading.Event,
    ):
        super().__init__(daemon=True)
        self.config = config
        self.frame_queue = frame_queue
        self.event_queue = event_queue
        self.stop_event = stop_event

    def run(self) -> None:
        try:
            camera = Camera(self.config.camera.index, self.config.camera.width, self.config.camera.height)
        except CameraError as exc:
            self.event_queue.put(("fatal_error", str(exc)))
            return

        try:
            detector = LandmarkDetector(MODELS_DIR)
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, not a crash
            camera.release()
            self.event_queue.put(("fatal_error", str(exc)))
            return

        engine = Engine(self.config)
        start_time = time.monotonic()
        frame_count = 0
        fps = 0.0
        fps_window_start = start_time

        try:
            while not self.stop_event.is_set():
                frame = camera.read()
                if frame is None:
                    continue

                now = time.monotonic()
                timestamp_ms = int((now - start_time) * 1000)

                frame_landmarks = detector.process(frame, timestamp_ms)
                frame_state = states.compute_frame_state(frame_landmarks)
                trigger = engine.update(frame_state, now)

                frame_count += 1
                elapsed = now - fps_window_start
                if elapsed >= FPS_WINDOW_SECONDS:
                    fps = frame_count / elapsed
                    frame_count = 0
                    fps_window_start = now

                # Preview freshness matters more than completeness: drop a
                # stale queued frame rather than block the detection loop.
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self.frame_queue.put_nowait((frame, frame_state, engine.debug_info(), fps))
                except queue.Full:
                    pass

                if trigger is not None:
                    self.event_queue.put(("trigger", trigger))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, not a crash
            self.event_queue.put(("fatal_error", f"Detection loop crashed: {exc}"))
        finally:
            camera.release()
            detector.close()


def _fatal_startup_error(message: str) -> None:
    print(f"\nPhysiognomy.ai startup error:\n{message}\n", file=sys.stderr)
    if IS_FROZEN:
        from tkinter import messagebox

        hidden = tk.Tk()
        hidden.withdraw()
        messagebox.showerror("Physiognomy.ai", message)
        hidden.destroy()
    sys.exit(1)


def main() -> None:
    try:
        ensure_models(MODELS_DIR)
    except RuntimeError as exc:
        _fatal_startup_error(str(exc))

    try:
        config = load_config(CONFIG_PATH)
    except ConfigError as exc:
        _fatal_startup_error(str(exc))

    frame_queue: "queue.Queue" = queue.Queue(maxsize=2)
    event_queue: "queue.Queue" = queue.Queue()
    stop_event = threading.Event()

    root = tk.Tk()
    popup_manager = PopupManager(root, config.popups)

    def do_quit() -> None:
        if stop_event.is_set():
            return
        stop_event.set()
        root.after(150, root.destroy)

    def do_clear_all() -> None:
        popup_manager.clear_all()

    preview = PreviewWindow(
        root,
        config.camera.width,
        config.camera.height,
        on_quit=do_quit,
        on_clear_all=do_clear_all,
    )

    worker = DetectionWorker(config, frame_queue, event_queue, stop_event)
    worker.start()

    def poll() -> None:
        if stop_event.is_set():
            return
        try:
            while True:
                frame, frame_state, debug, fps = frame_queue.get_nowait()
                preview.render(frame, frame_state, debug, fps)
        except queue.Empty:
            pass

        try:
            while True:
                kind, payload = event_queue.get_nowait()
                if kind == "trigger":
                    popup_manager.spawn(payload)
                elif kind == "fatal_error":
                    print(f"\nPhysiognomy.ai error: {payload}\n", file=sys.stderr)
                    if IS_FROZEN:
                        from tkinter import messagebox

                        messagebox.showerror("Physiognomy.ai", payload)
                    do_quit()
        except queue.Empty:
            pass

        if not stop_event.is_set():
            root.after(POLL_INTERVAL_MS, poll)

    root.after(POLL_INTERVAL_MS, poll)
    root.mainloop()
    stop_event.set()
    worker.join(timeout=2.0)


if __name__ == "__main__":
    main()
