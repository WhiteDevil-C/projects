import cv2
import os

# ----- Get person name from Flask temp file -----
os.makedirs("logs", exist_ok=True)
name_file = os.path.join("logs", "temp_name.txt")

if os.path.exists(name_file):
    with open(name_file, "r", encoding="utf-8") as f:
        person_name = f.read().strip()
else:
    person_name = "unknown_user"

# ----- Save images here -----
dataset_path = os.path.join("data", "faces", person_name)
os.makedirs(dataset_path, exist_ok=True)

# Load Haar Cascade for face detection
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cam.isOpened():
    print("❌ Camera not opened. Close other apps using camera (Zoom/Meet/Browser) and try again.")
    exit()

count = 0
print(f"📸 Face registration started for '{person_name}'. Press 'q' to stop.")

while True:
    ret, frame = cam.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        count += 1
        face_img = gray[y:y+h, x:x+w]

        img_path = os.path.join(dataset_path, f"{count}.jpg")
        cv2.imwrite(img_path, face_img)

        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    cv2.imshow("Register Face", frame)

    if cv2.waitKey(1) & 0xFF == ord('q') or count >= 50:
        break

cam.release()
cv2.destroyAllWindows()

print(f"✅ Face registration completed for '{person_name}'")
