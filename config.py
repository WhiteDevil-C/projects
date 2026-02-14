import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_change_me")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    FACES_DIR = os.path.join(DATA_DIR, "faces")
    DB_PATH = os.path.join(DATA_DIR, "app.db")

    MODELS_DIR = os.path.join(BASE_DIR, "models")
    MODEL_PATH = os.path.join(MODELS_DIR, "lbph_model.xml")
    LABEL_MAP_PATH = os.path.join(MODELS_DIR, "label_map.json")

    CERT_DIR = os.path.join(BASE_DIR, "certificates")

    # Email optional
    SMTP_ENABLED = os.environ.get("SMTP_ENABLED", "0") == "1"
