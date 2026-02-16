import os
import sqlite3
import time
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for

from config import Config
from src.register_face import register_face
from src.train_model import train_model
from src.verify_face import verify_face
from src.generate_certificate import generate_certificate
# from src.send_email import send_email_with_attachment  # optional

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
    con = db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS awards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            award_title TEXT NOT NULL,
            certificate_file TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    con.commit()
    con.close()

def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status

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
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()

    if not name:
        return json_error("Name is required")

    # Store user (upsert-like)
    con = db()
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO users(name, email, created_at) VALUES(?,?,?)",
                (name, email, now_ts()))
    if email:
        cur.execute("UPDATE users SET email=? WHERE name=?", (email, name))
    con.commit()

    # Ensure face folder
    user_dir = os.path.join(app.config["FACES_DIR"], name)
    os.makedirs(user_dir, exist_ok=True)

    con.close()

    # Camera capture (local machine)
    try:
        captured = register_face(name=name, save_dir=user_dir, num_samples=int(data.get("num_samples") or 25))
    except Exception as e:
        return json_error(str(e), 500)

    return jsonify({"ok": True, "name": name, "email": email, "captured": captured})

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

if __name__ == "__main__":
    ensure_dirs()
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)


#Favicon@app.route('/favicon.ico')
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.png'
    )
