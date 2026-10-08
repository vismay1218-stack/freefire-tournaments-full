import os
from datetime import timedelta
from pathlib import Path


class Config:
    BASE_DIR = Path(__file__).resolve().parent

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'freefire_tournament.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-change-me"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV", "development") == "production"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "10485760"))

    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads")
    PAYMENT_SCREENSHOTS_DIR = UPLOAD_FOLDER / "payment_screenshots"
    WINNERS_PUBLIC_DIR = UPLOAD_FOLDER / "winners_public"
    EXPORTS_DIR = BASE_DIR / "exports"
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_PAYMENT_BUCKET = os.getenv("SUPABASE_PAYMENT_BUCKET", "payment-screenshots")
    SUPABASE_WINNERS_BUCKET = os.getenv("SUPABASE_WINNERS_BUCKET", "winner-images")

    SITE_NAME = os.getenv("SITE_NAME", "Free Fire Tournaments")
    # Leave empty to use the built-in static QR at /static/images/upi_qr.jpeg
    UPI_QR_IMAGE = os.getenv("UPI_QR_IMAGE", "")
    UPI_ID = os.getenv("UPI_ID", "8660267306@axl")
    UPI_NAME = os.getenv("UPI_NAME", "VISMAY CM")

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

    RATELIMIT_DEFAULT = "200 per minute"
    RATELIMIT_STORAGE_URI = "memory://"
