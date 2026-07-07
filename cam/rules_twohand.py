"""Two-hand triggers: hands_up, pray, double_guns (spec §7)."""
from __future__ import annotations

from cam.config import Thresholds
from cam.states import FaceState, HandState, dist_iod, midpoint


def hands_up(
    hands: list[HandState],
    face: FaceState | None,
    wrist_speeds: dict[str, float],
    thresholds: Thresholds,
) -> bool:
    if face is None:
        return False
    palms = [h for h in hands if h.shape == "open_palm"]
    if len(palms) < 2:
        return False
    for hand in palms[:2]:
        if hand.wrist_px[1] >= face.chin_y:
            return False
        if wrist_speeds.get(hand.handedness, 0.0) >= thresholds.hands_up_max_speed:
            return False
    return True


def pray(hands: list[HandState], face: FaceState | None, thresholds: Thresholds) -> bool:
    # No finger-state requirement by design - interlocked fingers confuse the
    # landmarker, so this rule only looks at hand-to-hand and hand-to-mouth
    # proximity (spec §7).
    if face is None or len(hands) < 2:
        return False
    h1, h2 = hands[0], hands[1]
    hand_dist = dist_iod(h1.centroid_px, h2.centroid_px, face.iod)
    if hand_dist >= thresholds.pray_hands_distance:
        return False
    joint_centroid = midpoint(h1.centroid_px, h2.centroid_px)
    return dist_iod(joint_centroid, face.mouth_centre_px, face.iod) < thresholds.pray_mouth_distance


def double_guns(hands: list[HandState]) -> bool:
    guns = [h for h in hands if h.shape == "gun_sign"]
    return len(guns) >= 2
