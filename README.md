# Physiognomy.ai

> *Democratizing Facial Capital.*

Your webcam watches your face and hands. Pull a face, throw a gesture, and
the right contextual media pops up on screen — always on top, briefly, then gone.
Ten gestures, one terminator (`double_guns` clears everything and shows its
own meme), 100% rule-based, 100% local.

<!-- Demo GIF placeholder: record a short clip of a few triggers firing and
     drop it at docs/demo.gif, then add: ![demo](docs/demo.gif) -->

## Privacy

All video processing happens locally, in this process, on this machine.
No frame, landmark, or gesture data is ever written to disk (beyond the
downloaded model files) or sent anywhere over the network. The only network
access this app makes is the one-time model download on first run.

## Requirements

- Python **3.10 – 3.13** (check `pip index versions mediapipe` if a newer
  Python release refuses to install mediapipe)
- A built-in or USB webcam
- Windows 10/11 or macOS (Apple Silicon or Intel)

## Running it on a new machine

The repo ships with the meme files in `assets/` and downloads the MediaPipe
models automatically on first run — clone, install, run is all it takes.

### Windows

1. **Install Python** (3.10–3.13) from [python.org](https://www.python.org/downloads/)
   — tick **"Add python.exe to PATH"** in the installer — or:

   ```powershell
   winget install Python.Python.3.12
   ```

2. **Clone and set up** (in PowerShell):

   ```powershell
   git clone https://github.com/YOUR_USERNAME/Physiognomy.ai.git
   cd Physiognomy.ai
   python -m venv venv
   venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   If `Activate.ps1` is blocked ("running scripts is disabled"), either run
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and retry, or
   skip activation entirely and use `venv\Scripts\python.exe` in place of
   `python` below.

3. **Run:**

   ```powershell
   python main.py
   ```

### macOS

1. **Install Python** (3.10–3.13). The [python.org](https://www.python.org/downloads/)
   installer is easiest and includes Tk (needed for the preview window).
   With Homebrew you need the Tk package too:

   ```bash
   brew install python@3.12 python-tk@3.12
   ```

2. **Clone and set up** (in Terminal):

   ```bash
   git clone https://github.com/YOUR_USERNAME/Physiognomy.ai.git
   cd Physiognomy.ai
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run:**

   ```bash
   python main.py
   ```

   The first run triggers a camera-permission prompt — see the macOS
   section below if the window opens black.

### First run (both platforms)

On first run, Physiognomy.ai downloads two MediaPipe model bundles (`hand_landmarker.task`,
`face_landmarker.task`, a few MB each) into `models/`. You'll see a progress
bar in the terminal. If your network blocks the download, fetch them
manually and place them in `models/`:

- `hand_landmarker.task` — https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
- `face_landmarker.task` — https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task

### macOS camera permission

macOS requires an explicit camera-permission grant for whatever process
opens the webcam:

- **Running from Terminal.app / iTerm:** the first `python main.py` run
  triggers a system permission prompt. If you don't see one (or already
  denied it), go to **System Settings → Privacy & Security → Camera** and
  enable it for Terminal (or iTerm).
- **Running from an IDE (VS Code, PyCharm, etc.):** grant camera access to
  the IDE itself in the same Privacy & Security → Camera pane — the IDE's
  embedded terminal inherits the IDE's permission, not Terminal.app's.
- If the camera opens black or `main.py` reports it can't open the webcam,
  permission is almost always the cause; check that pane first.

### Windows

No extra permission step is usually required. If Windows' camera privacy
settings block desktop apps (**Settings → Privacy & security → Camera →
Let desktop apps access your camera**), enable that toggle.

## Building a standalone app (no Python needed to run it)

PyInstaller bundles Python and every library into the app, so end users just
double-click — no Python, pip, or venv on their machine. **PyInstaller cannot
cross-compile:** build the Windows app on Windows and the macOS app on a Mac.

### Windows → `dist\Physiognomy\Physiognomy.exe`

```powershell
venv\Scripts\python.exe -m pip install pyinstaller
powershell -File packaging\build.ps1
```

Launch `Physiognomy.exe`, or copy/zip the whole `dist\Physiognomy\` folder to
any 64-bit Windows 10/11 PC.

### macOS → `dist/Physiognomy.app`

Run this **on a Mac** (Apple Silicon or Intel) with Python 3.10–3.13:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt pyinstaller
bash packaging/build_macos.sh
```

Ship the whole `dist/` folder (the `.app` plus the staged `config.yaml`,
`assets/`, `models/`). Unsigned apps need a one-time **right-click → Open** to
clear Gatekeeper on the target Mac.

