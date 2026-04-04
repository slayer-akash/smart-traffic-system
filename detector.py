from ultralytics import YOLO
import cv2

# Load YOLOv8 small model (downloads automatically on first run)
model = YOLO("yolov8s.pt")

# Vehicle classes in YOLO COCO dataset
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

# Ambulance class name to detect
AMBULANCE_CLASS = "ambulance"

def detect(frame):
    """
    Runs YOLOv8 detection on a single frame.
    Returns:
        vehicle_count (int)     — number of vehicles detected
        ambulance_detected (bool) — True if ambulance found
        annotated_frame         — frame with bounding boxes drawn
    """
    if frame is None:
        return 0, False, None

    results = model(frame, verbose=False)[0]

    vehicle_count = 0
    ambulance_detected = False

    for box in results.boxes:
        cls_id = int(box.cls[0])
        cls_name = model.names[cls_id].lower()
        confidence = float(box.conf[0])

        # Count vehicles
        if cls_id in VEHICLE_CLASSES and confidence > 0.4:
            vehicle_count += 1

        # Detect ambulance
        if cls_name == AMBULANCE_CLASS and confidence > 0.5:
            ambulance_detected = True

    # Draw bounding boxes on frame
    annotated_frame = results.plot()

    return vehicle_count, ambulance_detected, annotated_frame


# ── Test: run this file directly to test detection ──
if __name__ == "__main__":
    import time
    from camera import start_cameras, get_frame, stop_cameras

    print("[INFO] Starting camera and detector test...")
    start_cameras()
    time.sleep(2)

    print("[INFO] Press 'q' to quit.")
    while True:
        frame = get_frame(0)  # Test on camera 0 only
        if frame is not None:
            count, amb, annotated = detect(frame)
            print(f"[DETECT] Vehicles: {count} | Ambulance: {amb}")

            if annotated is not None:
                cv2.imshow("Detector Test - Road 1", annotated)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stop_cameras()
    cv2.destroyAllWindows()