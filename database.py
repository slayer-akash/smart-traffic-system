import sqlite3
import os
from datetime import datetime

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "traffic.db")

def get_conn():
    """Returns a database connection."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """
    Creates all tables if they don't exist.
    Call this once at startup.
    """
    conn = get_conn()
    c = conn.cursor()

    # Plate log table — stores every detected plate
    c.execute('''
        CREATE TABLE IF NOT EXISTS plate_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            plate       TEXT    NOT NULL,
            road_name   TEXT    NOT NULL,
            signal_id   TEXT    NOT NULL,
            signal_state TEXT   NOT NULL,
            timestamp   TEXT    NOT NULL
        )
    ''')

    # Event log table — stores congestion, ambulance, accident events
    c.execute('''
        CREATE TABLE IF NOT EXISTS event_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT    NOT NULL,
            road_name   TEXT    NOT NULL,
            vehicle_count INTEGER,
            diverted_to TEXT,
            timestamp   TEXT    NOT NULL
        )
    ''')

    # Signal history table — stores signal state changes
    c.execute('''
        CREATE TABLE IF NOT EXISTS signal_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            road_name   TEXT    NOT NULL,
            signal_state TEXT   NOT NULL,
            green_time  INTEGER,
            vehicle_count INTEGER,
            timestamp   TEXT    NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")

def log_plate(plate, road_name, signal_id, signal_state):
    """Logs a detected plate to the database."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO plate_log (plate, road_name, signal_id, signal_state, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (plate, road_name, signal_id, signal_state, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    print(f"[DB] Plate logged: {plate} @ {road_name}")

def log_event(event_type, road_name, vehicle_count=0, diverted_to=""):
    """Logs a traffic event (congestion, ambulance, accident)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO event_log (event_type, road_name, vehicle_count, diverted_to, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (event_type, road_name, vehicle_count, diverted_to,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    print(f"[DB] Event logged: {event_type} on {road_name}")

def log_signal(road_name, signal_state, green_time, vehicle_count):
    """Logs a signal state change."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO signal_history (road_name, signal_state, green_time, vehicle_count, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (road_name, signal_state, green_time, vehicle_count,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_recent_plates(limit=20):
    """Returns the most recent plate logs."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT plate, road_name, signal_id, signal_state, timestamp
        FROM plate_log
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"plate": r[0], "road_name": r[1], "signal_id": r[2],
             "signal_state": r[3], "timestamp": r[4]} for r in rows]

def search_plate(plate):
    """
    Searches for a plate and returns its full journey
    across all signals.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT plate, road_name, signal_id, signal_state, timestamp
        FROM plate_log
        WHERE plate = ?
        ORDER BY timestamp ASC
    ''', (plate.upper(),))
    rows = c.fetchall()
    conn.close()
    return [{"plate": r[0], "road_name": r[1], "signal_id": r[2],
             "signal_state": r[3], "timestamp": r[4]} for r in rows]

def get_recent_events(limit=10):
    """Returns the most recent event logs."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT event_type, road_name, vehicle_count, diverted_to, timestamp
        FROM event_log
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"event_type": r[0], "road_name": r[1], "vehicle_count": r[2],
             "diverted_to": r[3], "timestamp": r[4]} for r in rows]

def get_stats():
    """Returns overall system statistics."""
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM plate_log")
    total_plates = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM event_log WHERE event_type='ambulance'")
    total_ambulance = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM event_log WHERE event_type='congestion'")
    total_congestion = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM event_log WHERE event_type='accident'")
    total_accidents = c.fetchone()[0]

    conn.close()
    return {
        "total_plates"    : total_plates,
        "total_ambulance" : total_ambulance,
        "total_congestion": total_congestion,
        "total_accidents" : total_accidents
    }

# ── Test: run directly to test database ──
if __name__ == "__main__":
    print("[TEST] Testing database...\n")

    # Initialize
    init_db()

    # Log some test plates
    log_plate("TN09AB1234", "North", "SIGNAL_1", "green")
    log_plate("KA05MN5678", "East",  "SIGNAL_2", "red")
    log_plate("MH01AB0001", "South", "SIGNAL_3", "green")
    log_plate("TN09AB1234", "West",  "SIGNAL_4", "red")

    # Log some events
    log_event("ambulance",  "North", 5,  "")
    log_event("congestion", "East",  12, "North, West")
    log_event("accident",   "South", 8,  "East")

    # Test search
    print("\n[TEST] Searching for TN09AB1234:")
    journey = search_plate("TN09AB1234")
    for j in journey:
        print(f"  {j['timestamp']} → {j['road_name']} ({j['signal_state']})")

    # Test stats
    print("\n[TEST] System stats:")
    stats = get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Test recent plates
    print("\n[TEST] Recent plates:")
    plates = get_recent_plates(5)
    for p in plates:
        print(f"  {p['plate']} @ {p['road_name']} — {p['timestamp']}")