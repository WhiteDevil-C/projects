import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

import cv2

def verify_face(
    model_path: str,
    label_map_path: str,
    camera_index: int = 0,
    threshold: float = 75.0,
    use_dshow: bool = True,
) -> Dict[str, Any]:
    """
    Verify a face using a trained LBPH model.
    Returns:
      {"matched": bool, "name": Optional[str], "confidence": Optional[float]}
    Notes:
      LBPH returns "distance" (lower is better). We treat <= threshold as match.
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}. Train the model first.")
    if not os.path.exists(label_map_path):
        raise FileNotFoundError(f"Label map not found: {label_map_path}. Train the model first.")

    with open(label_map_path, "r", encoding="utf-8") as f:
        label_map = json.load(f)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(model_path)

    if use_dshow and hasattr(cv2, "CAP_DSHOW"):
        cam = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    else:
        cam = cv2.VideoCapture(camera_index)

    if not cam.isOpened():
        raise RuntimeError("Camera not opened. Close other apps using camera (Zoom/Meet/Browser) and try again.")

    best = {"matched": False, "name": None, "confidence": None}

    try:
        print("🔍 Verifying face... (Press 'q' to exit)")
        while True:
            ret, frame = cam.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

            for (x, y, w, h) in faces:
                face_img = gray[y:y+h, x:x+w]
                face_img = cv2.resize(face_img, (200, 200))

                label, dist = recognizer.predict(face_img)  # dist: lower is better
                name = label_map.get(str(label), "unknown")

                matched = dist <= threshold and name != "unknown"
                best = {"matched": bool(matched), "name": name if matched else None, "confidence": float(dist)}

                # UI overlay
                color = (0, 255, 0) if matched else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, f"{name} ({dist:.1f})", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                # If match found, stop quickly
                if matched:
                    break

            # cv2.imshow("Verify Face - Press q to quit", frame)

            # if (cv2.waitKey(1) & 0xFF) == ord("q"):
            #     break
            if best["matched"]:
                break
                
        return best
    finally:
        cam.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(BASE_DIR, "models", "lbph_model.xml")
    label_map_path = os.path.join(BASE_DIR, "models", "label_map.json")

    result = verify_face(model_path, label_map_path)
    print("Result:", result)
