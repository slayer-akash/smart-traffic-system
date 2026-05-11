"""
Accident detection.
- Tracks vehicle bounding box centers per camera
- If a vehicle stays stationary for >STATIONARY_THRESHOLD seconds → accident
- Supports manual accident reports from the dashboard
- Provides clear() so the dashboard can cancel a false report
"""

import time
from collections import defaultdict

# ── Tuning ──
STATIONARY_THRESHOLD = 15      # seconds vehicle must be still
MOVEMENT_TOLERANCE   = 30      # pixels — anything less = stationary
MAX_VEHICLE_AGE      = 60      # drop tracker entry after this many seconds
NUM_CAMERAS          = 4

# Per-camera tracker:
#   { cam_id : { vid : {"pos": (cx, cy), "since": ts, "last_seen": ts} } }
_trackers = defaultdict(dict)
_next_vid = defaultdict(lambda: 1)

# Per-camera manual accident flags (set from dashboard)
_manual = {i: False for i in range(NUM_CAMERAS)}


def _match_vehicle(cam_id, cx, cy):
    """Return vid of nearest already-tracked vehicle within tolerance, else None."""
    best, best_d = None, MOVEMENT_TOLERANCE + 1
    for vid, data in _trackers[cam_id].items():
        px, py = data["pos"]
        d = abs(px - cx) + abs(py - cy)
        if d < best_d:
            best, best_d = vid, d
    return best if best_d <= MOVEMENT_TOLERANCE * 2 else None


def check_accident(cam_id, boxes):
    """
    Update tracker with this frame's boxes, return True if accident detected.
    boxes = list of (x1, y1, x2, y2)
    """
    # Manual report always wins
    if _manual[cam_id]:
        return True

    now = time.time()
    seen = set()

    for (x1, y1, x2, y2) in boxes:
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        vid = _match_vehicle(cam_id, cx, cy)
        if vid is None:
            vid = _next_vid[cam_id]
            _next_vid[cam_id] += 1
            _trackers[cam_id][vid] = {
                "pos": (cx, cy), "since": now, "last_seen": now
            }
        else:
            # Update position but keep original "since" so timer keeps counting
            _trackers[cam_id][vid]["pos"]       = (cx, cy)
            _trackers[cam_id][vid]["last_seen"] = now
        seen.add(vid)

    # Drop stale entries (vehicles that left frame)
    for vid in list(_trackers[cam_id].keys()):
        if vid not in seen and now - _trackers[cam_id][vid]["last_seen"] > 3:
            del _trackers[cam_id][vid]

    # Any vehicle stationary too long?
    for vid, data in _trackers[cam_id].items():
        stationary_for = now - data["since"]
        if stationary_for > STATIONARY_THRESHOLD:
            print(f"[ACCIDENT] Vehicle {vid} stationary {stationary_for:.0f}s "
                  f"on camera {cam_id}")
            return True

    return False


def set_manual_accident(cam_id, flag=True):
    """Called from /api/accident/<cam_id>."""
    if 0 <= cam_id < NUM_CAMERAS:
        _manual[cam_id] = bool(flag)
        print(f"[ACCIDENT] Manual flag cam {cam_id} = {flag}")


def clear_manual_accident(cam_id):
    """Called from /api/accident_clear/<cam_id>."""
    if 0 <= cam_id < NUM_CAMERAS:
        _manual[cam_id] = False
        # Also reset stationary timers for that camera so signal resumes cleanly
        _trackers[cam_id].clear()
        print(f"[ACCIDENT] Cleared on cam {cam_id}")


def get_manual_flags():
    return [_manual[i] for i in range(NUM_CAMERAS)]
