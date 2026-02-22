import os
import cv2
from typing import Optional

def register_face(
    name: str,
    save_dir: str,
    num_samples: int = 25,
    camera_index: int = 0,
    min_face_size: int = 80,
    use_dshow: bool = True,
) -> int:
    """
    Capture face samples for a person using OpenCV camera and save cropped grayscale faces.

    Returns: number of samples saved.
    """
    if not name or not name.strip():
        raise ValueError("name is required")
    os.makedirs(save_dir, exist_ok=True)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    # Prefer DirectShow on Windows to avoid long camera open times
    if use_dshow and hasattr(cv2, "CAP_DSHOW"):
        cam = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    else:
        cam = cv2.VideoCapture(camera_index)

    if not cam.isOpened():
        raise RuntimeError("Camera not opened. Close other apps using camera (Zoom/Meet/Browser) and try again.")

    count = 0
    try:
        print(f"📸 Capturing face samples for: {name}")
        print("   Press 'q' to stop early.")
        while True:
            ret, frame = cam.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

            for (x, y, w, h) in faces:
                if w < min_face_size or h < min_face_size:
                    continue

                face_img = gray[y:y+h, x:x+w]
                face_img = cv2.resize(face_img, (200, 200))

                count += 1
                out_path = os.path.join(save_dir, f"{count:03d}.jpg")
                cv2.imwrite(out_path, face_img)

                # UI
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"{count}/{num_samples}", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

                if count >= num_samples:
                    break

            # cv2.imshow("Register Face - Press q to quit", frame)

            # if (cv2.waitKey(1) & 0xFF) == ord("q"):
            #     break
            if count >= num_samples:
                break
            
            # Non-blocking delay if needed, but for web we don't need it. 
            # For script usage, without waitKey, this loop might run very fast or not update GUI.
            # Since we are removing GUI, we just loop until count is met.
            
        print(f"✅ Saved {count} samples to: {save_dir}")
        return count
    finally:
        cam.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Register face samples for a person.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--save_dir", required=True)
    parser.add_argument("--num_samples", type=int, default=25)
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    register_face(args.name, args.save_dir, num_samples=args.num_samples, camera_index=args.camera)
