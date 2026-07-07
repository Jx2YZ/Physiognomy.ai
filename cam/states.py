"""Atomic per-frame states computed from raw MediaPipe landmarks.

Atomic states fire nothing themselves. They are the vocabulary rules_*.py
is built from: finger extension, hand shapes, face blendshape reads, and
IOD-normalised geometry (mouth centre, chin, nose).

All pixel distances below are plain Euclidean distance in pixel space
(landmarks are converted from MediaPipe's normalized [0,1] coords using the
frame's actual width/height first, so aspect ratio does not distort them).
Every rule module then divides by FaceState.iod to get scale-invariant
"x IOD" units, per spec §5.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from cam.landmarks import FaceResult, FrameLandmarks, HandResult, Point3

Px = tuple[float, float]

# MediaPipe hand landmark topology: (MCP, PIP, DIP, TIP) per finger.
# Thumb uses (CMC, MCP, IP, TIP) - see is_thumb_extended for its own logic.
FINGER_JOINTS = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}
WRIST = 0

# Standard MediaPipe hand-skeleton bone connections (for preview drawing).
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

# Face mesh landmark indices used for geometry (canonical MediaPipe indices).
FACE_LEFT_EYE_OUTER = 263
FACE_RIGHT_EYE_OUTER = 33
FACE_MOUTH_TOP = 13
FACE_MOUTH_BOTTOM = 14
FACE_MOUTH_LEFT = 61
FACE_MOUTH_RIGHT = 291
FACE_CHIN = 152
FACE_NOSE_TIP = 1


def _to_px(point: Point3, width: int, height: int) -> Px:
    return (point[0] * width, point[1] * height)


def _dist(a: Px, b: Px) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _midpoint(*points: Px) -> Px:
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)


# Public aliases used by rules_*.py (kept alongside the private names above
# so this module's internal geometry helpers stay one canonical implementation).
def midpoint(*points: Px) -> Px:
    return _midpoint(*points)


def dist_iod(a: Px, b: Px, iod: float) -> float:
    """Euclidean pixel distance between a and b, expressed in units of IOD."""
    return _dist(a, b) / max(iod, 1e-6)


def _angle_deg(v1: Px, v2: Px) -> float:
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    cos_a = max(-1.0, min(1.0, dot / (n1 * n2)))
    return math.degrees(math.acos(cos_a))


@dataclass
class HandState:
    handedness: str
    landmarks_px: list[Px]
    extended: dict[str, bool]
    shape: str  # "open_palm" | "fist" | "gun_sign" | "other"
    wrist_px: Px
    centroid_px: Px
    fingertips_px: dict[str, Px] = field(default_factory=dict)


@dataclass
class FaceState:
    iod: float
    mouth_centre_px: Px
    chin_y: float
    nose_tip_px: Px
    tongue_out: float
    eye_squint: float
    mouth_smile: float
    jaw_open: float
    mouth_lower_down: float
    landmarks_px: list[Px] = field(default_factory=list)


@dataclass
class FrameState:
    hands: list[HandState]
    face: FaceState | None
    width: int
    height: int


@dataclass
class HistoryEntry:
    """One frame's worth of computed state, timestamped for sliding-window
    analysis (rules_motion.six_seven) and per-frame deltas (hands_up speed)."""

    timestamp: float
    frame_state: FrameState


def _is_finger_extended(pts: list[Px], wrist: Px, joints: tuple[int, int, int, int]) -> bool:
    mcp_i, pip_i, dip_i, tip_i = joints
    mcp, pip, tip = pts[mcp_i], pts[pip_i], pts[tip_i]
    dist_tip = _dist(wrist, tip)
    dist_pip = _dist(wrist, pip)
    if dist_tip <= dist_pip * 1.1:
        return False
    # Straightness check at the PIP joint: near-180 degrees means extended.
    v1 = (mcp[0] - pip[0], mcp[1] - pip[1])
    v2 = (tip[0] - pip[0], tip[1] - pip[1])
    return _angle_deg(v1, v2) > 140.0


def _is_thumb_extended(pts: list[Px], wrist: Px) -> bool:
    cmc_i, mcp_i, ip_i, tip_i = FINGER_JOINTS["thumb"]
    cmc, mcp, ip, tip = pts[cmc_i], pts[mcp_i], pts[ip_i], pts[tip_i]

    direction = (mcp[0] - cmc[0], mcp[1] - cmc[1])
    norm = math.hypot(*direction)
    if norm < 1e-6:
        return False
    direction = (direction[0] / norm, direction[1] / norm)

    disp = (tip[0] - ip[0], tip[1] - ip[1])
    along = disp[0] * direction[0] + disp[1] * direction[1]

    dist_tip = _dist(wrist, tip)
    dist_mcp = _dist(wrist, mcp)
    # Strict: tip must continue past the IP joint along the thumb's own axis
    # AND be meaningfully farther from the wrist than the MCP - this is what
    # disambiguates gun_sign's extended thumb from a thumb tucked into a fist.
    return along > 0 and dist_tip > dist_mcp * 1.2


def _classify_shape(extended: dict[str, bool], pts: list[Px], wrist: Px) -> str:
    all_extended = all(extended.values())
    none_extended = not any(extended.values())

    if all_extended:
        index_tip = pts[FINGER_JOINTS["index"][3]]
        pinky_tip = pts[FINGER_JOINTS["pinky"][3]]
        middle_mcp = pts[FINGER_JOINTS["middle"][0]]
        hand_size = _dist(wrist, middle_mcp)
        spread = _dist(index_tip, pinky_tip)
        if hand_size > 1e-6 and spread > 0.9 * hand_size:
            return "open_palm"

    if none_extended:
        return "fist"

    if (
        extended["thumb"]
        and extended["index"]
        and extended["middle"]
        and not extended["ring"]
        and not extended["pinky"]
    ):
        return "gun_sign"

    return "other"


def _compute_hand_state(hand: HandResult, width: int, height: int) -> HandState:
    pts = [_to_px(p, width, height) for p in hand.landmarks]
    wrist = pts[WRIST]

    extended = {"thumb": _is_thumb_extended(pts, wrist)}
    for name, joints in FINGER_JOINTS.items():
        if name == "thumb":
            continue
        extended[name] = _is_finger_extended(pts, wrist, joints)

    fingertips = {name: pts[joints[3]] for name, joints in FINGER_JOINTS.items()}
    shape = _classify_shape(extended, pts, wrist)
    centroid = _midpoint(*pts)

    return HandState(
        handedness=hand.handedness,
        landmarks_px=pts,
        extended=extended,
        shape=shape,
        wrist_px=wrist,
        centroid_px=centroid,
        fingertips_px=fingertips,
    )


def _compute_face_state(face: FaceResult, width: int, height: int) -> FaceState:
    pts = [_to_px(p, width, height) for p in face.landmarks]
    iod = _dist(pts[FACE_LEFT_EYE_OUTER], pts[FACE_RIGHT_EYE_OUTER])
    mouth_centre = _midpoint(
        pts[FACE_MOUTH_TOP], pts[FACE_MOUTH_BOTTOM], pts[FACE_MOUTH_LEFT], pts[FACE_MOUTH_RIGHT]
    )
    bs = face.blendshapes
    return FaceState(
        iod=max(iod, 1e-6),
        mouth_centre_px=mouth_centre,
        chin_y=pts[FACE_CHIN][1],
        nose_tip_px=pts[FACE_NOSE_TIP],
        tongue_out=bs.get("tongueOut", 0.0),
        eye_squint=(bs.get("eyeSquintLeft", 0.0) + bs.get("eyeSquintRight", 0.0)) / 2.0,
        mouth_smile=(bs.get("mouthSmileLeft", 0.0) + bs.get("mouthSmileRight", 0.0)) / 2.0,
        jaw_open=bs.get("jawOpen", 0.0),
        mouth_lower_down=(bs.get("mouthLowerDownLeft", 0.0) + bs.get("mouthLowerDownRight", 0.0)) / 2.0,
        landmarks_px=pts,
    )


def compute_frame_state(frame_landmarks: FrameLandmarks) -> FrameState:
    w, h = frame_landmarks.width, frame_landmarks.height
    hands = [_compute_hand_state(hand, w, h) for hand in frame_landmarks.hands]
    face = _compute_face_state(frame_landmarks.face, w, h) if frame_landmarks.face else None
    return FrameState(hands=hands, face=face, width=w, height=h)
