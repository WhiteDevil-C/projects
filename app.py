from flask import Flask, render_template, request
import os
import json
import sys
import subprocess

# Your python exe inside conda env (correct)
PY = sys.executable

app = Flask(__name__)

# -----------------------------
# Helpers: users.json (name -> email)
# -----------------------------
USERS_FILE = os.path.join("data", "users.json")

def load_users():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users: dict):
    os.makedirs("data", exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

# -----------------------------
# Helpers: quick result (verify_once)
# logs/last_once_result.txt => "name|confidence|time"
# -----------------------------
def read_quick_result():
    try:
        with open("logs/last_once_result.txt", "r", encoding="utf-8") as f:
            line = f.readline().strip()
        name, conf, t = line.split("|", 2)
        return name, float(conf), t
    except:
        return "Unknown", 999.0, "-"

def run_script(script_path: str):
    """Runs a python script using the same conda env python."""
    subprocess.run([PY, script_path], check=False)

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()

    if not username:
        return "Name is required. <a href='/'>Go Back</a>"
    if not email:
        return "Email is required. <a href='/'>Go Back</a>"

    # Save email to users.json
    users = load_users()
    users[username] = email
    save_users(users)

    # Write temp name (used by register_face.py)
    os.makedirs("logs", exist_ok=True)
    with open("logs/temp_name.txt", "w", encoding="utf-8") as f:
        f.write(username)

    user_folder = os.path.join("data", "faces", username)

    # If folder exists, prevent wrong naming using quick verify
    if os.path.isdir(user_folder):
        run_script(os.path.join("src", "verify_once.py"))
        pred, conf, _ = read_quick_result()

        if pred == username:
            return f"✅ You are already registered as {username}. <a href='/'>Go Back</a>"

        if pred != "Unknown" and pred != username:
            return f"❌ This face already exists as '{pred}'. Use that name. <a href='/'>Go Back</a>"

        # Unknown with existing folder => allow adding more images
        run_script(os.path.join("src", "register_face.py"))
        run_script(os.path.join("src", "train_model.py"))
        return f"✅ Added more images for {username} and retrained. <a href='/'>Go Back</a>"

    # New user
    run_script(os.path.join("src", "register_face.py"))
    run_script(os.path.join("src", "train_model.py"))
    return f"✅ Registered {username} and trained model. <a href='/'>Go Back</a>"

@app.route("/train", methods=["POST"])
def train():
    run_script(os.path.join("src", "train_model.py"))
    return "✅ Model trained. <a href='/'>Go Back</a>"

@app.route("/verify", methods=["POST"])
def verify():
    # Run verification camera
    run_script(os.path.join("src", "verify_face.py"))

    # Read result written by verify_face.py
    try:
        with open("logs/last_result.json", "r", encoding="utf-8") as f:
            result = json.load(f)
    except:
        result = {"name": "Unknown", "status": "AWARD DENIED", "confidence": 999.0, "time": "-"}

    # If unknown => ask user to enter name+email
    if result.get("name") == "Unknown":
        return render_template("ask_name.html")

    # If verified => generate certificate + email it
    if result.get("status") == "AWARD GRANTED":
        name = result.get("name")

        # Generate certificate
        from src.generate_certificate import generate_certificate
        cert_path = generate_certificate(name)

        # Send email if user exists
        users = load_users()
        to_email = users.get(name)

        if to_email:
            from src.send_email import send_email_with_attachment
            send_email_with_attachment(
                to_email=to_email,
                subject="🎉 Face Award Certificate",
                body="Congratulations! Your face matched successfully ✅\nCertificate attached.",
                attachment_path=cert_path
            )

        # Show result page
        return render_template("result.html", result=result, email=to_email, cert_path=cert_path)

    # Award denied
    return render_template("result.html", result=result, email=None, cert_path=None)

@app.route("/register_unknown", methods=["POST"])
def register_unknown():
    # User typed name+email after unknown verification
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()

    if not username:
        return "Name is required. <a href='/'>Go Back</a>"
    if not email:
        return "Email is required. <a href='/'>Go Back</a>"

    # Save user email
    users = load_users()
    users[username] = email
    save_users(users)

    # Save temp name for register_face.py
    os.makedirs("logs", exist_ok=True)
    with open("logs/temp_name.txt", "w", encoding="utf-8") as f:
        f.write(username)

    # Prevent wrong naming: quick verify
    run_script(os.path.join("src", "verify_once.py"))
    pred, conf, _ = read_quick_result()

    if pred != "Unknown" and pred != username:
        return f"❌ Your face already exists as '{pred}'. Please use that name. <a href='/'>Go Back</a>"

    # Register + train
    run_script(os.path.join("src", "register_face.py"))
    run_script(os.path.join("src", "train_model.py"))

    return f"✅ Registered {username}. Now click Verify again. <a href='/'>Go Back</a>"

if __name__ == "__main__":
    app.run(debug=True)
