"""The trigger engine: priority tiers, suppression, hold-to-confirm,
cooldowns, idle detection, and the shared landmark history deque
(spec §4, §7, §8).

Engine.update() is called once per processed frame from the worker thread
and returns at most one TriggerEvent - the caller pushes that onto the
thread-safe queue main.py drains on the Tk side.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from cam import rules_face, rules_interactions, rules_motion, rules_singlehand, rules_twohand
from cam.config import AppConfig, GestureConfig
from cam.states import FrameState, HistoryEntry

# Must hold at least head_shake_window_seconds of frames (~2.5s at 30fps).
HISTORY_MAXLEN = 120

# Triggers confirmed via N-consecutive-frames hold (all except six_seven,
# which uses its own sliding window, and neutral, which uses a duration timer).
HOLD_BASED_IDS = (
    "double_guns",
    "hands_up",
    "pray",
    "finger_bite",
    "fist_cover_mouth",
    "lip_pull",
    "tongue_out",
    "squint_smile",
    "nerd",
    "thumbs_up",
)

# Priority tiers, high -> low (spec §8). Combos are evaluated first (engine
# supports them; config ships none). Order within the two-hand+motion tier
# is a deliberate tie-break: double_guns (terminator) first, six_seven
# (already window-confirmed) next, then hands_up, then pray.
TWO_HAND_MOTION_ORDER = ("double_guns", "six_seven", "hands_up", "pray")
INTERACTION_ORDER = ("finger_bite", "fist_cover_mouth", "lip_pull")
SINGLE_HAND_ORDER = ("thumbs_up", "nerd")
FACE_ORDER = ("head_shake", "tongue_out", "squint_smile")


@dataclass
class TriggerEvent:
    gesture_id: str
    timestamp: float
    meme_path: Path
    display_seconds: float
    clears_all: bool


@dataclass
class EngineDebugInfo:
    """Snapshot for preview.py's HUD - not used for decision logic."""

    conditions: dict[str, bool] = field(default_factory=dict)
    hold_counters: dict[str, int] = field(default_factory=dict)
    idle_elapsed: float = 0.0
    idle_seconds: float = 5.0
    six_seven_hot: bool = False
    last_fired: str | None = None
    last_fired_ts: float | None = None
    wrist_speeds: dict[str, float] = field(default_factory=dict)


