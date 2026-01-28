import cv2
import os
import numpy as np

# ----- Absolute paths -----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "faces")
MODEL_PATH = os.path.join(BASE_DIR, "models", "lbph_model.xml")

os.makedirs(DATASET_PATH, exist_ok=True)
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

# Load LBPH recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

faces = []
labels = []
label_map = {}
current_label = 0

# Read dataset folders
for person_name in sorted(os.listdir(DATASET_PATH)):
    person_dir = os.path.join(DATASET_PATH, person_name)
    if not os.path.isdir(person_dir):
        continue

    label_map[current_label] = person_name

    for img_name in os.listdir(person_dir):
        img_path = os.path.join(person_dir, img_name)

        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        img = cv2.resize(img, (200, 200))
        faces.append(img)
        labels.append(current_label)

    current_label += 1

# Train only if data exists
if len(faces) == 0:
    print("❌ No training images found in data/faces. Register first!")
    exit()

recognizer.train(faces, np.array(labels))
recognizer.save(MODEL_PATH)

print("✅ LBPH model trained and saved successfully")
print("👤 Label map:", label_map)
