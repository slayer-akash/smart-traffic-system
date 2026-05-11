"""
Communicator: sends signal states to ESP32 via HTTP.
Now handles 8 signals (matching the physical prototype).
"""

import requests
import json

# ── ESP32 Configuration ──
# Find this in Serial Monitor after uploading the .ino sketch
ESP32_IP   = "192.168.1.100"
ESP32_PORT = 80
BASE_URL   = f"http://{ESP32_IP}:{ESP32_PORT}"
TIMEOUT    = 2   # seconds

NUM_SIGNALS = 8

# Signal state constants
RED, YELLOW, GREEN = "red", "yellow", "green"

SIGNAL_IDS = [f"SIGNAL_{i+1}" for i in range(NUM_SIGNALS)]


def send_signal_state(states):
    """
    Send 8 signal states to ESP32.
    states = list of 8 strings: ['green','red','red','red','red','red','red','red']
    """
    if len(states) != NUM_SIGNALS:
        print(f"[COMM] ERROR: expected {NUM_SIGNALS} states, got {len(states)}")
        return False

    payload = {
        "signals": [
            {"id": SIGNAL_IDS[i], "state": states[i]}
            for i in range(NUM_SIGNALS)
        ]
    }

    try:
        resp = requests.post(f"{BASE_URL}/signal", json=payload, timeout=TIMEOUT)
        if resp.status_code == 200:
            # Print compact format: 'GRRRRRRR'
            short = "".join(s[0].upper() for s in states)
            print(f"[COMM] → ESP32: {short}")
            return True
        print(f"[COMM] ESP32 returned status {resp.status_code}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"[COMM] ESP32 unreachable at {ESP32_IP} (simulation mode)")
        return False
    except requests.exceptions.Timeout:
        print("[COMM] ESP32 timeout (simulation mode)")
        return False
    except Exception as e:
        print(f"[COMM] Error: {e}")
        return False


def set_all_red():
    """Emergency stop — all 8 signals red."""
    return send_signal_state([RED] * NUM_SIGNALS)


def get_esp32_status():
    try:
        r = requests.get(f"{BASE_URL}/status", timeout=TIMEOUT)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def is_esp32_connected():
    return get_esp32_status() is not None


# ── Test ──
if __name__ == "__main__":
    print(f"[TEST] Pinging ESP32 at {ESP32_IP}...")
    print(f"[TEST] Connected: {is_esp32_connected()}\n")

    print("[TEST] Sample payload that would be sent:")
    states = [GREEN, RED, RED, RED, GREEN, RED, RED, RED]
    payload = {
        "signals": [
            {"id": SIGNAL_IDS[i], "state": states[i]}
            for i in range(NUM_SIGNALS)
        ]
    }
    print(json.dumps(payload, indent=2))

    if is_esp32_connected():
        print("\n[TEST] Sending sample state...")
        send_signal_state(states)
