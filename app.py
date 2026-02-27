import os
import sqlite3
import time
import base64
import numpy as np
import cv2
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for

from config import Config
from src.register_face import register_face
from src.generate_certificate import generate_certificate
import json
import logging
import re
import uuid

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from flask import send_from_directory
import os

app = Flask(__name__)
app.config.from_object(Config)

# -------------------- Utilities --------------------
def ensure_dirs():
    os.makedirs(app.config["DATA_DIR"], exist_ok=True)
    os.makedirs(app.config["FACES_DIR"], exist_ok=True)
    os.makedirs(app.config["MODELS_DIR"], exist_ok=True)
    os.makedirs(app.config["CERT_DIR"], exist_ok=True)

def db():
    con = sqlite3.connect(app.config["DB_PATH"])
    con.row_factory = sqlite3.Row
    return con

def init_db():
    logger.info("Initializing database...")
    try:
        con = db()
        cur = con.cursor()
        # Use DATETIME DEFAULT CURRENT_TIMESTAMP for cleaner audit trails
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                email TEXT,
                image_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                award_title TEXT NOT NULL,
                certificate_file TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        con.commit()
        con.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status

def base64_to_cv2(image_data):
    """
    Convert base64 image string to OpenCV image (numpy array).
    """
    try:
        if "," in image_data:
            image_data = image_data.split(",")[1]
        decoded_data = base64.b64decode(image_data)
        np_data = np.frombuffer(decoded_data, np.uint8)
        img = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None

# -------------------- UI Routes --------------------
# -------------------- UI Routes --------------------
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# -------------------- API (v1) --------------------
@app.route("/api/v1/health")
def health():
    return jsonify({"ok": True, "service": "face_reward", "version": "v1"})

@app.route("/api/v1/users", methods=["GET"])
def api_users_list():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT id, name, email, created_at FROM users ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return jsonify({"ok": True, "users": rows})

