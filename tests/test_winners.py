import io
import struct
import zlib
from pathlib import Path
from werkzeug.security import generate_password_hash
from werkzeug.datastructures import FileStorage
from app import db
from app.models.admin import Admin
from app.models.winner_proof import WinnerProof


def _make_png_storage(filename="winner.png"):
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


def _login_admin(app, client):
    with app.app_context():
        admin = Admin(
            email="admin@test.com",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(admin)
        db.session.commit()
    client.post("/admin/login", data={"email": "admin@test.com", "password": "password123"})


def test_winner_publish_toggle_and_public_visibility(app, client):
    _login_admin(app, client)

    # 1. Create published winner
    resp_create = client.post(
        "/admin/winners/new",
        data={
            "title": "Season 1 Champions: Team Tiger",
            "description": "Defeated 47 teams in Bermuda final.",
            "published": "on",
            "image": _make_png_storage("tiger.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp_create.status_code == 200

    with app.app_context():
        winner = WinnerProof.query.filter_by(title="Season 1 Champions: Team Tiger").first()
        assert winner is not None
        assert winner.published is True
        winner_id = winner.id
        img_filename = winner.image_path

    # Verify public visibility on /winners and home page
    resp_pub = client.get("/winners")
    assert resp_pub.status_code == 200
    assert "Season 1 Champions: Team Tiger" in resp_pub.get_data(as_text=True)

    resp_home = client.get("/")
    assert resp_home.status_code == 200
    assert "Season 1 Champions: Team Tiger" in resp_home.get_data(as_text=True)

    # Verify image is publicly served via /media/winners/<filename>
    resp_media = client.get(f"/media/winners/{img_filename}")
    assert resp_media.status_code == 200

    # 2. Toggle unpublish
    resp_toggle = client.post(f"/admin/winners/{winner_id}/toggle-publish", follow_redirects=True)
    assert resp_toggle.status_code == 200
    with app.app_context():
        w_up = db.session.get(WinnerProof, winner_id)
        assert w_up.published is False

    # Check that unpublished winner is no longer on public pages
    resp_pub_after = client.get("/winners")
    assert "Season 1 Champions: Team Tiger" not in resp_pub_after.get_data(as_text=True)
    client.post("/admin/logout")
    assert client.get(f"/media/winners/{img_filename}").status_code == 404
    client.post(
        "/admin/login",
        data={"email": "admin@test.com", "password": "password123"},
    )

    # 3. Delete winner
    resp_del = client.post(f"/admin/winners/{winner_id}/delete", follow_redirects=True)
    assert resp_del.status_code == 200
    with app.app_context():
        assert db.session.get(WinnerProof, winner_id) is None
