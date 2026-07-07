"""Motion trigger: six_seven, a sliding-window wrist-oscillation detector
(spec §7). Consumes the shared landmark history deque that engine.py
maintains; does not keep its own state so it stays a pure function of
(history, now) and is easy to unit test."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from cam.config import Thresholds
from cam.states import HistoryEntry

_OPEN_ISH_MIN_EXTENDED = 3


def _is_open_ish(extended: dict[str, bool]) -> bool:
    return sum(1 for v in extended.values() if v) >= _OPEN_ISH_MIN_EXTENDED


def _count_reversals(values: Sequence[float], amplitude: float) -> int:
    """Counts direction reversals in a y-position (IOD units) sequence whose
    swing exceeds `amplitude`. Runs peak/trough tracking: extend the current
    run while it keeps moving the same way, and only count a reversal once
    the run's total swing clears the amplitude floor."""
    if len(values) < 3:
        return 0

    reversals = 0
    direction = 0  # 0 unknown, 1 = moving up (y decreasing... see note below), -1 = moving down
    extreme = values[0]
    last_confirmed = values[0]

    for v in values[1:]:
        if direction == 0:
            if v > extreme:
                direction = 1
                extreme = v
            elif v < extreme:
                direction = -1
                extreme = v
            continue

        moving_same_way = (direction == 1 and v >= extreme) or (direction == -1 and v <= extreme)
        if moving_same_way:
            extreme = v
            continue

        # Direction flipped: bank the previous run if it was big enough.
        if abs(extreme - last_confirmed) >= amplitude:
            reversals += 1
            last_confirmed = extreme
        direction = 1 if v > extreme else -1
        extreme = v

    if abs(extreme - last_confirmed) >= amplitude:
        reversals += 1

    return reversals


def _reversal_sequences(history: "list[HistoryEntry]", now_ts: float, window_seconds: float):
    window_entries = [e for e in history if now_ts - e.timestamp <= window_seconds]
    sequences: dict[str, list[float]] = defaultdict(list)
    for entry in window_entries:
        fs = entry.frame_state
        if not fs.face:
            continue
        iod = fs.face.iod
        for hand in fs.hands:
            sequences[hand.handedness].append(hand.wrist_px[1] / iod)
    return window_entries, sequences


def six_seven_building(
    history: "list[HistoryEntry]",
    now_ts: float,
    window_seconds: float,
    thresholds: Thresholds,
) -> bool:
    """True while an oscillation looks like it's forming: at least one
    reversal already logged for a currently-open-ish wrist within the
    window. Used to suppress hands_up before six_seven fully confirms
    (spec §8: "oscillation building or just fired")."""
    if not history:
        return False
    current = history[-1].frame_state
    if not current.face:
        return False
    current_hands = [h for h in current.hands if _is_open_ish(h.extended)]
    if not current_hands:
        return False
    window_entries, sequences = _reversal_sequences(history, now_ts, window_seconds)
    if len(window_entries) < 3:
        return False
    for hand in current_hands:
        seq = sequences.get(hand.handedness, [])
        if _count_reversals(seq, thresholds.six_seven_amplitude) >= 1:
            return True
    return False


def head_shake(
    history: "list[HistoryEntry]",
    now_ts: float,
    window_seconds: float,
    thresholds: Thresholds,
) -> bool:
    """Left-right head-shake detector: counts horizontal direction reversals
    of the nose tip (in IOD units) inside the sliding window. Same
    peak/trough reversal counting as six_seven, but on the face instead of
    the wrists, so it needs no hands in frame."""
    if not history:
        return False
    if not history[-1].frame_state.face:
        return False

    xs = [
        e.frame_state.face.nose_tip_px[0] / e.frame_state.face.iod
        for e in history
        if e.frame_state.face and now_ts - e.timestamp <= window_seconds
    ]
    if len(xs) < 3:
        return False
    return _count_reversals(xs, thresholds.head_shake_amplitude) >= thresholds.head_shake_reversals


def six_seven(
    history: "list[HistoryEntry]",
    now_ts: float,
    window_seconds: float,
    thresholds: Thresholds,
) -> bool:
    """Both hands doing the 6-7 motion: a Left AND a Right open-ish hand
    must each log more than two up-down shifts (six_seven_reversals, in
    IOD-unit wrist-y reversals) inside the sliding window. One hand
    oscillating alone, or two same-labelled hands, is not enough."""
    if not history:
        return False

    current = history[-1].frame_state
    if not current.face:
        return False

    current_labels = {h.handedness for h in current.hands if _is_open_ish(h.extended)}
    if not {"Left", "Right"} <= current_labels:
        return False

    window_entries = [e for e in history if now_ts - e.timestamp <= window_seconds]
    if len(window_entries) < 3:
        return False

    sequences: dict[str, list[float]] = defaultdict(list)
    for entry in window_entries:
        fs = entry.frame_state
        if not fs.face:
            continue
        iod = fs.face.iod
        for hand in fs.hands:
            sequences[hand.handedness].append(hand.wrist_px[1] / iod)

    for label in ("Left", "Right"):
        seq = sequences.get(label, [])
        if _count_reversals(seq, thresholds.six_seven_amplitude) < thresholds.six_seven_reversals:
            return False

    return True