@app.route("/api/v1/awards", methods=["GET"])
def api_awards_list():
    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT a.id, u.name as user_name, a.award_title, a.certificate_file, a.created_at
        FROM awards a
        JOIN users u ON u.id = a.user_id
        ORDER BY a.id DESC
        LIMIT 50
    """)
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return jsonify({"ok": True, "awards": rows})

@app.route("/api/v1/register", methods=["POST"])
def api_register():
    logger.info("Registration request received")
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        return json_error("Invalid JSON body", 400)

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    image_data = data.get("image")

    # 1. Validation
    if not name:
        return json_error("Name is required")
    if not re.match(r"^[a-zA-Z0-9\s._-]+$", name):
        return json_error("Invalid name format. Only alphanumeric and spaces/dots/dashes allowed.")
    
    if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return json_error("Invalid email format")

    if not image_data:
         return json_error("Image data required for registration", 400)

    try:
        # 2. Directory Management
        user_dir = os.path.join(app.config["FACES_DIR"], name)
        os.makedirs(user_dir, exist_ok=True)

        # 3. Image Processing
        frame = base64_to_cv2(image_data)
        if frame is None:
            return json_error("Invalid image data")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        
        saved_count = 0
        out_path = None
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            if w >= 80 and h >= 80:
                 face_img = gray[y:y+h, x:x+w]
                 face_img = cv2.resize(face_img, (200, 200))
                 
                 # Unique filename using uuid and timestamp
                 filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
                 out_path = os.path.join(user_dir, filename)
                 
                 # Verify write success
                 success = cv2.imwrite(out_path, face_img)
                 if not success:
                     logger.error(f"Failed to write image to disk: {out_path}")
                     return json_error("Failed to save image to server storage", 500)
                 
                 saved_count = 1
                 logger.info(f"Saved face image to {out_path}")
            else:
                logger.warning(f"Detected face too small: {w}x{h}")
        else:
            logger.warning("No face detected in registration frame")

        # 4. Database Persistence
        con = db()
        cur = con.cursor()
        try:
            # Upsert user info
            cur.execute("INSERT OR IGNORE INTO users(name, email) VALUES(?,?)", (name, email))
            if email:
                cur.execute("UPDATE users SET email=? WHERE name=?", (email, name))
            if out_path:
                cur.execute("UPDATE users SET image_path=? WHERE name=?", (out_path, name))
            con.commit()
            logger.info(f"Database entry updated for user: {name}")
        except sqlite3.Error as db_err:
            logger.error(f"Database error during registration: {db_err}")
            return json_error("Database persistence failed", 500)
        finally:
            con.close()

        return jsonify({
            "ok": True, 
            "name": name, 
            "captured": saved_count,
            "message": "Registration step processed"
        })

    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}", exc_info=True)
        return json_error("Internal server error during registration", 500)

@app.route("/process_frame", methods=["POST"])
def process_frame():
    """
    Process a single frame for verification or just detection.
    """
    start_time = time.time()
    data = request.get_json(force=True) or {}
    image_data = data.get("image")
    threshold = float(data.get("threshold") or 75.0)

    if not image_data:
        return json_error("No image data provided")

    frame = base64_to_cv2(image_data)
    if frame is None:
        return json_error("Invalid image")

    # Load Model Resources
    model_path = app.config["MODEL_PATH"]
    label_map_path = app.config["LABEL_MAP_PATH"]
    
    # Check if model exists (for graceful fallback to just detection)
    model_ready = os.path.exists(model_path) and os.path.exists(label_map_path)

    # Prepare Recognizer & Cascade
    try:
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        
        recognizer = None
        label_map = {}
        if model_ready:
            with open(label_map_path, "r", encoding="utf-8") as f:
                label_map = json.load(f)
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(model_path)
    except Exception as e:
        return json_error(f"Error initializing detector: {str(e)}", 500)

    # Detect and Recognize
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    
    results = []
    best_match = {"matched": False, "name": None, "confidence": None}

    for (x, y, w, h) in faces:
        res = {
            "x": int(x), "y": int(y), "w": int(w), "h": int(h),
            "label": "Face",
            "confidence": 0,
            "matched": False
        }
        
        if recognizer:
            face_img = gray[y:y+h, x:x+w]
            face_img = cv2.resize(face_img, (200, 200))
            label, dist = recognizer.predict(face_img)
            name = label_map.get(str(label), "unknown")
            matched = dist <= threshold and name != "unknown"
            
            res["label"] = name if matched else "Unknown"
            res["confidence"] = float(dist)
            res["matched"] = bool(matched)
            
            if matched and (best_match["confidence"] is None or dist < best_match["confidence"]):
                best_match = {"matched": True, "name": name, "confidence": float(dist)}

        results.append(res)

    processing_ms = int((time.time() - start_time) * 1000)

    return jsonify({
        "ok": True,
        "faces": results,
        "count": len(results),
        "matched": best_match["matched"],
        "name": best_match["name"],
        "confidence": best_match["confidence"],
        "processing_ms": processing_ms
    })

@app.route("/api/v1/train", methods=["POST"])
def api_train():
    try:
        summary = train_model(
            faces_dir=app.config["FACES_DIR"],
            model_path=app.config["MODEL_PATH"],
            label_map_path=app.config["LABEL_MAP_PATH"],
        )
    except Exception as e:
        return json_error(str(e), 500)

    return jsonify({"ok": True, "message": "Model trained", "details": summary})

@app.route("/api/v1/verify", methods=["POST"])
def api_verify():
    data = request.get_json(force=True) or {}
    threshold = float(data.get("threshold") or 75.0)
    try:
        result = verify_face(
            model_path=app.config["MODEL_PATH"],
            label_map_path=app.config["LABEL_MAP_PATH"],
            threshold=threshold,
        )
    except Exception as e:
        return json_error(str(e), 500)

    return jsonify({"ok": True, **result})

@app.route("/api/v1/award", methods=["POST"])
def api_award():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    award_title = (data.get("award_title") or "Certificate of Achievement").strip()

    if not name:
        return json_error("Name is required")

    con = db()
    cur = con.cursor()
    cur.execute("SELECT id, email FROM users WHERE name=?", (name,))
    row = cur.fetchone()
    if not row:
        con.close()
        return json_error("User not found. Register first.", 404)

    safe = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_") or "Unknown"
    cert_filename = f"{safe}_certificate.png"
    cert_path = os.path.join(app.config["CERT_DIR"], cert_filename)

    try:
        generate_certificate(name=name, award_title=award_title, output_path=cert_path)
    except Exception as e:
        con.close()
        return json_error(str(e), 500)

    cur.execute(
        "INSERT INTO awards(user_id, award_title, certificate_file, created_at) VALUES(?,?,?,?)",
        (row["id"], award_title, cert_filename, now_ts())
    )
    con.commit()
    con.close()

    download_url = url_for("download_cert", filename=cert_filename, _external=False)

    # Optional email send (if you enable)
    # if app.config["SMTP_ENABLED"] and row["email"]:
    #     send_email_with_attachment(row["email"], "Your Certificate", "Congrats!", cert_path)

    return jsonify({"ok": True, "certificate_file": cert_filename, "download_url": download_url})

@app.route("/download/<path:filename>")
def download_cert(filename):
    return send_from_directory(app.config["CERT_DIR"], filename, as_attachment=True)

# -------------------- Backward compatible endpoints --------------------
# Keep old endpoints used by your existing frontend (if any)
@app.route("/api/register", methods=["POST"])
def api_register_legacy():
    return api_register()

@app.route("/api/train", methods=["POST"])
def api_train_legacy():
    return api_train()

@app.route("/api/verify", methods=["POST"])
def api_verify_legacy():
    return api_verify()

@app.route("/api/award", methods=["POST"])
def api_award_legacy():
    return api_award()

# --- Initialization Block ---
# Wrap in app_context to ensure it runs even under Gunicorn (Render)
with app.app_context():
    try:
        ensure_dirs()
        init_db()
        logger.info("Application context initialization complete.")
    except Exception as init_err:
        logger.error(f"Fatal error during initialization: {init_err}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


#Favicon@app.route('/favicon.ico')
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.png'
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)