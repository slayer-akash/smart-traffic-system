"""
Signal logic for smart traffic system.
- 8 signals across 2 intersections (4 cameras, each maps to specific signals)
- Vehicle-count-proportional green time
- Yellow transition before switching
- Ambulance override: cam's signal(s) green, all others red
- Accident skip: skips signals on roads with reported/detected accident
- Manual override from dashboard
"""

import time

# ── Configuration ──
NUM_SIGNALS      = 8
NUM_CAMERAS      = 4
MIN_GREEN_TIME   = 10      # seconds — minimum green per camera-group
MAX_GREEN_TIME   = 60      # seconds — maximum green per camera-group
TOTAL_CYCLE_TIME = 120     # seconds — total cycle across all 4 groups
YELLOW_TIME      = 3       # seconds — yellow light duration before red
CONGESTION_LIMIT = 10      # vehicles — threshold to trigger congestion alert

# Camera → signals it controls
# Edit this to match your physical wiring!
CAM_TO_SIGNALS = {
    0: [4],   # cam 0 → S5
    1: [5],   # cam 1 → S6
    2: [6],   # cam 2 → S7
    3: [7],   # cam 3 → S8
}

CAM_NAMES    = ["North", "East", "South", "West"]
SIGNAL_NAMES = [f"S{i+1}" for i in range(NUM_SIGNALS)]

# ── State ──
current_green_cam   = 0
last_switch_time    = time.time()
in_yellow_phase     = False
yellow_start_time   = 0.0
next_cam_after_yellow = 0

ambulance_override  = False
ambulance_cam       = -1

manual_override     = False
manual_cam          = 0

green_times         = [30] * NUM_CAMERAS
vehicle_counts      = [0]  * NUM_CAMERAS
congestion_alerts   = [False] * NUM_CAMERAS
accident_flags_int  = [False] * NUM_CAMERAS   # last received accident state


def compute_green_times(counts):
    """Proportional green time per camera-group based on vehicle count."""
    total = sum(counts)
    if total == 0:
        equal = TOTAL_CYCLE_TIME // NUM_CAMERAS
        return [equal] * NUM_CAMERAS
    times = []
    for c in counts:
        t = int((c / total) * TOTAL_CYCLE_TIME)
        t = max(MIN_GREEN_TIME, min(t, MAX_GREEN_TIME))
        times.append(t)
    return times


def check_congestion(counts):
    for i, c in enumerate(counts):
        was = congestion_alerts[i]
        congestion_alerts[i] = c >= CONGESTION_LIMIT
        if congestion_alerts[i] and not was:
            print(f"[ALERT] Congestion on {CAM_NAMES[i]} ({c} vehicles)")


def set_ambulance_override(cam_index):
    global ambulance_override, ambulance_cam
    if not ambulance_override or ambulance_cam != cam_index:
        ambulance_override = True
        ambulance_cam = cam_index
        print(f"[EMERGENCY] Ambulance on {CAM_NAMES[cam_index]} — override active")


def clear_ambulance_override():
    global ambulance_override, ambulance_cam
    if ambulance_override:
        ambulance_override = False
        ambulance_cam = -1
        print("[INFO] Ambulance cleared, resuming normal cycle")


def set_manual_override(cam_index):
    global manual_override, manual_cam
    manual_override = True
    manual_cam = cam_index
    print(f"[MANUAL] {CAM_NAMES[cam_index]} forced GREEN")


def clear_manual_override():
    global manual_override
    manual_override = False
    print("[INFO] Manual override cleared")


def _pick_next_cam(start_cam, accident_flags):
    """Find next non-accident camera in rotation. Returns same cam if all blocked."""
    for offset in range(1, NUM_CAMERAS + 1):
        nxt = (start_cam + offset) % NUM_CAMERAS
        if not accident_flags[nxt]:
            return nxt
    return start_cam   # all blocked — stay


def get_signal_state():
    """Returns list of 8 strings: 'green' | 'yellow' | 'red'."""
    state = ["red"] * NUM_SIGNALS

    # Priority 1: ambulance override
    if ambulance_override and ambulance_cam >= 0:
        for sig in CAM_TO_SIGNALS[ambulance_cam]:
            state[sig] = "green"
        return state

    # Priority 2: manual override
    if manual_override:
        for sig in CAM_TO_SIGNALS[manual_cam]:
            state[sig] = "green"
        return state

    # Priority 3: yellow transition
    if in_yellow_phase:
        for sig in CAM_TO_SIGNALS[current_green_cam]:
            state[sig] = "yellow"
        return state

    # Normal: current_green_cam's signals are green
    for sig in CAM_TO_SIGNALS[current_green_cam]:
        state[sig] = "green"
    return state


