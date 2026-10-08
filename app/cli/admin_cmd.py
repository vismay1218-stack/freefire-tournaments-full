def register_admin_cmd(app):
    import click
    from werkzeug.security import generate_password_hash
    from app.models.admin import Admin
    from app import db

    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("password")
    def create_admin(email, password):
        with app.app_context():
            exists = Admin.query.filter_by(email=email).first()
            if exists:
                click.echo(f"Admin with email {email} already exists.")
                return
            admin = Admin(
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(admin)
            db.session.commit()
            click.echo(f"Admin {email} created.")
