from datetime import datetime, timedelta
from decimal import Decimal
from app import db
from app.models.tournament import Tournament
from app.models.registration import Registration


def test_status_privacy_and_lookup(app, client):
    with app.app_context():
        t = Tournament(
            name="Privacy Cup",
            description="desc",
            entry_fee=Decimal("100.00"),
            prize_pool=Decimal("1000.00"),
            date="2026-12-25",
            time="20:00",
            map_name="Bermuda",
            max_teams=16,
            registration_deadline=datetime.utcnow() + timedelta(days=7),
            rules="Fair play",
            status="OPEN",
        )
        db.session.add(t)
        db.session.flush()

        r1 = Registration(
            tournament_id=t.id,
            registration_id="PV-1001",
            team_name="Alpha Warriors",
            captain_name="Alpha Cap",
            captain_phone="9876543210",
            payment_transaction_id="TXN1",
            registration_status="CONFIRMED",
            confirmation_date=datetime.utcnow(),
        )
        r2 = Registration(
            tournament_id=t.id,
            registration_id="PV-1002",
            team_name="Beta Legends",
            captain_name="Beta Cap",
            captain_phone="9876543220",
            payment_transaction_id="TXN2",
            registration_status="REJECTED",
            rejection_reason="Duplicate screenshot submitted.",
        )
        db.session.add_all([r1, r2])
        db.session.commit()

    # 1. Correct R1 id + correct R1 phone -> shows R1 details
    resp_r1 = client.post("/status", data={
        "registration_id": "PV-1001",
        "captain_phone": "9876543210",
    })
    assert resp_r1.status_code == 200
    html_r1 = resp_r1.get_data(as_text=True)
    assert "Alpha Warriors" in html_r1
    assert "Confirmed" in html_r1
    assert "Beta Legends" not in html_r1

    # 2. R1 id + R2 phone -> Not found (no cross-team leak)
    resp_cross = client.post("/status", data={
        "registration_id": "PV-1001",
        "captain_phone": "9876543220",
    })
    assert resp_cross.status_code == 200
    html_cross = resp_cross.get_data(as_text=True)
    assert "Registration not found" in html_cross
    assert "Alpha Warriors" not in html_cross
    assert "Beta Legends" not in html_cross

    # 3. R2 id + R1 phone -> Not found
    resp_cross2 = client.post("/status", data={
        "registration_id": "PV-1002",
        "captain_phone": "9876543210",
    })
    assert resp_cross2.status_code == 200
    html_cross2 = resp_cross2.get_data(as_text=True)
    assert "Registration not found" in html_cross2
    assert "Beta Legends" not in html_cross2

    # 4. Correct R2 id + correct R2 phone -> shows REJECTED status + reason
    resp_r2 = client.post("/status", data={
        "registration_id": "PV-1002",
        "captain_phone": "9876543220",
    })
    assert resp_r2.status_code == 200
    html_r2 = resp_r2.get_data(as_text=True)
    assert "Beta Legends" in html_r2
    assert "Rejected" in html_r2
    assert "Duplicate screenshot submitted." in html_r2
