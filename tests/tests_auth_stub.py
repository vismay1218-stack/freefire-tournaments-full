from werkzeug.security import check_password_hash
from app.models.admin import Admin
from app import db


def test_create_admin_cli_inserts_row_with_hash(app, runner):
    email = "admin@example.com"
    password = "SecurePass123!"

    result = runner.invoke(args=["create-admin", email, password])
    assert result.exit_code == 0
    assert f"Admin {email} created." in result.output

    with app.app_context():
        admin = Admin.query.filter_by(email=email).first()
        assert admin is not None
        assert admin.email == email
        assert admin.password_hash != password
        assert admin.password_hash is not None
        assert len(admin.password_hash) > 0
        assert check_password_hash(admin.password_hash, password) is True
        assert check_password_hash(admin.password_hash, "WrongPass") is False


def test_create_admin_cli_duplicate_email(app, runner):
    email = "dup@example.com"
    password = "pass1"

    result1 = runner.invoke(args=["create-admin", email, password])
    assert result1.exit_code == 0
    assert f"Admin {email} created." in result1.output

    result2 = runner.invoke(args=["create-admin", email, "pass2"])
    assert result2.exit_code == 0
    assert f"Admin with email {email} already exists." in result2.output

    with app.app_context():
        count = Admin.query.filter_by(email=email).count()
        assert count == 1
