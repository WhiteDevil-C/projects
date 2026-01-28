import cv2
import os
from datetime import datetime

# ---------- Absolute paths ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "faces")
MODEL_PATH = os.path.join(BASE_DIR, "models", "lbph_model.xml")
LOG_DIR = os.path.join(BASE_DIR, "logs")
RESULT_PATH = os.path.join(LOG_DIR, "last_once_result.txt")

os.makedirs(DATASET_PATH, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ---------- Load Haar Cascade ----------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ---------- Load LBPH model ----------
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_PATH)

# ---------- Build label map ----------
label_map = {}
current_label = 0
for person_name in sorted(os.listdir(DATASET_PATH)):
    person_dir = os.path.join(DATASET_PATH, person_name)
    if os.path.isdir(person_dir):
        label_map[current_label] = person_name
        current_label += 1

# ---------- Open camera ----------
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

pred_name = "Unknown"
pred_confidence = 999.0

print("🔍 Quick face verification started (verify_once)")

# Try for ~2 seconds (60 frames)
for _ in range(60):
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        cv2.imshow("Quick Verify", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue

    (x, y, w, h) = faces[0]
    face_img = gray[y:y+h, x:x+w]
    face_img = cv2.resize(face_img, (200, 200))

    label, confidence = recognizer.predict(face_img)

    if confidence < 80:
        pred_name = label_map.get(label, "Unknown")
        pred_confidence = float(confidence)
        break

    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
    cv2.imshow("Quick Verify", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# ---------- Save result for Flask ----------
with open(RESULT_PATH, "w", encoding="utf-8") as f:
    f.write(f"{pred_name}|{pred_confidence}|{datetime.now()}\n")

print(f"[verify_once] {pred_name} | {pred_confidence}")
