"""Single-hand <-> face interaction triggers: finger_bite, fist_cover_mouth,
lip_pull (spec §7)."""
from __future__ import annotations

import math

from cam.config import Thresholds
from cam.states import FINGER_JOINTS, FaceState, HandState, dist_iod


def _pinky_showing(hand: HandState) -> bool:
    """Pinky sticking out rather than balled: tip farther from the wrist than
    its PIP joint. Softer than the extension flag, which demands a straight
    finger - a pinky hooked into the lip is bent but still showing."""
    if len(hand.landmarks_px) < 21:
        return False
    _, pip_i, _, tip_i = FINGER_JOINTS["pinky"]
    wx, wy = hand.wrist_px
    tip = hand.landmarks_px[tip_i]
    pip = hand.landmarks_px[pip_i]
    tip_dist = math.hypot(tip[0] - wx, tip[1] - wy)
    pip_dist = math.hypot(pip[0] - wx, pip[1] - wy)
    return tip_dist > pip_dist * 1.05


def finger_bite(hands: list[HandState], face: FaceState | None, thresholds: Thresholds) -> bool:
    if face is None:
        return False
    low, high = thresholds.finger_bite_jaw
    if not (low <= face.jaw_open <= high):
        return False
    for hand in hands:
        if hand.shape == "fist":
            continue
        for tip in hand.fingertips_px.values():
            if dist_iod(tip, face.mouth_centre_px, face.iod) <= thresholds.finger_bite_distance:
                return True
    return False


def fist_cover_mouth(hands: list[HandState], face: FaceState | None, thresholds: Thresholds) -> bool:
    if face is None:
        return False
    for hand in hands:
        # Strict "fist" classification is unreliable when the knuckles face
        # the camera (curled fingers occlude their own joints), so accept any
        # mostly-closed hand: at most one finger reading as extended.
        if sum(1 for v in hand.extended.values() if v) > 1:
            continue
        if dist_iod(hand.centroid_px, face.mouth_centre_px, face.iod) <= thresholds.fist_mouth_distance:
            return True
    return False


def lip_pull(hands: list[HandState], face: FaceState | None, thresholds: Thresholds) -> bool:
    """Grill-flex meme: lower lip pulled down (teeth shown) by the pinky of a
    shaka-like hand - thumb and pinky both clearly showing, index/middle/ring
    balled up."""
    if face is None:
        return False
    if face.mouth_lower_down <= thresholds.lip_pull_lower_down:
        return False
    for hand in hands:
        # Thumb clearly showing (it sits away from the face, so its
        # extension flag reads reliably here).
        if not hand.extended["thumb"]:
            continue
        # index/middle/ring balled up. Extension flags misread when the
        # knuckles face the camera and fingers occlude their own joints (the
        # hand is right at the face), so tolerate one stray "extended"
        # reading: reject only when two or more read extended (open hand).
        if sum(1 for f in ("index", "middle", "ring") if hand.extended[f]) >= 2:
            continue
        # Pinky clearly showing: extension flag, or geometrically not balled
        # (a pinky hooked into the lip is bent, which fails the flag).
        if not hand.extended["pinky"] and not _pinky_showing(hand):
            continue
        pinky_tip = hand.fingertips_px.get("pinky")
        if pinky_tip is None:
            continue
        pinky_dist = dist_iod(pinky_tip, face.mouth_centre_px, face.iod)
        if pinky_dist > thresholds.lip_pull_distance:
            continue
        # The pinky does the pulling: nearest to the mouth of the four
        # fingers. The thumb is excluded - it sticks out sideways in this
        # pose and can legitimately hover near the chin.
        other_dists = [
            dist_iod(hand.fingertips_px[f], face.mouth_centre_px, face.iod)
            for f in ("index", "middle", "ring")
            if f in hand.fingertips_px
        ]
        if not other_dists or pinky_dist < min(other_dists):
            return True
    return False
