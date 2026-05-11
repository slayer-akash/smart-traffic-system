"""
Vehicle + ambulance detector.
- YOLOv8s for vehicle detection (car, motorcycle, bus, truck)
- HSV color thresholding for ambulance flash detection
  (looks for red+blue flashing pixels in top of vehicle boxes)
- Returns vehicle boxes so accident.py can track stationary vehicles
"""

from ultralytics import YOLO
import cv2
import numpy as np
from collections import deque

# ── Load YOLO ──
model = YOLO("yolov8s.pt")

VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
CONFIDENCE_THRESHOLD = 0.5

# ── Ambulance flash detection ──
# Per-camera history of (red_count, blue_count) in upper-third of vehicle boxes
FLASH_HISTORY_LEN = 10
flash_history = {i: deque(maxlen=FLASH_HISTORY_LEN) for i in range(8)}

# Tune these if you get too many false positives / false negatives
RED_MIN_PIXELS  = 200   # minimum pixel count to register a red flash
BLUE_MIN_PIXELS = 200   # minimum pixel count to register a blue flash
FLASH_DELTA     = 150   # min (max - min) over recent frames to count as flash


def _count_red_blue(roi):
    """Count red and blue pixels in HSV color space."""
    if roi is None or roi.size == 0:
        return 0, 0
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # Red wraps around in HSV — two ranges
    red1 = cv2.inRange(hsv, (0,   120, 100), (10,  255, 255))
    red2 = cv2.inRange(hsv, (170, 120, 100), (180, 255, 255))
    red_mask  = cv2.bitwise_or(red1, red2)
    blue_mask = cv2.inRange(hsv, (100, 120, 100), (130, 255, 255))
    return int(cv2.countNonZero(red_mask)), int(cv2.countNonZero(blue_mask))


def _is_flashing(cam_id):
    """An ambulance has fluctuating red+blue pixel counts. A red car is steady."""
    hist = flash_history[cam_id]
    if len(hist) < 5:
        return False
    reds  = [r for r, _ in hist]
    blues = [b for _, b in hist]
    red_flash  = max(reds)  > RED_MIN_PIXELS  and (max(reds)  - min(reds))  > FLASH_DELTA
    blue_flash = max(blues) > BLUE_MIN_PIXELS and (max(blues) - min(blues)) > FLASH_DELTA
    return red_flash and blue_flash   # require BOTH colors flashing


def detect(frame, cam_id=0):
    """
    Run YOLO + ambulance detection on a frame.
    Returns:
        vehicle_count     : int
        ambulance_detected: bool
        vehicle_boxes     : list of (x1, y1, x2, y2) for accident tracker
        annotated_frame   : frame with YOLO boxes drawn
    """
    if frame is None:
        return 0, False, [], None

    results = model(frame, verbose=False)[0]
    vehicle_count = 0
    vehicle_boxes = []
    total_red, total_blue = 0, 0

    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf   = float(box.conf[0])
        if cls_id in VEHICLE_CLASSES and conf >= CONFIDENCE_THRESHOLD:
            vehicle_count += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            vehicle_boxes.append((x1, y1, x2, y2))

            # Crop top-third of vehicle box (where siren lights would be)
            top_h = max(1, (y2 - y1) // 3)
            roi   = frame[y1:y1 + top_h, x1:x2]
            r, b  = _count_red_blue(roi)
            total_red  += r
            total_blue += b

    flash_history[cam_id].append((total_red, total_blue))
    ambulance_detected = _is_flashing(cam_id)
    if ambulance_detected:
        print(f"[DETECT] 🚨 Ambulance flash on camera {cam_id} "
              f"(red={total_red}, blue={total_blue})")

    annotated_frame = results.plot()
    return vehicle_count, ambulance_detected, vehicle_boxes, annotated_frame


# ── Test ──
if __name__ == "__main__":
    import time
    from camera import start_cameras, get_frame, stop_cameras

    print("[INFO] Testing detector. Wave a red/blue flashing object at camera 0.")
    print("[INFO] Press 'q' to quit.\n")
    start_cameras()
    time.sleep(2)

    while True:
        frame = get_frame(0)
        if frame is not None:
            count, amb, boxes, annotated = detect(frame, cam_id=0)
            label = f"Vehicles: {count} | Ambulance: {amb}"
            cv2.putText(annotated, label, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 0, 255) if amb else (0, 255, 0), 2)
            cv2.imshow("Detector Test", annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stop_cameras()
    cv2.destroyAllWindows()
