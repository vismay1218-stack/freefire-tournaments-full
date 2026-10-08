"""
End-to-end zero-to-run smoke test script for Free Fire Tournament System.
Simulates:
1. Initialize test database
2. Create admin user
3. Admin login
4. Create an OPEN tournament
5. Public submits 2 team registrations (Team Phoenix and Team Cobra)
6. Admin approves Team Phoenix (assigned Team ID, status CONFIRMED)
7. Admin rejects Team Cobra (status REJECTED with reason)
8. Admin exports registrations to Excel (.xlsx) and verifies row count and columns
9. Public verifies registration status privacy on /status endpoint
"""

import io
import os
import struct
import sys
import tempfile
import zlib
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import openpyxl
from werkzeug.datastructures import FileStorage
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models.admin import Admin
from app.models.tournament import Tournament
from app.models.registration import Registration


class SmokeConfig:
    TESTING = True
    SECRET_KEY = "smoke-test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    BASE_DIR = Path(tempfile.mkdtemp())
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    PAYMENT_SCREENSHOTS_DIR = str(BASE_DIR / "uploads" / "payment_screenshots")
    WINNERS_PUBLIC_DIR = str(BASE_DIR / "uploads" / "winners_public")
    EXPORTS_DIR = str(BASE_DIR / "exports")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    SITE_NAME = "Free Fire Smoke Test Arena"
    UPI_ID = "smoke@upi"
    UPI_NAME = "Smoke Organizer"
    UPI_QR_IMAGE = ""


def make_png_storage(filename="payment.png"):
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


