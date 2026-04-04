import cv2
import threading

# Number of cameras (one per road)
NUM_CAMERAS = 4

# Shared frames dictionary — stores latest frame from each camera
frames = {i: None for i in range(NUM_CAMERAS)}
locks  = {i: threading.Lock() for i in range(NUM_CAMERAS)}
running = True

def capture_camera(cam_id):
    """Continuously captures frames from a single camera."""
    cap = cv2.VideoCapture(cam_id)

    if not cap.isOpened():
        print(f"[WARNING] Camera {cam_id} not found. Using blank frame.")
        return

    print(f"[INFO] Camera {cam_id} started.")

    while running:
        ret, frame = cap.read()
        if ret:
            with locks[cam_id]:
                frames[cam_id] = frame
        else:
            print(f"[WARNING] Camera {cam_id} failed to read frame.")

    cap.release()
    print(f"[INFO] Camera {cam_id} released.")

def get_frame(cam_id):
    """Returns the latest frame from the given camera."""
    with locks[cam_id]:
        return frames[cam_id]

def start_cameras():
    """Starts all camera threads."""
    threads = []
    for i in range(NUM_CAMERAS):
        t = threading.Thread(target=capture_camera, args=(i,), daemon=True)
        t.start()
        threads.append(t)
    print(f"[INFO] All {NUM_CAMERAS} camera threads started.")
    return threads

def stop_cameras():
    """Stops all camera threads."""
    global running
    running = False
    print("[INFO] All cameras stopped.")

# ── Test: run this file directly to preview all cameras ──
if __name__ == "__main__":
    start_cameras()
    import time
    time.sleep(2)  # Let cameras warm up

    print("[INFO] Press 'q' to quit preview.")
    while True:
        for i in range(NUM_CAMERAS):
            frame = get_frame(i)
            if frame is not None:
                cv2.imshow(f"Camera {i} - Road {i+1}", frame)
            else:
                print(f"[INFO] Camera {i} not available.")

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stop_cameras()
    cv2.destroyAllWindows()