class Engine:
    def __init__(self, config: AppConfig):
        self.config = config
        self._history: deque[HistoryEntry] = deque(maxlen=HISTORY_MAXLEN)
        # Gestures absent from config.yaml are disabled: no hold counter, no
        # rule evaluation, no suppression influence.
        self._hold_counters: dict[str, int] = {
            gid: 0 for gid in HOLD_BASED_IDS if gid in config.gestures
        }
        self._last_fired: dict[str, float] = {}
        self._activity_free_since: float | None = None
        self._last_debug = EngineDebugInfo()

    def _gesture(self, gesture_id: str) -> GestureConfig:
        return self.config.gestures[gesture_id]

    def _compute_wrist_speeds(self) -> dict[str, float]:
        """Per-wrist vertical speed in IOD/frame, from the last two frames."""
        if len(self._history) < 2:
            return {}
        curr = self._history[-1].frame_state
        prev = self._history[-2].frame_state
        if not curr.face:
            return {}
        iod = curr.face.iod
        prev_by_hand = {h.handedness: h for h in prev.hands}
        speeds: dict[str, float] = {}
        for hand in curr.hands:
            prev_hand = prev_by_hand.get(hand.handedness)
            if prev_hand is None:
                speeds[hand.handedness] = 0.0
                continue
            dy = abs(hand.wrist_px[1] - prev_hand.wrist_px[1])
            speeds[hand.handedness] = dy / iod
        return speeds

    def _cooldown_ok(self, gesture_id: str, timestamp: float) -> bool:
        last = self._last_fired.get(gesture_id)
        if last is None:
            return True
        return (timestamp - last) >= self._gesture(gesture_id).cooldown_seconds

    def update(self, frame_state: FrameState, timestamp: float) -> TriggerEvent | None:
        self._history.append(HistoryEntry(timestamp=timestamp, frame_state=frame_state))
        history_list = list(self._history)
        th = self.config.thresholds
        engine_cfg = self.config.engine

        hands = frame_state.hands
        face = frame_state.face
        wrist_speeds = self._compute_wrist_speeds()

        # --- Raw (pre-suppression) conditions -----------------------------
        # A gesture missing from config.gestures is disabled: its rule is not
        # evaluated, so it can't fire, suppress others, or reset the idle timer.
        enabled = self.config.gestures

        double_guns_raw = "double_guns" in enabled and rules_twohand.double_guns(hands)
        six_seven_active = "six_seven" in enabled and rules_motion.six_seven(
            history_list, timestamp, engine_cfg.motion_window_seconds, th
        )
        six_seven_hot = "six_seven" in enabled and (
            six_seven_active
            or rules_motion.six_seven_building(
                history_list, timestamp, engine_cfg.motion_window_seconds, th
            )
        )
        hands_up_raw = "hands_up" in enabled and rules_twohand.hands_up(
            hands, face, wrist_speeds, th
        )
        pray_raw = "pray" in enabled and rules_twohand.pray(hands, face, th)

        finger_bite_raw = "finger_bite" in enabled and rules_interactions.finger_bite(
            hands, face, th
        )
        fist_cover_mouth_raw = (
            "fist_cover_mouth" in enabled
            and rules_interactions.fist_cover_mouth(hands, face, th)
        )
        lip_pull_raw = "lip_pull" in enabled and rules_interactions.lip_pull(hands, face, th)

        tongue_out_raw = "tongue_out" in enabled and rules_face.tongue_out(face, th)
        squint_smile_raw = "squint_smile" in enabled and rules_face.squint_smile(face, th)
        head_shake_raw = "head_shake" in enabled and rules_motion.head_shake(
            history_list, timestamp, th.head_shake_window_seconds, th
        )

        # --- Suppression (spec §8, mandatory) ------------------------------
        # six_seven hot (building or firing) suppresses hands_up.
        hands_up_active = hands_up_raw and not six_seven_hot
        double_guns_active = double_guns_raw
        pray_active = pray_raw

        two_hand_any_active = double_guns_active or six_seven_active or hands_up_active or pray_active

        # Any two-hand trigger active suppresses interactions this frame.
        finger_bite_active = finger_bite_raw and not two_hand_any_active
        fist_cover_mouth_active = fist_cover_mouth_raw and not two_hand_any_active
        lip_pull_active = lip_pull_raw and not two_hand_any_active
        interaction_any_active = finger_bite_active or fist_cover_mouth_active or lip_pull_active

        # Single-hand static poses: suppressed by two-hand gestures and
        # hand-to-face interactions (a thumb near the mouth is a fist-cover,
        # not a thumbs-up).
        nerd_raw = "nerd" in enabled and rules_singlehand.nerd(hands)
        thumbs_up_raw = "thumbs_up" in enabled and rules_singlehand.thumbs_up(hands)
        nerd_active = nerd_raw and not interaction_any_active and not two_hand_any_active
        thumbs_up_active = thumbs_up_raw and not interaction_any_active and not two_hand_any_active

        # Any interaction active suppresses face singles this frame.
        tongue_out_active = tongue_out_raw and not interaction_any_active and not two_hand_any_active
        squint_smile_active = squint_smile_raw and not interaction_any_active and not two_hand_any_active
        head_shake_active = head_shake_raw and not interaction_any_active and not two_hand_any_active

        conditions = {
            "double_guns": double_guns_active,
            "six_seven": six_seven_active,
            "hands_up": hands_up_active,
            "pray": pray_active,
            "finger_bite": finger_bite_active,
            "fist_cover_mouth": fist_cover_mouth_active,
            "lip_pull": lip_pull_active,
            "tongue_out": tongue_out_active,
            "squint_smile": squint_smile_active,
            "head_shake": head_shake_active,
            "nerd": nerd_active,
            "thumbs_up": thumbs_up_active,
        }

        # --- Hold-to-confirm counters (configured gestures only) ---------
        for gid in self._hold_counters:
            if conditions.get(gid, False):
                self._hold_counters[gid] += 1
            else:
                self._hold_counters[gid] = 0

        ready: dict[str, bool] = {}
        for gid in self._hold_counters:
            ready[gid] = self._hold_counters[gid] >= self._gesture(gid).hold_frames
        ready["six_seven"] = six_seven_active
        # head_shake is window-confirmed like six_seven, not hold-based.
        ready["head_shake"] = head_shake_active

        # --- Idle / neutral (evaluated last; any activity resets its timer) ---
        any_activity = (
            double_guns_raw
            or six_seven_hot
            or hands_up_raw
            or pray_raw
            or finger_bite_raw
            or fist_cover_mouth_raw
            or lip_pull_raw
            or tongue_out_raw
            or squint_smile_raw
            or head_shake_raw
            or nerd_raw
            or thumbs_up_raw
            or any(c > 0 for c in self._hold_counters.values())
        )
        if face is None or any_activity:
            self._activity_free_since = None
            idle_elapsed = 0.0
        else:
            if self._activity_free_since is None:
                self._activity_free_since = timestamp
            idle_elapsed = timestamp - self._activity_free_since

        neutral_ready = (
            "neutral" in enabled
            and face is not None
            and not any_activity
            and idle_elapsed >= engine_cfg.idle_seconds
        )

        # --- Priority resolution: at most one trigger fires this frame ---
        winner: str | None = None
        for gid in (*TWO_HAND_MOTION_ORDER, *INTERACTION_ORDER, *SINGLE_HAND_ORDER, *FACE_ORDER):
            if ready.get(gid, False) and self._cooldown_ok(gid, timestamp):
                winner = gid
                break
        if winner is None and neutral_ready and self._cooldown_ok("neutral", timestamp):
            winner = "neutral"

        self._last_debug = EngineDebugInfo(
            conditions=conditions,
            hold_counters=dict(self._hold_counters),
            idle_elapsed=idle_elapsed,
            idle_seconds=engine_cfg.idle_seconds,
            six_seven_hot=six_seven_hot,
            last_fired=self._last_debug.last_fired,
            last_fired_ts=self._last_debug.last_fired_ts,
            wrist_speeds=wrist_speeds,
        )

        if winner is None:
            return None

        self._last_fired[winner] = timestamp
        self._last_debug.last_fired = winner
        self._last_debug.last_fired_ts = timestamp

        gesture_cfg = self._gesture(winner)
        return TriggerEvent(
            gesture_id=winner,
            timestamp=timestamp,
            meme_path=gesture_cfg.meme_path,
            display_seconds=self.config.popups.display_seconds,
            clears_all=gesture_cfg.clears_all,
        )

    def debug_info(self) -> EngineDebugInfo:
        return self._last_debug