def update(counts, ambulance_flags, accident_flags):
    """
    Called every processing cycle from app.py.
    counts          : list[4] vehicle counts per camera
    ambulance_flags : list[4] True if ambulance seen
    accident_flags  : list[4] True if accident on that road
    Returns: list[8] signal states
    """
    global current_green_cam, last_switch_time
    global in_yellow_phase, yellow_start_time, next_cam_after_yellow
    global vehicle_counts, green_times, accident_flags_int

    vehicle_counts     = list(counts)
    accident_flags_int = list(accident_flags)

    # ── Ambulance check (highest priority) ──
    for i, flag in enumerate(ambulance_flags):
        if flag:
            set_ambulance_override(i)
            return get_signal_state()

    if ambulance_override:
        clear_ambulance_override()

    # Manual override skips cycling
    if manual_override:
        return get_signal_state()

    check_congestion(counts)
    green_times = compute_green_times(counts)

    now = time.time()

    # ── Yellow phase handling ──
    if in_yellow_phase:
        if now - yellow_start_time >= YELLOW_TIME:
            current_green_cam = next_cam_after_yellow
            last_switch_time  = now
            in_yellow_phase   = False
            print(f"[CYCLE] Green → {CAM_NAMES[current_green_cam]}")
        return get_signal_state()

    # ── If current cam is on accident road, immediately move on ──
    if accident_flags[current_green_cam]:
        nxt = _pick_next_cam(current_green_cam, accident_flags)
        if nxt != current_green_cam:
            in_yellow_phase       = True
            yellow_start_time     = now
            next_cam_after_yellow = nxt
            print(f"[ACCIDENT-SKIP] Yellow phase on {CAM_NAMES[current_green_cam]}")
        return get_signal_state()

    # ── Check if it's time to rotate ──
    elapsed = now - last_switch_time
    if elapsed >= green_times[current_green_cam]:
        nxt = _pick_next_cam(current_green_cam, accident_flags)
        in_yellow_phase       = True
        yellow_start_time     = now
        next_cam_after_yellow = nxt
        print(f"[CYCLE] {CAM_NAMES[current_green_cam]} → yellow → {CAM_NAMES[nxt]}")

    return get_signal_state()


def get_status():
    """Full system status for dashboard."""
    return {
        "current_green_cam"  : current_green_cam,
        "cam_names"          : CAM_NAMES,
        "signal_names"       : SIGNAL_NAMES,
        "cam_to_signals"     : CAM_TO_SIGNALS,
        "green_times"        : green_times,
        "vehicle_counts"     : vehicle_counts,
        "ambulance_override" : ambulance_override,
        "ambulance_cam"      : ambulance_cam,
        "manual_override"    : manual_override,
        "manual_cam"         : manual_cam,
        "in_yellow_phase"    : in_yellow_phase,
        "congestion_alerts"  : congestion_alerts,
        "accident_flags"     : accident_flags_int,
        "signal_state"       : get_signal_state(),
    }


# ── Test ──
if __name__ == "__main__":
    print("[TEST] Simulating signal logic with 8 signals...\n")

    # Override yellow time for faster test
    YELLOW_TIME = 1
    MIN_GREEN_TIME = 3
    TOTAL_CYCLE_TIME = 20

    scenarios = [
        ([5, 2, 8, 1], [False]*4,        [False]*4),
        ([3, 0, 12, 4], [False]*4,       [False]*4),
        ([2, 6, 3, 1], [False, True, False, False], [False]*4),  # Ambulance E
        ([7, 3, 5, 9], [False]*4,        [False, False, True, False]),  # Accident S
    ]
    for counts, amb, acc in scenarios:
        state = update(counts, amb, acc)
        print(f"counts={counts} amb={amb} acc={acc}")
        print(f"  signals: {dict(zip(SIGNAL_NAMES, state))}")
        print(f"  green_cam={CAM_NAMES[current_green_cam]} yellow={in_yellow_phase}")
        print("-" * 60)
        time.sleep(0.5)
