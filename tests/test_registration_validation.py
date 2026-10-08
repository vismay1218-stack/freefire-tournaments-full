import io
import struct
import zlib
from datetime import datetime, timedelta
from decimal import Decimal
from werkzeug.datastructures import FileStorage
from app import db
from app.models.tournament import Tournament
from app.models.registration import Registration


def _make_png_storage(filename="payment.png"):
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


def _seed_open_tournament(app):
    with app.app_context():
        t = Tournament(
            name="Apex Cup",
            description="desc",
            entry_fee=Decimal("100.00"),
            prize_pool=Decimal("10000.00"),
            date="2026-12-25",
            time="20:00",
            map_name="Bermuda",
            max_teams=48,
            registration_deadline=datetime.utcnow() + timedelta(days=7),
            rules="Fair play",
            status="OPEN",
        )
        db.session.add(t)
        db.session.commit()
        return t.id


def _base_valid_data(t_id):
    data = {
        "tournament_id": str(t_id),
        "team_name": "Phoenix Squad",
        "captain_name": "Phoenix Captain",
        "captain_phone": "9876543210",
        "player_1_name": "P1",
        "player_1_uid": "1234567890",
        "player_1_level": "45",
        "player_2_name": "P2",
        "player_2_uid": "1234567891",
        "player_2_level": "50",
        "player_3_name": "P3",
        "player_3_uid": "1234567892",
        "player_3_level": "35",
        "player_4_name": "P4",
        "player_4_uid": "1234567893",
        "player_4_level": "40",
        "payment_transaction_id": "UPI123456789",
        "payment_screenshot": _make_png_storage(),
    }
    return data


def test_validation_invalid_phone(app, client):
    t_id = _seed_open_tournament(app)
    data = _base_valid_data(t_id)
    data["captain_phone"] = "1234567890"  # Starts with 1 instead of [6-9]
    resp = client.post("/api/registrations", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    json_data = resp.get_json()
    assert json_data["ok"] is False
    assert "Phone number must contain exactly 10 digits." in json_data["errors"]["captain_phone"]


def test_validation_invalid_player_level(app, client):
    t_id = _seed_open_tournament(app)
    data = _base_valid_data(t_id)
    data["player_2_level"] = "28"  # Must be > 30
    resp = client.post("/api/registrations", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    json_data = resp.get_json()
    assert json_data["ok"] is False
    assert "Player 2 level must be more than 30. Current level: 28." in json_data["errors"]["player_2_level"]


def test_validation_invalid_player_uid(app, client):
    t_id = _seed_open_tournament(app)
    data = _base_valid_data(t_id)
    data["player_3_uid"] = "invalid_uid_abc"
    resp = client.post("/api/registrations", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    json_data = resp.get_json()
    assert json_data["ok"] is False
    assert "Player 3 UID is invalid. Please enter a valid Free Fire UID." in json_data["errors"]["player_3_uid"]


def test_validation_missing_transaction_id(app, client):
    t_id = _seed_open_tournament(app)
    data = _base_valid_data(t_id)
    data["payment_transaction_id"] = ""
    resp = client.post("/api/registrations", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    json_data = resp.get_json()
    assert json_data["ok"] is False
    assert "Please enter your payment transaction ID." in json_data["errors"]["payment_transaction_id"]


def test_validation_missing_screenshot(app, client):
    t_id = _seed_open_tournament(app)
    data = _base_valid_data(t_id)
    del data["payment_screenshot"]
    resp = client.post("/api/registrations", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    json_data = resp.get_json()
    assert json_data["ok"] is False
    assert "Please upload your payment screenshot." in json_data["errors"]["payment_screenshot"]


def test_validation_duplicate_team_name(app, client):
    t_id = _seed_open_tournament(app)
    data1 = _base_valid_data(t_id)
    resp1 = client.post("/api/registrations", data=data1, content_type="multipart/form-data")
    assert resp1.status_code == 201

    # Second submission with same team name for same tournament
    data2 = _base_valid_data(t_id)
    data2["payment_screenshot"] = _make_png_storage("screenshot2.png")
    resp2 = client.post("/api/registrations", data=data2, content_type="multipart/form-data")
    assert resp2.status_code == 400
    json_data = resp2.get_json()
    assert json_data["ok"] is False
    assert "Team name is already registered for this tournament." in json_data["errors"]["team_name"]
