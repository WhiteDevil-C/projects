import os
import json
from typing import Dict, Any, Tuple, List

import cv2
import numpy as np

def train_model(
    faces_dir: str,
    model_path: str,
    label_map_path: str,
) -> Dict[str, Any]:
    """
    Train an LBPH face recognizer from a folder structure:
      faces_dir/
        personA/001.jpg ...
        personB/001.jpg ...

    Saves:
      - model_path (xml)
      - label_map_path (json): {"0": "personA", "1": "personB"}

    Returns training summary dict.
    """
    os.makedirs(faces_dir, exist_ok=True)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    faces: List[np.ndarray] = []
    labels: List[int] = []
    label_map: Dict[int, str] = {}
    current_label = 0

    for person_name in sorted(os.listdir(faces_dir)):
        person_dir = os.path.join(faces_dir, person_name)
        if not os.path.isdir(person_dir):
            continue

        label_map[current_label] = person_name
        for img_name in sorted(os.listdir(person_dir)):
            if not img_name.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            img_path = os.path.join(person_dir, img_name)

            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            img = cv2.resize(img, (200, 200))

            faces.append(img)
            labels.append(current_label)

        current_label += 1

    if not faces:
        raise RuntimeError(f"No training images found in {faces_dir}. Register faces first.")

    recognizer.train(faces, np.array(labels))
    recognizer.save(model_path)

    # Save label map as JSON with string keys for portability
    os.makedirs(os.path.dirname(label_map_path), exist_ok=True)
    with open(label_map_path, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in label_map.items()}, f, indent=2)

    return {
        "people": len(label_map),
        "images": len(faces),
        "model_path": model_path,
        "label_map_path": label_map_path,
        "label_map": label_map,
    }

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    faces_dir = os.path.join(BASE_DIR, "data", "faces")
    model_path = os.path.join(BASE_DIR, "models", "lbph_model.xml")
    label_map_path = os.path.join(BASE_DIR, "models", "label_map.json")

    summary = train_model(faces_dir, model_path, label_map_path)
    print("✅ Model trained and saved successfully")
    print("👤 Label map:", summary["label_map"])