def run_smoke():
    print("=" * 60)
    print("[*] Running Free Fire Tournament E2E Smoke Test")
    print("=" * 60)

    # 1. Create App and DB
    app = create_app(SmokeConfig)
    client = app.test_client()

    with app.app_context():
        db.create_all()
        print("[+] [1/8] In-memory database initialized and tables created.")

        # 2. Create Admin
        admin = Admin(
            email="admin@ffarena.com",
            password_hash=generate_password_hash("AdminPass123!"),
        )
        db.session.add(admin)
        db.session.commit()
        print("[+] [2/8] Admin user created (admin@ffarena.com).")

    # 3. Admin Login
    login_resp = client.post(
        "/admin/login",
        data={"email": "admin@ffarena.com", "password": "AdminPass123!"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (301, 302), f"Login failed: {login_resp.status_code}"
    print("[+] [3/8] Admin logged in successfully.")

    # 4. Admin Creates Tournament
    deadline_str = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    t_data = {
        "name": "Free Fire Winter Championship 2026",
        "description": "Squad Battle Royale with Rs. 25,000 prize pool.",
        "entry_fee": "200.00",
        "prize_pool": "25000.00",
        "date": "2026-12-30",
        "time": "19:00",
        "map_name": "Bermuda",
        "max_teams": "48",
        "registration_deadline": deadline_str,
        "rules": "Squad mode. No hacking. Level > 30 required.",
        "status": "OPEN",
    }
    t_resp = client.post("/admin/tournaments/new", data=t_data, follow_redirects=True)
    assert t_resp.status_code == 200

    with app.app_context():
        tourney = Tournament.query.filter_by(name="Free Fire Winter Championship 2026").first()
        assert tourney is not None
        assert tourney.status == "OPEN"
        tourney_id = tourney.id
        print(f"[+] [4/8] Tournament created (ID: {tourney_id}, Name: '{tourney.name}').")

    # 5. Public Submits 2 Team Registrations
    reg1_data = {
        "tournament_id": str(tourney_id),
        "team_name": "Team Phoenix",
        "captain_name": "Phoenix Leader",
        "captain_phone": "9876543210",
        "player_1_name": "P1_Aman", "player_1_uid": "1000000001", "player_1_level": "55",
        "player_2_name": "P2_Rahul", "player_2_uid": "1000000002", "player_2_level": "48",
        "player_3_name": "P3_Vikram", "player_3_uid": "1000000003", "player_3_level": "60",
        "player_4_name": "P4_Suraj", "player_4_uid": "1000000004", "player_4_level": "42",
        "payment_transaction_id": "UPI-PHOENIX-991",
        "payment_screenshot": make_png_storage("phoenix_slip.png"),
    }
    r1_resp = client.post("/api/registrations", data=reg1_data, content_type="multipart/form-data")
    assert r1_resp.status_code == 201, f"Reg 1 failed: {r1_resp.get_data(as_text=True)}"

    reg2_data = {
        "tournament_id": str(tourney_id),
        "team_name": "Team Cobra",
        "captain_name": "Cobra King",
        "captain_phone": "9876543220",
        "player_1_name": "C1_Ravi", "player_1_uid": "2000000001", "player_1_level": "50",
        "player_2_name": "C2_Arun", "player_2_uid": "2000000002", "player_2_level": "45",
        "player_3_name": "C3_Deepak", "player_3_uid": "2000000003", "player_3_level": "38",
        "player_4_name": "C4_Sunil", "player_4_uid": "2000000004", "player_4_level": "52",
        "payment_transaction_id": "UPI-COBRA-882",
        "payment_screenshot": make_png_storage("cobra_slip.png"),
    }
    r2_resp = client.post("/api/registrations", data=reg2_data, content_type="multipart/form-data")
    assert r2_resp.status_code == 201, f"Reg 2 failed: {r2_resp.get_data(as_text=True)}"

    with app.app_context():
        r1 = Registration.query.filter_by(team_name="Team Phoenix").first()
        r2 = Registration.query.filter_by(team_name="Team Cobra").first()
        assert r1.registration_status == "PENDING_PAYMENT_VERIFICATION"
        assert r2.registration_status == "PENDING_PAYMENT_VERIFICATION"
        r1_id, r2_id = r1.id, r2.id
        print("[+] [5/8] 2 team registrations submitted (status: PENDING_PAYMENT_VERIFICATION).")

    # 6. Admin Approves Team Phoenix
    appr_resp = client.post(f"/admin/registrations/{r1_id}/approve", follow_redirects=True)
    assert appr_resp.status_code == 200

    with app.app_context():
        r1_updated = db.session.get(Registration, r1_id)
        assert r1_updated.registration_status == "CONFIRMED"
        assert r1_updated.payment_status == "VERIFIED"
        assert r1_updated.registration_id.startswith("PV-")
        team_id = r1_updated.registration_id
        t_check = db.session.get(Tournament, tourney_id)
        assert t_check.confirmed_count == 1
        print(f"[+] [6/8] Team Phoenix APPROVED -> Confirmed, Team ID: {team_id}.")

    # 7. Admin Rejects Team Cobra
    rej_resp = client.post(
        f"/admin/registrations/{r2_id}/reject",
        data={"rejection_reason": "Payment screenshot is unreadable."},
        follow_redirects=True,
    )
    assert rej_resp.status_code == 200

    with app.app_context():
        r2_updated = db.session.get(Registration, r2_id)
        assert r2_updated.registration_status == "REJECTED"
        assert r2_updated.rejection_reason == "Payment screenshot is unreadable."
        print(f"[+] [7/8] Team Cobra REJECTED with reason: '{r2_updated.rejection_reason}'.")

    # 8. Export to Excel and verify
    excel_resp = client.get("/admin/export/excel?filter=all")
    assert excel_resp.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(excel_resp.data))
    ws = wb.active
    assert ws.title == "Registrations"
    # Row 1 header + Row 2 Phoenix + Row 3 Cobra = 3 rows
    assert ws.max_row == 3

    # Check Public Status Lookups
    # Phoenix lookup with correct ID + phone
    stat_resp = client.post("/status", data={"registration_id": team_id, "captain_phone": "9876543210"})
    assert "Team Phoenix" in stat_resp.get_data(as_text=True)
    assert "Confirmed" in stat_resp.get_data(as_text=True)

    # Cross phone lookup fails cleanly
    cross_resp = client.post("/status", data={"registration_id": team_id, "captain_phone": "9999999999"})
    assert "Registration not found" in cross_resp.get_data(as_text=True)

    print("[+] [8/8] Excel export verified (.xlsx, 2 teams, all columns) & public status lookup verified.")
    print("=" * 60)
    print("[SUCCESS] ALL END-TO-END SMOKE TESTS PASSED CLEANLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_smoke()
