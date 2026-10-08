import os
import tempfile
from pathlib import Path

import pytest

from app import create_app, db


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"
    BASE_DIR = Path(tempfile.mkdtemp())
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    PAYMENT_SCREENSHOTS_DIR = str(BASE_DIR / "uploads" / "payment_screenshots")
    WINNERS_PUBLIC_DIR = str(BASE_DIR / "uploads" / "winners_public")
    EXPORTS_DIR = str(BASE_DIR / "exports")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    SITE_NAME = "Test Tournaments"
    UPI_ID = "test@upi"
    UPI_NAME = "Test Organizer"
    UPI_QR_IMAGE = ""


@pytest.fixture()
def app():
    Path(TestConfig.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(TestConfig.PAYMENT_SCREENSHOTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(TestConfig.WINNERS_PUBLIC_DIR).mkdir(parents=True, exist_ok=True)
    Path(TestConfig.EXPORTS_DIR).mkdir(parents=True, exist_ok=True)
    a = create_app(TestConfig)
    with a.app_context():
        db.create_all()
        yield a
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
