import cv2
import os
import json
from datetime import datetime

# ---------- Absolute paths ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "faces")
MODEL_PATH = os.path.join(BASE_DIR, "models", "lbph_model.xml")
LOG_DIR = os.path.join(BASE_DIR, "logs")
ACCESS_LOG = os.path.join(LOG_DIR, "access_log.txt")
RESULT_JSON = os.path.join(LOG_DIR, "last_result.json")

os.makedirs(DATASET_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ---------- Load Haar Cascade ----------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ---------- Load LBPH model ----------
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_PATH)

# IMPORTANT: sort folders to match train_model.py
label_map = {}
current_label = 0
for person_name in sorted(os.listdir(DATASET_PATH)):
    person_dir = os.path.join(DATASET_PATH, person_name)
    if os.path.isdir(person_dir):
        label_map[current_label] = person_name
        current_label += 1

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

final_name = "Unknown"
final_status = "AWARD DENIED"
final_conf = 999.0

print("🎥 Face verification started. Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        face_img = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
        label, confidence = recognizer.predict(face_img)
        final_conf = float(confidence)

        if confidence < 80:
            final_name = label_map.get(label, "Unknown")
            final_status = "AWARD GRANTED"
            color = (0, 255, 0)
        else:
            final_name = "Unknown"
            final_status = "AWARD DENIED"
            color = (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(frame, final_name, (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, final_status, (x, y+h+25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Log every detection
        with open(ACCESS_LOG, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now()} | {final_name} | {final_status} | Confidence: {final_conf}\n")

    cv2.imshow("Face Verification", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

result = {
    "name": final_name,
    "status": final_status,
    "confidence": final_conf,
    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

with open(RESULT_JSON, "w", encoding="utf-8") as f:
    json.dump(result, f)

print("✅ verify_face result:", result)
