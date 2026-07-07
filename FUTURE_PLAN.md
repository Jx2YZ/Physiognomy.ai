# Physiognomy.ai — Future Plan

> _Last updated: 2026-07-06_

This is a **direction document, not a commitment**. It captures the vision for
v2.0 and the honest engineering assessment behind it, so whoever picks it up
later starts with context instead of a blank page.

---

## The v2.0 Idea

**Today (v1.0):** 10 hand-written gesture rules, each hard-mapped to a fixed
meme in `config.yaml`. Adding a new trigger means writing new geometry code.

**Goal (v2.0):** drop **any media** into the `assets/` folder, and an improved
model analyses it and auto-derives the trigger. The popup fires when the user
_mirrors_ the pose / expression / gesture shown in that media. No code changes
to add a new trigger — just drop a file.

In short: replace the 10 hand-coded rules with **one general matcher** that
asks _"does the user's live pose match this reference media?"_

---

## How It Would Work

_Pragmatic approach — stays 100% local and real-time._

The key insight: reuse the MediaPipe landmarkers already in the app, but run
them over the **dropped media** too — not just the live webcam.

### 1. On drop (offline, once per file)

- Run face + hand (**+ new:** body pose) landmarkers over the media.
- Extract a normalized **pose signature**:
  - face blendshapes (already computed in `states.py`)
  - hand landmark geometry (already computed)
  - full-body pose landmarks (**NEW** — MediaPipe Pose/Holistic, 33 pts)
- A still image → **one feature vector** (a static pose template).
- A gif / video → **a short sequence of vectors** (a motion template).
- Cache the template next to the media so it's computed only once.

### 2. At runtime (live)

- Compute the same features from the webcam every frame (already done).
- Compare live features to each cached template:
  - **static pose** → cosine / euclidean similarity on the vector
  - **motion** → sequence alignment (Dynamic Time Warping) to handle the
    user moving faster / slower than the reference
- Fire the popup when similarity crosses a threshold **and** holds briefly.

### 3. Reuse what exists

- `engine.py`'s hold-to-confirm, cooldown, priority, suppression, and idle
  logic all carry over unchanged.
- `states.py`'s feature extraction is the foundation; extend it with body pose.
- The popup manager and preview window need no changes.

> This is a natural **evolution** of the v1 architecture, **not a rewrite**.

---

## What's Easy vs Hard

_Honest scoping._

### ✅ Easy / straightforward

- Static human poses & facial expressions. Feature vector + similarity is
  well-trodden and fast on CPU.
- Reusing the existing engine / popup / preview plumbing.

### ⚠️ Harder (more work, still doable)

- **Motion matching** from a gif/video. Needs temporal alignment (DTW) and
  speed normalization, plus deciding when a motion "starts."
- **Full-body pose** (MediaPipe Pose/Holistic) — more CPU per frame, still fine
  on a modern laptop (~15 fps target).
- **Auto-tuning the match threshold per dropped file.** Today thresholds are
  hand-tuned in `config.yaml`; v2 must derive sensible ones automatically.
  This is the real difficulty — too loose = false fires, too tight = never
  triggers.

### ❌ Where "any media" breaks down (be honest with users)

- Media with **no human in a clear pose** — a text meme, a cartoon, a cat, an
  abstract image — has nothing to mirror, so no trigger can be derived.
- A true "understand literally anything" system would need a heavy multimodal
  model. That would be slower, less reliable, and would break the 100% local +
  real-time promise. **Not recommended** as the core path.
- **Honest scope:** _"drop in media of a person doing a pose / expression /
  gesture, and mirror it to trigger."_

---

## Open Questions to Resolve Before Building

- How does the app know **which** person/pose in a multi-person image is the
  intended trigger? (Pick largest? First detected? Let user pick?)
- Should templates be auto-cached, or is there a **calibration step** where the
  user confirms the derived pose looks right?
- How to name / track the mapping now that `config.yaml`'s gesture ids no longer
  apply? (Maybe: the filename _is_ the trigger; cache lives beside it.)
- Threshold auto-derivation strategy (per-file calibration vs global).
- Do we keep the 10 v1 rules as built-ins alongside the new matcher, or fully
  replace them?

---

## Smaller Improvements

_Not tied to the v2 vision._

- **Code-sign** the Windows `.exe` and the macOS `.app` to kill the SmartScreen
  / Gatekeeper "unknown publisher" warnings for end users.
- Optional **video-file input source** (`camera.source` in `config.yaml`) so the
  full pipeline can be tested on a machine without a webcam.
- A **gesture-recording / calibration UI** (was out of scope for v1).
- **Combos** are already supported by the engine but unconfigured — could ship a
  few in `config.yaml`.
- **One-file packaging** (currently one-folder for faster startup).
