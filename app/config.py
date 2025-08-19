import os

def _get_env(key, default=None):
    return os.getenv(key, default)

class Config:
    SECRET_KEY = _get_env("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = _get_env("DATABASE_URL", "sqlite:///fintrack.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = _get_env("UPLOAD_FOLDER", "app/uploads")
    MAX_CONTENT_LENGTH = int(float(_get_env("MAX_UPLOAD_MB", "10")) * 1024 * 1024)

    ALLOWED_EXTENSIONS = set((_get_env("ALLOWED_EXTENSIONS", "jpg,jpeg,png,pdf")).split(","))
