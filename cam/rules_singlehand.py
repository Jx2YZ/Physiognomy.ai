"""Single-hand static-pose triggers: nerd (index finger up), thumbs_up.

Pure geometry on HandState - no face required and no tunable thresholds:
finger-extension flags plus an upward-orientation check (tip above both its
MCP joint and the wrist in image space, i.e. smaller y).
"""
from __future__ import annotations

import math

from cam.states import FINGER_JOINTS, HandState

INDEX_MCP = 5
THUMB_MCP = 2


def _fingers_balled(hand: HandState) -> bool:
    """True when index/middle/ring/pinky are all folded back into the palm:
    each fingertip no farther from the wrist than its PIP joint. Stricter
    than "not extended" - a relaxed half-open hand passes the extension
    flags but fails this."""
    wx, wy = hand.wrist_px
    for name in ("index", "middle", "ring", "pinky"):
        _, pip_i, _, tip_i = FINGER_JOINTS[name]
        tip = hand.landmarks_px[tip_i]
        pip = hand.landmarks_px[pip_i]
        tip_dist = math.hypot(tip[0] - wx, tip[1] - wy)
        pip_dist = math.hypot(pip[0] - wx, pip[1] - wy)
        if tip_dist > pip_dist * 1.05:
            return False
    return True


def nerd(hands: list[HandState]) -> bool:
    """Index finger extended and pointing up; middle/ring/pinky curled.
    Thumb state is ignored - it reads noisily when tucked beside the fist."""
    for hand in hands:
        ext = hand.extended
        if not ext["index"] or ext["middle"] or ext["ring"] or ext["pinky"]:
            continue
        tip = hand.fingertips_px["index"]
        mcp = hand.landmarks_px[INDEX_MCP]
        if tip[1] < mcp[1] and tip[1] < hand.wrist_px[1]:
            return True
    return False


def thumbs_up(hands: list[HandState]) -> bool:
    """Thumb extended and clearly pointing up; the four fingers balled into
    a fist (tips folded back to their PIP joints, not merely "not extended"),
    so a relaxed open-ish hand cannot fire it."""
    for hand in hands:
        ext = hand.extended
        if not ext["thumb"] or ext["index"] or ext["middle"] or ext["ring"] or ext["pinky"]:
            continue
        if not _fingers_balled(hand):
            continue
        tip = hand.fingertips_px["thumb"]
        mcp = hand.landmarks_px[THUMB_MCP]
        # Mostly vertical: the thumb must rise more than it drifts sideways
        # (within ~45 degrees of straight up), not just end above its MCP.
        rise = mcp[1] - tip[1]
        run = abs(tip[0] - mcp[0])
        if rise > run and tip[1] < hand.wrist_px[1]:
            return True
    return False