### Both builds

Each build stages the user-editable files beside the app: `config.yaml`
(thresholds, gesture→meme mapping), `assets/` (the memes), and `models/` (the
MediaPipe bundles, pre-staged so the app never needs the network). Since the
app has no console, startup output and errors go to `physiognomy.log` beside
the app, and fatal errors also pop up a dialog.

## Usage

Run `python main.py`. A preview window opens showing your mirrored webcam
feed with hand skeletons, face-mesh points, live state readouts (per-hand
shape, key blendshape scores, IOD), the last fired trigger, an idle
countdown, and FPS.

**Hotkeys** (click the preview window first so it has keyboard focus):

| Key | Action |
|---|---|
| `q` | Quit (releases the camera cleanly) |
| `p` | Toggle the preview on/off (detection keeps running either way) |
| `c` | Keyboard fallback: clear all open popups |

## The 10 triggers

| Trigger | Class | What to do |
|---|---|---|
| `head_shake` | motion | Shake your head left-right a few times |
| `squint_smile` | face | Squint + a faint smile (not a full grin) |
| `erm` | single-hand | Index finger pointing up, other fingers curled |
| `thumbs_up` | single-hand | Thumb clearly up, all four fingers balled into a fist |
| `fist_cover_mouth` | interaction | Cover your mouth with a fist |
| `johnny_dang` | interaction | Shaka-style hand (thumb + pinky out, rest balled), pinky pulls your lower lip down, teeth showing |
| `hands_up` | two-hand | Both palms open, raised above your chin, held still |
| `pray` | two-hand | Hands together near your mouth, prayer-style |
| `double_guns` | two-hand | Both hands in a "finger gun" shape — **clears every open popup**, then shows its own meme |
| `six_seven` | motion | Left and right open hands both shifting up-down more than 2 times, fast |

All distance thresholds, hold-frame counts, and cooldowns live in
`config.yaml` under `thresholds:` and `gestures:` — tune them there if a
trigger fires too eagerly or not eagerly enough for your lighting/camera
distance.

## How it works (short version)

A worker thread captures webcam frames, runs MediaPipe's `HandLandmarker`
and `FaceLandmarker` (Tasks API, VIDEO mode) on each one, derives atomic
states (finger extension, hand shape, face blendshape scores, IOD-normalised
distances), evaluates the 10 trigger rules with priority + suppression +
hold-to-confirm + per-trigger cooldowns, and hands off trigger events and
preview frames to the Tk main thread via thread-safe queues. See
`cam/engine.py` for the priority/suppression logic and `cam/states.py`
for the geometry.

## Project layout

```
main.py                    entry point
config.yaml                camera/engine/popup/threshold/gesture config
scripts/download_models.py MediaPipe model bundle downloader
assets/                    the images/GIFs the triggers pop up
cam/
  camera.py                 webcam capture worker
  landmarks.py               MediaPipe HandLandmarker + FaceLandmarker wrappers
  states.py                  atomic states: finger extension, hand shape, IOD, blendshapes
  rules_face.py               tongue_out, squint_smile
  rules_interactions.py       finger_bite, fist_cover_mouth, johnny_dang
  rules_singlehand.py         erm, thumbs_up
  rules_twohand.py            hands_up, pray, double_guns
  rules_motion.py             six_seven, head_shake
  engine.py                  priority/suppression/hold/cooldown/idle + event queue
  popups.py                  popup window manager (GIF playback, grid placement, clear-all)
  preview.py                 Tk preview window + overlays + hotkeys
  config.py                  config.yaml loader/validator
```

## Troubleshooting

- **"Could not open webcam"**: another app may be using it, or the OS has
  denied camera permission to this process (see the macOS/Windows sections
  above). Try a different `camera.index` in `config.yaml` if you have more
  than one camera.
- **Config errors on startup**: Physiognomy.ai validates `config.yaml` before
  opening the camera and prints every problem it finds (missing files,
  unknown gesture ids, more than one `clears_all: true`, malformed
  thresholds) instead of a raw traceback. Fix everything listed and rerun.
- **Low FPS**: detection runs on CPU by default. Closing other camera/GPU-heavy
  apps helps; MediaPipe Tasks is generally fast enough for ≥15 FPS on a
  modern laptop CPU.

## Out of scope (v1)

Audio, model training, a gesture-recording UI, multi-camera support, mobile,
single-*file* packaging (the standalone build is a one-folder app), and
combos (the engine supports them via `combos:` in `config.yaml`, but none
are configured out of the box).

## License

MIT — see `LICENSE`.
