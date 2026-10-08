import io
import struct
import zlib
from datetime import datetime, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash
from werkzeug.datastructures import FileStorage
from app import db
from app.models.admin import Admin
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


def _login_admin(app, client):
    with app.app_context():
        admin = Admin(
            email="admin@test.com",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(admin)
        db.session.commit()
    client.post("/admin/login", data={"email": "admin@test.com", "password": "password123"})


def test_registration_flow_create_pending_does_not_consume_capacity(app, client):
    with app.app_context():
        t = Tournament(
            name="Small Cup",
            description="2 teams max",
            entry_fee=Decimal("100.00"),
            prize_pool=Decimal("1000.00"),
            date="2026-12-25",
            time="20:00",
            map_name="Bermuda",
            max_teams=2,
            registration_deadline=datetime.utcnow() + timedelta(days=7),
            rules="Fair play",
            status="OPEN",
        )
        db.session.add(t)
        db.session.commit()
        t_id = t.id

    # Register team 1
    resp1 = client.post("/api/registrations", data={
        "tournament_id": str(t_id),
        "team_name": "Team One",
        "captain_name": "Captain 1",
        "captain_phone": "9876543210",
        "player_1_name": "P1", "player_1_uid": "1234567890", "player_1_level": "40",
        "player_2_name": "P2", "player_2_uid": "1234567891", "player_2_level": "40",
        "player_3_name": "P3", "player_3_uid": "1234567892", "player_3_level": "40",
        "player_4_name": "P4", "player_4_uid": "1234567893", "player_4_level": "40",
        "payment_transaction_id": "TXN001",
        "payment_screenshot": _make_png_storage("s1.png"),
    }, content_type="multipart/form-data")
    assert resp1.status_code == 201

    with app.app_context():
        t = db.session.get(Tournament, t_id)
        assert t.confirmed_count == 0
        r1 = Registration.query.filter_by(team_name="Team One").first()
        assert r1.registration_status == "PENDING_PAYMENT_VERIFICATION"
        assert r1.payment_status == "PAID_PENDING"


def test_registration_approve_and_capacity_limit(app, client):
    _login_admin(app, client)

    with app.app_context():
        t = Tournament(
            name="Limited Cup",
            description="2 teams max",
            entry_fee=Decimal("100.00"),
            prize_pool=Decimal("1000.00"),
            date="2026-12-25",
            time="20:00",
            map_name="Bermuda",
            max_teams=2,
            registration_deadline=datetime.utcnow() + timedelta(days=7),
            rules="Fair play",
            status="OPEN",
        )
        db.session.add(t)
        db.session.commit()
        t_id = t.id

    # Create 3 pending registrations
    for i in (1, 2, 3):
        resp = client.post("/api/registrations", data={
            "tournament_id": str(t_id),
            "team_name": f"Team {i}",
            "captain_name": f"Cap {i}",
            "captain_phone": f"987654321{i}",
            "player_1_name": "P1", "player_1_uid": f"123456789{i}", "player_1_level": "40",
            "player_2_name": "P2", "player_2_uid": f"223456789{i}", "player_2_level": "40",
            "player_3_name": "P3", "player_3_uid": f"323456789{i}", "player_3_level": "40",
            "player_4_name": "P4", "player_4_uid": f"423456789{i}", "player_4_level": "40",
            "payment_transaction_id": f"TXN00{i}",
            "payment_screenshot": _make_png_storage(f"s{i}.png"),
        }, content_type="multipart/form-data")
        assert resp.status_code == 201

    with app.app_context():
        r1 = Registration.query.filter_by(team_name="Team 1").first()
        r2 = Registration.query.filter_by(team_name="Team 2").first()
        r3 = Registration.query.filter_by(team_name="Team 3").first()
        r1_id, r2_id, r3_id = r1.id, r2.id, r3.id

    # 1. Approve Team 1
    resp_app1 = client.post(f"/admin/registrations/{r1_id}/approve", follow_redirects=True)
    assert resp_app1.status_code == 200
    with app.app_context():
        r1 = db.session.get(Registration, r1_id)
        assert r1.registration_status == "CONFIRMED"
        assert r1.payment_status == "VERIFIED"
        assert r1.registration_id.startswith("PV-")
        assert r1.confirmation_date is not None
        t = db.session.get(Tournament, t_id)
        assert t.confirmed_count == 1

    # 2. Approve Team 2 (reaches max_teams=2)
    resp_app2 = client.post(f"/admin/registrations/{r2_id}/approve", follow_redirects=True)
    assert resp_app2.status_code == 200
    with app.app_context():
        t = db.session.get(Tournament, t_id)
        assert t.confirmed_count == 2

    # 3. Attempt to approve Team 3 (should fail due to capacity)
    resp_app3 = client.post(f"/admin/registrations/{r3_id}/approve", follow_redirects=True)
    assert resp_app3.status_code == 200
    assert "already full" in resp_app3.get_data(as_text=True)
    with app.app_context():
        r3 = db.session.get(Registration, r3_id)
        assert r3.registration_status == "PENDING_PAYMENT_VERIFICATION"
        t = db.session.get(Tournament, t_id)
        assert t.confirmed_count == 2


def test_registration_reject_stores_reason(app, client):
    _login_admin(app, client)

    with app.app_context():
        t = Tournament(
            name="Reject Cup",
            description="desc",
            entry_fee=Decimal("100.00"),
            prize_pool=Decimal("1000.00"),
            date="2026-12-25",
            time="20:00",
            map_name="Bermuda",
            max_teams=8,
            registration_deadline=datetime.utcnow() + timedelta(days=7),
            rules="rules",
            status="OPEN",
        )
        db.session.add(t)
        db.session.commit()
        t_id = t.id

    client.post("/api/registrations", data={
        "tournament_id": str(t_id),
        "team_name": "Team To Reject",
        "captain_name": "Cap",
        "captain_phone": "9876543299",
        "player_1_name": "P1", "player_1_uid": "1234567890", "player_1_level": "40",
        "player_2_name": "P2", "player_2_uid": "1234567891", "player_2_level": "40",
        "player_3_name": "P3", "player_3_uid": "1234567892", "player_3_level": "40",
        "player_4_name": "P4", "player_4_uid": "1234567893", "player_4_level": "40",
        "payment_transaction_id": "BADTXN",
        "payment_screenshot": _make_png_storage("bad.png"),
    }, content_type="multipart/form-data")

    with app.app_context():
        reg = Registration.query.filter_by(team_name="Team To Reject").first()
        reg_id = reg.id

    # Reject with specific reason
    resp_rej = client.post(
        f"/admin/registrations/{reg_id}/reject",
        data={"rejection_reason": "Payment could not be verified."},
        follow_redirects=True,
    )
    assert resp_rej.status_code == 200

    with app.app_context():
        reg = db.session.get(Registration, reg_id)
        assert reg.registration_status == "REJECTED"
        assert reg.payment_status == "FAILED"
        assert reg.rejection_reason == "Payment could not be verified."
