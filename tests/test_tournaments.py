from datetime import datetime, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash
from app import db
from app.models.admin import Admin
from app.models.tournament import Tournament


def _login_admin(app, client):
    with app.app_context():
        admin = Admin(
            email="admin@test.com",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(admin)
        db.session.commit()
    client.post("/admin/login", data={"email": "admin@test.com", "password": "password123"})


def test_admin_tournament_crud(app, client):
    _login_admin(app, client)

    # 1. Create Tournament
    deadline_str = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
    form_data = {
        "name": "Championship Series 2026",
        "description": "Grand Free Fire Battle",
        "entry_fee": "150.00",
        "prize_pool": "15000.00",
        "date": "2026-11-20",
        "time": "18:00",
        "map_name": "Purgatory",
        "max_teams": "24",
        "registration_deadline": deadline_str,
        "rules": "Squad only. No emulators.",
        "status": "OPEN",
    }
    resp = client.post("/admin/tournaments/new", data=form_data, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        t = Tournament.query.filter_by(name="Championship Series 2026").first()
        assert t is not None
        assert t.status == "OPEN"
        assert t.max_teams == 24
        assert t.entry_fee == Decimal("150.00")
        t_id = t.id

    # 2. View Tournament in Admin
    resp_view = client.get(f"/admin/tournaments/{t_id}")
    assert resp_view.status_code == 200
    assert "Championship Series 2026" in resp_view.get_data(as_text=True)

    # 3. Edit Tournament
    edit_data = dict(form_data)
    edit_data["name"] = "Championship Series 2026 (Updated)"
    edit_data["status"] = "CLOSED"
    resp_edit = client.post(f"/admin/tournaments/{t_id}/edit", data=edit_data, follow_redirects=True)
    assert resp_edit.status_code == 200

    with app.app_context():
        t = db.session.get(Tournament, t_id)
        assert t.name == "Championship Series 2026 (Updated)"
        assert t.status == "CLOSED"

    # 4. Delete Tournament
    resp_del = client.post(f"/admin/tournaments/{t_id}/delete", follow_redirects=True)
    assert resp_del.status_code == 200
    with app.app_context():
        t = db.session.get(Tournament, t_id)
        assert t is None


def test_tournament_open_vs_closed_and_deadline(app, client):
    with app.app_context():
        # Open tournament in future
        t_open = Tournament(
            name="Open Tournament",
            description="desc",
            entry_fee=Decimal("50.00"),
            prize_pool=Decimal("5000.00"),
            date="2026-12-01",
            time="19:00",
            map_name="Bermuda",
            max_teams=16,
            registration_deadline=datetime.utcnow() + timedelta(days=10),
            rules="Fair play",
            status="OPEN",
        )
        # Closed tournament
        t_closed = Tournament(
            name="Closed Tournament",
            description="desc",
            entry_fee=Decimal("50.00"),
            prize_pool=Decimal("5000.00"),
            date="2026-12-01",
            time="19:00",
            map_name="Bermuda",
            max_teams=16,
            registration_deadline=datetime.utcnow() + timedelta(days=10),
            rules="Fair play",
            status="CLOSED",
        )
        # Open tournament but past deadline
        t_expired = Tournament(
            name="Expired Tournament",
            description="desc",
            entry_fee=Decimal("50.00"),
            prize_pool=Decimal("5000.00"),
            date="2026-09-01",
            time="19:00",
            map_name="Bermuda",
            max_teams=16,
            registration_deadline=datetime.utcnow() - timedelta(days=2),
            rules="Fair play",
            status="OPEN",
        )
        db.session.add_all([t_open, t_closed, t_expired])
        db.session.commit()
        open_id = t_open.id
        closed_id = t_closed.id
        expired_id = t_expired.id

    # Open tournament detail shows REGISTER NOW
    resp_open = client.get(f"/tournaments/{open_id}")
    assert resp_open.status_code == 200
    assert "REGISTER NOW" in resp_open.get_data(as_text=True)

    # Closed tournament detail shows REGISTRATION CLOSED
    resp_closed = client.get(f"/tournaments/{closed_id}")
    assert resp_closed.status_code == 200
    assert "REGISTRATION CLOSED" in resp_closed.get_data(as_text=True)

    # Expired tournament detail shows REGISTRATION CLOSED
    resp_expired = client.get(f"/tournaments/{expired_id}")
    assert resp_expired.status_code == 200
    assert "REGISTRATION CLOSED" in resp_expired.get_data(as_text=True)
