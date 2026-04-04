from flask import Flask, jsonify, send_file
import threading
import time
import os

from camera       import start_cameras, get_frame, stop_cameras
from detector     import detect
from ocr          import extract_plate_from_frame
from signal_logic import update, get_status, set_manual_override, clear_manual_override
from communicator import send_signal_state, set_all_red
from database     import init_db, log_plate, log_event, log_signal, \
                         get_recent_plates, get_recent_events, get_stats, search_plate

# ── Flask App ──
app = Flask(__name__)

# ── Road Names ──
ROAD_NAMES  = ["North", "East", "South", "West"]
SIGNAL_IDS  = ["SIGNAL_1", "SIGNAL_2", "SIGNAL_3", "SIGNAL_4"]

# ── Global State ──
running     = True
last_plates = set()  # avoid logging same plate twice in short time

# ──────────────────────────────────────────
# MAIN PROCESSING LOOP
# ──────────────────────────────────────────
def processing_loop():
    """
    Main loop — runs in background thread.
    Every cycle:
      1. Grab frames from all 4 cameras
      2. Run YOLO detection
      3. Run OCR
      4. Update signal logic
      5. Send to ESP32
      6. Log to database
    """
    global running, last_plates

    print("[APP] Processing loop started.")

    while running:
        counts      = [0, 0, 0, 0]
        amb_flags   = [False, False, False, False]

        for i in range(4):
            frame = get_frame(i)
            if frame is None:
                continue

            # YOLO detection
            count, ambulance, _ = detect(frame)
            counts[i]    = count
            amb_flags[i] = ambulance

            # Log ambulance event
            if ambulance:
                log_event("ambulance", ROAD_NAMES[i], count, "")

            # Congestion check
            if count >= 10:
                log_event("congestion", ROAD_NAMES[i], count,
                          ROAD_NAMES[(i+1) % 4])

            # OCR — read plates
            plate = extract_plate_from_frame(frame)
            if plate and plate not in last_plates:
                status = get_status()
                state  = status["signal_state"][i]
                log_plate(plate, ROAD_NAMES[i], SIGNAL_IDS[i], state)
                last_plates.add(plate)
                # Clear plate cache every 30 seconds
                threading.Timer(30, lambda p=plate: last_plates.discard(p)).start()

        # Update signal logic
        states = update(counts, amb_flags)

        # Log signal states
        for i in range(4):
            log_signal(ROAD_NAMES[i], states[i], 0, counts[i])

        # Send to ESP32
        send_signal_state(states)

        time.sleep(1)  # process every 1 second

# ──────────────────────────────────────────
# FLASK REST API ENDPOINTS
# ──────────────────────────────────────────

@app.route("/")
def index():
    """Serves the dashboard HTML file."""
    dash_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    if os.path.exists(dash_path):
        return send_file(dash_path)
    return "<h2>Dashboard not found. Place dashboard.html in the project folder.</h2>"

@app.route("/api/status")
def api_status():
    """Returns current system status."""
    status = get_status()
    stats  = get_stats()
    status.update(stats)
    return jsonify(status)

@app.route("/api/plates")
def api_plates():
    """Returns recent plate logs."""
    return jsonify(get_recent_plates(20))

@app.route("/api/events")
def api_events():
    """Returns recent event logs."""
    return jsonify(get_recent_events(10))

@app.route("/api/search/<plate>")
def api_search(plate):
    """Searches for a plate journey."""
    results = search_plate(plate.upper())
    return jsonify(results)

@app.route("/api/override/<int:road>")
def api_override(road):
    """Manually sets a road to green."""
    if 0 <= road <= 3:
        set_manual_override(road)
        return jsonify({"status": "ok", "road": ROAD_NAMES[road]})
    return jsonify({"status": "error", "message": "Invalid road index"}), 400

@app.route("/api/auto")
def api_auto():
    """Clears manual override and resumes auto mode."""
    clear_manual_override()
    return jsonify({"status": "ok", "mode": "auto"})

@app.route("/api/allred")
def api_allred():
    """Emergency all-red button."""
    set_all_red()
    return jsonify({"status": "ok", "message": "All signals set to RED"})

@app.route("/api/stats")
def api_stats():
    """Returns system statistics."""
    return jsonify(get_stats())

# ──────────────────────────────────────────
# STARTUP
# ──────────────────────────────────────────
if __name__ == "__main__":
    print("[APP] Initializing Smart Traffic System...")

    # Initialize database
    init_db()

    # Start cameras
    start_cameras()
    time.sleep(2)

    # Start processing loop in background thread
    proc_thread = threading.Thread(target=processing_loop, daemon=True)
    proc_thread.start()

    print("[APP] System running!")
    print("[APP] Dashboard → http://127.0.0.1:5000")
    print("[APP] Press Ctrl+C to stop.\n")

    # Start Flask server
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n[APP] Shutting down...")
        running = False
        stop_cameras()