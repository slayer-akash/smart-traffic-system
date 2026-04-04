import requests
import json

# ── ESP32 Configuration ──
# Change this to your ESP32's IP address (shown in Serial Monitor after upload)
ESP32_IP   = "192.168.1.100"
ESP32_PORT = 80
BASE_URL   = f"http://{ESP32_IP}:{ESP32_PORT}"

# Timeout for HTTP requests (seconds)
TIMEOUT = 2

# Signal state constants
RED    = "red"
YELLOW = "yellow"
GREEN  = "green"

# Road index to signal ID mapping
SIGNAL_IDS = {
    0: "SIGNAL_1",  # North
    1: "SIGNAL_2",  # East
    2: "SIGNAL_3",  # South
    3: "SIGNAL_4",  # West
}

def send_signal_state(states):
    """
    Sends signal states for all 4 roads to ESP32.
    states = list of 4 strings: ['green','red','red','red']
    Returns True if successful, False otherwise.
    """
    payload = {
        "signals": [
            {"id": SIGNAL_IDS[i], "state": states[i]}
            for i in range(4)
        ]
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/signal",
            json=payload,
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            print(f"[COMM] Signal sent: {states}")
            return True
        else:
            print(f"[COMM] ESP32 returned status: {resp.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"[COMM] ESP32 not reachable at {ESP32_IP} — running in simulation mode")
        return False
    except requests.exceptions.Timeout:
        print(f"[COMM] ESP32 timeout — running in simulation mode")
        return False
    except Exception as e:
        print(f"[COMM] Error: {e}")
        return False

def set_all_red():
    """Sets all 4 signals to red. Used for emergency stop."""
    return send_signal_state([RED, RED, RED, RED])

def set_green(road_index):
    """Sets one road to green, all others to red."""
    states = [RED] * 4
    states[road_index] = GREEN
    return send_signal_state(states)

def set_yellow(road_index):
    """Sets one road to yellow, all others to red."""
    states = [RED] * 4
    states[road_index] = YELLOW
    return send_signal_state(states)

def get_esp32_status():
    """
    Gets current status from ESP32.
    Returns status dict or None if unreachable.
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/status",
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None

def is_esp32_connected():
    """Checks if ESP32 is reachable on the network."""
    status = get_esp32_status()
    return status is not None

# ── Test: run directly to test communication ──
if __name__ == "__main__":
    print("[TEST] Testing ESP32 communication...\n")

    # Check connection
    connected = is_esp32_connected()
    print(f"[COMM] ESP32 connected: {connected}")

    if connected:
        print("\n[TEST] Setting North to GREEN...")
        set_green(0)

        import time
        time.sleep(2)

        print("[TEST] Setting East to GREEN...")
        set_green(1)

        time.sleep(2)

        print("[TEST] Setting all RED...")
        set_all_red()

        print("\n[TEST] Done! Check your ESP32 LEDs.")
    else:
        print("\n[INFO] ESP32 not connected yet.")
        print("[INFO] This is expected — ESP32 code not uploaded yet.")
        print("[INFO] communicator.py is ready and will work once ESP32 is set up!")

        # Simulate what would be sent
        print("\n[SIMULATION] What would be sent to ESP32:")
        states = [GREEN, RED, RED, RED]
        payload = {
            "signals": [
                {"id": SIGNAL_IDS[i], "state": states[i]}
                for i in range(4)
            ]
        }
        print(json.dumps(payload, indent=2))