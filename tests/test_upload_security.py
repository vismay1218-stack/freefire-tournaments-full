import io
import struct
import zlib
from pathlib import Path
from werkzeug.security import generate_password_hash
from werkzeug.datastructures import FileStorage
from app import db
from app.models.admin import Admin
from app.services.upload_service import (
    validate_image,
    save_payment_screenshot,
    save_winner_image,
    load_stored_image,
)


def _make_png_storage(filename="test.png"):
    def chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\x00\x00\x00"
    idat = zlib.compress(raw)
    png_bytes = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    return FileStorage(
        stream=io.BytesIO(png_bytes),
        filename=filename,
        content_type="image/png",
    )


def test_upload_valid_image_and_uuid_naming(app):
    file_storage = _make_png_storage("original_user_photo.png")
    filename, errors = save_payment_screenshot(file_storage, app.config)
    assert not errors
    assert filename is not None
    assert filename != "original_user_photo.png"
    assert filename.endswith(".png")

    saved_path = Path(app.config["PAYMENT_SCREENSHOTS_DIR"]) / filename
    assert saved_path.is_file()
    assert not (Path(app.config["PAYMENT_SCREENSHOTS_DIR"]) / "original_user_photo.png").exists()


def test_upload_disallowed_extension(app):
    fake_exe = FileStorage(
        stream=io.BytesIO(b"binary content"),
        filename="malware.exe",
        content_type="application/octet-stream",
    )
    errors, ext = validate_image(fake_exe)
    assert len(errors) > 0
    assert "Invalid file type" in errors[0]


def test_upload_fake_image_fails_pillow_verification(app):
    fake_png = FileStorage(
        stream=io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00not a valid image"),
        filename="disguised.png",
        content_type="image/png",
    )
    errors, ext = validate_image(fake_png)
    assert len(errors) > 0
    assert "corrupted or not a real image" in errors[0]


def test_upload_exceeds_size_limit(app):
    file_storage = _make_png_storage()
    # Test with very small limit (10 bytes)
    errors, ext = validate_image(file_storage, max_size_bytes=10)
    assert len(errors) > 0
    assert "too large" in errors[0]


def test_payment_screenshot_auth_protection(app, client):
    # Save a screenshot
    file_storage = _make_png_storage("secret_slip.png")
    filename, errors = save_payment_screenshot(file_storage, app.config)
    assert not errors

    # 1. Unauthenticated request -> should be redirected to login
    resp_anon = client.get(f"/api/admin/screenshots/{filename}", follow_redirects=False)
    assert resp_anon.status_code in (301, 302, 401)
    if resp_anon.status_code in (301, 302):
        assert "/admin/login" in resp_anon.headers["Location"]

    # 2. Authenticated request -> 200 OK with image data
    with app.app_context():
        admin = Admin(
            email="admin@test.com",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(admin)
        db.session.commit()
    client.post("/admin/login", data={"email": "admin@test.com", "password": "password123"})

    resp_auth = client.get(f"/api/admin/screenshots/{filename}")
    assert resp_auth.status_code == 200
    assert resp_auth.data.startswith(b"\x89PNG")

    # 3. Directory traversal attempt
    resp_traversal = client.get("/api/admin/screenshots/../config.py")
    assert resp_traversal.status_code in (400, 404)


def test_remote_screenshot_load_uses_private_storage_service_key(app, monkeypatch):
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"private image bytes"

    def fake_urlopen(request, timeout):
        requests.append(request)
        assert timeout == 30
        return FakeResponse()

    monkeypatch.setattr("app.services.upload_service.urlopen", fake_urlopen)
    config = {
        "SUPABASE_URL": "https://storage.example.test",
        "SUPABASE_SERVICE_ROLE_KEY": "server-only-test-key",
        "SUPABASE_PAYMENT_BUCKET": "payment-screenshots",
    }

    image = load_stored_image(
        "payment-proof.png", config, purpose="payment"
    )

    assert image == b"private image bytes"
    assert requests[0].full_url == (
        "https://storage.example.test/storage/v1/object/"
        "payment-screenshots/payment-proof.png"
    )
    assert requests[0].get_header("Authorization") == "Bearer server-only-test-key"
