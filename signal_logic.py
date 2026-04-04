import time

# ── Configuration ──
NUM_ROADS        = 4
MIN_GREEN_TIME   = 10   # seconds — minimum green per road
MAX_GREEN_TIME   = 60   # seconds — maximum green per road
TOTAL_CYCLE_TIME = 120  # seconds — total cycle across all 4 roads
CONGESTION_LIMIT = 10   # vehicles — threshold to trigger congestion alert
YELLOW_TIME      = 3    # seconds — yellow light duration

# Road names
ROAD_NAMES = ["North", "East", "South", "West"]

# ── State ──
current_green_road    = 0       # which road is currently green
ambulance_override    = False   # is ambulance override active?
ambulance_road        = -1      # which road has the ambulance
manual_override       = False   # is manual override active?
manual_green_road     = 0       # which road is manually set green
green_times           = [30, 30, 30, 30]  # current green time per road
vehicle_counts        = [0, 0, 0, 0]      # current vehicle count per road
congestion_alerts     = [False, False, False, False]  # congestion flags

def compute_green_times(counts):
    """
    Computes proportional green time for each road
    based on vehicle count.
    """
    total = sum(counts)
    times = []

    if total == 0:
        # Equal time if no vehicles detected
        equal = TOTAL_CYCLE_TIME // NUM_ROADS
        return [equal] * NUM_ROADS

    for c in counts:
        t = int((c / total) * TOTAL_CYCLE_TIME)
        t = max(t, MIN_GREEN_TIME)
        t = min(t, MAX_GREEN_TIME)
        times.append(t)

    return times

def check_congestion(counts):
    """
    Checks if any road has exceeded the congestion threshold.
    Returns list of congested road indices.
    """
    congested = []
    for i, c in enumerate(counts):
        if c >= CONGESTION_LIMIT:
            congested.append(i)
            congestion_alerts[i] = True
            print(f"[ALERT] Congestion on {ROAD_NAMES[i]} road! ({c} vehicles)")
        else:
            congestion_alerts[i] = False
    return congested

def set_ambulance_override(road_index):
    """Activates ambulance override for the given road."""
    global ambulance_override, ambulance_road
    ambulance_override = True
    ambulance_road     = road_index
    print(f"[EMERGENCY] Ambulance detected on {ROAD_NAMES[road_index]}! Override active.")

def clear_ambulance_override():
    """Clears ambulance override and resumes normal operation."""
    global ambulance_override, ambulance_road
    ambulance_override = False
    ambulance_road     = -1
    print("[INFO] Ambulance cleared. Resuming normal signal cycle.")

def set_manual_override(road_index):
    """Activates manual override for the given road."""
    global manual_override, manual_green_road
    manual_override    = True
    manual_green_road  = road_index
    print(f"[MANUAL] Manual override: {ROAD_NAMES[road_index]} set to GREEN.")

def clear_manual_override():
    """Clears manual override and resumes auto mode."""
    global manual_override
    manual_override = False
    print("[INFO] Manual override cleared. Resuming auto mode.")

def get_signal_state():
    """
    Returns the current signal state for all 4 roads.
    Each road gets: 'green', 'yellow', or 'red'
    """
    state = ["red"] * NUM_ROADS

    if ambulance_override and ambulance_road >= 0:
        state[ambulance_road] = "green"
        return state

    if manual_override:
        state[manual_green_road] = "green"
        return state

    state[current_green_road] = "green"
    return state

def update(counts, ambulance_flags):
    """
    Main update function — called every processing cycle.
    Takes vehicle counts and ambulance flags from detector.
    Returns current signal state.
    """
    global vehicle_counts, green_times, current_green_road

    vehicle_counts = counts

    # Check ambulance on any road
    for i, flag in enumerate(ambulance_flags):
        if flag:
            set_ambulance_override(i)
            return get_signal_state()

    # Clear ambulance if no longer detected
    if ambulance_override:
        clear_ambulance_override()

    # Check congestion
    check_congestion(counts)

    # Compute green times
    green_times = compute_green_times(counts)

    return get_signal_state()

def get_status():
    """Returns full system status as a dictionary for dashboard."""
    return {
        "current_green_road"  : current_green_road,
        "road_names"          : ROAD_NAMES,
        "green_times"         : green_times,
        "vehicle_counts"      : vehicle_counts,
        "ambulance_override"  : ambulance_override,
        "ambulance_road"      : ambulance_road,
        "manual_override"     : manual_override,
        "congestion_alerts"   : congestion_alerts,
        "signal_state"        : get_signal_state()
    }

# ── Test: run directly to simulate signal logic ──
if __name__ == "__main__":
    print("[TEST] Simulating signal logic...\n")

    # Simulate different vehicle counts per road
    test_scenarios = [
        ([5, 2, 8, 1],  [False, False, False, False]),  # Normal traffic
        ([3, 0, 12, 4], [False, False, False, False]),  # Congestion on South
        ([2, 6, 3, 1],  [False, True,  False, False]),  # Ambulance on East
        ([7, 3, 5, 9],  [False, False, False, False]),  # Heavy West traffic
    ]

    for counts, amb_flags in test_scenarios:
        state  = update(counts, amb_flags)
        status = get_status()
        print(f"Counts : {counts}")
        print(f"Signals: {dict(zip(ROAD_NAMES, state))}")
        print(f"Green times: {dict(zip(ROAD_NAMES, green_times))}")
        print("-" * 50)
        time.sleep(1)
        