from werkzeug.security import generate_password_hash
from app import db
from app.models.admin import Admin


def _create_admin(app, email="admin@test.com", password="Passw0rd!Secure"):
    with app.app_context():
        admin = Admin(
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(admin)
        db.session.commit()
    return email, password


def test_admin_login_success(app, client):
    email, password = _create_admin(app)
    resp = client.post(
        "/admin/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302)
    assert "/admin/dashboard" in resp.headers["Location"]

    # Access dashboard while authenticated
    dash_resp = client.get("/admin/dashboard")
    assert dash_resp.status_code == 200
    html = dash_resp.get_data(as_text=True)
    assert "Dashboard" in html
    assert 'href="/admin/tournaments"' in html
    assert "Manage Tournaments" in html


def test_admin_login_failure_wrong_password(app, client):
    email, _ = _create_admin(app)
    resp = client.post(
        "/admin/login",
        data={"email": email, "password": "WrongPassword123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Invalid email or password." in html


def test_admin_login_failure_unknown_email(app, client):
    _create_admin(app)
    resp = client.post(
        "/admin/login",
        data={"email": "nobody@test.com", "password": "AnyPassword"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Invalid email or password." in html


def test_admin_unauthorized_access(app, client):
    resp = client.get("/admin/dashboard", follow_redirects=False)
    assert resp.status_code in (301, 302)
    assert "/admin/login" in resp.headers["Location"]

    api_resp = client.get("/api/admin/me")
    assert api_resp.status_code == 401


def test_admin_logout(app, client):
    email, password = _create_admin(app)
    client.post("/admin/login", data={"email": email, "password": password})
    dash_resp = client.get("/admin/dashboard")
    assert dash_resp.status_code == 200

    logout_resp = client.post("/admin/logout", follow_redirects=False)
    assert logout_resp.status_code in (301, 302)
    assert "/admin/login" in logout_resp.headers["Location"]

    subsequent_resp = client.get("/admin/dashboard", follow_redirects=False)
    assert subsequent_resp.status_code in (301, 302)
