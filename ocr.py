import easyocr
import cv2
import re

# Initialize EasyOCR reader (English)
# gpu=False since we're running on laptop without dedicated GPU
reader = easyocr.Reader(['en'], gpu=False)

# Indian number plate pattern (e.g. TN09AB1234)
PLATE_PATTERN = re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$')

def clean_plate(text):
    """
    Cleans raw OCR text to extract valid plate format.
    Removes spaces, special characters, converts to uppercase.
    """
    text = text.upper().strip()
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text

def is_valid_plate(text):
    """
    Checks if the cleaned text matches Indian plate format.
    e.g. TN09AB1234, KA05MN5678
    """
    return bool(PLATE_PATTERN.match(text))

def extract_plate_from_frame(frame):
    """
    Runs OCR on a full frame and returns detected plate text.
    Returns plate string if found, None otherwise.
    """
    if frame is None:
        return None

    # Convert to grayscale for better OCR accuracy
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Run EasyOCR
    results = reader.readtext(gray)

    for (bbox, text, confidence) in results:
        if confidence < 0.4:
            continue

        cleaned = clean_plate(text)

        if is_valid_plate(cleaned):
            print(f"[OCR] Plate detected: {cleaned} (confidence: {confidence:.2f})")
            return cleaned

    return None

def extract_plate_from_crop(frame, box):
    """
    Extracts plate from a cropped vehicle bounding box region.
    box = (x1, y1, x2, y2)
    """
    if frame is None:
        return None

    x1, y1, x2, y2 = map(int, box)

    # Add small padding
    pad = 10
    h, w = frame.shape[:2]
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    return extract_plate_from_frame(crop)

def extract_plates_from_detections(frame, boxes):
    """
    Runs OCR on all vehicle bounding boxes in a frame.
    Returns list of detected plates.
    boxes = list of (x1, y1, x2, y2)
    """
    plates = []
    for box in boxes:
        plate = extract_plate_from_crop(frame, box)
        if plate:
            plates.append(plate)
    return plates


# ── Test: run directly to test OCR on laptop camera ──
if __name__ == "__main__":
    import time
    from camera import start_cameras, get_frame, stop_cameras

    print("[INFO] Starting OCR test...")
    print("[INFO] Show a number plate to the camera!")
    print("[INFO] Press 'q' to quit.\n")

    start_cameras()
    time.sleep(2)

    while True:
        frame = get_frame(0)
        if frame is not None:
            plate = extract_plate_from_frame(frame)
            if plate:
                # Draw plate text on frame
                cv2.putText(frame, f"PLATE: {plate}", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow("OCR Test - Show a number plate", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stop_cameras()
    cv2.destroyAllWindows()